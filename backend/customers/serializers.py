from rest_framework import serializers
from customers.models import Customer, CustomerIdentity, SourceSystem


class CustomerIdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerIdentity
        fields = ['id', 'source_system', 'source_id', 'match_type', 'score', 'evidence', 'created_at']


class CustomerSerializer(serializers.ModelSerializer):
    identities = CustomerIdentitySerializer(many=True, read_only=True)

    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'email', 'phone', 'date_of_birth', 'address', 'risk_note',
            'source_system', 'source_record_id', 'observed_at', 'ingested_at', 'transformation_version',
            'identities', 'created_at', 'updated_at'
        ]


class SourceSystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceSystem
        fields = '__all__'
