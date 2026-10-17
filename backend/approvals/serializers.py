from rest_framework import serializers
from approvals.models import ApprovalRequest
from decisioning.serializers import DecisionMemorySerializer


class ApprovalRequestSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.CharField(source='requested_by.username', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.username', read_only=True)
    account_id = serializers.CharField(source='recommendation.account.id', read_only=True)
    customer_id = serializers.CharField(source='recommendation.account.customer.id', read_only=True)
    customer_name = serializers.CharField(source='recommendation.account.customer.name', read_only=True)
    account_product = serializers.CharField(source='recommendation.account.product', read_only=True)
    overdue_balance = serializers.DecimalField(source='recommendation.account.overdue_balance', max_digits=12, decimal_places=2, read_only=True)
    dpd = serializers.IntegerField(source='recommendation.account.dpd', read_only=True)
    contact_count_7d = serializers.IntegerField(source='recommendation.account.contact_count_7d', read_only=True)
    score = serializers.FloatField(source='recommendation.score', read_only=True)
    model_version = serializers.CharField(source='recommendation.model_version', read_only=True)
    top_features = serializers.JSONField(source='recommendation.top_features', read_only=True)
    recommendation_status = serializers.CharField(source='recommendation.status', read_only=True)
    decision_memory = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalRequest
        fields = [
            'id', 'recommendation', 'recommendation_version', 'status',
            'requested_by', 'requested_by_name', 'reviewed_by', 'reviewed_by_name',
            'reason', 'proposed_action', 'final_action', 'override_payload',
            'idempotency_key', 'executed_at', 'execution_result',
            'account_id', 'customer_id', 'customer_name', 'account_product',
            'overdue_balance', 'dpd', 'contact_count_7d', 'score', 'model_version',
            'top_features', 'recommendation_status', 'decision_memory',
            'created_at', 'updated_at'
        ]

    def get_decision_memory(self, obj):
        if not obj.recommendation_id:
            return None
        dm = obj.recommendation.decision_memory.order_by('-created_at').first()
        if dm:
            return DecisionMemorySerializer(dm).data
        return None

