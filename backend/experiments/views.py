"""
Controlled experiments and champion-challenger A/B testing views.
"""
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from experiments.models import Experiment, ExperimentCohort, MetricSnapshot
from experiments.serializers import ExperimentSerializer, MetricSnapshotSerializer


class ExperimentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Experiment.objects.prefetch_related('cohorts', 'metric_snapshots').all().order_by('-created_at')
    serializer_class = ExperimentSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['get'])
    def metrics(self, request, pk=None):
        experiment = self.get_object()
        snapshots = MetricSnapshot.objects.filter(experiment=experiment).select_related('cohort').order_by('snapshot_date')
        return Response(MetricSnapshotSerializer(snapshots, many=True).data)

    @action(detail=True, methods=['get'])
    def significance(self, request, pk=None):
        """Calculates two-proportion Z-test, 95% confidence intervals, and statistical maturity."""
        from experiments.statistics import stat_engine
        experiment = self.get_object()
        report = stat_engine.analyze_experiment(experiment)
        return Response(report)

