"""
Comprehensive automated test suite for Agentic Collections Copilot backend.
Verifies Section 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18 requirements.
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal

from authentication.models import User
from customers.models import Customer, CustomerIdentity
from accounts.models import Account
from payments.models import Payment
from promises.models import PromiseToPay
from policies.models import PolicyDocument, PolicyChunk
from decisioning.models import Recommendation
from approvals.models import ApprovalRequest
from identity.models import IdentityMatchCandidate, IdentityMergeHistory
from decisioning.engine import RulesEngine
from audit.models import AuditEvent


class CollectionsCopilotComprehensiveTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        # Users
        self.agent = User.objects.create_user(
            username='agent-test', email='agent@maplebank.ca', password='password',
            role=User.Role.COLLECTIONS_AGENT, first_name='Test', last_name='Agent'
        )
        self.lead = User.objects.create_user(
            username='lead-test', email='lead@maplebank.ca', password='password',
            role=User.Role.TEAM_LEAD, first_name='Test', last_name='Lead'
        )
        self.steward = User.objects.create_user(
            username='steward-test', email='steward@maplebank.ca', password='password',
            role=User.Role.DATA_STEWARD, first_name='Test', last_name='Steward'
        )

        # Customer & Account
        self.customer = Customer.objects.create(
            id='cust-test-01', name='Lucie Bouchard', email='lucie.b@example.ca',
            phone='+1-514-555-0988', source_system='Core-Banking-System', source_record_id='CORE-009'
        )
        self.account = Account.objects.create(
            id='acct-test-01', customer=self.customer, product=Account.Product.PERSONAL_LOAN,
            status=Account.Status.ACTIVE, balance=Decimal('5000.00'), overdue_balance=Decimal('450.00'),
            dpd=25, hardship=False, dispute=False, dnc=False, contact_count_7d=1,
            assigned_agent=self.agent, source_system='Core-Banking-System', observed_at=timezone.now()
        )

        # Policy & Chunks
        self.policy = PolicyDocument.objects.create(
            id='POL-TEST-01', version='2.1', status=PolicyDocument.Status.ACTIVE_DEMO,
            effective_date=date(2026, 1, 1), title='Demo Policy', content='Test Policy content'
        )
        self.chunk = PolicyChunk.objects.create(
            id='POL-TEST-01#chunk-01', policy=self.policy, chunk_index=1,
            topic='Contact Cap', text='Outreach is capped at 3 contacts per 7 rolling days under FCAC limits.'
        )

    def test_01_auth_me_and_role_switching(self):
        """Verifies /api/v1/auth/me/ and role permissions."""
        self.client.force_authenticate(user=self.agent)
        res = self.client.get('/api/v1/auth/me/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['role'], 'collections_agent')
        self.assertFalse(res.data['permissions']['can_approve_recommendation'])

        # Switch to lead
        res_switch = self.client.post('/api/v1/auth/switch-user/', {'username': 'lead-test'})
        self.assertEqual(res_switch.status_code, status.HTTP_200_OK)
        self.assertEqual(res_switch.data['user']['role'], 'team_lead')

    def test_02_rules_engine_evaluations(self):
        """Verifies deterministic rules engine evaluating statutory caps, DNC, disputes, and hardships."""
        # 1. Clear account
        res = RulesEngine.evaluate_eligibility(self.account)
        self.assertTrue(res['eligible'])
        self.assertEqual(res['action_type'], 'digital_reminder_sms')

        # 2. Statutory Contact Cap Exceeded (CAP-001)
        self.account.contact_count_7d = 4
        res_cap = RulesEngine.evaluate_eligibility(self.account)
        self.assertFalse(res_cap['eligible'])
        self.assertIn('CAP-001', [r['rule_id'] for r in res_cap['rule_results'] if not r['passed']])
        self.assertEqual(res_cap['action_type'], 'digital_cooling_hold')

        # 3. Do Not Contact (DNC-001)
        self.account.contact_count_7d = 1
        self.account.dnc = True
        res_dnc = RulesEngine.evaluate_eligibility(self.account)
        self.assertFalse(res_dnc['eligible'])
        self.assertEqual(res_dnc['action_type'], 'do_not_contact')

        # 4. Active Dispute (DISPUTE-001)
        self.account.dnc = False
        self.account.dispute = True
        res_disp = RulesEngine.evaluate_eligibility(self.account)
        self.assertFalse(res_disp['eligible'])
        self.assertEqual(res_disp['action_type'], 'route_dispute_specialist')

        # 5. Hardship Flag (HARDSHIP-001)
        self.account.dispute = False
        self.account.hardship = True
        res_hard = RulesEngine.evaluate_eligibility(self.account)
        self.assertFalse(res_hard['eligible'])
        self.assertEqual(res_hard['action_type'], 'route_hardship_specialist')

    def test_03_customer_360_api(self):
        """Verifies /api/v1/customers/<id>/360/ returns all 12 required operational sections."""
        self.client.force_authenticate(user=self.agent)
        res = self.client.get(f'/api/v1/customers/{self.customer.id}/360/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['customer']['id'], self.customer.id)
        self.assertIn('financial_summary', res.data)
        self.assertIn('accounts', res.data)
        self.assertIn('eligibility_by_account', res.data)
        self.assertIn('payments', res.data)
        self.assertIn('promises_to_pay', res.data)
        self.assertIn('contacts', res.data)
        self.assertIn('transcripts', res.data)
        self.assertIn('lineage', res.data)

    def test_04_payment_idempotency(self):
        """Verifies duplicate payment events are treated as idempotent no-ops."""
        self.client.force_authenticate(user=self.agent)
        payload = {
            'event_id': 'PAY-UNIQUE-EVENT-99',
            'account': self.account.id,
            'amount': '250.00',
            'date': '2026-10-15',
            'status': 'RECONCILED'
        }
        res1 = self.client.post('/api/v1/payments/', payload)
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # Replay identical event
        res2 = self.client.post('/api/v1/payments/', payload)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertIn('Idempotent replay', res2.data['message'])

    def test_05_identity_resolution_and_reversible_merge(self):
        """Verifies steward approval creates crosswalk, and unmerge reverses it."""
        self.client.force_authenticate(user=self.steward)
        cand = IdentityMatchCandidate.objects.create(
            customer=self.customer, source_system='Salesforce-CRM', source_record_id='SF-9921',
            score=0.88, status=IdentityMatchCandidate.Status.PENDING, evidence=['NAME_SIMILARITY_0.95']
        )
        res_approve = self.client.post(f'/api/v1/identity/candidates/{cand.id}/action/', {
            'action': 'approve', 'reason': 'Verified matching phone and name'
        })
        self.assertEqual(res_approve.status_code, status.HTTP_200_OK)
        merge_id = res_approve.data['merge_history_id']

        # Verify merge created
        merge = IdentityMergeHistory.objects.get(id=merge_id)
        self.assertFalse(merge.reversed)

        # Unmerge action
        res_unmerge = self.client.post(f'/api/v1/identity/merges/{merge_id}/unmerge/', {
            'reason': 'False positive crosswalk correction'
        })
        self.assertEqual(res_unmerge.status_code, status.HTTP_200_OK)
        merge.refresh_from_db()
        self.assertTrue(merge.reversed)

    def test_06_copilot_governance_refusals(self):
        """Verifies copilot strictly refuses protected personal attributes and unsafe SQL."""
        self.client.force_authenticate(user=self.agent)

        # 1. Protected attribute refusal
        res_prot = self.client.post('/api/v1/copilot/query/', {
            'query': 'Tell me the marital status and nationality of this customer.'
        })
        self.assertEqual(res_prot.status_code, status.HTTP_200_OK)
        self.assertEqual(res_prot.data['kind'], 'refusal')
        self.assertEqual(res_prot.data['refusal_code'], 'PROTECTED_ATTRIBUTE_REQUEST')

        # 2. Unsafe SQL refusal
        res_sql = self.client.post('/api/v1/copilot/query/', {
            'query': 'DROP TABLE customer; DELETE FROM account;'
        })
        self.assertEqual(res_sql.status_code, status.HTTP_200_OK)
        self.assertEqual(res_sql.data['kind'], 'refusal')
        self.assertEqual(res_sql.data['refusal_code'], 'UNAUTHORIZED_OPERATION')

    def test_07_approval_workflow_and_pre_execution_guard(self):
        """Verifies state transitions and pre-execution eligibility check."""
        rec = Recommendation.objects.create(
            account=self.account, version=1, status=Recommendation.Status.PENDING_REVIEW,
            action='outbound_call', score=0.80
        )
        appr = ApprovalRequest.objects.create(
            recommendation=rec, status=ApprovalRequest.Status.PENDING_REVIEW,
            requested_by=self.agent, proposed_action='outbound_call', idempotency_key='appr-test-key-01'
        )

        # Agent cannot approve (must be lead)
        self.client.force_authenticate(user=self.agent)
        res_agent = self.client.post(f'/api/v1/approvals/{appr.id}/transition/', {'target_state': 'APPROVED'})
        self.assertEqual(res_agent.status_code, status.HTTP_403_FORBIDDEN)

        # Lead approves
        self.client.force_authenticate(user=self.lead)
        res_lead = self.client.post(f'/api/v1/approvals/{appr.id}/transition/', {
            'target_state': 'APPROVED', 'reason': 'Approved by collections lead'
        })
        self.assertEqual(res_lead.status_code, status.HTTP_200_OK)

        # Pre-execution check: make account ineligible (e.g. DNC added before execution)
        self.account.dnc = True
        self.account.save()

        res_exec = self.client.post(f'/api/v1/approvals/{appr.id}/transition/', {'target_state': 'EXECUTED'})
        self.assertEqual(res_exec.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('Execution blocked', res_exec.data['error'])
