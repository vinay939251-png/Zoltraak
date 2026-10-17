"""Customer domain models — Golden Customer 360 and source records."""
from django.db import models
from django.conf import settings
import uuid


class SourceSystem(models.Model):
    """Registered source system for data provenance tracking."""
    name = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=30, default='DEMO_ADAPTER')
    last_refresh = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'source_system'

    def __str__(self):
        return self.name


class Customer(models.Model):
    """Golden Customer record — the unified identity."""
    id = models.CharField(max_length=50, primary_key=True, default='')
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    risk_note = models.TextField(blank=True, help_text='Internal notes, not customer-facing')

    # Lineage
    source_system = models.CharField(max_length=100, default='golden-customer')
    source_record_id = models.CharField(max_length=100, blank=True)
    observed_at = models.DateTimeField(null=True, blank=True)
    ingested_at = models.DateTimeField(auto_now_add=True)
    transformation_version = models.CharField(max_length=50, default='golden-v1')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customer'

    def __str__(self):
        return f"{self.name} ({self.id})"

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"cust-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)


class CustomerIdentity(models.Model):
    """Source-system identity linked to a golden customer."""

    class MatchType(models.TextChoices):
        EXACT = 'exact', 'Exact'
        PROBABILISTIC = 'probabilistic', 'Probabilistic'

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='identities')
    source_system = models.CharField(max_length=100)
    source_id = models.CharField(max_length=100)
    match_type = models.CharField(max_length=20, choices=MatchType.choices)
    score = models.FloatField(null=True, blank=True, help_text='Match confidence 0-1')
    evidence = models.JSONField(default=list, help_text='List of matching evidence types')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'customer_identity'
        unique_together = ['source_system', 'source_id']

    def __str__(self):
        return f"{self.source_system}:{self.source_id} → {self.customer_id}"
