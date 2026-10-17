"""
Append-only immutable audit trail explorer views.
"""
from rest_framework import viewsets, permissions
from audit.models import AuditEvent
from audit.serializers import AuditEventSerializer


class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only audit trail explorer per Section 12.10.
    Provides authorized filtering by entity, actor, event type, and date.
    """
    queryset = AuditEvent.objects.all().order_by('-timestamp')
    serializer_class = AuditEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        event_type = self.request.query_params.get('type')
        entity_id = self.request.query_params.get('entity_id')
        actor = self.request.query_params.get('actor')
        search = self.request.query_params.get('search', '').strip()

        if event_type:
            qs = qs.filter(type=event_type)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        if actor:
            qs = qs.filter(actor__username=actor) | qs.filter(actor_name__icontains=actor)
        if search:
            qs = qs.filter(summary__icontains=search) | qs.filter(entity_id__icontains=search)

        return qs
