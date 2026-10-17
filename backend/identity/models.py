"""Identity resolution models — match candidates, reviews, merge history."""
from django.db import models
from django.conf import settings


class IdentityMatchCandidate(models.Model):
    """Proposed identity match awaiting review or auto-linked."""

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Review'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        DEFERRED = 'DEFERRED', 'Deferred'
        AUTO_LINKED = 'AUTO_LINKED', 'Auto-Linked'

    id = models.CharField(max_length=50, primary_key=True, default='')
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, related_name='match_candidates')
    source_system = models.CharField(max_length=100)
    source_record_id = models.CharField(max_length=100)
    score = models.FloatField(help_text='Match confidence 0-1')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    evidence = models.JSONField(default=list)
    conflicts = models.JSONField(default=list)
    reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='identity_reviews'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'identity_match_candidate'

    def __str__(self):
        return f"{self.id} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.id:
            import uuid
            self.id = f"match-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)


class IdentityMergeHistory(models.Model):
    """Versioned, reversible identity crosswalk changes."""
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, related_name='merge_history')
    previous_golden_id = models.CharField(max_length=50, blank=True)
    new_golden_id = models.CharField(max_length=50)
    source_ids = models.JSONField(default=list)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    reason = models.TextField()
    evidence = models.JSONField(default=dict)
    reversed = models.BooleanField(default=False)
    reversed_at = models.DateTimeField(null=True, blank=True)
    reversed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='merge_reversals'
    )
    reversal_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'identity_merge_history'
        ordering = ['-created_at']

    def __str__(self):
        return f"Merge {self.previous_golden_id} → {self.new_golden_id}"
