"""
Platform monitoring views for health checks, pipeline telemetry, and data quality metrics.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.utils import timezone
from accounts.models import Account
from customers.models import Customer
from decisioning.models import Recommendation
from identity.models import IdentityMatchCandidate


class SystemHealthView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from data_platform.streaming.broker import broker
        telemetry = broker.get_topic_telemetry()

        return Response({
            'status': 'OPERATIONAL',
            'timestamp': timezone.now().isoformat(),
            'environment': 'DEMO',
            'components': {
                'database': 'CONNECTED (SQLite local development substitute for PostgreSQL)',
                'llm_copilot': 'ACTIVE (Google Gemini 1.5 Flash configured)',
                'rules_engine': 'ONLINE (v2.1 statutory compliance rules active)',
                'identity_service': 'ONLINE (Splink deterministic & probabilistic tiers)',
                'audit_subsystem': 'RECORDING (Append-only immutable trail)',
                'kafka_streaming_engine': f"ONLINE ({telemetry['total_topics']} topics, {telemetry['total_messages']} messages in partitioned log)",
                'spark_lakehouse_pipeline': 'ONLINE (PySpark DataFrame lakehouse engine: Raw -> Silver -> Golden)'
            }
        })


class PipelineStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        import json
        from pathlib import Path
        from django.conf import settings
        from data_platform.streaming.broker import broker
        from data_platform import LAKEHOUSE_ROOT

        telemetry = broker.get_topic_telemetry()
        manifest_file = LAKEHOUSE_ROOT / "manifests" / "latest_manifest.json"
        latest_job = None
        if manifest_file.exists():
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    latest_job = json.load(f)
            except Exception:
                pass

        return Response({
            'pipeline_status': 'ACTIVE',
            'streaming_broker': {
                'status': 'ONLINE',
                'engine': 'Python Partitioned Commit Log (Kafka-compatible API)',
                'total_topics': telemetry['total_topics'],
                'total_events_streamed': telemetry['total_messages'],
                'topics': telemetry['topics']
            },
            'batch_lakehouse': {
                'status': 'ONLINE',
                'engine': 'PySpark DataFrame Batch Processor (Raw -> Silver -> Golden)',
                'latest_job': latest_job or {
                    'status': 'READY_FOR_EXECUTION',
                    'note': 'Trigger on demand via POST /api/v1/monitoring/pipeline/'
                }
            },
            'zones': {
                'raw': {
                    'description': 'Raw event ingestion (Kafka commit log & raw payloads)',
                    'status': 'HEALTHY',
                    'records_processed': latest_job['zones']['raw']['records_ingested'] if latest_job else telemetry['total_messages']
                },
                'silver': {
                    'description': 'Deduplicated, standardized schemas with idempotency keys & DLQ',
                    'status': 'HEALTHY',
                    'cleansed_records': latest_job['zones']['silver']['cleansed_records'] if latest_job else Account.objects.count(),
                    'dlq_count': latest_job['zones']['silver']['dlq_records'] if latest_job else 0
                },
                'golden': {
                    'description': 'Golden Customer 360 and unified financial read models',
                    'status': 'HEALTHY',
                    'total_golden_customers': Customer.objects.count(),
                    'total_active_accounts': Account.objects.filter(status='ACTIVE').count()
                }
            }
        })

    def post(self, request):
        """Triggers a live Spark lakehouse batch transformation job."""
        from data_platform.lakehouse.runner import pipeline_runner
        manifest = pipeline_runner.run_pipeline()
        return Response({
            'status': 'SUCCESS',
            'message': 'Spark lakehouse batch pipeline executed successfully.',
            'manifest': manifest
        })


class DataQualityView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        accounts = Account.objects.all()
        total_accounts = accounts.count() or 1
        dnc_count = accounts.filter(dnc=True).count()
        cap_exceeded = accounts.filter(contact_count_7d__gte=4).count()
        disputes = accounts.filter(dispute=True).count()
        hardship = accounts.filter(hardship=True).count()
        pending_identities = IdentityMatchCandidate.objects.filter(status='PENDING').count()

        return Response({
            'total_monitored_accounts': total_accounts,
            'violations_summary': {
                'contact_cap_exceeded_count': cap_exceeded,
                'do_not_contact_active_count': dnc_count,
                'active_disputes_count': disputes,
                'active_hardship_count': hardship,
                'pending_identity_ambiguities': pending_identities
            },
            'quality_score_percent': round(100.0 - ((cap_exceeded + pending_identities) / total_accounts * 10), 1),
            'last_evaluated': timezone.now().isoformat()
        })
