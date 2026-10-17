"""
Customer views including Customer 360 unified view.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from customers.models import Customer, SourceSystem
from customers.serializers import CustomerSerializer, SourceSystemSerializer
from accounts.models import Account
from accounts.serializers import AccountSerializer
from payments.models import Payment
from payments.serializers import PaymentSerializer
from promises.models import PromiseToPay
from promises.serializers import PromiseToPaySerializer
from calls.models import CollectionContact, CallTranscript, Dispute, HardshipCase
from calls.serializers import CollectionContactSerializer, CallTranscriptSerializer, DisputeSerializer, HardshipCaseSerializer
from decisioning.models import Recommendation
from decisioning.serializers import RecommendationSerializer
from decisioning.engine import RulesEngine
from audit.models import AuditEvent
from audit.serializers import AuditEventSerializer


class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Customer.objects.all().prefetch_related('identities', 'accounts').order_by('name')
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(name__icontains=search) | qs.filter(id__icontains=search) | qs.filter(phone__icontains=search)
        return qs

    @action(detail=True, methods=['get'], url_path='360')
    def customer_360(self, request, pk=None):
        """
        Returns full 360 view organized into the 12 required sections per Section 12.4.
        """
        customer = self.get_object()

        # 1. Accounts — Customer 360 displays full exposure across all products
        accounts = Account.objects.filter(customer=customer)
        visible_accounts = accounts

        # 2. Balances & Arrears aggregate
        total_balance = sum(a.balance for a in accounts)
        total_overdue = sum(a.overdue_balance for a in accounts)
        max_dpd = max((a.dpd for a in accounts), default=0)

        # 3. Payments
        payments = Payment.objects.filter(account__customer=customer).order_by('-date')[:20]

        # 4. Promises to Pay
        promises = PromiseToPay.objects.filter(account__customer=customer).order_by('-due_date')[:10]

        # 5. Contacts & Transcripts
        contacts = CollectionContact.objects.filter(account__customer=customer).order_by('-date')[:20]
        transcripts = CallTranscript.objects.filter(account__customer=customer).order_by('-created_at')[:10]

        # 6. Disputes & Hardship
        disputes = Dispute.objects.filter(account__customer=customer)
        hardships = HardshipCase.objects.filter(account__customer=customer)

        # 7. Recommendations
        recommendations = Recommendation.objects.filter(account__in=accounts).order_by('-created_at')[:10]

        # 8. Rules evaluations per account
        account_eligibility = {
            a.id: RulesEngine.evaluate_eligibility(a) for a in accounts
        }

        # 9. Audit trail for customer
        audits = AuditEvent.objects.filter(entity_id__in=[customer.id] + [a.id for a in accounts]).order_by('-timestamp')[:15]

        # 10. Data lineage & freshness
        lineage = {
            'golden_id': customer.id,
            'source_system': customer.source_system,
            'source_record_id': customer.source_record_id,
            'observed_at': customer.observed_at,
            'ingested_at': customer.ingested_at,
            'transformation_version': customer.transformation_version,
            'data_as_of': customer.observed_at or customer.updated_at,
        }

        return Response({
            'customer': CustomerSerializer(customer).data,
            'identities': [
                {
                    'id': i.id,
                    'source_system': i.source_system,
                    'source_id': i.source_id,
                    'match_type': i.match_type,
                    'score': i.score,
                    'evidence': i.evidence
                } for i in customer.identities.all()
            ],
            'financial_summary': {
                'total_balance': total_balance,
                'total_overdue': total_overdue,
                'max_dpd': max_dpd,
                'active_accounts_count': accounts.filter(status='ACTIVE').count()
            },
            'accounts': AccountSerializer(visible_accounts, many=True).data,
            'eligibility_by_account': account_eligibility,
            'payments': PaymentSerializer(payments, many=True).data,
            'promises_to_pay': PromiseToPaySerializer(promises, many=True).data,
            'contacts': CollectionContactSerializer(contacts, many=True).data,
            'transcripts': CallTranscriptSerializer(transcripts, many=True).data,
            'disputes': DisputeSerializer(disputes, many=True).data,
            'hardships': HardshipCaseSerializer(hardships, many=True).data,
            'recommendations': RecommendationSerializer(recommendations, many=True).data,
            'lineage': lineage,
            'audit_history': AuditEventSerializer(audits, many=True).data
        })
