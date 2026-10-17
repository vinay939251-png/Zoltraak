"""
Approval models for human-in-the-loop decisioning and governance.
Enforces durable approval workflow with explicit states and idempotency.
"""
from django.db import models
from django.conf import settings
import uuid


class ApprovalRequest(models.Model):
    """Durable approval record for recommendations requiring human review."""

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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recommendation = models.ForeignKey(
        'decisioning.Recommendation',
        on_delete=models.CASCADE,
        related_name='approvals'
    )
    recommendation_version = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING_REVIEW
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requested_approvals'
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_approvals'
    )
    reason = models.TextField(blank=True, help_text="Justification for approval, override, or rejection")
    proposed_action = models.CharField(max_length=100)
    final_action = models.CharField(max_length=100, blank=True)
    override_payload = models.JSONField(default=dict, blank=True)
    idempotency_key = models.CharField(max_length=128, unique=True, db_index=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    execution_result = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Approval {self.id} [{self.status}] for Rec {self.recommendation_id}"
