from rest_framework import serializers
from experiments.models import Experiment, ExperimentCohort, CohortAssignment, MetricSnapshot


class ExperimentCohortSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExperimentCohort
        fields = '__all__'


class MetricSnapshotSerializer(serializers.ModelSerializer):
    cohort_name = serializers.CharField(source='cohort.name', read_only=True)

    class Meta:
        model = MetricSnapshot
        fields = '__all__'


class ExperimentSerializer(serializers.ModelSerializer):
    cohorts = ExperimentCohortSerializer(many=True, read_only=True)
    metric_snapshots = MetricSnapshotSerializer(many=True, read_only=True)

    class Meta:
        model = Experiment
        fields = [
            'id', 'name', 'description', 'hypothesis', 'status', 'primary_metric',
            'target_sample_size', 'created_by', 'cohorts', 'metric_snapshots',
            'created_at', 'updated_at'
        ]
