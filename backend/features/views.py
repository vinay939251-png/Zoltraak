"""
Feature store views with monitoring and definitions.
"""
from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from features.models import FeatureDefinition, FeatureSnapshot
from features.serializers import FeatureDefinitionSerializer, FeatureSnapshotSerializer


class FeatureDefinitionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FeatureDefinition.objects.all().order_by('name')
    serializer_class = FeatureDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated]


class FeatureMonitoringView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from features.skew_detector import skew_detector
        report = skew_detector.evaluate_skew()
        return Response(report)
