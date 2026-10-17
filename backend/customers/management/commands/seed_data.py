"""
Deterministic synthetic demonstration dataset seeding command per Section 16.
Creates multi-product customers, payments, reversals, kept/broken PTPs, DPD buckets,
hardship flags, open disputes, regulatory DNC restrictions, contact cap violations,
probabilistic identity candidates, policy documents with chunks, feature store metrics,
registered ML models, recommendations, approvals, and experiment cohorts.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import uuid

from authentication.models import User
from customers.models import Customer, CustomerIdentity, SourceSystem
from accounts.models import Account
from payments.models import Payment
from promises.models import PromiseToPay
from calls.models import CollectionContact, CallTranscript, HardshipCase, Dispute
from identity.models import IdentityMatchCandidate, IdentityMergeHistory
from policies.models import PolicyDocument, PolicyChunk
from features.models import FeatureDefinition, FeatureSnapshot
from models_ml.models import ModelRegistry, Prediction
from decisioning.models import RuleSetVersion, Recommendation, DecisionMemory
from approvals.models import ApprovalRequest
from assignments.models import AgentProfile, QueueAssignment
from experiments.models import Experiment, ExperimentCohort, MetricSnapshot
from audit.utils import log_audit


class Command(BaseCommand):
    help = "Seeds deterministic demonstration data covering all Section 16 scenarios."

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Wipe existing tables before seeding')

    def handle(self, *args, **options):
        self.stdout.write("Seeding Agentic Collections Copilot database...")

        # 1. Users for all 5 roles
        self.stdout.write("Creating demo user personas...")
        agent, _ = User.objects.get_or_create(
            username='agent-001',
            defaults={'first_name': 'Sarah', 'last_name': 'Jenkins', 'email': 'sarah.jenkins@maplebank.ca', 'role': User.Role.COLLECTIONS_AGENT}
        )
        agent2, _ = User.objects.get_or_create(
            username='agent-002',
            defaults={'first_name': 'Liam', 'last_name': 'Tremblay', 'email': 'liam.tremblay@maplebank.ca', 'role': User.Role.COLLECTIONS_AGENT}
        )
        lead, _ = User.objects.get_or_create(
            username='lead-001',
            defaults={'first_name': 'Marcus', 'last_name': 'Vance', 'email': 'marcus.vance@maplebank.ca', 'role': User.Role.TEAM_LEAD}
        )
        specialist, _ = User.objects.get_or_create(
            username='specialist-001',
            defaults={'first_name': 'Elena', 'last_name': 'Rostova', 'email': 'elena.rostova@maplebank.ca', 'role': User.Role.HARDSHIP_SPECIALIST}
        )
        steward, _ = User.objects.get_or_create(
            username='steward-001',
            defaults={'first_name': 'David', 'last_name': 'Chen', 'email': 'david.chen@maplebank.ca', 'role': User.Role.DATA_STEWARD}
        )
        admin_user, _ = User.objects.get_or_create(
            username='admin-001',
            defaults={'first_name': 'Rachel', 'last_name': 'Kim', 'email': 'rachel.kim@maplebank.ca', 'role': User.Role.ADMINISTRATOR}
        )

        # Agent profiles
        AgentProfile.objects.get_or_create(
            user=agent,
            defaults={'max_active_cases': 60, 'current_workload': 18, 'skills': ['tier1_early', 'personal_loans', 'sms_channel']}
        )
        AgentProfile.objects.get_or_create(
            user=agent2,
            defaults={'max_active_cases': 50, 'current_workload': 24, 'skills': ['tier2_late', 'credit_cards', 'bilingual_fr']}
        )

        # 2. Source Systems
        self.stdout.write("Registering source systems...")
        for name in ['Core-Banking-System', 'Card-Management-TSYS', 'Salesforce-CRM', 'Collections-Dialer', 'Equifax-Bureau']:
            SourceSystem.objects.get_or_create(name=name, defaults={'status': 'DEMO_ADAPTER', 'last_refresh': timezone.now()})

        # 3. Policy Documents with chunks for RAG
        self.stdout.write("Publishing policy library with traceable chunks...")
        pol_active, _ = PolicyDocument.objects.get_or_create(
            id='POL-MAPLE-2026-V21',
            defaults={
                'version': '2.1',
                'status': PolicyDocument.Status.ACTIVE_DEMO,
                'effective_date': date(2026, 1, 1),
                'title': 'Maple Bank Collections Operational Governance Policy (v2.1)',
                'content': 'Comprehensive collections standard operating procedure covering contact limits, hardship, disputes, and consent restrictions.',
                'access_classification': 'internal',
                'approved_by': admin_user
            }
        )

        PolicyChunk.objects.get_or_create(
            id='POL-MAPLE-2026-V21#chunk-01',
            defaults={
                'policy': pol_active,
                'chunk_index': 1,
                'topic': 'Contact Frequency and Statutory Caps (CAP-001)',
                'text': 'Under Canadian FCAC regulations and Maple Bank standard operations, collections outreach is strictly capped at three (3) contacts within any rolling seven (7) day period across all channels. Any outbound call or SMS that would result in a fourth contact is strictly prohibited.'
            }
        )
        PolicyChunk.objects.get_or_create(
            id='POL-MAPLE-2026-V21#chunk-02',
            defaults={
                'policy': pol_active,
                'chunk_index': 2,
                'topic': 'Do-Not-Contact and Written-Only Demands (DNC-001)',
                'text': 'When a borrower requests communication in writing only or submits a verified Do-Not-Contact (DNC) request, all voice telephony, automated dialing, and SMS solicitations must be suspended immediately. Communications are restricted exclusively to formal mail notifications.'
            }
        )
        PolicyChunk.objects.get_or_create(
            id='POL-MAPLE-2026-V21#chunk-03',
            defaults={
                'policy': pol_active,
                'chunk_index': 3,
                'topic': 'Customer Hardship and Vulnerability Protocols (HARDSHIP-001)',
                'text': 'Borrowers demonstrating temporary financial distress due to medical circumstance, employment disruption, or family emergency must be transferred to the Vulnerable Customer Care & Hardship Team. Ordinary enforcement, interest accumulation, and aggressive outbound calls must be halted pending review.'
            }
        )
        PolicyChunk.objects.get_or_create(
            id='POL-MAPLE-2026-V21#chunk-04',
            defaults={
                'policy': pol_active,
                'chunk_index': 4,
                'topic': 'Formal Disputes and Billing Inquiries (DISPUTE-001)',
                'text': 'If a customer disputes loan charges, interest calculation, or unauthorized card transactions, collections actions on the disputed amount must be suspended until dispute adjudication is certified complete by the dispute operations unit.'
            }
        )

        # 4. Feature Definitions
        self.stdout.write("Registering feature store definitions...")
        features_data = [
            ('days_past_due', 'account.id', 'integer', 'Days past due based on snapshot date'),
            ('overdue_balance', 'account.id', 'decimal', 'Total arrears balance overdue'),
            ('contact_count_7d', 'account.id', 'integer', 'Contact events in rolling 7 days'),
            ('historical_ptp_adherence', 'customer.id', 'float', 'Proportion of historical promises kept'),
            ('recent_payment_count', 'account.id', 'integer', 'Count of payments within 90 days'),
            ('recent_payment_amount', 'account.id', 'decimal', 'Sum of payments within 90 days'),
            ('days_since_last_payment', 'account.id', 'integer', 'Elapsed days since last reconciled payment'),
            ('average_monthly_spend', 'account.id', 'decimal', 'Rolling 6-month average debit or card spend'),
            ('credit_utilization_ratio', 'account.id', 'float', 'Balance divided by available limit'),
            ('bureau_risk_score', 'customer.id', 'integer', 'Equifax credit risk score'),
        ]
        for name, key, dtype, desc in features_data:
            FeatureDefinition.objects.get_or_create(
                name=name,
                defaults={
                    'entity_key': key,
                    'data_type': dtype,
                    'description': desc,
                    'calculation_logic': f'SELECT {name} FROM silver_feature_store',
                    'observation_window': '30d',
                    'source_lineage': 'silver_account_features',
                    'version': 'demo-features-v2.1',
                    'leakage_safe': True
                }
            )

        # 5. ML Model Registry
        self.stdout.write("Registering ML models...")
        model_champion, _ = ModelRegistry.objects.get_or_create(
            id='champion-xgb-cure-v2',
            defaults={
                'target': '30-day cure propensity',
                'status': ModelRegistry.Status.DEPLOYED,
                'calibrated': True,
                'trained': True,
                'explanation': 'Gradient boosted tree calibrated via isotonic regression predicting cure without legal escalation.',
                'artifact_path': 'models/champion_xgb_v2.json'
            }
        )
        model_challenger, _ = ModelRegistry.objects.get_or_create(
            id='challenger-lgbm-cure-v1',
            defaults={
                'target': '30-day cure propensity',
                'status': ModelRegistry.Status.VALIDATED,
                'calibrated': True,
                'trained': True,
                'explanation': 'LightGBM challenger model optimized for early-stage digital payment response.',
                'artifact_path': 'models/challenger_lgbm_v1.json'
            }
        )

        # 6. Customers and Accounts (Scenarios covering all Section 16 rules)
        self.stdout.write("Creating synthetic customers and multi-product accounts...")

        now_dt = timezone.now()

        # Customer 1: Normal Eligible Case (Early delinquency, high cure probability)
        c1, _ = Customer.objects.get_or_create(
            id='cust-001',
            defaults={
                'name': 'Alexandre Tremblay',
                'email': 'a.tremblay@example.ca',
                'phone': '+1-514-555-0142',
                'date_of_birth': date(1986, 5, 14),
                'address': '452 Rue Sherbrooke, Montreal, QC H2X 1E6',
                'source_system': 'Core-Banking-System',
                'source_record_id': 'CORE-CUST-88310',
                'observed_at': now_dt - timedelta(hours=2),
                'transformation_version': 'golden-v2.1'
            }
        )
        CustomerIdentity.objects.get_or_create(
            customer=c1, source_system='Core-Banking-System', source_id='CORE-CUST-88310',
            defaults={'match_type': CustomerIdentity.MatchType.EXACT, 'score': 1.0, 'evidence': ['SIN_MATCH', 'NAME_DOB_MATCH']}
        )
        CustomerIdentity.objects.get_or_create(
            customer=c1, source_system='Salesforce-CRM', source_id='SF-099412',
            defaults={'match_type': CustomerIdentity.MatchType.EXACT, 'score': 1.0, 'evidence': ['EMAIL_PHONE_EXACT']}
        )

        a1, _ = Account.objects.get_or_create(
            id='acct-loan-001',
            defaults={
                'customer': c1,
                'product': Account.Product.PERSONAL_LOAN,
                'status': Account.Status.ACTIVE,
                'balance': Decimal('14500.00'),
                'overdue_balance': Decimal('480.00'),
                'dpd': 18,
                'hardship': False,
                'dispute': False,
                'dnc': False,
                'contact_count_7d': 1,
                'assigned_agent': agent,
                'source_system': 'Core-Banking-System',
                'source_record_id': 'LOAN-88310-A',
                'observed_at': now_dt - timedelta(hours=2),
                'recent_payment_count': 3,
                'recent_payment_amount': Decimal('1440.00'),
                'historical_ptp_adherence': 0.90,
                'days_since_last_payment': 48
            }
        )
        Payment.objects.get_or_create(
            event_id='PAY-EVT-001A',
            defaults={
                'id': 'pay-001', 'account': a1, 'amount': Decimal('480.00'), 'status': Payment.Status.RECONCILED,
                'date': date(2026, 8, 15), 'source_system': 'Core-Banking-System'
            }
        )
        PromiseToPay.objects.get_or_create(
            id='ptp-001',
            defaults={
                'account': a1, 'amount': Decimal('480.00'), 'due_date': date(2026, 10, 24),
                'status': PromiseToPay.Status.PENDING, 'source_system': 'collections'
            }
        )
        CollectionContact.objects.get_or_create(
            id='contact-001',
            defaults={
                'account': a1, 'date': date(2026, 10, 10), 'channel': CollectionContact.Channel.SMS,
                'outcome': 'Reminder delivered; customer confirmed receipt', 'agent': agent, 'source_system': 'dialer'
            }
        )
        CallTranscript.objects.get_or_create(
            id='transcript-001',
            defaults={
                'account': a1, 'language': 'fr',
                'text': 'Agent: Bonjour M. Tremblay, nous vous contactons concernant votre solde en souffrance. Client: Oui, je vais payer ce vendredi dès que ma paie est déposée. Agent: Parfait, nous notons cette promesse.',
                'signals': [{'signal': 'payment_intent', 'confidence': 0.94}], 'source_system': 'transcription-adapter'
            }
        )

        rec1, _ = Recommendation.objects.get_or_create(
            id='rec-001',
            defaults={
                'account': a1, 'version': 1, 'status': Recommendation.Status.PENDING_REVIEW,
                'target': '30-day cure propensity', 'score': 0.86, 'model_version': 'champion-xgb-cure-v2',
                'action': 'digital_reminder_sms',
                'top_features': [
                    {'feature': 'historical_ptp_adherence', 'value': 0.90, 'importance': 0.38, 'direction': 'positive'},
                    {'feature': 'recent_payment_count', 'value': 3, 'importance': 0.25, 'direction': 'positive'},
                    {'feature': 'days_past_due', 'value': 18, 'importance': 0.18, 'direction': 'neutral'}
                ],
                'idempotency_key': 'rec-key-001'
            }
        )
        ApprovalRequest.objects.get_or_create(
            idempotency_key='appr-key-001',
            defaults={
                'recommendation': rec1, 'recommendation_version': 1, 'status': ApprovalRequest.Status.PENDING_REVIEW,
                'requested_by': agent, 'proposed_action': 'digital_reminder_sms'
            }
        )
        QueueAssignment.objects.get_or_create(
            account=a1,
            defaults={'assigned_agent': agent, 'priority_score': 84.5, 'status': QueueAssignment.Status.ASSIGNED, 'routing_reason': 'Priority early-stage loan'}
        )

        # Customer 2: Contact-Cap Exceeded (Violates CAP-001: 4 contacts in 7 days)
        c2, _ = Customer.objects.get_or_create(
            id='cust-002',
            defaults={
                'name': 'Priya Patel',
                'email': 'priya.patel@example.ca',
                'phone': '+1-416-555-0891',
                'date_of_birth': date(1992, 11, 28),
                'address': '180 University Ave, Toronto, ON M5H 0A2',
                'source_system': 'Card-Management-TSYS',
                'source_record_id': 'CARD-PATEL-4421',
                'observed_at': now_dt - timedelta(hours=1),
                'transformation_version': 'golden-v2.1'
            }
        )
        CustomerIdentity.objects.get_or_create(
            customer=c2, source_system='Card-Management-TSYS', source_id='CARD-PATEL-4421',
            defaults={'match_type': CustomerIdentity.MatchType.EXACT, 'score': 1.0, 'evidence': ['CARD_HASH_MATCH']}
        )
        a2, _ = Account.objects.get_or_create(
            id='acct-card-002',
            defaults={
                'customer': c2,
                'product': Account.Product.CREDIT_CARD,
                'status': Account.Status.ACTIVE,
                'balance': Decimal('6200.00'),
                'overdue_balance': Decimal('1250.00'),
                'dpd': 42,
                'hardship': False,
                'dispute': False,
                'dnc': False,
                'contact_count_7d': 4,  # EXCEEDS CAP!
                'assigned_agent': agent,
                'source_system': 'Card-Management-TSYS',
                'source_record_id': 'TSYS-ACCT-9921',
                'observed_at': now_dt - timedelta(hours=1),
                'recent_payment_count': 1,
                'recent_payment_amount': Decimal('200.00'),
                'historical_ptp_adherence': 0.60,
                'days_since_last_payment': 65
            }
        )
        rec2, _ = Recommendation.objects.get_or_create(
            id='rec-002',
            defaults={
                'account': a2, 'version': 1, 'status': Recommendation.Status.PENDING_REVIEW,
                'target': '30-day cure propensity', 'score': 0.45, 'model_version': 'champion-xgb-cure-v2',
                'action': 'digital_cooling_hold',
                'top_features': [
                    {'feature': 'contact_count_7d', 'value': 4, 'importance': 0.50, 'direction': 'negative'},
                    {'feature': 'days_past_due', 'value': 42, 'importance': 0.30, 'direction': 'negative'}
                ],
                'idempotency_key': 'rec-key-002'
            }
        )
        ApprovalRequest.objects.get_or_create(
            idempotency_key='appr-key-002',
            defaults={
                'recommendation': rec2, 'recommendation_version': 1, 'status': ApprovalRequest.Status.PENDING_REVIEW,
                'requested_by': agent, 'proposed_action': 'digital_cooling_hold',
                'reason': 'Account held in digital cooling period due to statutory 7-day contact cap.'
            }
        )
        QueueAssignment.objects.get_or_create(
            account=a2,
            defaults={'assigned_agent': agent, 'priority_score': 32.0, 'status': QueueAssignment.Status.ASSIGNED, 'routing_reason': 'Held: Contact cap reached'}
        )

        # Customer 3: Hardship Case & Broken Promise (Vulnerability & Broken PTP)
        c3, _ = Customer.objects.get_or_create(
            id='cust-003',
            defaults={
                'name': 'Sarah Al-Mansoor',
                'email': 'sarah.almansoor@example.ca',
                'phone': '+1-604-555-0312',
                'date_of_birth': date(1979, 3, 21),
                'address': '1055 W Georgia St, Vancouver, BC V6E 3P3',
                'source_system': 'Core-Banking-System',
                'source_record_id': 'CORE-CUST-77412',
                'observed_at': now_dt - timedelta(hours=5),
                'transformation_version': 'golden-v2.1'
            }
        )
        a3, _ = Account.objects.get_or_create(
            id='acct-mortgage-003',
            defaults={
                'customer': c3,
                'product': Account.Product.MORTGAGE,
                'status': Account.Status.ACTIVE,
                'balance': Decimal('385000.00'),
                'overdue_balance': Decimal('3420.00'),
                'dpd': 64,
                'hardship': True,  # Active Hardship!
                'dispute': False,
                'dnc': False,
                'contact_count_7d': 0,
                'assigned_agent': specialist,
                'source_system': 'Core-Banking-System',
                'source_record_id': 'MORT-77412-1',
                'observed_at': now_dt - timedelta(hours=5),
                'recent_payment_count': 0,
                'recent_payment_amount': Decimal('0.00'),
                'historical_ptp_adherence': 0.30,
                'days_since_last_payment': 92
            }
        )
        HardshipCase.objects.get_or_create(
            id='hardship-001',
            defaults={
                'account': a3, 'status': HardshipCase.Status.UNDER_REVIEW, 'source': 'Customer Inbound / Medical Notice',
                'specialist_required': True, 'notes': 'Borrower undergoing medical leave. Requesting 3-month payment suspension.'
            }
        )
        PromiseToPay.objects.get_or_create(
            id='ptp-003',
            defaults={
                'account': a3, 'amount': Decimal('3420.00'), 'due_date': date(2026, 9, 30),
                'status': PromiseToPay.Status.BROKEN, 'source_system': 'collections'
            }
        )
        rec3, _ = Recommendation.objects.get_or_create(
            id='rec-003',
            defaults={
                'account': a3, 'version': 1, 'status': Recommendation.Status.ESCALATED,
                'target': '30-day cure propensity', 'score': 0.15, 'model_version': 'champion-xgb-cure-v2',
                'action': 'route_hardship_specialist',
                'top_features': [
                    {'feature': 'hardship_flag', 'value': 1, 'importance': 0.60, 'direction': 'negative'},
                    {'feature': 'days_past_due', 'value': 64, 'importance': 0.30, 'direction': 'negative'}
                ],
                'idempotency_key': 'rec-key-003'
            }
        )
        ApprovalRequest.objects.get_or_create(
            idempotency_key='appr-key-003',
            defaults={
                'recommendation': rec3, 'recommendation_version': 1, 'status': ApprovalRequest.Status.ESCALATED,
                'requested_by': agent, 'reviewed_by': lead, 'proposed_action': 'route_hardship_specialist',
                'reason': 'Escalated to Hardship Specialist per HARDSHIP-001 protocol.'
            }
        )

        # Customer 4: Formal Dispute & Payment Reversal (DISPUTE-001)
        c4, _ = Customer.objects.get_or_create(
            id='cust-004',
            defaults={
                'name': 'Dmitri Volkov',
                'email': 'd.volkov@example.ca',
                'phone': '+1-403-555-0721',
                'date_of_birth': date(1982, 8, 9),
                'address': '530 8 Ave SW, Calgary, AB T2P 3S8',
                'source_system': 'Core-Banking-System',
                'source_record_id': 'CORE-CUST-99411',
                'observed_at': now_dt - timedelta(hours=3),
                'transformation_version': 'golden-v2.1'
            }
        )
        a4, _ = Account.objects.get_or_create(
            id='acct-card-004',
            defaults={
                'customer': c4,
                'product': Account.Product.CREDIT_CARD,
                'status': Account.Status.ACTIVE,
                'balance': Decimal('4890.00'),
                'overdue_balance': Decimal('890.00'),
                'dpd': 35,
                'hardship': False,
                'dispute': True,  # Active Dispute!
                'dnc': False,
                'contact_count_7d': 1,
                'assigned_agent': agent2,
                'source_system': 'Card-Management-TSYS',
                'source_record_id': 'TSYS-VOLKOV-1',
                'observed_at': now_dt - timedelta(hours=3),
                'recent_payment_count': 1,
                'recent_payment_amount': Decimal('890.00'),
                'historical_ptp_adherence': 0.75,
                'days_since_last_payment': 35
            }
        )
        Dispute.objects.get_or_create(
            id='dispute-001',
            defaults={
                'account': a4, 'status': Dispute.Status.UNDER_INVESTIGATION, 'source': 'Customer Card Billing Challenge',
                'collection_action_blocked': True, 'notes': 'Unauthorized merchant charge of $890.00 on 2026-09-02 currently under investigation.'
            }
        )
        Payment.objects.get_or_create(
            event_id='PAY-EVT-004-REV',
            defaults={
                'id': 'pay-004-rev', 'account': a4, 'amount': Decimal('890.00'), 'status': Payment.Status.REVERSED,
                'date': date(2026, 9, 10), 'source_system': 'Card-Management-TSYS'
            }
        )
        rec4, _ = Recommendation.objects.get_or_create(
            id='rec-004',
            defaults={
                'account': a4, 'version': 1, 'status': Recommendation.Status.PENDING_REVIEW,
                'target': '30-day cure propensity', 'score': 0.25, 'model_version': 'champion-xgb-cure-v2',
                'action': 'route_dispute_specialist',
                'top_features': [
                    {'feature': 'open_dispute', 'value': 1, 'importance': 0.55, 'direction': 'negative'},
                    {'feature': 'payment_reversed', 'value': 1, 'importance': 0.25, 'direction': 'negative'}
                ],
                'idempotency_key': 'rec-key-004'
            }
        )
        ApprovalRequest.objects.get_or_create(
            idempotency_key='appr-key-004',
            defaults={
                'recommendation': rec4, 'recommendation_version': 1, 'status': ApprovalRequest.Status.PENDING_REVIEW,
                'requested_by': agent2, 'proposed_action': 'route_dispute_specialist'
            }
        )

        # Customer 5: Do-Not-Contact Restriction (DNC-001)
        c5, _ = Customer.objects.get_or_create(
            id='cust-005',
            defaults={
                'name': 'Fiona Gallagher',
                'email': 'fiona.g@example.ca',
                'phone': '+1-902-555-0619',
                'date_of_birth': date(1995, 7, 19),
                'address': '1800 Argyle St, Halifax, NS B3J 3N8',
                'source_system': 'Core-Banking-System',
                'source_record_id': 'CORE-CUST-33120',
                'observed_at': now_dt - timedelta(hours=4),
                'transformation_version': 'golden-v2.1'
            }
        )
        a5, _ = Account.objects.get_or_create(
            id='acct-loc-005',
            defaults={
                'customer': c5,
                'product': Account.Product.LINE_OF_CREDIT,
                'status': Account.Status.ACTIVE,
                'balance': Decimal('12000.00'),
                'overdue_balance': Decimal('2100.00'),
                'dpd': 55,
                'hardship': False,
                'dispute': False,
                'dnc': True,  # Mandatory DNC Restriction!
                'contact_count_7d': 0,
                'assigned_agent': agent,
                'source_system': 'Core-Banking-System',
                'source_record_id': 'LOC-33120-1',
                'observed_at': now_dt - timedelta(hours=4),
                'recent_payment_count': 0,
                'recent_payment_amount': Decimal('0.00'),
                'historical_ptp_adherence': 0.50,
                'days_since_last_payment': 70
            }
        )
        rec5, _ = Recommendation.objects.get_or_create(
            id='rec-005',
            defaults={
                'account': a5, 'version': 1, 'status': Recommendation.Status.PENDING_REVIEW,
                'target': '30-day cure propensity', 'score': 0.10, 'model_version': 'champion-xgb-cure-v2',
                'action': 'do_not_contact',
                'top_features': [
                    {'feature': 'dnc_flag', 'value': 1, 'importance': 0.70, 'direction': 'negative'},
                    {'feature': 'days_past_due', 'value': 55, 'importance': 0.20, 'direction': 'negative'}
                ],
                'idempotency_key': 'rec-key-005'
            }
        )

        # Customer 6: Executed and Approved case (For workflow demonstration)
        c6, _ = Customer.objects.get_or_create(
            id='cust-006',
            defaults={
                'name': 'Jean-Marc Belanger',
                'email': 'jm.belanger@example.ca',
                'phone': '+1-613-555-0914',
                'date_of_birth': date(1974, 12, 5),
                'address': '240 Sparks St, Ottawa, ON K1A 0X9',
                'source_system': 'Core-Banking-System',
                'source_record_id': 'CORE-CUST-55102',
                'observed_at': now_dt - timedelta(hours=1),
                'transformation_version': 'golden-v2.1'
            }
        )
        a6, _ = Account.objects.get_or_create(
            id='acct-loan-006',
            defaults={
                'customer': c6,
                'product': Account.Product.PERSONAL_LOAN,
                'status': Account.Status.ACTIVE,
                'balance': Decimal('8900.00'),
                'overdue_balance': Decimal('320.00'),
                'dpd': 22,
                'hardship': False,
                'dispute': False,
                'dnc': False,
                'contact_count_7d': 2,
                'assigned_agent': agent2,
                'source_system': 'Core-Banking-System',
                'source_record_id': 'LOAN-55102-1',
                'observed_at': now_dt - timedelta(hours=1),
                'recent_payment_count': 2,
                'recent_payment_amount': Decimal('640.00'),
                'historical_ptp_adherence': 0.85,
                'days_since_last_payment': 52
            }
        )
        rec6, _ = Recommendation.objects.get_or_create(
            id='rec-006',
            defaults={
                'account': a6, 'version': 1, 'status': Recommendation.Status.APPROVED,
                'target': '30-day cure propensity', 'score': 0.82, 'model_version': 'champion-xgb-cure-v2',
                'action': 'outbound_call',
                'top_features': [
                    {'feature': 'historical_ptp_adherence', 'value': 0.85, 'importance': 0.35, 'direction': 'positive'},
                    {'feature': 'days_past_due', 'value': 22, 'importance': 0.20, 'direction': 'neutral'}
                ],
                'reviewed_by': lead, 'review_reason': 'Approved outbound telephone contact during core business hours.',
                'idempotency_key': 'rec-key-006'
            }
        )
        ApprovalRequest.objects.get_or_create(
            idempotency_key='appr-key-006',
            defaults={
                'recommendation': rec6, 'recommendation_version': 1, 'status': ApprovalRequest.Status.APPROVED,
                'requested_by': agent2, 'reviewed_by': lead, 'proposed_action': 'outbound_call',
                'final_action': 'outbound_call', 'reason': 'Customer responsive to direct phone discussion.'
            }
        )

        # 1. Customer 7: Devon Campbell
        c7, _ = Customer.objects.get_or_create(
            id='cust-007',
            defaults={
                'name': 'Devon Campbell',
                'email': 'devon.campbell@example.ca',
                'phone': '+1-204-555-0482',
                'date_of_birth': date(1980, 4, 18),
                'address': '215 Portage Ave, Winnipeg, MB R3B 1Z9',
                'source_system': 'Core-Banking-System',
                'source_record_id': 'CORE-CUST-66190',
                'observed_at': now_dt - timedelta(hours=6),
                'transformation_version': 'golden-v2.1'
            }
        )
        CustomerIdentity.objects.get_or_create(
            customer=c7, source_system='Core-Banking-System', source_id='CORE-CUST-66190',
            defaults={'match_type': CustomerIdentity.MatchType.EXACT, 'score': 1.0, 'evidence': ['SIN_MATCH']}
        )
        a7, _ = Account.objects.get_or_create(
            id='acct-loan-007',
            defaults={
                'customer': c7,
                'product': Account.Product.PERSONAL_LOAN,
                'status': Account.Status.ACTIVE,
                'balance': Decimal('48000.00'),
                'overdue_balance': Decimal('3450.00'),
                'dpd': 88,
                'hardship': False,
                'dispute': False,
                'dnc': False,
                'contact_count_7d': 1,
                'assigned_agent': agent,
                'source_system': 'Core-Banking-System',
                'source_record_id': 'AGRI-LOAN-66190',
                'observed_at': now_dt - timedelta(hours=6),
                'recent_payment_count': 1,
                'recent_payment_amount': Decimal('1150.00'),
                'historical_ptp_adherence': 0.40,
                'days_since_last_payment': 88
            }
        )
        PromiseToPay.objects.get_or_create(
            id='ptp-007',
            defaults={
                'account': a7, 'amount': Decimal('1200.00'), 'due_date': date(2026, 10, 10),
                'status': PromiseToPay.Status.BROKEN, 'source_system': 'collections'
            }
        )
        Payment.objects.get_or_create(
            event_id='PAY-EVT-007A',
            defaults={
                'id': 'pay-007', 'account': a7, 'amount': Decimal('1150.00'), 'status': Payment.Status.RECONCILED,
                'date': date(2026, 7, 15), 'source_system': 'Core-Banking-System'
            }
        )
        CallTranscript.objects.get_or_create(
            id='transcript-007',
            defaults={
                'account': a7, 'language': 'en',
                'text': 'Devon: The harvest was delayed due to heavy rain, but we are selling grain next week. I can pay $1,500 by next Friday.',
                'signals': [{'signal': 'payment_intent', 'confidence': 0.88}], 'source_system': 'transcription-adapter'
            }
        )
        rec7, _ = Recommendation.objects.get_or_create(
            id='rec-007',
            defaults={
                'account': a7, 'version': 1, 'status': Recommendation.Status.PENDING_REVIEW,
                'target': '30-day cure propensity', 'score': 0.35, 'model_version': 'champion-xgb-cure-v2',
                'action': 'restructure_payment_plan',
                'top_features': [
                    {'feature': 'historical_ptp_adherence', 'value': 0.40, 'importance': 0.45, 'direction': 'negative'},
                    {'feature': 'days_past_due', 'value': 88, 'importance': 0.30, 'direction': 'negative'}
                ],
                'idempotency_key': 'rec-key-007'
            }
        )
        ApprovalRequest.objects.get_or_create(
            idempotency_key='appr-key-007',
            defaults={
                'recommendation': rec7, 'recommendation_version': 1, 'status': ApprovalRequest.Status.PENDING_REVIEW,
                'requested_by': agent, 'proposed_action': 'restructure_payment_plan',
                'reason': 'Customer experienced agricultural delay; proposed restructured amortization schedule.'
            }
        )
        QueueAssignment.objects.get_or_create(
            account=a7,
            defaults={'assigned_agent': agent, 'priority_score': 68.0, 'status': QueueAssignment.Status.ASSIGNED, 'routing_reason': 'Broken PTP follow-up'}
        )

        # 2. Customer 8: Fatima Zahra
        c8, _ = Customer.objects.get_or_create(
            id='cust-008',
            defaults={
                'name': 'Fatima Zahra',
                'email': 'fatima.zahra@example.ca',
                'phone': '+1-306-555-0814',
                'date_of_birth': date(1988, 9, 12),
                'address': '410 22nd St E, Saskatoon, SK S7K 5T6',
                'source_system': 'Core-Banking-System',
                'source_record_id': 'CORE-CUST-78219',
                'observed_at': now_dt - timedelta(hours=2),
                'transformation_version': 'golden-v2.1'
            }
        )
        CustomerIdentity.objects.get_or_create(
            customer=c8, source_system='Core-Banking-System', source_id='CORE-CUST-78219',
            defaults={'match_type': CustomerIdentity.MatchType.EXACT, 'score': 1.0, 'evidence': ['BUSINESS_TAX_ID']}
        )
        a8, _ = Account.objects.get_or_create(
            id='acct-comm-008',
            defaults={
                'customer': c8,
                'product': Account.Product.PERSONAL_LOAN,
                'status': Account.Status.ACTIVE,
                'balance': Decimal('28500.00'),
                'overdue_balance': Decimal('2100.00'),
                'dpd': 29,
                'hardship': False,
                'dispute': False,
                'dnc': False,
                'contact_count_7d': 0,
                'assigned_agent': agent2,
                'source_system': 'Core-Banking-System',
                'source_record_id': 'COMM-TERM-78219',
                'observed_at': now_dt - timedelta(hours=2),
                'recent_payment_count': 3,
                'recent_payment_amount': Decimal('6300.00'),
                'historical_ptp_adherence': 0.95,
                'days_since_last_payment': 45
            }
        )
        PromiseToPay.objects.get_or_create(
            id='ptp-008',
            defaults={
                'account': a8, 'amount': Decimal('2100.00'), 'due_date': date(2026, 10, 28),
                'status': PromiseToPay.Status.PENDING, 'source_system': 'collections'
            }
        )
        Payment.objects.get_or_create(
            event_id='PAY-EVT-008A',
            defaults={
                'id': 'pay-008', 'account': a8, 'amount': Decimal('2100.00'), 'status': Payment.Status.RECONCILED,
                'date': date(2026, 8, 30), 'source_system': 'Core-Banking-System'
            }
        )
        rec8, _ = Recommendation.objects.get_or_create(
            id='rec-008',
            defaults={
                'account': a8, 'version': 1, 'status': Recommendation.Status.PENDING_REVIEW,
                'target': '30-day cure propensity', 'score': 0.91, 'model_version': 'champion-xgb-cure-v2',
                'action': 'digital_reminder_sms',
                'top_features': [
                    {'feature': 'historical_ptp_adherence', 'value': 0.95, 'importance': 0.42, 'direction': 'positive'},
                    {'feature': 'recent_payment_amount', 'value': 6300, 'importance': 0.30, 'direction': 'positive'}
                ],
                'idempotency_key': 'rec-key-008'
            }
        )
        ApprovalRequest.objects.get_or_create(
            idempotency_key='appr-key-008',
            defaults={
                'recommendation': rec8, 'recommendation_version': 1, 'status': ApprovalRequest.Status.PENDING_REVIEW,
                'requested_by': agent2, 'proposed_action': 'digital_reminder_sms'
            }
        )
        QueueAssignment.objects.get_or_create(
            account=a8,
            defaults={'assigned_agent': agent2, 'priority_score': 88.0, 'status': QueueAssignment.Status.ASSIGNED, 'routing_reason': 'High cure commercial borrower'}
        )

        # 3. Customer 9: Liam O'Connor
        c9, _ = Customer.objects.get_or_create(
            id='cust-009',
            defaults={
                'name': "Liam O'Connor",
                'email': 'liam.oconnor@example.ca',
                'phone': '+1-709-555-0923',
                'date_of_birth': date(1997, 1, 23),
                'address': "100 Water St, St. John's, NL A1C 6E6",
                'source_system': 'Core-Banking-System',
                'source_record_id': 'CORE-CUST-44109',
                'observed_at': now_dt - timedelta(hours=3),
                'transformation_version': 'golden-v2.1'
            }
        )
        CustomerIdentity.objects.get_or_create(
            customer=c9, source_system='Core-Banking-System', source_id='CORE-CUST-44109',
            defaults={'match_type': CustomerIdentity.MatchType.EXACT, 'score': 1.0, 'evidence': ['STUDENT_ID_VERIFIED']}
        )
        a9, _ = Account.objects.get_or_create(
            id='acct-stud-009',
            defaults={
                'customer': c9,
                'product': Account.Product.PERSONAL_LOAN,
                'status': Account.Status.ACTIVE,
                'balance': Decimal('16800.00'),
                'overdue_balance': Decimal('940.00'),
                'dpd': 55,
                'hardship': False,
                'dispute': False,
                'dnc': False,
                'contact_count_7d': 2,
                'assigned_agent': agent,
                'source_system': 'Core-Banking-System',
                'source_record_id': 'STUD-CONSOL-44109',
                'observed_at': now_dt - timedelta(hours=3),
                'recent_payment_count': 1,
                'recent_payment_amount': Decimal('470.00'),
                'historical_ptp_adherence': 0.70,
                'days_since_last_payment': 60
            }
        )
        CollectionContact.objects.get_or_create(
            id='contact-009-1',
            defaults={'account': a9, 'date': (now_dt - timedelta(days=4)).date(), 'channel': CollectionContact.Channel.SMS, 'outcome': 'Delivered', 'agent': agent, 'source_system': 'dialer'}
        )
        CollectionContact.objects.get_or_create(
            id='contact-009-2',
            defaults={'account': a9, 'date': (now_dt - timedelta(days=1)).date(), 'channel': CollectionContact.Channel.PHONE, 'outcome': 'Left voicemail', 'agent': agent, 'source_system': 'dialer'}
        )
        CallTranscript.objects.get_or_create(
            id='transcript-009',
            defaults={
                'account': a9, 'language': 'en',
                'text': "Liam: I started my graduate internship, can we lower the monthly installment until full-time conversion?",
                'signals': [{'signal': 'hardship_indicator', 'confidence': 0.82}], 'source_system': 'transcription-adapter'
            }
        )
        rec9, _ = Recommendation.objects.get_or_create(
            id='rec-009',
            defaults={
                'account': a9, 'version': 1, 'status': Recommendation.Status.PENDING_REVIEW,
                'target': '30-day cure propensity', 'score': 0.52, 'model_version': 'champion-xgb-cure-v2',
                'action': 'outbound_call',
                'top_features': [
                    {'feature': 'contact_count_7d', 'value': 2, 'importance': 0.40, 'direction': 'negative'},
                    {'feature': 'days_past_due', 'value': 55, 'importance': 0.30, 'direction': 'neutral'}
                ],
                'idempotency_key': 'rec-key-009'
            }
        )
        QueueAssignment.objects.get_or_create(
            account=a9,
            defaults={'assigned_agent': agent, 'priority_score': 54.0, 'status': QueueAssignment.Status.ASSIGNED, 'routing_reason': 'Near contact cap warning'}
        )

        # 4. Customer 10: Mei-Ling Zhou
        c10, _ = Customer.objects.get_or_create(
            id='cust-010',
            defaults={
                'name': 'Mei-Ling Zhou',
                'email': 'meiling.zhou@example.ca',
                'phone': '+1-604-555-0771',
                'date_of_birth': date(1984, 10, 30),
                'address': '888 Burrard St, Vancouver, BC V6Z 1X3',
                'source_system': 'Core-Banking-System',
                'source_record_id': 'CORE-CUST-99882',
                'observed_at': now_dt - timedelta(hours=1),
                'transformation_version': 'golden-v2.1'
            }
        )
        CustomerIdentity.objects.get_or_create(
            customer=c10, source_system='Core-Banking-System', source_id='CORE-CUST-99882',
            defaults={'match_type': CustomerIdentity.MatchType.EXACT, 'score': 1.0, 'evidence': ['SIN_MATCH', 'BRANCH_KYC']}
        )
        CustomerIdentity.objects.get_or_create(
            customer=c10, source_system='Card-Management-TSYS', source_id='TSYS-ZHOU-882',
            defaults={'match_type': CustomerIdentity.MatchType.EXACT, 'score': 1.0, 'evidence': ['CARD_TOKEN_MATCH']}
        )
        a10, _ = Account.objects.get_or_create(
            id='acct-loc-010',
            defaults={
                'customer': c10,
                'product': Account.Product.LINE_OF_CREDIT,
                'status': Account.Status.ACTIVE,
                'balance': Decimal('34000.00'),
                'overdue_balance': Decimal('12800.00'),
                'dpd': 105,
                'hardship': True,
                'dispute': False,
                'dnc': False,
                'contact_count_7d': 1,
                'assigned_agent': specialist,
                'source_system': 'Core-Banking-System',
                'source_record_id': 'PREMIER-LOC-99882',
                'observed_at': now_dt - timedelta(hours=1),
                'recent_payment_count': 0,
                'recent_payment_amount': Decimal('0.00'),
                'historical_ptp_adherence': 0.20,
                'days_since_last_payment': 110
            }
        )
        HardshipCase.objects.get_or_create(
            id='hardship-010',
            defaults={
                'account': a10, 'status': HardshipCase.Status.UNDER_REVIEW, 'source': 'Customer Inbound / Layoff Notice',
                'specialist_required': True, 'notes': 'Borrower laid off due to tech sector restructuring. Applied for EI. Requesting minimum payment waiver for 90 days.'
            }
        )
        CallTranscript.objects.get_or_create(
            id='transcript-010',
            defaults={
                'account': a10, 'language': 'en',
                'text': 'Mei-Ling: I was laid off when the tech firm restructured last month. I have applied for EI benefits and need temporary relief on the minimum payments.',
                'signals': [{'signal': 'hardship_indicator', 'confidence': 0.98}, {'signal': 'vulnerability_claim', 'confidence': 0.95}],
                'source_system': 'transcription-adapter'
            }
        )
        rec10, _ = Recommendation.objects.get_or_create(
            id='rec-010',
            defaults={
                'account': a10, 'version': 1, 'status': Recommendation.Status.ESCALATED,
                'target': '30-day cure propensity', 'score': 0.12, 'model_version': 'champion-xgb-cure-v2',
                'action': 'route_hardship_specialist',
                'top_features': [
                    {'feature': 'hardship_flag', 'value': 1, 'importance': 0.65, 'direction': 'negative'},
                    {'feature': 'days_past_due', 'value': 105, 'importance': 0.25, 'direction': 'negative'}
                ],
                'idempotency_key': 'rec-key-010'
            }
        )
        ApprovalRequest.objects.get_or_create(
            idempotency_key='appr-key-010',
            defaults={
                'recommendation': rec10, 'recommendation_version': 1, 'status': ApprovalRequest.Status.ESCALATED,
                'requested_by': agent, 'reviewed_by': lead, 'proposed_action': 'route_hardship_specialist',
                'reason': 'Escalated to Hardship Specialist Elena Rostova under HARDSHIP-001.'
            }
        )
        QueueAssignment.objects.get_or_create(
            account=a10,
            defaults={'assigned_agent': specialist, 'priority_score': 95.0, 'status': QueueAssignment.Status.ASSIGNED, 'routing_reason': 'High exposure late-stage hardship'}
        )


        # 7. Identity Candidates (Probabilistic Splink matches awaiting Data Steward)
        self.stdout.write("Generating probabilistic identity match candidates for Data Steward...")
        IdentityMatchCandidate.objects.get_or_create(
            id='match-001',
            defaults={
                'customer': c1,
                'source_system': 'Salesforce-CRM',
                'source_record_id': 'SF-LEAD-884102',
                'score': 0.88,
                'status': IdentityMatchCandidate.Status.PENDING,
                'evidence': [
                    {'field': 'name', 'similarity': 0.96, 'source_val': 'Alex Tremblay', 'target_val': 'Alexandre Tremblay'},
                    {'field': 'phone', 'similarity': 1.0, 'source_val': '+1-514-555-0142', 'target_val': '+1-514-555-0142'},
                    {'field': 'postal_code', 'similarity': 0.90, 'source_val': 'H2X 1E6', 'target_val': 'H2X 1E6'}
                ],
                'conflicts': [],
                'reason': 'High probabilistic Jaro-Winkler & exact phone match awaiting steward crosswalk confirmation.'
            }
        )
        IdentityMatchCandidate.objects.get_or_create(
            id='match-002',
            defaults={
                'customer': c2,
                'source_system': 'Equifax-Bureau',
                'source_record_id': 'EQ-BUREAU-99214',
                'score': 0.74,
                'status': IdentityMatchCandidate.Status.PENDING,
                'evidence': [
                    {'field': 'name', 'similarity': 0.85, 'source_val': 'Priya R. Patel', 'target_val': 'Priya Patel'},
                    {'field': 'dob', 'similarity': 1.0, 'source_val': '1992-11-28', 'target_val': '1992-11-28'}
                ],
                'conflicts': [
                    {'field': 'address', 'source_val': '77 Bloor St W, Toronto', 'target_val': '180 University Ave, Toronto'}
                ],
                'reason': 'Address discrepancy requires manual steward verification before merge.'
            }
        )

        # 8. Controlled Experiments (Section 15 Champion/Challenger)
        self.stdout.write("Setting up A/B testing experiment cohorts...")
        exp1, _ = Experiment.objects.get_or_create(
            name='EXP-2026-SMS-FIRST',
            defaults={
                'description': 'Evaluating digital SMS-first workflow versus traditional voice-first outbound calling for 1-30 DPD accounts.',
                'hypothesis': 'Proactive digital SMS reminders will increase 30-day cure rate by 12% while reducing collection contact attempts.',
                'status': Experiment.Status.RUNNING,
                'primary_metric': 'cure_rate',
                'target_sample_size': 2000,
                'created_by': admin_user
            }
        )
        cohort_ctrl, _ = ExperimentCohort.objects.get_or_create(
            experiment=exp1, name='Control (Voice-First)',
            defaults={'allocation_percentage': 50.0, 'strategy_config': {'primary_channel': 'voice_call', 'retry_interval_days': 3}}
        )
        cohort_chall, _ = ExperimentCohort.objects.get_or_create(
            experiment=exp1, name='Challenger (SMS-First)',
            defaults={'allocation_percentage': 50.0, 'strategy_config': {'primary_channel': 'sms_reminder', 'interactive_pay_link': True}}
        )

        # Metric snapshots for past 3 weeks
        for i, days_ago in enumerate([21, 14, 7]):
            snap_date = (now_dt - timedelta(days=days_ago)).date()
            MetricSnapshot.objects.get_or_create(
                experiment=exp1, cohort=cohort_ctrl, snapshot_date=snap_date,
                defaults={
                    'sample_size': 450 + (i * 120),
                    'cure_rate': 0.58 + (i * 0.01),
                    'ptp_adherence_rate': 0.68,
                    'contacts_per_cure': 3.8,
                    'total_recovered': Decimal(str(125000 + (i * 45000))),
                    'p_value': 0.12 - (i * 0.03),
                    'is_statistically_significant': (i == 2)
                }
            )
            MetricSnapshot.objects.get_or_create(
                experiment=exp1, cohort=cohort_chall, snapshot_date=snap_date,
                defaults={
                    'sample_size': 460 + (i * 125),
                    'cure_rate': 0.69 + (i * 0.02),
                    'ptp_adherence_rate': 0.81,
                    'contacts_per_cure': 2.1,
                    'total_recovered': Decimal(str(178000 + (i * 62000))),
                    'p_value': 0.04 - (i * 0.01),
                    'is_statistically_significant': True
                }
            )

        # 9. Audit Trail Events
        self.stdout.write("Recording initial audit events...")
        log_audit(
            'SEED_CREATED', 'SYSTEM_INITIALIZATION',
            'Synthetic demonstration database seeded successfully with deterministic personas and scenario accounts.',
            actor=admin_user,
            details={'customers_count': 6, 'accounts_count': 6, 'policies_count': 1, 'experiments_count': 1}
        )

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))
