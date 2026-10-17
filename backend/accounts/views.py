"""
Account views including deterministic eligibility evaluations.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from accounts.models import Account
from accounts.serializers import AccountSerializer
from decisioning.engine import RulesEngine


class AccountViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Account.objects.select_related('customer', 'assigned_agent').all().order_by('-overdue_balance')
    serializer_class = AccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        # Role-based visibility
        if user.is_authenticated and user.role == 'collections_agent':
            qs = qs.filter(assigned_agent=user)

        # Filters
        product = self.request.query_params.get('product')
        status_param = self.request.query_params.get('status')
        min_dpd = self.request.query_params.get('min_dpd')
        max_dpd = self.request.query_params.get('max_dpd')
        hardship = self.request.query_params.get('hardship')
        dispute = self.request.query_params.get('dispute')
        dnc = self.request.query_params.get('dnc')
        customer_id = self.request.query_params.get('customer')

        if product:
            qs = qs.filter(product=product)
        if status_param:
            qs = qs.filter(status=status_param)
        if min_dpd:
            qs = qs.filter(dpd__gte=int(min_dpd))
        if max_dpd:
            qs = qs.filter(dpd__lte=int(max_dpd))
        if hardship is not None:
            qs = qs.filter(hardship=hardship.lower() in ('1', 'true'))
        if dispute is not None:
            qs = qs.filter(dispute=dispute.lower() in ('1', 'true'))
        if dnc is not None:
            qs = qs.filter(dnc=dnc.lower() in ('1', 'true'))
        if customer_id:
            qs = qs.filter(customer_id=customer_id)

        return qs

    @action(detail=True, methods=['get'])
    def eligibility(self, request, pk=None):
        """Returns deterministic rule evaluation results for this account."""
        account = self.get_object()
        result = RulesEngine.evaluate_eligibility(account)
        return Response(result)
