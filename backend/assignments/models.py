"""
Assignment models — queue management, agent workload, and routing optimization.
"""
from django.db import models
from django.conf import settings
import uuid


class AgentProfile(models.Model):
    """Capacity, skills, and workload profile for a collection agent."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='agent_profile')
    max_active_cases = models.PositiveIntegerField(default=50)
    current_workload = models.PositiveIntegerField(default=0)
    skills = models.JSONField(default=list, help_text="List of agent skills: hardship, tier1, tier2, french, mortgage")
    is_active_for_routing = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Agent {self.user.username} ({self.current_workload}/{self.max_active_cases})"


class QueueAssignment(models.Model):
    """Dynamic queue assignment for accounts to authorized collections agents."""

    class Status(models.TextChoices):
        QUEUED = 'QUEUED', 'Queued'
        ASSIGNED = 'ASSIGNED', 'Assigned'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        RESOLVED = 'RESOLVED', 'Resolved'
        REASSIGNED = 'REASSIGNED', 'Reassigned'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE, related_name='assignments')
    assigned_agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_cases')
    priority_score = models.FloatField(default=0.0, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ASSIGNED)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='made_assignments')
    routing_reason = models.CharField(max_length=255, blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority_score', 'assigned_at']

    def __str__(self):
        return f"Assignment {self.id} -> Account {self.account_id} to {self.assigned_agent}"
