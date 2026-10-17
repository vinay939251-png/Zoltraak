"""
Comprehensive API routing for Agentic Collections Copilot (v1).
Maps all 21 endpoint groups required by Section 14 under /api/v1/.
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from authentication.views import MeView, SwitchUserView, UserViewSet
from customers.views import CustomerViewSet
from customers.ingest import IngestRawDataView
from accounts.views import AccountViewSet
from accounts.collections_views import CollectionsDashboardView, CollectionsQueueView
from payments.views import PaymentViewSet
from promises.views import PromiseToPayViewSet
from calls.views import CollectionContactViewSet, CallTranscriptViewSet, HardshipCaseViewSet, DisputeViewSet, TranscribeAudioView
from identity.views import IdentityCandidateViewSet, IdentityMergeHistoryViewSet
from copilot.views import CopilotQueryView, CopilotSessionViewSet, CopilotFeedbackView
from policies.views import PolicyDocumentViewSet, PolicyChunkViewSet
from features.views import FeatureDefinitionViewSet, FeatureMonitoringView
from models_ml.views import ModelRegistryViewSet, PredictionViewSet, TrainModelView, PredictAccountView
from decisioning.views import RecommendationViewSet, RuleSetVersionViewSet, DecisionMemoryViewSet, EvaluateRulesView
from approvals.views import ApprovalViewSet
from assignments.views import QueueAssignmentViewSet, AgentProfileViewSet, ReassignView, OptimizeQueueView
from audit.views import AuditEventViewSet
from experiments.views import ExperimentViewSet
from config.monitoring_views import SystemHealthView, PipelineStatusView, DataQualityView
import os
from django.conf import settings
from django.http import HttpResponse, FileResponse
from django.urls import re_path


def serve_spa(request, path=''):
    index_path = settings.BASE_DIR.parent / 'public' / 'index.html'
    if os.path.exists(index_path):
        return FileResponse(open(index_path, 'rb'), content_type='text/html')
    return HttpResponse("Collections Copilot SPA", content_type='text/plain')


def serve_public_asset(request, filename):
    file_path = settings.BASE_DIR.parent / 'public' / filename
    if os.path.exists(file_path):
        content_type = 'text/javascript' if filename.endswith('.js') else ('text/css' if filename.endswith('.css') else 'application/octet-stream')
        return FileResponse(open(file_path, 'rb'), content_type=content_type)
    return HttpResponse("File not found", status=404)


router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'accounts', AccountViewSet, basename='account')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'promises', PromiseToPayViewSet, basename='promise')
router.register(r'contacts/transcripts', CallTranscriptViewSet, basename='transcript')
router.register(r'contacts', CollectionContactViewSet, basename='contact')
router.register(r'identity/candidates', IdentityCandidateViewSet, basename='identity-candidate')
router.register(r'identity/merges', IdentityMergeHistoryViewSet, basename='identity-merge')
router.register(r'copilot/sessions', CopilotSessionViewSet, basename='copilot-session')
router.register(r'policies/chunks', PolicyChunkViewSet, basename='policy-chunk')
router.register(r'policies', PolicyDocumentViewSet, basename='policy')
router.register(r'features/definitions', FeatureDefinitionViewSet, basename='feature-definition')
router.register(r'models', ModelRegistryViewSet, basename='model-registry')
router.register(r'predictions', PredictionViewSet, basename='prediction')
router.register(r'recommendations', RecommendationViewSet, basename='recommendation')
router.register(r'rules', RuleSetVersionViewSet, basename='rule-set')
router.register(r'decisioning/memories', DecisionMemoryViewSet, basename='decision-memory')
router.register(r'approvals', ApprovalViewSet, basename='approval')
router.register(r'assignments/agents', AgentProfileViewSet, basename='agent-profile')
router.register(r'assignments', QueueAssignmentViewSet, basename='assignment')
router.register(r'audit', AuditEventViewSet, basename='audit')
router.register(r'experiments', ExperimentViewSet, basename='experiment')

urlpatterns = [
    path('admin/', admin.site.urls),

    # Authentication & User Management
    path('api/v1/auth/me/', MeView.as_view(), name='auth-me'),
    path('api/v1/auth/switch-user/', SwitchUserView.as_view(), name='auth-switch-user'),

    # Collections Operations & Outreach
    path('api/v1/collections/dashboard/', CollectionsDashboardView.as_view(), name='collections-dashboard'),
    path('api/v1/collections/queue/', CollectionsQueueView.as_view(), name='collections-queue'),
    path('api/v1/contacts/transcribe/', TranscribeAudioView.as_view(), name='contacts-transcribe'),
    path('api/v1/customers/ingest-raw/', IngestRawDataView.as_view(), name='customers-ingest-raw'),

    # Copilot AI Consultation
    path('api/v1/copilot/query/', CopilotQueryView.as_view(), name='copilot-query'),
    path('api/v1/copilot/feedback/', CopilotFeedbackView.as_view(), name='copilot-feedback'),

    # Feature & Rule Operations
    path('api/v1/features/monitoring/', FeatureMonitoringView.as_view(), name='features-monitoring'),
    path('api/v1/rules/evaluate/', EvaluateRulesView.as_view(), name='rules-evaluate'),

    # ML Training & Prediction Operations
    path('api/v1/models/train/', TrainModelView.as_view(), name='models-train'),
    path('api/v1/models/predict/', PredictAccountView.as_view(), name='models-predict'),

    # Assignments & Workload Optimization
    path('api/v1/assignments/reassign/', ReassignView.as_view(), name='assignments-reassign'),
    path('api/v1/assignments/optimize/', OptimizeQueueView.as_view(), name='assignments-optimize'),

    # Monitoring & Telemetry
    path('api/v1/monitoring/health/', SystemHealthView.as_view(), name='monitoring-health'),
    path('api/v1/monitoring/pipeline/', PipelineStatusView.as_view(), name='monitoring-pipeline'),
    path('api/v1/monitoring/quality/', DataQualityView.as_view(), name='monitoring-quality'),

    # DRF Router endpoints
    path('api/v1/', include(router.urls)),

    # Frontend SPA and Assets
    path('app.js', serve_public_asset, {'filename': 'app.js'}),
    path('styles.css', serve_public_asset, {'filename': 'styles.css'}),
    re_path(r'^(?!api/|admin/|static/).*$', serve_spa),
]

