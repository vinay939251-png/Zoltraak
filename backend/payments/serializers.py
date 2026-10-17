from rest_framework import serializers
from payments.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    customer_id = serializers.CharField(source='account.customer.id', read_only=True)
    customer_name = serializers.CharField(source='account.customer.name', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'account', 'customer_id', 'customer_name', 'event_id', 'amount', 'currency',
            'status', 'date', 'source_system', 'ingested_at', 'created_at'
        ]
