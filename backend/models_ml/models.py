"""ML model registry and predictions."""
from django.db import models
import uuid


class ModelRegistry(models.Model):
    """Registered ML model with version and status tracking."""

    class Status(models.TextChoices):
        DEVELOPMENT_DEMONSTRATION = 'DEVELOPMENT_DEMONSTRATION', 'Development Demonstration'
        DESIGN_ONLY = 'DESIGN_ONLY', 'Design Only'
        TRAINING = 'TRAINING', 'Training'
        EVALUATING = 'EVALUATING', 'Evaluating'
        VALIDATED = 'VALIDATED', 'Validated'
        DEPLOYED = 'DEPLOYED', 'Deployed'
        RETIRED = 'RETIRED', 'Retired'

    id = models.CharField(max_length=50, primary_key=True, default='')
    target = models.CharField(max_length=200)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DEVELOPMENT_DEMONSTRATION)
    calibrated = models.BooleanField(default=False)
    trained = models.BooleanField(default=False)
    explanation = models.TextField(blank=True)
    artifact_path = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'model_registry'

    def __str__(self):
        return f"{self.id} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"model-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)


class Prediction(models.Model):
    """Individual model prediction with provenance."""
    id = models.CharField(max_length=50, primary_key=True, default='')
    account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE, related_name='predictions')
    model = models.ForeignKey(ModelRegistry, on_delete=models.CASCADE, related_name='predictions')
    score = models.FloatField()
    target_definition = models.CharField(max_length=200)
    prediction_timestamp = models.DateTimeField(auto_now_add=True)
    feature_snapshot = models.ForeignKey(
        'features.FeatureSnapshot', null=True, blank=True,
        on_delete=models.SET_NULL
    )
    calibration_status = models.CharField(max_length=30, default='uncalibrated')
    data_quality_status = models.CharField(max_length=30, default='demo')
    shap_values = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'prediction'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"pred-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)
