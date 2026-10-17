"""Promise-to-pay tracking."""
from django.db import models
import uuid


class PromiseToPay(models.Model):
    """Tracked customer promise with maturity and adherence status."""

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        KEPT = 'KEPT', 'Kept'
        BROKEN = 'BROKEN', 'Broken'
        CANCELLED = 'CANCELLED', 'Cancelled'
        RESCHEDULED = 'RESCHEDULED', 'Rescheduled'

    id = models.CharField(max_length=50, primary_key=True, default='')
    account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE, related_name='promises')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default='CAD')
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    source_system = models.CharField(max_length=100, default='collections')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'promise_to_pay'
        ordering = ['-due_date']

    def __str__(self):
        return f"PTP {self.id}: ${self.amount} due {self.due_date} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"ptp-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)
