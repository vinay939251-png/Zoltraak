"""Decisioning models — recommendations, rules, and decision memory."""
from django.db import models
from django.conf import settings
import uuid


class RuleSetVersion(models.Model):
    """Versioned deterministic rule set."""
    id = models.CharField(max_length=50, primary_key=True, default='')
    version = models.CharField(max_length=30)
    description = models.TextField(blank=True)
    rules = models.JSONField(default=list)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'rule_set_version'

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"rules-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)


class Recommendation(models.Model):
    """AI-generated recommendation requiring human review."""

    class Status(models.TextChoices):
        GENERATED = 'GENERATED', 'Generated'
        PENDING_REVIEW = 'PENDING_REVIEW', 'Pending Review'
        APPROVED = 'APPROVED', 'Approved'
        EDITED = 'EDITED', 'Edited'
        OVERRIDDEN = 'OVERRIDDEN', 'Overridden'
        REJECTED = 'REJECTED', 'Rejected'
        ESCALATED = 'ESCALATED', 'Escalated'
        EXECUTED = 'EXECUTED', 'Executed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        FAILED = 'FAILED', 'Failed'

    ALLOWED_TRANSITIONS = {
        'GENERATED': ['PENDING_REVIEW'],
        'PENDING_REVIEW': ['APPROVED', 'EDITED', 'REJECTED', 'ESCALATED'],
        'EDITED': ['APPROVED', 'REJECTED'],
        'ESCALATED': ['APPROVED', 'REJECTED'],
        'APPROVED': ['EXECUTED', 'CANCELLED'],
        'EXECUTED': [],
        'REJECTED': [],
        'CANCELLED': [],
        'FAILED': [],
        'OVERRIDDEN': ['APPROVED', 'REJECTED'],
    }

    id = models.CharField(max_length=50, primary_key=True, default='')
    account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE, related_name='recommendations')
    version = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_REVIEW)
    target = models.CharField(max_length=200, default='30-day cure demonstration')
    score = models.FloatField(default=0)
    model_version = models.CharField(max_length=50, default='demo-untrained-v1')
    prediction_timestamp = models.DateTimeField(null=True, blank=True)
    action = models.CharField(max_length=50, default='outbound_call')
    top_features = models.JSONField(default=list)
    review_reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='reviewed_recommendations'
    )
    idempotency_key = models.CharField(max_length=100, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'recommendation'
        ordering = ['-created_at']

    def __str__(self):
        return f"Rec {self.id}: {self.action} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"rec-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)

    def can_transition_to(self, new_status):
        return new_status in self.ALLOWED_TRANSITIONS.get(self.status, [])


class DecisionMemory(models.Model):
    """Immutable decision snapshot for audit and reproducibility."""
    id = models.CharField(max_length=50, primary_key=True, default='')
    recommendation = models.ForeignKey(Recommendation, on_delete=models.CASCADE, related_name='decision_memory')
    account_id = models.CharField(max_length=50)
    feature_values = models.JSONField(default=dict)
    feature_timestamps = models.JSONField(default=dict)
    feature_version = models.CharField(max_length=30)
    model_id = models.CharField(max_length=50)
    model_version = models.CharField(max_length=50)
    model_prediction = models.FloatField()
    policy_version = models.CharField(max_length=30)
    rule_version = models.CharField(max_length=30)
    rule_results = models.JSONField(default=list)
    candidate_action = models.CharField(max_length=50)
    explanation_inputs = models.JSONField(default=dict)
    human_review_outcome = models.CharField(max_length=30, blank=True)
    final_action = models.CharField(max_length=50, blank=True)
    correlation_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'decision_memory'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"dm-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)
