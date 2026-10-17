"""
Payment views with idempotency and reconciliation tracking.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from payments.models import Payment
from payments.serializers import PaymentSerializer
from audit.utils import log_audit


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().order_by('-date')
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        event_id = request.data.get('event_id')
        if event_id and Payment.objects.filter(event_id=event_id).exists():
            existing = Payment.objects.get(event_id=event_id)
            return Response(
                {
                    'message': 'Idempotent replay: payment event already recorded.',
                    'payment': PaymentSerializer(existing).data
                },
                status=status.HTTP_200_OK
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()

        log_audit(
            'PAYMENT_INGESTED',
            payment.id,
            f'Recorded payment of ${payment.amount} for account {payment.account_id}',
            actor=request.user,
            details={'amount': float(payment.amount), 'source_system': payment.source_system, 'status': payment.status}
        )

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
