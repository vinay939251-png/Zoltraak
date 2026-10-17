"""
Copilot models for conversation tracking, NL-to-SQL audit, and RAG ground truth.
"""
from django.db import models
from django.conf import settings
import uuid


class CopilotSession(models.Model):
    """User conversation session with the AI Copilot."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='copilot_sessions')
    customer = models.ForeignKey('customers.Customer', on_delete=models.SET_NULL, null=True, blank=True, related_name='copilot_sessions')
    title = models.CharField(max_length=255, default='New Consultation')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"CopilotSession {self.id} ({self.user.username})"


class CopilotQuery(models.Model):
    """Grounded natural-language copilot query and answer execution record."""

    class ResponseKind(models.TextChoices):
        STRUCTURED = 'structured', 'Structured DB Query'
        POLICY = 'policy', 'Policy Retrieval'
        AMBIGUOUS = 'ambiguous', 'Clarification Required'
        REFUSAL = 'refusal', 'Governance Refusal'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(CopilotSession, on_delete=models.CASCADE, related_name='queries')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    query_text = models.TextField()
    response_kind = models.CharField(max_length=20, choices=ResponseKind.choices, default=ResponseKind.STRUCTURED)
    answer_text = models.TextField()
    sql_query = models.TextField(blank=True, help_text="Validated read-only SQL generated and executed")
    sql_provenance = models.JSONField(default=dict, blank=True)
    citations = models.JSONField(default=list, blank=True)
    evidence = models.JSONField(default=list, blank=True)
    refusal_code = models.CharField(max_length=50, blank=True)
    uncertainty_note = models.CharField(max_length=255, blank=True)
    confidence_score = models.FloatField(default=1.0)
    latency_ms = models.PositiveIntegerField(default=0)
    feedback = models.CharField(
        max_length=10,
        choices=[('UP', 'Thumbs Up'), ('DOWN', 'Thumbs Down'), ('NONE', 'None')],
        default='NONE'
    )
    feedback_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Query {self.id} [{self.response_kind}]: {self.query_text[:40]}"
