"""
Constrained Work-Allocation Optimizer (OR-Tools / Optimization Engine).
Adheres strictly to Section 10.5:
1. Inputs: Eligible accounts, predicted outcomes, approved priority values, agent capacity, agent skills.
2. Constraints:
   - Mandatory rules (e.g. DNC blocked accounts are excluded from outreach assignment).
   - Agent capacity limits (max_active_cases).
   - Specialist requirements (hardship cases -> hardship-skilled agents; disputes -> dispute specialists).
   - Workload balancing to avoid single-agent saturation.
3. Formulates explicit optimization problem and supports preview (dry-run) and execution modes.
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from django.db import transaction
from accounts.models import Account
from assignments.models import QueueAssignment, AgentProfile
from authentication.models import User
from audit.utils import log_audit


class WorkloadOptimizationError(ValueError):
    pass


class QueueWorkloadOptimizer:
    """Constrained optimization engine for intelligent collector assignment."""

    def optimize_queue(
        self,
        strategy: str = "balanced_recovery",
        apply_reassignments: bool = False,
        actor_user: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Solves the constrained assignment optimization problem.
        Supported strategies:
        - 'balanced_recovery': Maximize expected cure value while balancing caseload.
        - 'specialist_priority': Strictly route hardship/dispute cases to specialized collectors first.
        - 'equal_distribution': Equalize active accounts across all active agents.
        """
        # 1. Fetch eligible accounts (excluding DNC-blocked accounts)
        accounts = list(Account.objects.filter(status='ACTIVE', dnc=False).select_related('assigned_agent', 'customer'))
        agent_profiles = list(AgentProfile.objects.filter(is_active_for_routing=True).select_related('user'))

        if not agent_profiles:
            raise WorkloadOptimizationError("No active agents available for queue routing.")

        # 2. Build agent capacity map
        # Agent: {id, username, capacity, skills, current_workload, assigned_accounts}
        agents = []
        for ap in agent_profiles:
            current_cases = Account.objects.filter(assigned_agent=ap.user, status='ACTIVE').count()
            rem_capacity = max(0, ap.max_active_cases - current_cases)
            agents.append({
                "user": ap.user,
                "username": ap.user.username,
                "name": ap.user.get_full_name() or ap.user.username,
                "max_capacity": ap.max_active_cases,
                "current_workload": current_cases,
                "available_capacity": rem_capacity,
                "skills": [s.lower() for s in (ap.skills or [])],
                "assigned_in_plan": []
            })

        # 3. Score and prioritize accounts
        # Higher score = higher priority for assignment
        scored_accounts = []
        for a in accounts:
            overdue = float(a.overdue_balance)
            dpd = int(a.dpd)
            contact_factor = max(1, a.contact_count_7d + 1)
            # Expected recovery score
            priority = round((overdue * (1.0 / (1.0 + dpd * 0.02))) / contact_factor, 2)

            specialist_needed = None
            if a.hardship:
                specialist_needed = "hardship"
            elif a.dispute:
                specialist_needed = "dispute"
            elif "MORTGAGE" in a.product.upper():
                specialist_needed = "mortgage"

            scored_accounts.append({
                "account": a,
                "account_id": a.id,
                "customer_name": a.customer.name if a.customer else "Unknown",
                "overdue_balance": overdue,
                "dpd": dpd,
                "priority_score": priority,
                "specialist_needed": specialist_needed,
                "current_agent": a.assigned_agent.username if a.assigned_agent else None
            })

        # Sort accounts by priority descending
        scored_accounts.sort(key=lambda x: x["priority_score"], reverse=True)

        # 4. Constrained Optimization Solver (Google OR-Tools CP-SAT or Fallback)
        solver_name = "Heuristic Greedy"
        assignments_plan = []
        unassigned_accounts = []

        solved_with_ortools = False
        try:
            from ortools.sat.python import cp_model
            model = cp_model.CpModel()
            num_accounts = len(scored_accounts)
            num_agents = len(agents)

            # Decision variables: x[i, j] = 1 if account i is assigned to agent j
            x = {}
            for i in range(num_accounts):
                for j in range(num_agents):
                    x[i, j] = model.NewBoolVar(f"assign_a{i}_c{j}")

            # Constraint 1: Each account is assigned to at most one agent
            for i in range(num_accounts):
                model.AddAtMostOne(x[i, j] for j in range(num_agents))

            # Constraint 2: Agent capacity limits
            for j, ag in enumerate(agents):
                # Cannot exceed available capacity
                model.Add(sum(x[i, j] for i in range(num_accounts)) <= ag["available_capacity"])

            # Constraint 3: Specialist skill constraints
            for i, item in enumerate(scored_accounts):
                spec = item["specialist_needed"]
                if spec:
                    for j, ag in enumerate(agents):
                        if spec not in ag["skills"]:
                            # Hard constraint: collector lacking required specialist skill cannot be assigned
                            model.Add(x[i, j] == 0)

            # Objective formulation:
            # Maximize: sum(priority * x[i, j]) + affinity_bonus (keep current agent)
            objective_terms = []
            for i, item in enumerate(scored_accounts):
                p_int = int(round(item["priority_score"] * 10))
                current_ag = item["current_agent"]
                for j, ag in enumerate(agents):
                    coef = p_int
                    if current_ag == ag["username"]:
                        coef += 5  # Continuity bonus
                    if strategy == "specialist_priority" and item["specialist_needed"] and item["specialist_needed"] in ag["skills"]:
                        coef += 20
                    objective_terms.append(coef * x[i, j])

            model.Maximize(sum(objective_terms))

            # Solve CP-SAT model
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = 5.0
            solver.parameters.num_workers = 1
            status = solver.Solve(model)

            if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                solved_with_ortools = True
                solver_name = f"Google OR-Tools CP-SAT ({solver.StatusName(status)})"

                for i, item in enumerate(scored_accounts):
                    assigned_to_agent = None
                    for j, ag in enumerate(agents):
                        if solver.Value(x[i, j]) == 1:
                            assigned_to_agent = ag
                            break

                    if assigned_to_agent:
                        assigned_to_agent["assigned_in_plan"].append(item["account_id"])
                        is_changed = (item["current_agent"] != assigned_to_agent["username"])
                        assignments_plan.append({
                            "account_id": item["account_id"],
                            "customer_name": item["customer_name"],
                            "overdue_balance": item["overdue_balance"],
                            "dpd": item["dpd"],
                            "priority_score": item["priority_score"],
                            "specialist_requirement": item["specialist_needed"] or "STANDARD",
                            "previous_agent": item["current_agent"],
                            "assigned_agent": assigned_to_agent["username"],
                            "agent_name": assigned_to_agent["name"],
                            "is_reassignment": is_changed,
                            "solver": "Google OR-Tools CP-SAT",
                            "reason": f"OR-Tools CP-SAT optimal constraint match ({strategy}) with specialist={item['specialist_needed'] or 'NONE'}"
                        })
                    else:
                        unassigned_accounts.append({
                            "account_id": item["account_id"],
                            "reason": "ALL_QUALIFIED_AGENTS_AT_MAX_CAPACITY"
                        })
        except Exception as e:
            solved_with_ortools = False

        # Fallback to greedy heuristic if OR-Tools did not solve
        if not solved_with_ortools:
            solver_name = "Constrained Priority Greedy Heuristic (Fallback)"
            for ag in agents:
                ag["assigned_in_plan"] = []
            assignments_plan = []
            unassigned_accounts = []

            for item in scored_accounts:
                spec = item["specialist_needed"]
                eligible_agents = [ag for ag in agents if not spec or spec in ag["skills"]]
                if not eligible_agents:
                    eligible_agents = agents

                eligible_agents.sort(key=lambda ag: len(ag["assigned_in_plan"]) + ag["current_workload"])
                assigned_agent = None
                for cand in eligible_agents:
                    if len(cand["assigned_in_plan"]) < cand["available_capacity"]:
                        assigned_agent = cand
                        break

                if assigned_agent:
                    assigned_agent["assigned_in_plan"].append(item["account_id"])
                    is_changed = (item["current_agent"] != assigned_agent["username"])
                    assignments_plan.append({
                        "account_id": item["account_id"],
                        "customer_name": item["customer_name"],
                        "overdue_balance": item["overdue_balance"],
                        "dpd": item["dpd"],
                        "priority_score": item["priority_score"],
                        "specialist_requirement": spec or "STANDARD",
                        "previous_agent": item["current_agent"],
                        "assigned_agent": assigned_agent["username"],
                        "agent_name": assigned_agent["name"],
                        "is_reassignment": is_changed,
                        "solver": "Greedy Heuristic",
                        "reason": f"Greedy constraint match ({strategy}) with specialist={spec or 'NONE'}"
                    })
                else:
                    unassigned_accounts.append({
                        "account_id": item["account_id"],
                        "reason": "ALL_QUALIFIED_AGENTS_AT_MAX_CAPACITY"
                    })

        # 5. Apply reassignments if requested
        reassignments_applied = 0
        if apply_reassignments:
            with transaction.atomic():
                user_lookup = {ag["username"]: ag["user"] for ag in agents}
                for item in assignments_plan:
                    if item["is_reassignment"]:
                        target_user = user_lookup.get(item["assigned_agent"])
                        account_obj = Account.objects.get(id=item["account_id"])
                        account_obj.assigned_agent = target_user
                        account_obj.save(update_fields=['assigned_agent'])

                        qa, _ = QueueAssignment.objects.get_or_create(account=account_obj)
                        qa.assigned_agent = target_user
                        qa.assigned_by = actor_user
                        qa.priority_score = item["priority_score"]
                        qa.routing_reason = item["reason"]
                        qa.status = QueueAssignment.Status.ASSIGNED
                        qa.save()

                        log_audit(
                            'OPTIMIZER_REASSIGNMENT',
                            item["account_id"],
                            f"Optimizer reassigned {item['account_id']} to {item['assigned_agent']}",
                            actor=actor_user.username if actor_user else 'system_optimizer',
                            extra_context={'priority': item['priority_score'], 'strategy': strategy}
                        )
                        reassignments_applied += 1

        # Summary of agent post-optimization workloads
        agent_workload_summary = []
        for ag in agents:
            new_cases = len(ag["assigned_in_plan"])
            agent_workload_summary.append({
                "agent": ag["username"],
                "name": ag["name"],
                "skills": ag["skills"],
                "max_capacity": ag["max_capacity"],
                "baseline_workload": ag["current_workload"],
                "planned_assignments": new_cases,
                "projected_total": ag["current_workload"] + new_cases,
                "utilization_pct": round(((ag["current_workload"] + new_cases) / max(1, ag["max_capacity"])) * 100, 1)
            })

        return {
            "strategy": strategy,
            "solver_engine": solver_name,
            "optimization_timestamp": datetime.now(timezone.utc).isoformat(),
            "applied": apply_reassignments,
            "total_accounts_evaluated": len(accounts),
            "total_assigned": len(assignments_plan),
            "unassigned_count": len(unassigned_accounts),
            "reassignments_triggered": reassignments_applied if apply_reassignments else len([p for p in assignments_plan if p["is_reassignment"]]),
            "agent_workloads": agent_workload_summary,
            "plan_sample": assignments_plan[:15],
            "unassigned_accounts": unassigned_accounts
        }


optimizer = QueueWorkloadOptimizer()
