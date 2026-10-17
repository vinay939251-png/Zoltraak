from rest_framework import serializers
from audit.models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = ['id', 'type', 'actor', 'actor_name', 'entity_id', 'timestamp', 'summary', 'details']
        read_only_fields = fields
