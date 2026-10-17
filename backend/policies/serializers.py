from rest_framework import serializers
from policies.models import PolicyDocument, PolicyChunk


class PolicyChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyChunk
        fields = ['id', 'policy', 'text', 'topic', 'chunk_index', 'created_at']


class PolicyDocumentSerializer(serializers.ModelSerializer):
    chunks = PolicyChunkSerializer(many=True, read_only=True)
    approved_by_username = serializers.CharField(source='approved_by.username', read_only=True)

    class Meta:
        model = PolicyDocument
        fields = [
            'id', 'version', 'status', 'effective_date', 'title', 'content',
            'checksum', 'access_classification', 'approved_by', 'approved_by_username',
            'chunks', 'created_at', 'updated_at'
        ]
