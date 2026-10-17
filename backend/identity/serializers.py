from rest_framework import serializers
from identity.models import IdentityMatchCandidate, IdentityMergeHistory


class IdentityMatchCandidateSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)

    class Meta:
        model = IdentityMatchCandidate
        fields = [
            'id', 'customer', 'customer_name', 'source_system', 'source_record_id',
            'score', 'status', 'evidence', 'conflicts', 'reason',
            'reviewed_by', 'reviewed_at', 'created_at', 'updated_at'
        ]


class IdentityMergeHistorySerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source='actor.username', read_only=True)
    reversed_by_username = serializers.CharField(source='reversed_by.username', read_only=True)

    class Meta:
        model = IdentityMergeHistory
        fields = '__all__'
