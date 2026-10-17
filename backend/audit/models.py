"""Audit event model — append-only audit trail."""
from django.db import models
from django.conf import settings
import uuid


class AuditEvent(models.Model):
    """Immutable audit event record."""

    class EventType(models.TextChoices):
        SEED_CREATED = 'SEED_CREATED', 'Seed Created'
        PAYMENT_INGESTED = 'PAYMENT_INGESTED', 'Payment Ingested'
        IDENTITY_MATCH_PROPOSED = 'IDENTITY_MATCH_PROPOSED', 'Identity Match Proposed'
        IDENTITY_APPROVED = 'IDENTITY_APPROVED', 'Identity Approved'
        IDENTITY_REJECTED = 'IDENTITY_REJECTED', 'Identity Rejected'
        IDENTITY_DEFERRED = 'IDENTITY_DEFERRED', 'Identity Deferred'
        RECOMMENDATION_APPROVED = 'RECOMMENDATION_APPROVED', 'Recommendation Approved'
        RECOMMENDATION_REJECTED = 'RECOMMENDATION_REJECTED', 'Recommendation Rejected'
        RECOMMENDATION_ESCALATED = 'RECOMMENDATION_ESCALATED', 'Recommendation Escalated'
        RECOMMENDATION_EXECUTED = 'RECOMMENDATION_EXECUTED', 'Recommendation Executed'
        RECOMMENDATION_EDITED = 'RECOMMENDATION_EDITED', 'Recommendation Edited'
        COPILOT_QUERY = 'COPILOT_QUERY', 'Copilot Query'
        SQL_REJECTED = 'SQL_REJECTED', 'SQL Rejected'
        SECURITY_REFUSAL = 'SECURITY_REFUSAL', 'Security Refusal'
        LOGIN = 'LOGIN', 'Login'
        LOGOUT = 'LOGOUT', 'Logout'
        ASSIGNMENT_CHANGED = 'ASSIGNMENT_CHANGED', 'Assignment Changed'
        POLICY_PUBLISHED = 'POLICY_PUBLISHED', 'Policy Published'

    id = models.CharField(max_length=50, primary_key=True, default='')
    type = models.CharField(max_length=50, choices=EventType.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='audit_events'
    )
    actor_name = models.CharField(max_length=200, blank=True, help_text='Denormalized for immutability')
    entity_id = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    summary = models.TextField()
    details = models.JSONField(default=dict)

    class Meta:
        db_table = 'audit_event'
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.type}] {self.entity_id} at {self.timestamp}"

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"audit-{uuid.uuid4().hex[:8]}"
        super().save(*args, **kwargs)
