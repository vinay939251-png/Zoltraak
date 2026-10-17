from rest_framework import serializers
from decisioning.models import RuleSetVersion, Recommendation, DecisionMemory


class RuleSetVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuleSetVersion
        fields = '__all__'


class DecisionMemorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DecisionMemory
        fields = '__all__'


class RecommendationSerializer(serializers.ModelSerializer):
    account_id = serializers.CharField(source='account.id', read_only=True)
    customer_name = serializers.CharField(source='account.customer.name', read_only=True)
    customer_id = serializers.CharField(source='account.customer.id', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.username', read_only=True)
    decision_memory = serializers.SerializerMethodField()

    class Meta:
        model = Recommendation
        fields = [
            'id', 'account', 'account_id', 'customer_id', 'customer_name', 'version', 'status',
            'target', 'score', 'model_version', 'prediction_timestamp',
            'action', 'top_features', 'review_reason', 'reviewed_by', 'reviewed_by_name',
            'idempotency_key', 'created_at', 'updated_at', 'decision_memory'
        ]

    def get_decision_memory(self, obj):
        dm = obj.decision_memory.order_by('-created_at').first()
        if dm:
            return DecisionMemorySerializer(dm).data
        return None
