from rest_framework import serializers
from copilot.models import CopilotSession, CopilotQuery


class CopilotQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = CopilotQuery
        fields = [
            'id', 'session', 'user', 'query_text', 'response_kind',
            'answer_text', 'sql_query', 'sql_provenance', 'citations',
            'evidence', 'refusal_code', 'uncertainty_note', 'confidence_score',
            'latency_ms', 'feedback', 'feedback_notes', 'created_at'
        ]


class CopilotSessionSerializer(serializers.ModelSerializer):
    queries = CopilotQuerySerializer(many=True, read_only=True)

    class Meta:
        model = CopilotSession
        fields = ['id', 'user', 'customer', 'title', 'queries', 'created_at', 'updated_at']
