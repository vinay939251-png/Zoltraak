from rest_framework import serializers
from accounts.models import Account
from customers.serializers import CustomerSerializer


class AccountSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    assigned_agent_name = serializers.CharField(source='assigned_agent.username', read_only=True)

    class Meta:
        model = Account
        fields = [
            'id', 'customer', 'customer_name', 'product', 'status',
            'balance', 'overdue_balance', 'currency', 'dpd',
            'hardship', 'dispute', 'dnc', 'contact_count_7d',
            'assigned_agent', 'assigned_agent_name',
            'source_system', 'source_record_id', 'observed_at', 'transformation_version',
            'recent_payment_count', 'recent_payment_amount', 'historical_ptp_adherence', 'days_since_last_payment',
            'created_at', 'updated_at'
        ]
