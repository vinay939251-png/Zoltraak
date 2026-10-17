from rest_framework import serializers
from assignments.models import AgentProfile, QueueAssignment


class AgentProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = AgentProfile
        fields = ['id', 'user', 'username', 'full_name', 'max_active_cases', 'current_workload', 'skills', 'is_active_for_routing', 'updated_at']


class QueueAssignmentSerializer(serializers.ModelSerializer):
    account_product = serializers.CharField(source='account.product', read_only=True)
    customer_id = serializers.CharField(source='account.customer.id', read_only=True)
    customer_name = serializers.CharField(source='account.customer.name', read_only=True)
    agent_name = serializers.CharField(source='assigned_agent.username', read_only=True)

    class Meta:
        model = QueueAssignment
        fields = [
            'id', 'account', 'account_product', 'customer_id', 'customer_name',
            'assigned_agent', 'agent_name', 'priority_score', 'status',
            'assigned_by', 'routing_reason', 'assigned_at', 'updated_at'
        ]
