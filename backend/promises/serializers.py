from rest_framework import serializers
from promises.models import PromiseToPay


class PromiseToPaySerializer(serializers.ModelSerializer):
    customer_id = serializers.CharField(source='account.customer.id', read_only=True)
    customer_name = serializers.CharField(source='account.customer.name', read_only=True)

    class Meta:
        model = PromiseToPay
        fields = [
            'id', 'account', 'customer_id', 'customer_name', 'amount', 'currency',
            'due_date', 'status', 'source_system', 'created_at', 'updated_at'
        ]
