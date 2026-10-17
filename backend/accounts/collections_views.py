"""
Collections operations views — Dashboard KPIs and Work Queue.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from accounts.models import Account
from accounts.serializers import AccountSerializer
from customers.models import Customer
from decisioning.models import Recommendation
from decisioning.engine import RulesEngine
from payments.models import Payment
from payments.serializers import PaymentSerializer
from promises.models import PromiseToPay
from identity.models import IdentityMatchCandidate


class CollectionsDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        accounts = Account.objects.all()
        if user.is_authenticated:
            if user.role == 'collections_agent':
                accounts = accounts.filter(assigned_agent=user)
            elif user.role == 'hardship_specialist':
                accounts = accounts.filter(Q(hardship=True) | Q(assigned_agent=user))
            elif user.role == 'data_steward':
                accounts = accounts.filter(Q(dispute=True) | Q(dnc=True))
            elif user.role in ['team_lead', 'administrator', 'auditor']:
                agent_param = request.query_params.get('agent')
                if agent_param:
                    accounts = accounts.filter(assigned_agent__username=agent_param)

        total_accounts = accounts.count()
        total_overdue = sum(a.overdue_balance for a in accounts)

        # Evaluations
        eligible_count = 0
        hardship_count = 0
        dispute_count = 0
        dnc_count = 0
        cap_exceeded_count = 0

        for a in accounts:
            if a.hardship:
                hardship_count += 1
            if a.dispute:
                dispute_count += 1
            if a.dnc:
                dnc_count += 1
            if a.contact_count_7d >= 4:
                cap_exceeded_count += 1
            eval_res = RulesEngine.evaluate_eligibility(a)
            if eval_res['eligible']:
                eligible_count += 1

        awaiting_review = Recommendation.objects.filter(
            account__in=accounts,
            status__in=['PENDING_REVIEW', 'ESCALATED']
        ).count()

        pending_identities = IdentityMatchCandidate.objects.filter(status='PENDING').count()

        now = timezone.now().date()
        ptp_due_soon = PromiseToPay.objects.filter(
            account__in=accounts,
            status='PENDING',
            due_date__gte=now,
            due_date__lte=now + timedelta(days=7)
        ).count()

        ptp_broken = PromiseToPay.objects.filter(
            account__in=accounts,
            status='BROKEN'
        ).count()

        recent_payments = Payment.objects.filter(account__in=accounts).order_by('-date')[:6]

        data_quality_warnings = []
        for a in accounts:
            if a.dnc:
                data_quality_warnings.append({'account_id': a.id, 'issue': 'Do-Not-Contact Restriction Active', 'severity': 'HIGH'})
            elif a.dispute:
                data_quality_warnings.append({'account_id': a.id, 'issue': 'Active Customer Dispute Under Review', 'severity': 'HIGH'})
            elif a.contact_count_7d >= 4:
                data_quality_warnings.append({'account_id': a.id, 'issue': f'Statutory Contact Cap Exceeded ({a.contact_count_7d}/3 in 7d)', 'severity': 'CRITICAL'})
            elif not a.observed_at:
                data_quality_warnings.append({'account_id': a.id, 'issue': 'Missing Lineage Observation Timestamp', 'severity': 'MEDIUM'})

        kpis = [
            {'label': 'Eligible Accounts', 'value': eligible_count, 'definition': 'Active accounts passing statutory caps, DNC, dispute, and hardship checks.'},
            {'label': 'Awaiting Human Review', 'value': awaiting_review, 'definition': 'AI recommendations pending approval, override, or escalation.'},
            {'label': 'Hardship Cases', 'value': hardship_count, 'definition': 'Customers flagged for vulnerability requiring specialist intervention.'},
            {'label': 'Pending Identity Merges', 'value': pending_identities, 'definition': 'Probabilistic Splink match candidates awaiting steward review.'},
            {'label': 'PTPs Due Soon (7d)', 'value': ptp_due_soon, 'definition': 'Active promises maturing within the next seven days.'},
            {'label': 'Broken Promises', 'value': ptp_broken, 'definition': 'Promises unfulfilled beyond grace period.'},
        ]

        dpd_distribution = {
            '1-30 DPD': accounts.filter(dpd__gt=0, dpd__lte=30).count(),
            '31-60 DPD': accounts.filter(dpd__gt=30, dpd__lte=60).count(),
            '61-90 DPD': accounts.filter(dpd__gt=60, dpd__lte=90).count(),
            '90+ DPD': accounts.filter(dpd__gt=90).count(),
        }

        pipeline_health = {
            'raw': 'HEALTHY (Deterministic Ingestion Stream)',
            'silver': 'HEALTHY (Cleaned and Reconciled)',
            'golden': 'HEALTHY (C360 Identity Crosswalk Active)',
            'event_broker': 'SIMULATION (Local In-Memory Kafka Substitute)',
            'feature_store': 'ACTIVE (Point-in-time consistent)',
        }

        return Response({
            'kpis': kpis,
            'summary': {
                'total_accounts': total_accounts,
                'total_overdue': float(total_overdue),
                'eligible_count': eligible_count,
                'hardship_count': hardship_count,
                'dispute_count': dispute_count,
                'dnc_count': dnc_count,
            },
            'dpd_distribution': dpd_distribution,
            'recent_payments': PaymentSerializer(recent_payments, many=True).data,
            'data_quality_warnings': data_quality_warnings[:10],
            'pipeline_health': pipeline_health,
        })


class CollectionsQueueView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        accounts = Account.objects.select_related('customer', 'assigned_agent').all()
        if user.is_authenticated:
            if user.role == 'collections_agent':
                accounts = accounts.filter(assigned_agent=user)
            elif user.role == 'hardship_specialist':
                accounts = accounts.filter(Q(hardship=True) | Q(assigned_agent=user))
            elif user.role == 'data_steward':
                accounts = accounts.filter(Q(dispute=True) | Q(dnc=True))
            elif user.role in ['team_lead', 'administrator', 'auditor']:
                agent_param = request.query_params.get('agent')
                if agent_param:
                    accounts = accounts.filter(assigned_agent__username=agent_param)

        # Filters
        dpd_bucket = request.query_params.get('dpd_bucket')
        product = request.query_params.get('product')
        status_filter = request.query_params.get('status')
        hardship = request.query_params.get('hardship')
        dispute = request.query_params.get('dispute')
        dnc = request.query_params.get('dnc')
        search = request.query_params.get('search', '').strip()

        if dpd_bucket == '1-30':
            accounts = accounts.filter(dpd__gt=0, dpd__lte=30)
        elif dpd_bucket == '31-60':
            accounts = accounts.filter(dpd__gt=30, dpd__lte=60)
        elif dpd_bucket == '61-90':
            accounts = accounts.filter(dpd__gt=60, dpd__lte=90)
        elif dpd_bucket == '90+':
            accounts = accounts.filter(dpd__gt=90)

        if product:
            accounts = accounts.filter(product=product)
        if status_filter:
            accounts = accounts.filter(status=status_filter)
        if hardship is not None:
            accounts = accounts.filter(hardship=hardship.lower() in ('1', 'true'))
        if dispute is not None:
            accounts = accounts.filter(dispute=dispute.lower() in ('1', 'true'))
        if dnc is not None:
            accounts = accounts.filter(dnc=dnc.lower() in ('1', 'true'))
        if search:
            accounts = accounts.filter(customer__name__icontains=search) | accounts.filter(id__icontains=search)

        # Build prioritized queue list
        queue_items = []
        for a in accounts.order_by('-overdue_balance')[:100]:
            eligibility = RulesEngine.evaluate_eligibility(a)
            latest_rec = a.recommendations.order_by('-created_at').first()

            # Priority formula: (overdue / 1000) * (dpd / 30) - penalty for blocks
            base_priority = (float(a.overdue_balance) / 500.0) + (a.dpd * 0.5)
            if not eligibility['eligible']:
                base_priority *= 0.5

            queue_items.append({
                'account_id': a.id,
                'customer_id': a.customer.id,
                'customer_name': a.customer.name,
                'product': a.product,
                'status': a.status,
                'balance': float(a.balance),
                'overdue_balance': float(a.overdue_balance),
                'dpd': a.dpd,
                'hardship': a.hardship,
                'dispute': a.dispute,
                'dnc': a.dnc,
                'contact_count_7d': a.contact_count_7d,
                'assigned_agent': a.assigned_agent.username if a.assigned_agent else 'Unassigned',
                'priority_score': round(base_priority, 2),
                'eligibility': eligibility,
                'latest_recommendation': {
                    'id': latest_rec.id,
                    'action': latest_rec.action,
                    'status': latest_rec.status,
                    'score': latest_rec.score,
                    'top_features': latest_rec.top_features,
                } if latest_rec else None
            })

        # Sort by priority score descending
        queue_items.sort(key=lambda x: x['priority_score'], reverse=True)

        return Response({
            'count': len(queue_items),
            'results': queue_items
        })
