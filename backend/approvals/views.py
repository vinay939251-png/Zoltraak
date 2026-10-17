"""
Approval workflow views enforcing Section 10.8 state transitions and pre-execution eligibility checks.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
import uuid
from approvals.models import ApprovalRequest
from approvals.serializers import ApprovalRequestSerializer
from decisioning.models import Recommendation
from decisioning.engine import RulesEngine
from audit.utils import log_audit


class ApprovalViewSet(viewsets.ModelViewSet):
    queryset = ApprovalRequest.objects.select_related(
        'recommendation', 'recommendation__account', 'recommendation__account__customer',
        'requested_by', 'reviewed_by'
    ).all().order_by('-created_at')
    serializer_class = ApprovalRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = ApprovalRequest.objects.select_related(
            'recommendation', 'recommendation__account', 'recommendation__account__customer',
            'requested_by', 'reviewed_by'
        ).all().order_by('-created_at')

        scope = self.request.query_params.get('scope')
        agent_param = self.request.query_params.get('agent')

        # Allow supervisors (team_lead, administrator, auditor) to inspect specific agent's queue
        if agent_param and user.is_authenticated and user.role in ['team_lead', 'administrator', 'auditor']:
            qs = qs.filter(recommendation__account__assigned_agent__username=agent_param)
        elif scope == 'all' and user.is_authenticated and user.role in ['team_lead', 'administrator', 'auditor']:
            # Supervisor viewing entire team queue
            pass
        elif scope == 'pending_approval' and user.is_authenticated and user.role in ['team_lead', 'administrator']:
            # Supervisor viewing decisions waiting for approval
            qs = qs.filter(status='PENDING_REVIEW')
        elif user.is_authenticated:
            if user.role == 'collections_agent':
                # Operational agent sees only their assigned accounts
                qs = qs.filter(recommendation__account__assigned_agent=user)
            elif user.role == 'hardship_specialist':
                # Hardship specialist sees accounts flagged for hardship, escalated status, or assigned
                from django.db.models import Q
                qs = qs.filter(
                    Q(recommendation__account__hardship=True) |
                    Q(status=ApprovalRequest.Status.ESCALATED) |
                    Q(recommendation__account__assigned_agent=user)
                ).distinct()
            elif user.role == 'data_steward':
                # Data steward sees disputes, pre-execution compliance aborts, and DNC flags
                from django.db.models import Q
                qs = qs.filter(
                    Q(recommendation__account__dispute=True) |
                    Q(status=ApprovalRequest.Status.FAILED) |
                    Q(recommendation__account__dnc=True)
                ).distinct()
            elif user.role in ['team_lead', 'administrator']:
                # By default, team leads see all portfolio decisions
                pass

        account_id = self.request.query_params.get('account')
        if account_id:
            qs = qs.filter(recommendation__account_id=account_id)

        customer_id = self.request.query_params.get('customer')
        if customer_id:
            qs = qs.filter(recommendation__account__customer_id=customer_id)

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        return qs

    @action(detail=True, methods=['post'], url_path='transition')
    def transition(self, request, pk=None):
        """
        Executes an audited state transition on an approval record and its underlying recommendation.
        Re-validates eligibility before EXECUTED transition to prevent stale approvals.
        """
        approval = self.get_object()
        target_state = request.data.get('target_state')
        reason = request.data.get('reason', '')
        override_action = request.data.get('override_action', '')
        idempotency_key = request.data.get('idempotency_key') or f"trans-{uuid.uuid4().hex[:12]}"

        valid_states = [s[0] for s in ApprovalRequest.Status.choices]
        if target_state not in valid_states:
            return Response({'error': f'Invalid target state. Must be one of {valid_states}'}, status=status.HTTP_400_BAD_REQUEST)

        # Role restrictions
        user = request.user
        if target_state in ['APPROVED', 'OVERRIDDEN'] and user.role == 'collections_agent':
            return Response(
                {'error': 'Collections agents cannot approve or override recommendations. Team Lead or Administrator authorization is required.'},
                status=status.HTTP_403_FORBIDDEN
            )

        rec = approval.recommendation

        # Check allowed transition
        if not rec.can_transition_to(target_state) and target_state != 'EXECUTED':
            return Response(
                {'error': f"Cannot transition recommendation from '{rec.status}' to '{target_state}'. Allowed: {rec.ALLOWED_TRANSITIONS.get(rec.status, [])}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Pre-execution check (Section 10.8 requirement)
        if target_state == 'EXECUTED':
            eligibility = RulesEngine.evaluate_eligibility(rec.account)
            if not eligibility['eligible']:
                approval.status = ApprovalRequest.Status.FAILED
                approval.execution_result = {'error': 'Stale approval rejected: mandatory eligibility check failed immediately prior to execution.', 'blocking_reasons': eligibility['blocking_reasons']}
                approval.save()
                rec.status = Recommendation.Status.FAILED
                rec.save()

                log_audit(
                    'SECURITY_REFUSAL',
                    approval.id,
                    f"Execution rejected for Account {rec.account_id}: critical condition became ineligible before execution.",
                    actor=user,
                    details={'blocking_reasons': eligibility['blocking_reasons']}
                )

                return Response({
                    'error': 'Execution blocked: Account conditions changed. Pre-execution eligibility failed.',
                    'blocking_reasons': eligibility['blocking_reasons'],
                    'approval': ApprovalRequestSerializer(approval).data
                }, status=status.HTTP_409_CONFLICT)

        with transaction.atomic():
            approval.status = target_state
            approval.reviewed_by = user
            approval.reason = reason
            if override_action:
                approval.final_action = override_action
                rec.action = override_action

            if target_state == 'EXECUTED':
                approval.executed_at = timezone.now()
                approval.execution_result = {
                    'status': 'SIMULATED_SUCCESS',
                    'action': rec.action,
                    'account_id': rec.account_id,
                    'customer_id': rec.account.customer_id,
                    'note': 'Demonstration simulation executed. Live external side effects disabled.'
                }

            approval.save()
            rec.status = target_state
            rec.reviewed_by = user
            rec.review_reason = reason
            rec.save()

            # Record audit event
            event_type_map = {
                'APPROVED': 'RECOMMENDATION_APPROVED',
                'REJECTED': 'RECOMMENDATION_REJECTED',
                'ESCALATED': 'RECOMMENDATION_ESCALATED',
                'EXECUTED': 'RECOMMENDATION_EXECUTED',
                'EDITED': 'RECOMMENDATION_EDITED',
                'OVERRIDDEN': 'RECOMMENDATION_EDITED'
            }
            log_audit(
                event_type_map.get(target_state, 'RECOMMENDATION_APPROVED'),
                approval.id,
                f"Transitioned approval for Recommendation {rec.id} to '{target_state}'. Reason: {reason or 'None'}",
                actor=user,
                details={'previous_state': approval.status, 'target_state': target_state, 'final_action': rec.action}
            )

        return Response({
            'message': f"Successfully transitioned to {target_state}",
            'approval': ApprovalRequestSerializer(approval).data,
            'recommendation_status': rec.status
        })
