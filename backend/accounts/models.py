"""Account models — loans, cards, balances, and arrears."""
from django.db import models


class Account(models.Model):
    """Financial account linked to a golden customer."""

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        CLOSED = 'CLOSED', 'Closed'
        SUSPENDED = 'SUSPENDED', 'Suspended'
        CHARGED_OFF = 'CHARGED_OFF', 'Charged Off'

    class Product(models.TextChoices):
        PERSONAL_LOAN = 'Personal loan', 'Personal Loan'
        CREDIT_CARD = 'Credit card', 'Credit Card'
        MORTGAGE = 'Mortgage', 'Mortgage'
        LINE_OF_CREDIT = 'Line of credit', 'Line of Credit'

    id = models.CharField(max_length=50, primary_key=True, default='')
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, related_name='accounts')
    product = models.CharField(max_length=50, choices=Product.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    # Financial — use DecimalField for monetary amounts
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    overdue_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='CAD')

    # Collections state
    dpd = models.IntegerField(default=0, help_text='Days past due')
    hardship = models.BooleanField(default=False)
    dispute = models.BooleanField(default=False)
    dnc = models.BooleanField(default=False, help_text='Do-not-contact restriction')
    contact_count_7d = models.IntegerField(default=0, help_text='Contacts in 7-day window')

    # Assigned agent
    assigned_agent = models.ForeignKey(
        'authentication.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='assigned_accounts'
    )

    # Lineage
    source_system = models.CharField(max_length=100, default='')
    source_record_id = models.CharField(max_length=100, blank=True)
    observed_at = models.DateTimeField(null=True, blank=True)
    ingested_at = models.DateTimeField(auto_now_add=True)
    transformation_version = models.CharField(max_length=50, default='silver-v2')

    # Feature cache
    recent_payment_count = models.IntegerField(default=0)
    recent_payment_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    historical_ptp_adherence = models.FloatField(default=0.0)
    days_since_last_payment = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'account'

    def __str__(self):
        return f"{self.id} ({self.product}) - {self.customer_id}"

    def save(self, *args, **kwargs):
        if not self.id:
            import uuid
            self.id = f"acct-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)
