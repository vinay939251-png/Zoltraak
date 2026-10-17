"""Payment models with idempotency and provenance."""
from django.db import models
import uuid


class Payment(models.Model):
    """Recorded payment event with idempotency protection."""

    class Status(models.TextChoices):
        RECONCILED = 'RECONCILED', 'Reconciled'
        PENDING = 'PENDING', 'Pending'
        REVERSED = 'REVERSED', 'Reversed'
        FAILED = 'FAILED', 'Failed'

    id = models.CharField(max_length=50, primary_key=True, default='')
    event_id = models.CharField(max_length=100, unique=True, help_text='Idempotency key')
    account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default='CAD')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECONCILED)
    date = models.DateField()
    source_system = models.CharField(max_length=100, default='payment-ledger')
    ingested_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payment'
        ordering = ['-date']

    def __str__(self):
        return f"Payment {self.id}: ${self.amount} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"pay-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)
