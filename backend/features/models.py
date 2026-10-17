"""Feature store models — definitions and snapshots."""
from django.db import models


class FeatureDefinition(models.Model):
    """Versioned feature definition."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    data_type = models.CharField(max_length=30)
    entity_key = models.CharField(max_length=50, default='account.id')
    calculation_logic = models.TextField(blank=True)
    observation_window = models.CharField(max_length=50, blank=True)
    missing_value_behavior = models.CharField(max_length=100, default='abstain')
    validation_rules = models.JSONField(default=dict)
    source_lineage = models.CharField(max_length=200, default='')
    owner = models.CharField(max_length=100, default='local-demo')
    version = models.CharField(max_length=30, default='demo-features-v1')
    leakage_safe = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'feature_definition'

    def __str__(self):
        return self.name


class FeatureSnapshot(models.Model):
    """Point-in-time feature snapshot for an account."""
    account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE, related_name='feature_snapshots')
    feature_version = models.CharField(max_length=30)
    values = models.JSONField(default=dict)
    missing_features = models.JSONField(default=list)
    observed_at = models.DateTimeField()
    available_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'feature_snapshot'
        ordering = ['-created_at']
