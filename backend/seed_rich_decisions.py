"""
Deterministic Seeder for Enhanced Decisioning, Human-in-the-Loop Governance,
Rule Set Versions, Decision Memories, and Counterfactual Reasoning.
"""
import os
import django
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from authentication.models import User
from customers.models import Customer
from accounts.models import Account
from decisioning.models import RuleSetVersion, Recommendation, DecisionMemory
from approvals.models import ApprovalRequest
from audit.utils import log_audit


def seed_decisioning():
    print("=== 1. Seeding Deterministic Rule Set Versions ===")
    
    # 1. Rule Set Version 2.1 (Active Production)
    rules_v21, created = RuleSetVersion.objects.update_or_create(
        id='ruleset-v2.1-prod',
        defaults={
            'version': '2.1.0-prod',
            'description': 'Production Collections Compliance Ruleset enforcing Canadian FCAC guidelines, TCPA statutory calling hours (08:00-21:00), statutory 3-contact weekly cap, hardship vulnerability protections, and delegated authority limits.',
            'active': True,
            'rules': [
                {
                    'rule_id': 'ACCOUNT-001',
                    'name': 'Core Account Active Check',
                    'description': 'Account status must be ACTIVE in core banking system. Inactive accounts cannot receive active collection outreach.',
                    'mandatory': True,
                    'severity': 'BLOCKING'
                },
                {
                    'rule_id': 'DNC-001',
                    'name': 'Statutory Do-Not-Contact & Written-Only Screening',
                    'description': 'Borrowers registered on Do-Not-Contact or specifying written-only demands are strictly shielded from automated or manual telephone solicitations.',
                    'mandatory': True,
                    'severity': 'BLOCKING'
                },
                {
                    'rule_id': 'CAP-001',
                    'name': 'Statutory 7-Day Contact Frequency Cap (FCAC Rule 3)',
                    'description': 'Statutory limit of maximum 3 contact attempts within any rolling 7-day window. Breaches trigger mandatory 48-hour cooling period hold.',
                    'mandatory': True,
                    'severity': 'BLOCKING'
                },
                {
                    'rule_id': 'TIME-001',
                    'name': 'Permissible Local Calling Hours Window',
                    'description': 'Outbound collector calls and telephony dialer dispatches are strictly restricted to 08:00 to 21:00 borrower local time.',
                    'mandatory': True,
                    'severity': 'BLOCKING'
                },
                {
                    'rule_id': 'DISPUTE-001',
                    'name': 'Formal Billing & Transactional Dispute Collections Freeze',
                    'description': 'Accounts with open formal disputes must have ordinary recovery activities halted on contested sums until resolved by dispute specialists.',
                    'mandatory': True,
                    'severity': 'BLOCKING'
                },
                {
                    'rule_id': 'HARDSHIP-001',
                    'name': 'Vulnerable Borrower Hardship & Distress Shield',
                    'description': 'Customers flagged with active financial hardship or distress must be routed directly to specialized relief teams with legal enforcement moratorium.',
                    'mandatory': True,
                    'severity': 'BLOCKING'
                },
                {
                    'rule_id': 'SETTLE-001',
                    'name': 'Delegation of Authority Settlement Discount Threshold',
                    'description': 'Discounts <=20% permitted under collector authority. Discounts >20% require Team Lead Marcus Vance sign-off; >30% require Credit Committee.',
                    'mandatory': False,
                    'severity': 'WARNING_AUTHORIZATION_REQUIRED'
                },
                {
                    'rule_id': 'DATA-001',
                    'name': 'Upstream Core Provenance & Freshness SLA Check',
                    'description': 'Feature store observation must have been verified within the past 24 hours to prevent stale algorithmic decisions.',
                    'mandatory': False,
                    'severity': 'AUDIT_WARNING'
                }
            ]
        }
    )
    print(f"  [OK] RuleSetVersion: {rules_v21.id} (active={rules_v21.active})")

    # 2. Rule Set Version 2.0 (Legacy Baseline)
    rules_v20, _ = RuleSetVersion.objects.update_or_create(
        id='ruleset-v2.0-baseline',
        defaults={
            'version': '2.0.0-legacy',
            'description': 'Legacy static ruleset without dynamic sentiment-driven vulnerability routing or time-of-day geo-enforcement.',
            'active': False,
            'rules': [
                {'rule_id': 'ACCOUNT-001', 'name': 'Active Status', 'mandatory': True},
                {'rule_id': 'DNC-001', 'name': 'Do Not Contact', 'mandatory': True},
                {'rule_id': 'CAP-001', 'name': 'Contact Cap 3/7d', 'mandatory': True}
            ]
        }
    )
    print(f"  [OK] RuleSetVersion: {rules_v20.id} (active={rules_v20.active})")

    # 3. Rule Set Version 2.2 (Candidate Staged)
    rules_v22, _ = RuleSetVersion.objects.update_or_create(
        id='ruleset-v2.2-rc1',
        defaults={
            'version': '2.2.0-candidate',
            'description': 'Staged candidate ruleset introducing automated Interac e-Transfer self-cure links and omnichannel WhatsApp notifications for sub-30 DPD borrowers.',
            'active': False,
            'rules': [
                {'rule_id': 'ACCOUNT-001', 'name': 'Core Account Active Check', 'mandatory': True},
                {'rule_id': 'DNC-001', 'name': 'Statutory Do-Not-Contact Screening', 'mandatory': True},
                {'rule_id': 'CAP-001', 'name': 'Statutory 7-Day Contact Cap', 'mandatory': True},
                {'rule_id': 'TIME-001', 'name': 'Permissible Local Calling Hours', 'mandatory': True},
                {'rule_id': 'DISPUTE-001', 'name': 'Dispute Collections Freeze', 'mandatory': True},
                {'rule_id': 'HARDSHIP-001', 'name': 'Vulnerable Borrower Hardship Shield', 'mandatory': True},
                {'rule_id': 'SETTLE-001', 'name': 'Settlement Authority Limits', 'mandatory': False},
                {'rule_id': 'OMNI-001', 'name': 'Omnichannel Digital First Route', 'mandatory': False}
            ]
        }
    )
    print(f"  [OK] RuleSetVersion: {rules_v22.id} (active={rules_v22.active})")

    print("\n=== 2. Resolving Actors ===")
    agent1 = User.objects.get(username='agent-001') # Sarah Jenkins
    agent2 = User.objects.get(username='agent-002') # Liam Tremblay
    lead = User.objects.get(username='lead-001') # Marcus Vance
    specialist = User.objects.get(username='specialist-001') # Elena Rostova
    admin_user = User.objects.get(username='admin-001') # Rachel Kim
    now = timezone.now()

    print("\n=== 3. Seeding Rich Recommendations, Approvals & Decision Memory ===")

    def build_rule_results(account_status='ACTIVE', dnc=False, cap_count=1, local_hour=14, dispute=False, hardship=False, discount=15.0):
        return [
            {
                'rule_id': 'ACCOUNT-001',
                'passed': account_status == 'ACTIVE',
                'reason_code': 'ACTIVE' if account_status == 'ACTIVE' else 'ACCOUNT_INACTIVE',
                'reason': 'Account is active in core banking system.' if account_status == 'ACTIVE' else f'Status is {account_status}. Inactive accounts shielded from collections.',
                'mandatory': True
            },
            {
                'rule_id': 'DNC-001',
                'passed': not dnc,
                'reason_code': 'CONTACT_ALLOWED' if not dnc else 'CONTACT_RESTRICTED',
                'reason': 'No active Do-Not-Contact restriction.' if not dnc else 'Active Do-Not-Contact restriction enforced by regulation. Telephony and automated outreach strictly prohibited.',
                'mandatory': True
            },
            {
                'rule_id': 'CAP-001',
                'passed': cap_count < 4,
                'reason_code': 'CONTACT_CAP_AVAILABLE' if cap_count < 4 else 'CONTACT_CAP_EXCEEDED',
                'reason': f'{cap_count} contacts in rolling 7 days; below statutory limit (3).' if cap_count < 4 else f'{cap_count} recorded contact attempts in 7-day window (limit: 3). Statutory cooldown required.',
                'mandatory': True
            },
            {
                'rule_id': 'TIME-001',
                'passed': 8 <= local_hour <= 21,
                'reason_code': 'PERMISSIBLE_CALLING_HOURS' if 8 <= local_hour <= 21 else 'OUTSIDE_CALLING_HOURS',
                'reason': f'Local borrower time ({local_hour:02d}:00) is within statutory calling window (08:00 - 21:00).' if 8 <= local_hour <= 21 else f'Borrower local time {local_hour:02d}:00 is outside permissible window.',
                'mandatory': True
            },
            {
                'rule_id': 'DISPUTE-001',
                'passed': not dispute,
                'reason_code': 'NO_OPEN_DISPUTE' if not dispute else 'SPECIALIST_REQUIRED_DISPUTE',
                'reason': 'No active dispute filed on this account.' if not dispute else 'Formal customer dispute is active. Ordinary debt collection halted; routed for specialist dispute resolution.',
                'mandatory': True
            },
            {
                'rule_id': 'HARDSHIP-001',
                'passed': not hardship,
                'reason_code': 'NO_HARDSHIP_FLAG' if not hardship else 'SPECIALIST_REQUIRED_HARDSHIP',
                'reason': 'No active hardship assistance plan.' if not hardship else 'Customer enrolled in hardship relief; requires specialist case management and moratorium protection.',
                'mandatory': True
            },
            {
                'rule_id': 'SETTLE-001',
                'passed': discount <= 20.0,
                'reason_code': 'WITHIN_DELEGATED_AUTHORITY' if discount <= 20.0 else 'SUPERVISOR_APPROVAL_REQUIRED',
                'reason': f'Proposed settlement discount ({discount:.1f}%) is within collector delegated authority (<=20%).' if discount <= 20.0 else f'Proposed discount ({discount:.1f}%) exceeds collector limit (20%); requires Team Lead Marcus Vance sign-off.',
                'mandatory': False
            },
            {
                'rule_id': 'DATA-001',
                'passed': True,
                'reason_code': 'DATA_FRESHNESS_VERIFIED',
                'reason': 'Complete source provenance and observation timestamp verified within 24h SLA.',
                'mandatory': False
            }
        ]

    # Clean existing DecisionMemory and ApprovalRequest to ensure clean state
    DecisionMemory.objects.all().delete()
    ApprovalRequest.objects.all().delete()
    Recommendation.objects.all().delete()
    print("  [CLEAN] Cleared prior recommendations, approvals, and decision memories.")

    # -------------------------------------------------------------
    # CUSTOMER 1: Alexandre Tremblay (acct-loan-001)
    # -------------------------------------------------------------
    a1 = Account.objects.get(id='acct-loan-001')
    
    # Rec 1 (Historical Executed)
    r1_hist = Recommendation.objects.create(
        id='rec-001-hist',
        account=a1,
        version=1,
        status=Recommendation.Status.EXECUTED,
        target='30-day cure propensity',
        score=0.84,
        model_version='champion-xgb-cure-v2',
        prediction_timestamp=now - timedelta(days=6),
        action='digital_reminder_sms',
        top_features=[
            {'feature': 'historical_ptp_adherence', 'value': 0.95, 'importance': 0.38, 'direction': 'positive'},
            {'feature': 'days_past_due', 'value': 12, 'importance': 0.28, 'direction': 'neutral'},
            {'feature': 'recent_payment_count', 'value': 3, 'importance': 0.18, 'direction': 'positive'},
            {'feature': 'overdue_balance', 'value': 412.50, 'importance': 0.16, 'direction': 'negative'}
        ],
        review_reason='Early arrears sub-30 DPD account with high cure propensity. Automated payment link SMS authorized.',
        reviewed_by=lead
    )
    ApprovalRequest.objects.create(
        id='00000000-0000-0000-0001-000000000001',
        recommendation=r1_hist,
        recommendation_version=1,
        status=ApprovalRequest.Status.EXECUTED,
        requested_by=agent1,
        reviewed_by=lead,
        reason='Low DPD sub-30 account with pristine repayment history. Automated Interac payment link SMS approved and executed.',
        proposed_action='digital_reminder_sms',
        final_action='digital_reminder_sms',
        idempotency_key='seed-appr-001-hist',
        executed_at=now - timedelta(days=5),
        execution_result={
            'status': 'SIMULATED_SUCCESS',
            'channel': 'SMS_PORTAL',
            'sms_provider_ref': 'TWILIO-SMS-884129',
            'delivery_receipt': 'DELIVERED',
            'target_mobile': '+1-514-555-0192',
            'link_clicked': True
        }
    )
    DecisionMemory.objects.create(
        id='dm-001-hist',
        recommendation=r1_hist,
        account_id=a1.id,
        feature_values={'dpd': 12, 'overdue_balance': 412.50, 'contact_count_7d': 0, 'hardship': False, 'dispute': False, 'dnc': False, 'ptp_adherence': 0.95},
        feature_timestamps={'observed_at': (now - timedelta(days=6)).isoformat()},
        feature_version='features-v2.1-online',
        model_id='champion-xgb-cure-v2',
        model_version='2.4.1-calibrated',
        model_prediction=0.84,
        policy_version='policy-fcac-2024.1',
        rule_version='ruleset-v2.1-prod',
        rule_results=build_rule_results(account_status='ACTIVE', dnc=False, cap_count=0, local_hour=14, dispute=False, hardship=False, discount=0),
        candidate_action='digital_reminder_sms',
        human_review_outcome='APPROVED_AND_EXECUTED',
        final_action='digital_reminder_sms',
        correlation_id='corr-001-hist-8821',
        explanation_inputs={
            'counterfactuals': [
                {'scenario': 'Arrears aging progression', 'condition_change': 'dpd: 12 -> 45 (unpaid cycle crosses 30 DPD)', 'resulting_action': 'outbound_call', 'rule_impact': 'Triggers agent voice call outreach.'}
            ],
            'shap_drivers': [
                {'feature': 'historical_ptp_adherence', 'impact': '+0.28', 'direction': 'positive'},
                {'feature': 'days_past_due', 'impact': '+0.15', 'direction': 'positive'}
            ]
        }
    )

    # Rec 2 (Current Pending Review)
    r1 = Recommendation.objects.create(
        id='rec-001',
        account=a1,
        version=1,
        status=Recommendation.Status.PENDING_REVIEW,
        target='30-day cure propensity',
        score=0.86,
        model_version='champion-xgb-cure-v2',
        prediction_timestamp=now - timedelta(hours=3),
        action='digital_self_cure_portal',
        top_features=[
            {'feature': 'historical_ptp_adherence', 'value': 0.95, 'importance': 0.38, 'direction': 'positive'},
            {'feature': 'days_past_due', 'value': 18, 'importance': 0.28, 'direction': 'neutral'},
            {'feature': 'recent_payment_count', 'value': 4, 'importance': 0.18, 'direction': 'positive'},
            {'feature': 'overdue_balance', 'value': 412.50, 'importance': 0.16, 'direction': 'negative'}
        ],
        review_reason='Follow-up interactive self-cure web arrangement with 5-day grace extension option.',
        reviewed_by=None
    )
    ApprovalRequest.objects.create(
        id='00000000-0000-0000-0001-000000000002',
        recommendation=r1,
        recommendation_version=1,
        status=ApprovalRequest.Status.PENDING_REVIEW,
        requested_by=agent1,
        reviewed_by=None,
        reason='Early arrears account with high cure probability. Recommending digital self-cure payment portal link with 5-day grace extension.',
        proposed_action='digital_self_cure_portal',
        final_action='',
        idempotency_key='seed-appr-001-curr'
    )
    DecisionMemory.objects.create(
        id='dm-001-curr',
        recommendation=r1,
        account_id=a1.id,
        feature_values={'dpd': 18, 'overdue_balance': 412.50, 'contact_count_7d': 1, 'hardship': False, 'dispute': False, 'dnc': False, 'ptp_adherence': 0.95},
        feature_timestamps={'observed_at': (now - timedelta(hours=3)).isoformat()},
        feature_version='features-v2.1-online',
        model_id='champion-xgb-cure-v2',
        model_version='2.4.1-calibrated',
        model_prediction=0.86,
        policy_version='policy-fcac-2024.1',
        rule_version='ruleset-v2.1-prod',
        rule_results=build_rule_results(account_status='ACTIVE', dnc=False, cap_count=1, local_hour=14, dispute=False, hardship=False, discount=0),
        candidate_action='digital_self_cure_portal',
        human_review_outcome='PENDING_REVIEW',
        final_action='',
        correlation_id='corr-001-curr-9912',
        explanation_inputs={
            'counterfactuals': [
                {'scenario': 'Arrears aging beyond 30 DPD', 'condition_change': 'dpd: 18 -> 35', 'resulting_action': 'outbound_call', 'rule_impact': 'Requires collector phone outreach.'},
                {'scenario': 'Full cure receipt', 'condition_change': 'overdue_balance: 412.50 -> 0.00', 'resulting_action': 'no_action_cured', 'rule_impact': 'Account returns to Good Standing.'}
            ],
            'delegation_level': 'Collector Standard Authority (No escalation needed)'
        }
    )
    print("  [OK] cust-001 (Alexandre Tremblay): 2 decisions seeded (1 Executed, 1 Pending Review).")

    # -------------------------------------------------------------
    # CUSTOMER 2: Priya Patel (acct-card-002) - Contact Cap Protection
    # -------------------------------------------------------------
    a2 = Account.objects.get(id='acct-card-002')
    
    # Rec 1 (Historical Overridden)
    r2_hist = Recommendation.objects.create(
        id='rec-002-hist',
        account=a2,
        version=1,
        status=Recommendation.Status.OVERRIDDEN,
        target='30-day cure propensity',
        score=0.52,
        model_version='champion-xgb-cure-v2',
        prediction_timestamp=now - timedelta(days=2),
        action='digital_cooling_hold',
        top_features=[
            {'feature': 'contact_count_7d', 'value': 4, 'importance': 0.42, 'direction': 'negative'},
            {'feature': 'days_past_due', 'value': 42, 'importance': 0.30, 'direction': 'negative'},
            {'feature': 'overdue_balance', 'value': 1280.00, 'importance': 0.18, 'direction': 'negative'}
        ],
        review_reason='Proposed outbound voice call overridden: Customer reached 4 contacts in 7-day rolling window, violating statutory contact cap.',
        reviewed_by=lead
    )
    ApprovalRequest.objects.create(
        id='00000000-0000-0000-0002-000000000001',
        recommendation=r2_hist,
        recommendation_version=1,
        status=ApprovalRequest.Status.OVERRIDDEN,
        requested_by=agent1,
        reviewed_by=lead,
        reason='Supervisor override by Marcus Vance: Telephony dialing blocked. Rule CAP-001 breached with 4 contacts in rolling 7-day window. Enforcing cooling period hold.',
        proposed_action='outbound_call',
        final_action='digital_cooling_hold',
        override_payload={'override_reason': 'STATUTORY_CAP_BREACH', 'cooling_hours': 48, 'supervisor': 'Marcus Vance'},
        idempotency_key='seed-appr-002-hist'
    )
    DecisionMemory.objects.create(
        id='dm-002-hist',
        recommendation=r2_hist,
        account_id=a2.id,
        feature_values={'dpd': 42, 'overdue_balance': 1280.00, 'contact_count_7d': 4, 'hardship': False, 'dispute': False, 'dnc': False},
        feature_timestamps={'observed_at': (now - timedelta(days=2)).isoformat()},
        feature_version='features-v2.1-online',
        model_id='champion-xgb-cure-v2',
        model_version='2.4.1-calibrated',
        model_prediction=0.52,
        policy_version='policy-fcac-2024.1',
        rule_version='ruleset-v2.1-prod',
        rule_results=build_rule_results(account_status='ACTIVE', dnc=False, cap_count=4, local_hour=14, dispute=False, hardship=False, discount=15),
        candidate_action='outbound_call',
        human_review_outcome='OVERRIDDEN_COOLING_HOLD',
        final_action='digital_cooling_hold',
        correlation_id='corr-002-hist-7721',
        explanation_inputs={
            'counterfactuals': [
                {'scenario': 'Contact frequency cooldown expiry', 'condition_change': 'contact_count_7d: 4 -> 2 (rolling 7-day window moves by 48h)', 'resulting_action': 'outbound_call', 'rule_impact': 'CAP-001 clears; phone outreach permitted with 15% settlement discount.'}
            ]
        }
    )

    # Rec 2 (Current Approved Cooling Hold)
    r2 = Recommendation.objects.create(
        id='rec-002',
        account=a2,
        version=1,
        status=Recommendation.Status.APPROVED,
        target='30-day cure propensity',
        score=0.45,
        model_version='champion-xgb-cure-v2',
        prediction_timestamp=now - timedelta(hours=4),
        action='digital_cooling_hold',
        top_features=[
            {'feature': 'contact_count_7d', 'value': 4, 'importance': 0.45, 'direction': 'negative'},
            {'feature': 'days_past_due', 'value': 42, 'importance': 0.28, 'direction': 'negative'},
            {'feature': 'overdue_balance', 'value': 1280.00, 'importance': 0.15, 'direction': 'negative'}
        ],
        review_reason='Statutory cooling period hold confirmed. All automated and manual outreach suppressed until 48-hour window expires.',
        reviewed_by=lead
    )
    ApprovalRequest.objects.create(
        id='00000000-0000-0000-0002-000000000002',
        recommendation=r2,
        recommendation_version=1,
        status=ApprovalRequest.Status.APPROVED,
        requested_by=agent1,
        reviewed_by=lead,
        reason='Approved 48-hour statutory contact freeze under Canadian FCAC guidelines. Cooling hold remains active until Friday 09:00 EST.',
        proposed_action='digital_cooling_hold',
        final_action='digital_cooling_hold',
        idempotency_key='seed-appr-002-curr'
    )
    DecisionMemory.objects.create(
        id='dm-002-curr',
        recommendation=r2,
        account_id=a2.id,
        feature_values={'dpd': 42, 'overdue_balance': 1280.00, 'contact_count_7d': 4, 'hardship': False, 'dispute': False, 'dnc': False},
        feature_timestamps={'observed_at': (now - timedelta(hours=4)).isoformat()},
        feature_version='features-v2.1-online',
        model_id='champion-xgb-cure-v2',
        model_version='2.4.1-calibrated',
        model_prediction=0.45,
        policy_version='policy-fcac-2024.1',
        rule_version='ruleset-v2.1-prod',
        rule_results=build_rule_results(account_status='ACTIVE', dnc=False, cap_count=4, local_hour=14, dispute=False, hardship=False, discount=15),
        candidate_action='digital_cooling_hold',
        human_review_outcome='APPROVED',
        final_action='digital_cooling_hold',
        correlation_id='corr-002-curr-1192',
        explanation_inputs={
            'counterfactuals': [
                {'scenario': 'Cooldown expiration', 'condition_change': 'contact_count_7d: 4 -> 2 (cooldown ends in 36h)', 'resulting_action': 'outbound_call', 'rule_impact': 'Account unlocks for standard collector phone negotiation.'}
            ],
            'governance_note': 'System dialer automatically disengaged via Kafka compliance event stream.'
        }
    )
    print("  [OK] cust-002 (Priya Patel): 2 decisions seeded (1 Overridden, 1 Approved).")

    # -------------------------------------------------------------
    # CUSTOMER 3: Sarah Al-Mansoor (acct-mortgage-003) - Hardship Moratorium
    # -------------------------------------------------------------
    a3 = Account.objects.get(id='acct-mortgage-003')

    # Rec 1 (Historical Escalated)
    r3_hist = Recommendation.objects.create(
        id='rec-003-hist',
        account=a3,
        version=1,
        status=Recommendation.Status.ESCALATED,
        target='30-day cure propensity',
        score=0.18,
        model_version='champion-xgb-cure-v2',
        prediction_timestamp=now - timedelta(days=7),
        action='route_hardship_specialist',
        top_features=[
            {'feature': 'hardship_flag', 'value': 1, 'importance': 0.48, 'direction': 'negative'},
            {'feature': 'days_past_due', 'value': 68, 'importance': 0.25, 'direction': 'negative'},
            {'feature': 'overdue_balance', 'value': 6450.00, 'importance': 0.18, 'direction': 'negative'}
        ],
        review_reason='Customer reported acute medical hardship and severe income shock. Escalated to Elena Rostova for specialized mortgage relief.',
        reviewed_by=agent1
    )
    ApprovalRequest.objects.create(
        id='00000000-0000-0000-0003-000000000001',
        recommendation=r3_hist,
        recommendation_version=1,
        status=ApprovalRequest.Status.ESCALATED,
        requested_by=agent1,
        reviewed_by=lead,
        reason='Escalated to Hardship Specialist Elena Rostova: borrower filed medical documentation confirming temporary disability.',
        proposed_action='outbound_call',
        final_action='route_hardship_specialist',
        idempotency_key='seed-appr-003-hist'
    )
    DecisionMemory.objects.create(
        id='dm-003-hist',
        recommendation=r3_hist,
        account_id=a3.id,
        feature_values={'dpd': 68, 'overdue_balance': 6450.00, 'contact_count_7d': 1, 'hardship': True, 'dispute': False, 'dnc': False},
        feature_timestamps={'observed_at': (now - timedelta(days=7)).isoformat()},
        feature_version='features-v2.1-online',
        model_id='champion-xgb-cure-v2',
        model_version='2.4.1-calibrated',
        model_prediction=0.18,
        policy_version='policy-fcac-2024.1',
        rule_version='ruleset-v2.1-prod',
        rule_results=build_rule_results(account_status='ACTIVE', dnc=False, cap_count=1, local_hour=14, dispute=False, hardship=True, discount=0),
        candidate_action='route_hardship_specialist',
        human_review_outcome='ESCALATED',
        final_action='route_hardship_specialist',
        correlation_id='corr-003-hist-3312',
        explanation_inputs={
            'counterfactuals': [
                {'scenario': 'Hardship relief stabilization', 'condition_change': 'hardship: True -> False (medical clearance verified)', 'resulting_action': 'restructure_payment_plan', 'rule_impact': 'Enables transition to structured 24-month term re-amortization.'}
            ]
        }
    )

    # Rec 2 (Current Approved Hardship Moratorium)
    r3 = Recommendation.objects.create(
        id='rec-003',
        account=a3,
        version=1,
        status=Recommendation.Status.APPROVED,
        target='30-day cure propensity',
        score=0.15,
        model_version='champion-xgb-cure-v2',
        prediction_timestamp=now - timedelta(hours=5),
        action='hardship_moratorium_60d',
        top_features=[
            {'feature': 'hardship_flag', 'value': 1, 'importance': 0.52, 'direction': 'negative'},
            {'feature': 'days_past_due', 'value': 68, 'importance': 0.22, 'direction': 'negative'},
            {'feature': 'overdue_balance', 'value': 6450.00, 'importance': 0.16, 'direction': 'negative'}
        ],
        review_reason='Specialist Elena Rostova approved 60-day mortgage payment pause and interest accrual suspension.',
        reviewed_by=specialist
    )
    ApprovalRequest.objects.create(
        id='00000000-0000-0000-0003-000000000002',
        recommendation=r3,
        recommendation_version=1,
        status=ApprovalRequest.Status.APPROVED,
        requested_by=specialist,
        reviewed_by=specialist,
        reason='Hardship Specialist Elena Rostova approved 60-day compassionate moratorium. Pre-foreclosure proceedings frozen; interest capitalisation deferred.',
        proposed_action='hardship_moratorium_60d',
        final_action='hardship_moratorium_60d',
        idempotency_key='seed-appr-003-curr'
    )
    DecisionMemory.objects.create(
        id='dm-003-curr',
        recommendation=r3,
        account_id=a3.id,
        feature_values={'dpd': 68, 'overdue_balance': 6450.00, 'contact_count_7d': 1, 'hardship': True, 'dispute': False, 'dnc': False},
        feature_timestamps={'observed_at': (now - timedelta(hours=5)).isoformat()},
        feature_version='features-v2.1-online',
        model_id='champion-xgb-cure-v2',
        model_version='2.4.1-calibrated',
        model_prediction=0.15,
        policy_version='policy-fcac-2024.1',
        rule_version='ruleset-v2.1-prod',
        rule_results=build_rule_results(account_status='ACTIVE', dnc=False, cap_count=1, local_hour=14, dispute=False, hardship=True, discount=0),
        candidate_action='hardship_moratorium_60d',
        human_review_outcome='APPROVED',
        final_action='hardship_moratorium_60d',
        correlation_id='corr-003-curr-8841',
        explanation_inputs={
            'counterfactuals': [
                {'scenario': 'Hardship relief stabilization', 'condition_change': 'hardship: True -> False (medical clearance verified)', 'resulting_action': 'restructure_payment_plan', 'rule_impact': 'Enables transition to structured 24-month term re-amortization.'}
            ],
            'moratorium_expiry': (now + timedelta(days=60)).strftime('%Y-%m-%d')
        }
    )
    print("  [OK] cust-003 (Sarah Al-Mansoor): 2 decisions seeded (1 Escalated, 1 Approved Moratorium).")

    # -------------------------------------------------------------
    # CUSTOMER 4: Dmitri Volkov (acct-card-004) - Dispute Freeze
    # -------------------------------------------------------------
    a4 = Account.objects.get(id='acct-card-004')
    r4 = Recommendation.objects.create(
        id='rec-004',
        account=a4,
        version=1,
        status=Recommendation.Status.PENDING_REVIEW,
        target='30-day cure propensity',
        score=0.25,
        model_version='champion-xgb-cure-v2',
        prediction_timestamp=now - timedelta(hours=6),
        action='route_dispute_specialist',
        top_features=[
            {'feature': 'dispute_active', 'value': 1, 'importance': 0.50, 'direction': 'negative'},
            {'feature': 'days_past_due', 'value': 78, 'importance': 0.26, 'direction': 'negative'},
            {'feature': 'overdue_balance', 'value': 2180.00, 'importance': 0.14, 'direction': 'negative'}
        ],
        review_reason='Formal billing dispute filed on $1,420 unauthorized merchant transaction. Ordinary debt recovery paused pending dispute adjudication.',
        reviewed_by=None
    )
    ApprovalRequest.objects.create(
        id='00000000-0000-0000-0004-000000000001',
        recommendation=r4,
        recommendation_version=1,
        status=ApprovalRequest.Status.PENDING_REVIEW,
        requested_by=agent1,
        reviewed_by=None,
        reason='Formal dispute active on card account. Ordinary debt collection halted in accordance with FCAC Rule DISPUTE-001. Requires dispute specialist sign-off.',
        proposed_action='route_dispute_specialist',
        final_action='',
        idempotency_key='seed-appr-004-curr'
    )
    DecisionMemory.objects.create(
        id='dm-004-curr',
        recommendation=r4,
        account_id=a4.id,
        feature_values={'dpd': 78, 'overdue_balance': 2180.00, 'contact_count_7d': 1, 'hardship': False, 'dispute': True, 'dnc': False},
        feature_timestamps={'observed_at': (now - timedelta(hours=6)).isoformat()},
        feature_version='features-v2.1-online',
        model_id='champion-xgb-cure-v2',
        model_version='2.4.1-calibrated',
        model_prediction=0.25,
        policy_version='policy-fcac-2024.1',
        rule_version='ruleset-v2.1-prod',
        rule_results=build_rule_results(account_status='ACTIVE', dnc=False, cap_count=1, local_hour=14, dispute=True, hardship=False, discount=0),
        candidate_action='route_dispute_specialist',
        human_review_outcome='PENDING_REVIEW',
        final_action='',
        correlation_id='corr-004-curr-6621',
        explanation_inputs={
            'counterfactuals': [
                {'scenario': 'Dispute investigation resolution', 'condition_change': 'dispute: True -> False (chargeback credited)', 'resulting_action': 'settlement_offer_discount', 'rule_impact': 'DISPUTE-001 legal freeze lifted; remaining undisputed $760 balance unlocks 20% discount offer.'}
            ],
            'disputed_amount': 1420.00,
            'undisputed_balance': 760.00
        }
    )
    print("  [OK] cust-004 (Dmitri Volkov): 1 decision seeded (Pending Dispute Specialist).")

    # -------------------------------------------------------------
    # CUSTOMER 5: Fiona Gallagher (acct-loc-005) - Pre-Execution Guardrail Refusal
    # -------------------------------------------------------------
    a5 = Account.objects.get(id='acct-loc-005')
    
    # Rec 1 (Historical FAILED Pre-Execution Check)
    r5_fail = Recommendation.objects.create(
        id='rec-005-fail',
        account=a5,
        version=1,
        status=Recommendation.Status.FAILED,
        target='30-day cure propensity',
        score=0.22,
        model_version='champion-xgb-cure-v2',
        prediction_timestamp=now - timedelta(days=3),
        action='outbound_call',
        top_features=[
            {'feature': 'dnc_flag', 'value': 1, 'importance': 0.55, 'direction': 'negative'},
            {'feature': 'days_past_due', 'value': 92, 'importance': 0.28, 'direction': 'negative'}
        ],
        review_reason='Stale approval rejected: Pre-execution safety check failed immediately prior to telephony dialer execution. Customer registered written-only DNC demand.',
        reviewed_by=lead
    )
    ApprovalRequest.objects.create(
        id='00000000-0000-0000-0005-000000000001',
        recommendation=r5_fail,
        recommendation_version=1,
        status=ApprovalRequest.Status.FAILED,
        requested_by=agent2,
        reviewed_by=lead,
        reason='Pre-execution safety refusal: Account condition changed before execution. Written-only DNC demand registered via legal courier 30 minutes prior to scheduled dialer dispatch.',
        proposed_action='outbound_call',
        final_action='outbound_call',
        idempotency_key='seed-appr-005-fail',
        execution_result={
            'status': 'SECURITY_REFUSAL',
            'blocking_rule': 'DNC-001',
            'error': 'Execution blocked: Account conditions changed. Pre-execution eligibility failed.',
            'timestamp': (now - timedelta(days=3)).isoformat()
        }
    )
    DecisionMemory.objects.create(
        id='dm-005-fail',
        recommendation=r5_fail,
        account_id=a5.id,
        feature_values={'dpd': 92, 'overdue_balance': 3890.00, 'contact_count_7d': 0, 'hardship': False, 'dispute': False, 'dnc': True},
        feature_timestamps={'observed_at': (now - timedelta(days=3)).isoformat()},
        feature_version='features-v2.1-online',
        model_id='champion-xgb-cure-v2',
        model_version='2.4.1-calibrated',
        model_prediction=0.22,
        policy_version='policy-fcac-2024.1',
        rule_version='ruleset-v2.1-prod',
        rule_results=build_rule_results(account_status='ACTIVE', dnc=True, cap_count=0, local_hour=14, dispute=False, hardship=False, discount=0),
        candidate_action='outbound_call',
        human_review_outcome='PRE_EXECUTION_BLOCKED',
        final_action='',
        correlation_id='corr-005-fail-9941',
        explanation_inputs={
            'counterfactuals': [
                {'scenario': 'Borrower opts into digital channel', 'condition_change': 'dnc: True -> False (written-only preference revoked)', 'resulting_action': 'digital_self_cure_portal', 'rule_impact': 'DNC-001 lifts; automated SMS notifications permitted.'}
            ]
        }
    )

    # Rec 2 (Current Pending Written Demand)
    r5 = Recommendation.objects.create(
        id='rec-005',
        account=a5,
        version=1,
        status=Recommendation.Status.PENDING_REVIEW,
        target='30-day cure propensity',
        score=0.10,
        model_version='champion-xgb-cure-v2',
        prediction_timestamp=now - timedelta(hours=2),
        action='registered_written_notice',
        top_features=[
            {'feature': 'dnc_flag', 'value': 1, 'importance': 0.55, 'direction': 'negative'},
            {'feature': 'days_past_due', 'value': 92, 'importance': 0.30, 'direction': 'negative'}
        ],
        review_reason='Statutory written demand letter via registered courier in compliance with written-only customer mandate.',
        reviewed_by=None
    )
    ApprovalRequest.objects.create(
        id='00000000-0000-0000-0005-000000000002',
        recommendation=r5,
        recommendation_version=1,
        status=ApprovalRequest.Status.PENDING_REVIEW,
        requested_by=agent2,
        reviewed_by=None,
        reason='Customer requested written-only correspondence. Proposing formal registered demand letter pursuant to Section 18 of Consumer Protection Act.',
        proposed_action='registered_written_notice',
        final_action='',
        idempotency_key='seed-appr-005-curr'
    )
    DecisionMemory.objects.create(
        id='dm-005-curr',
        recommendation=r5,
        account_id=a5.id,
        feature_values={'dpd': 92, 'overdue_balance': 3890.00, 'contact_count_7d': 0, 'hardship': False, 'dispute': False, 'dnc': True},
        feature_timestamps={'observed_at': (now - timedelta(hours=2)).isoformat()},
        feature_version='features-v2.1-online',
        model_id='champion-xgb-cure-v2',
        model_version='2.4.1-calibrated',
        model_prediction=0.10,
        policy_version='policy-fcac-2024.1',
        rule_version='ruleset-v2.1-prod',
        rule_results=build_rule_results(account_status='ACTIVE', dnc=True, cap_count=0, local_hour=14, dispute=False, hardship=False, discount=0),
        candidate_action='registered_written_notice',
        human_review_outcome='PENDING_REVIEW',
        final_action='',
        correlation_id='corr-005-curr-4412',
        explanation_inputs={
            'counterfactuals': [
                {'scenario': 'Borrower opts into digital channel', 'condition_change': 'dnc: True -> False (written-only preference revoked)', 'resulting_action': 'digital_self_cure_portal', 'rule_impact': 'DNC-001 lifts; automated SMS notifications permitted.'}
            ]
        }
    )
    print("  [OK] cust-005 (Fiona Gallagher): 2 decisions seeded (1 Pre-Execution FAILED, 1 Pending Written Notice).")

    # -------------------------------------------------------------
    # CUSTOMER 6: Jean-Marc Belanger (acct-loan-006) - Executed Call
    # -------------------------------------------------------------
    a6 = Account.objects.get(id='acct-loan-006')
    r6 = Recommendation.objects.create(
        id='rec-006',
        account=a6,
        version=1,
        status=Recommendation.Status.EXECUTED,
        target='30-day cure propensity',
        score=0.82,
        model_version='champion-xgb-cure-v2',
        prediction_timestamp=now - timedelta(days=2),
        action='outbound_call',
        top_features=[
            {'feature': 'historical_ptp_adherence', 'value': 0.90, 'importance': 0.36, 'direction': 'positive'},
            {'feature': 'days_past_due', 'value': 38, 'importance': 0.28, 'direction': 'negative'},
            {'feature': 'overdue_balance', 'value': 1950.00, 'importance': 0.18, 'direction': 'negative'}
        ],
        review_reason='Supervisor Marcus Vance authorized outbound agent telephone engagement. Secured verbal Promise to Pay for $1,000 due this Friday.',
        reviewed_by=lead
    )
    ApprovalRequest.objects.create(
        id='00000000-0000-0000-0006-000000000001',
        recommendation=r6,
        recommendation_version=1,
        status=ApprovalRequest.Status.EXECUTED,
        requested_by=agent1,
        reviewed_by=lead,
        reason='Supervisor Marcus Vance approved telephony outreach. Call completed; customer agreed to $1,000 payment installment on Friday.',
        proposed_action='outbound_call',
        final_action='outbound_call',
        idempotency_key='seed-appr-006-exec',
        executed_at=now - timedelta(days=2),
        execution_result={
            'status': 'SIMULATED_SUCCESS',
            'telephony_ref': 'AMAZON-CONNECT-CALL-99124',
            'duration_seconds': 284,
            'disposition': 'PROMISE_TO_PAY',
            'ptp_amount': 1000.00,
            'ptp_date': (now + timedelta(days=3)).strftime('%Y-%m-%d')
        }
    )
    DecisionMemory.objects.create(
        id='dm-006-exec',
        recommendation=r6,
        account_id=a6.id,
        feature_values={'dpd': 38, 'overdue_balance': 1950.00, 'contact_count_7d': 2, 'hardship': False, 'dispute': False, 'dnc': False, 'ptp_adherence': 0.90},
        feature_timestamps={'observed_at': (now - timedelta(days=2)).isoformat()},
        feature_version='features-v2.1-online',
        model_id='champion-xgb-cure-v2',
        model_version='2.4.1-calibrated',
        model_prediction=0.82,
        policy_version='policy-fcac-2024.1',
        rule_version='ruleset-v2.1-prod',
        rule_results=build_rule_results(account_status='ACTIVE', dnc=False, cap_count=2, local_hour=15, dispute=False, hardship=False, discount=0),
        candidate_action='outbound_call',
        human_review_outcome='APPROVED_AND_EXECUTED',
        final_action='outbound_call',
        correlation_id='corr-006-exec-1102',
        explanation_inputs={
            'counterfactuals': [
                {'scenario': 'PTP dishonored on payment date', 'condition_change': 'ptp_honored: True -> False', 'resulting_action': 'escalated_outbound_call', 'rule_impact': 'System triggers immediate escalation call and removes discount concessions.'}
            ]
        }
    )
    print("  [OK] cust-006 (Jean-Marc Belanger): 1 decision seeded (Executed Outbound Call).")

    # -------------------------------------------------------------
    # CUSTOMER 7: Devon Campbell (acct-loan-007) - Agricultural Restructure
    # -------------------------------------------------------------
    a7 = Account.objects.get(id='acct-loan-007')

    # Rec 1 (Historical Rejected)
    r7_rej = Recommendation.objects.create(
        id='rec-007-rej',
        account=a7,
        version=1,
        status=Recommendation.Status.REJECTED,
        target='30-day cure propensity',
        score=0.38,
        model_version='champion-xgb-cure-v2',
        prediction_timestamp=now - timedelta(days=5),
        action='outbound_call',
        top_features=[
            {'feature': 'days_past_due', 'value': 54, 'importance': 0.35, 'direction': 'negative'},
            {'feature': 'overdue_balance', 'value': 8300.00, 'importance': 0.30, 'direction': 'negative'}
        ],
        review_reason='Action rejected by Marcus Vance: standard consumer collection calls ineffective for seasonal crop revenue. Direct loan officer restructure required.',
        reviewed_by=lead
    )
    ApprovalRequest.objects.create(
        id='00000000-0000-0000-0007-000000000001',
        recommendation=r7_rej,
        recommendation_version=1,
        status=ApprovalRequest.Status.REJECTED,
        requested_by=agent2,
        reviewed_by=lead,
        reason='Rejected by Marcus Vance: Aggressive outbound telephony is inappropriate for commercial agricultural borrower undergoing seasonal grain harvest cycle.',
        proposed_action='outbound_call',
        final_action='restructure_payment_plan',
        idempotency_key='seed-appr-007-rej'
    )
    DecisionMemory.objects.create(
        id='dm-007-rej',
        recommendation=r7_rej,
        account_id=a7.id,
        feature_values={'dpd': 54, 'overdue_balance': 8300.00, 'contact_count_7d': 1, 'hardship': False, 'dispute': False, 'dnc': False},
        feature_timestamps={'observed_at': (now - timedelta(days=5)).isoformat()},
        feature_version='features-v2.1-online',
        model_id='champion-xgb-cure-v2',
        model_version='2.4.1-calibrated',
        model_prediction=0.38,
        policy_version='policy-fcac-2024.1',
        rule_version='ruleset-v2.1-prod',
        rule_results=build_rule_results(account_status='ACTIVE', dnc=False, cap_count=1, local_hour=14, dispute=False, hardship=False, discount=0),
        candidate_action='outbound_call',
        human_review_outcome='REJECTED_BY_SUPERVISOR',
        final_action='restructure_payment_plan',
        correlation_id='corr-007-rej-5512',
        explanation_inputs={'rejection_note': 'Seasonal cashflow requires term restructuring rather than short-term cure demand.'}
    )

    # Rec 2 (Current Pending Restructure)
    r7 = Recommendation.objects.create(
        id='rec-007',
        account=a7,
        version=1,
        status=Recommendation.Status.PENDING_REVIEW,
        target='30-day cure propensity',
        score=0.35,
        model_version='champion-xgb-cure-v2',
        prediction_timestamp=now - timedelta(hours=4),
        action='restructure_payment_plan',
        top_features=[
            {'feature': 'days_past_due', 'value': 54, 'importance': 0.35, 'direction': 'negative'},
            {'feature': 'overdue_balance', 'value': 8300.00, 'importance': 0.30, 'direction': 'negative'},
            {'feature': 'balance', 'value': 62000.00, 'importance': 0.20, 'direction': 'negative'}
        ],
        review_reason='Proposed 6-month seasonal amortization balloon extension aligned with harvest settlement. Delegation limit flagged under SETTLE-001.',
        reviewed_by=None
    )
    ApprovalRequest.objects.create(
        id='00000000-0000-0000-0007-000000000002',
        recommendation=r7,
        recommendation_version=1,
        status=ApprovalRequest.Status.PENDING_REVIEW,
        requested_by=agent2,
        reviewed_by=None,
        reason='Agricultural term loan restructuring proposal: 6-month balloon maturity extension pending Team Lead and Credit Committee approval.',
        proposed_action='restructure_payment_plan',
        final_action='',
        idempotency_key='seed-appr-007-curr'
    )
    DecisionMemory.objects.create(
        id='dm-007-curr',
        recommendation=r7,
        account_id=a7.id,
        feature_values={'dpd': 54, 'overdue_balance': 8300.00, 'contact_count_7d': 1, 'hardship': False, 'dispute': False, 'dnc': False},
        feature_timestamps={'observed_at': (now - timedelta(hours=4)).isoformat()},
        feature_version='features-v2.1-online',
        model_id='champion-xgb-cure-v2',
        model_version='2.4.1-calibrated',
        model_prediction=0.35,
        policy_version='policy-fcac-2024.1',
        rule_version='ruleset-v2.1-prod',
        rule_results=build_rule_results(account_status='ACTIVE', dnc=False, cap_count=1, local_hour=14, dispute=False, hardship=False, discount=25.0),
        candidate_action='restructure_payment_plan',
        human_review_outcome='PENDING_REVIEW',
        final_action='',
        correlation_id='corr-007-curr-2291',
        explanation_inputs={
            'counterfactuals': [
                {'scenario': 'Seasonal harvest validation pass', 'condition_change': 'cashflow_validated: True', 'resulting_action': 'restructure_payment_plan', 'rule_impact': 'Loan maturity extended by 12 months with zero default penalty.'}
            ],
            'delegation_of_authority': 'Credit Committee Approval Required (Balance > $50,000)'
        }
    )
    print("  [OK] cust-007 (Devon Campbell): 2 decisions seeded (1 Rejected, 1 Pending Restructure).")

    # -------------------------------------------------------------
    # CUSTOMER 8: Fatima Zahra (acct-comm-008) - Executed Digital SMS
    # -------------------------------------------------------------
    a8 = Account.objects.get(id='acct-comm-008')
    r8 = Recommendation.objects.create(
        id='rec-008',
        account=a8,
        version=1,
        status=Recommendation.Status.EXECUTED,
        target='30-day cure propensity',
        score=0.91,
        model_version='champion-xgb-cure-v2',
        prediction_timestamp=now - timedelta(days=1),
        action='digital_reminder_sms',
        top_features=[
            {'feature': 'historical_ptp_adherence', 'value': 0.98, 'importance': 0.45, 'direction': 'positive'},
            {'feature': 'recent_payment_count', 'value': 6, 'importance': 0.30, 'direction': 'positive'},
            {'feature': 'days_past_due', 'value': 14, 'importance': 0.15, 'direction': 'positive'}
        ],
        review_reason='Ultra-low DPD commercial client with pristine credit history. Direct Interac e-Transfer payment link dispatched.',
        reviewed_by=lead
    )
    ApprovalRequest.objects.create(
        id='00000000-0000-0000-0008-000000000001',
        recommendation=r8,
        recommendation_version=1,
        status=ApprovalRequest.Status.EXECUTED,
        requested_by=agent1,
        reviewed_by=lead,
        reason='High honor score (91/100). Approved automated Interac digital self-cure link. Telephony suppression active.',
        proposed_action='digital_reminder_sms',
        final_action='digital_reminder_sms',
        idempotency_key='seed-appr-008-exec',
        executed_at=now - timedelta(days=1),
        execution_result={
            'status': 'SIMULATED_SUCCESS',
            'channel': 'SMS_INTERAC_LINK',
            'gateway_ref': 'INTERAC-PAY-440182',
            'link_clicked': True,
            'client_response': 'PENDING_BANK_DEPOSIT'
        }
    )
    DecisionMemory.objects.create(
        id='dm-008-exec',
        recommendation=r8,
        account_id=a8.id,
        feature_values={'dpd': 14, 'overdue_balance': 740.00, 'contact_count_7d': 0, 'hardship': False, 'dispute': False, 'dnc': False, 'ptp_adherence': 0.98},
        feature_timestamps={'observed_at': (now - timedelta(days=1)).isoformat()},
        feature_version='features-v2.1-online',
        model_id='champion-xgb-cure-v2',
        model_version='2.4.1-calibrated',
        model_prediction=0.91,
        policy_version='policy-fcac-2024.1',
        rule_version='ruleset-v2.1-prod',
        rule_results=build_rule_results(account_status='ACTIVE', dnc=False, cap_count=0, local_hour=11, dispute=False, hardship=False, discount=0),
        candidate_action='digital_reminder_sms',
        human_review_outcome='APPROVED_AND_EXECUTED',
        final_action='digital_reminder_sms',
        correlation_id='corr-008-exec-8831',
        explanation_inputs={
            'counterfactuals': [
                {'scenario': 'Self-cure webhook received', 'condition_change': 'payment_received: True', 'resulting_action': 'no_action_cured', 'rule_impact': 'Account closes arrears queue and restores Good Standing.'}
            ]
        }
    )
    print("  [OK] cust-008 (Fatima Zahra): 1 decision seeded (Executed Digital SMS).")

    # -------------------------------------------------------------
    # CUSTOMER 9: Liam O'Connor (acct-stud-009) - Student Loan Repayment Assistance
    # -------------------------------------------------------------
    a9 = Account.objects.get(id='acct-stud-009')

    # Rec 1 (Historical Rejected)
    r9_rej = Recommendation.objects.create(
        id='rec-009-rej',
        account=a9,
        version=1,
        status=Recommendation.Status.REJECTED,
        target='30-day cure propensity',
        score=0.44,
        model_version='champion-xgb-cure-v2',
        prediction_timestamp=now - timedelta(days=4),
        action='escalated_outbound_call',
        top_features=[
            {'feature': 'days_past_due', 'value': 49, 'importance': 0.38, 'direction': 'negative'},
            {'feature': 'overdue_balance', 'value': 1150.00, 'importance': 0.28, 'direction': 'negative'}
        ],
        review_reason='Rejected by Marcus Vance: borrower enrolled in medical residency program; aggressive outreach violates institutional student fair lending policy.',
        reviewed_by=lead
    )
    ApprovalRequest.objects.create(
        id='00000000-0000-0000-0009-000000000001',
        recommendation=r9_rej,
        recommendation_version=1,
        status=ApprovalRequest.Status.REJECTED,
        requested_by=agent2,
        reviewed_by=lead,
        reason='Rejected by Marcus Vance: Borrower provided proof of hospital residency. Recommending enrollment in Repayment Assistance Plan (RAP) instead of dialer outreach.',
        proposed_action='escalated_outbound_call',
        final_action='student_repayment_assistance_plan',
        idempotency_key='seed-appr-009-rej'
    )
    DecisionMemory.objects.create(
        id='dm-009-rej',
        recommendation=r9_rej,
        account_id=a9.id,
        feature_values={'dpd': 49, 'overdue_balance': 1150.00, 'contact_count_7d': 1, 'hardship': False, 'dispute': False, 'dnc': False},
        feature_timestamps={'observed_at': (now - timedelta(days=4)).isoformat()},
        feature_version='features-v2.1-online',
        model_id='champion-xgb-cure-v2',
        model_version='2.4.1-calibrated',
        model_prediction=0.44,
        policy_version='policy-fcac-2024.1',
        rule_version='ruleset-v2.1-prod',
        rule_results=build_rule_results(account_status='ACTIVE', dnc=False, cap_count=1, local_hour=14, dispute=False, hardship=False, discount=0),
        candidate_action='escalated_outbound_call',
        human_review_outcome='REJECTED_BY_SUPERVISOR',
        final_action='student_repayment_assistance_plan',
        correlation_id='corr-009-rej-7712',
        explanation_inputs={'rejection_note': 'Protected student borrower category.'}
    )

    # Rec 2 (Current Pending RAP)
    r9 = Recommendation.objects.create(
        id='rec-009',
        account=a9,
        version=1,
        status=Recommendation.Status.PENDING_REVIEW,
        target='30-day cure propensity',
        score=0.52,
        model_version='champion-xgb-cure-v2',
        prediction_timestamp=now - timedelta(hours=3),
        action='student_repayment_assistance_plan',
        top_features=[
            {'feature': 'days_past_due', 'value': 49, 'importance': 0.35, 'direction': 'negative'},
            {'feature': 'overdue_balance', 'value': 1150.00, 'importance': 0.25, 'direction': 'negative'},
            {'feature': 'historical_ptp_adherence', 'value': 0.80, 'importance': 0.20, 'direction': 'positive'}
        ],
        review_reason='Enroll in Canadian Repayment Assistance Plan (RAP): monthly installment capped at $120.00 based on verified resident income.',
        reviewed_by=None
    )
    ApprovalRequest.objects.create(
        id='00000000-0000-0000-0009-000000000002',
        recommendation=r9,
        recommendation_version=1,
        status=ApprovalRequest.Status.PENDING_REVIEW,
        requested_by=agent2,
        reviewed_by=None,
        reason='Proposed enrollment in institutional Student Loan Forbearance & Repayment Assistance Plan (monthly payment: $120.00 for 12 months).',
        proposed_action='student_repayment_assistance_plan',
        final_action='',
        idempotency_key='seed-appr-009-curr'
    )
    DecisionMemory.objects.create(
        id='dm-009-curr',
        recommendation=r9,
        account_id=a9.id,
        feature_values={'dpd': 49, 'overdue_balance': 1150.00, 'contact_count_7d': 1, 'hardship': False, 'dispute': False, 'dnc': False},
        feature_timestamps={'observed_at': (now - timedelta(hours=3)).isoformat()},
        feature_version='features-v2.1-online',
        model_id='champion-xgb-cure-v2',
        model_version='2.4.1-calibrated',
        model_prediction=0.52,
        policy_version='policy-fcac-2024.1',
        rule_version='ruleset-v2.1-prod',
        rule_results=build_rule_results(account_status='ACTIVE', dnc=False, cap_count=1, local_hour=14, dispute=False, hardship=False, discount=0),
        candidate_action='student_repayment_assistance_plan',
        human_review_outcome='PENDING_REVIEW',
        final_action='',
        correlation_id='corr-009-curr-3381',
        explanation_inputs={
            'counterfactuals': [
                {'scenario': 'RAP application finalized', 'condition_change': 'rap_enrolled: True', 'resulting_action': 'restructure_payment_plan', 'rule_impact': 'Affordable monthly payments resume with government interest subsidy.'}
            ]
        }
    )
    print("  [OK] cust-009 (Liam O'Connor): 2 decisions seeded (1 Rejected, 1 Pending RAP Plan).")

    # -------------------------------------------------------------
    # CUSTOMER 10: Mei-Ling Zhou (acct-loc-010) - Compassionate Bereavement Hold
    # -------------------------------------------------------------
    a10 = Account.objects.get(id='acct-loc-010')

    # Rec 1 (Historical Escalated)
    r10_hist = Recommendation.objects.create(
        id='rec-010-hist',
        account=a10,
        version=1,
        status=Recommendation.Status.ESCALATED,
        target='30-day cure propensity',
        score=0.14,
        model_version='champion-xgb-cure-v2',
        prediction_timestamp=now - timedelta(days=6),
        action='route_hardship_specialist',
        top_features=[
            {'feature': 'acoustic_distress_signal', 'value': 0.92, 'importance': 0.50, 'direction': 'negative'},
            {'feature': 'days_past_due', 'value': 62, 'importance': 0.28, 'direction': 'negative'},
            {'feature': 'overdue_balance', 'value': 4100.00, 'importance': 0.15, 'direction': 'negative'}
        ],
        review_reason='Whisper signal extraction flagged acoustic distress and spouse bereavement keywords in contact audio. Escalated immediately to Hardship Specialist Elena Rostova.',
        reviewed_by=agent1
    )
    ApprovalRequest.objects.create(
        id='00000000-0000-0000-0010-000000000001',
        recommendation=r10_hist,
        recommendation_version=1,
        status=ApprovalRequest.Status.ESCALATED,
        requested_by=agent1,
        reviewed_by=lead,
        reason='Escalated to Hardship Specialist Elena Rostova: Acoustic sentiment analysis confirmed severe bereavement distress. Mandatory human specialist intervention.',
        proposed_action='route_hardship_specialist',
        final_action='route_hardship_specialist',
        idempotency_key='seed-appr-010-hist'
    )
    DecisionMemory.objects.create(
        id='dm-010-hist',
        recommendation=r10_hist,
        account_id=a10.id,
        feature_values={'dpd': 62, 'overdue_balance': 4100.00, 'contact_count_7d': 1, 'hardship': True, 'dispute': False, 'dnc': False, 'acoustic_distress': 0.92},
        feature_timestamps={'observed_at': (now - timedelta(days=6)).isoformat()},
        feature_version='features-v2.1-online',
        model_id='champion-xgb-cure-v2',
        model_version='2.4.1-calibrated',
        model_prediction=0.14,
        policy_version='policy-fcac-2024.1',
        rule_version='ruleset-v2.1-prod',
        rule_results=build_rule_results(account_status='ACTIVE', dnc=False, cap_count=1, local_hour=14, dispute=False, hardship=True, discount=0),
        candidate_action='route_hardship_specialist',
        human_review_outcome='ESCALATED',
        final_action='route_hardship_specialist',
        correlation_id='corr-010-hist-2241',
        explanation_inputs={
            'acoustic_signals': {'sentiment': 'DISTRESS', 'bereavement_detected': True, 'confidence': 0.94},
            'counterfactuals': [
                {'scenario': 'Compassionate relief expiry', 'condition_change': 'moratorium_completed: True (after 90 days)', 'resulting_action': 'restructure_payment_plan', 'rule_impact': 'Specialist conducts dignified re-entry assessment.'}
            ]
        }
    )

    # Rec 2 (Current Approved Compassionate Moratorium)
    r10 = Recommendation.objects.create(
        id='rec-010',
        account=a10,
        version=1,
        status=Recommendation.Status.APPROVED,
        target='30-day cure propensity',
        score=0.12,
        model_version='champion-xgb-cure-v2',
        prediction_timestamp=now - timedelta(hours=2),
        action='compassionate_hold_90d',
        top_features=[
            {'feature': 'acoustic_distress_signal', 'value': 0.92, 'importance': 0.52, 'direction': 'negative'},
            {'feature': 'days_past_due', 'value': 62, 'importance': 0.25, 'direction': 'negative'},
            {'feature': 'overdue_balance', 'value': 4100.00, 'importance': 0.15, 'direction': 'negative'}
        ],
        review_reason='Specialist Elena Rostova approved 90-day complete moratorium on all outbound telephone and postal contacts; interest suspended under bereavement relief guideline.',
        reviewed_by=specialist
    )
    ApprovalRequest.objects.create(
        id='00000000-0000-0000-0010-000000000002',
        recommendation=r10,
        recommendation_version=1,
        status=ApprovalRequest.Status.APPROVED,
        requested_by=specialist,
        reviewed_by=specialist,
        reason='Hardship Specialist Elena Rostova approved 90-day compassionate bereavement relief hold. All recovery efforts suppressed; interest accrual frozen.',
        proposed_action='compassionate_hold_90d',
        final_action='compassionate_hold_90d',
        idempotency_key='seed-appr-010-curr'
    )
    DecisionMemory.objects.create(
        id='dm-010-curr',
        recommendation=r10,
        account_id=a10.id,
        feature_values={'dpd': 62, 'overdue_balance': 4100.00, 'contact_count_7d': 1, 'hardship': True, 'dispute': False, 'dnc': False, 'acoustic_distress': 0.92},
        feature_timestamps={'observed_at': (now - timedelta(hours=2)).isoformat()},
        feature_version='features-v2.1-online',
        model_id='champion-xgb-cure-v2',
        model_version='2.4.1-calibrated',
        model_prediction=0.12,
        policy_version='policy-fcac-2024.1',
        rule_version='ruleset-v2.1-prod',
        rule_results=build_rule_results(account_status='ACTIVE', dnc=False, cap_count=1, local_hour=14, dispute=False, hardship=True, discount=0),
        candidate_action='compassionate_hold_90d',
        human_review_outcome='APPROVED',
        final_action='compassionate_hold_90d',
        correlation_id='corr-010-curr-8812',
        explanation_inputs={
            'counterfactuals': [
                {'scenario': 'Compassionate relief expiry', 'condition_change': 'moratorium_completed: True (after 90 days)', 'resulting_action': 'restructure_payment_plan', 'rule_impact': 'Specialist conducts dignified re-entry assessment.'}
            ],
            'moratorium_duration_days': 90,
            'approved_by': 'Elena Rostova (Hardship Specialist)'
        }
    )
    print("  [OK] cust-010 (Mei-Ling Zhou): 2 decisions seeded (1 Escalated, 1 Approved Compassionate Hold).")

    print("\n=== Seeding Complete ===")
    print(f"Total RuleSetVersions: {RuleSetVersion.objects.count()}")
    print(f"Total Recommendations: {Recommendation.objects.count()}")
    print(f"Total Approvals:       {ApprovalRequest.objects.count()}")
    print(f"Total DecisionMemories:{DecisionMemory.objects.count()}")


if __name__ == '__main__':
    seed_decisioning()
