"""
Experimentation models for A/B testing, champion/challenger strategies, and business metric tracking.
"""
from django.db import models
from django.conf import settings
import uuid


class Experiment(models.Model):
    """A/B experiment configuration for testing strategies, policies, or ML models."""

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        RUNNING = 'RUNNING', 'Running'
        PAUSED = 'PAUSED', 'Paused'
        CONCLUDED = 'CONCLUDED', 'Concluded'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField()
    hypothesis = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    primary_metric = models.CharField(max_length=100, default='cure_rate')
    target_sample_size = models.PositiveIntegerField(default=1000)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Experiment: {self.name} ({self.status})"


class ExperimentCohort(models.Model):
    """Variant / cohort arm in an active experiment (e.g., Champion vs Challenger)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name='cohorts')
    name = models.CharField(max_length=100)  # e.g., 'Control', 'Challenger-SMS-First'
    allocation_percentage = models.FloatField(default=50.0)
    strategy_config = models.JSONField(default=dict, help_text="Strategy hyperparameters or rule overrides")

    class Meta:
        unique_together = ('experiment', 'name')

    def __str__(self):
        return f"{self.experiment.name} - {self.name} ({self.allocation_percentage}%)"


class CohortAssignment(models.Model):
    """Assignment record linking an account or customer to an experiment cohort."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE)
    cohort = models.ForeignKey(ExperimentCohort, on_delete=models.CASCADE)
    account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE, related_name='experiment_assignments')
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('experiment', 'account')

    def __str__(self):
        return f"Account {self.account_id} -> {self.cohort.name}"


class MetricSnapshot(models.Model):
    """Point-in-time KPI snapshot comparing experiment arms."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name='metric_snapshots')
    cohort = models.ForeignKey(ExperimentCohort, on_delete=models.CASCADE)
    snapshot_date = models.DateField()
    sample_size = models.PositiveIntegerField(default=0)
    cure_rate = models.FloatField(default=0.0)
    ptp_adherence_rate = models.FloatField(default=0.0)
    contacts_per_cure = models.FloatField(default=0.0)
    total_recovered = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    p_value = models.FloatField(null=True, blank=True)
    is_statistically_significant = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.cohort.name} KPI @ {self.snapshot_date}: Cure={self.cure_rate:.2%}"
