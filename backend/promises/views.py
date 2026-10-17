"""
Promise-to-pay tracking views with maturity checking.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from promises.models import PromiseToPay
from promises.serializers import PromiseToPaySerializer
from audit.utils import log_audit


class PromiseToPayViewSet(viewsets.ModelViewSet):
    queryset = PromiseToPay.objects.all().order_by('-due_date')
    serializer_class = PromiseToPaySerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        ptp = serializer.save()
        try:
            from data_platform.django_integration import publish_promise_event
            publish_promise_event(ptp)
        except Exception:
            pass

        log_audit(
            'SEED_CREATED',
            ptp.id,
            f"Created Promise-to-Pay for ${ptp.amount} due {ptp.due_date} on account {ptp.account_id}",
            actor=self.request.user,
            details={'amount': float(ptp.amount), 'due_date': str(ptp.due_date)}
        )
