"""
Policy library views with RAG chunk retrieval and citations.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from policies.models import PolicyDocument, PolicyChunk
from policies.serializers import PolicyDocumentSerializer, PolicyChunkSerializer
from audit.utils import log_audit


class PolicyDocumentViewSet(viewsets.ModelViewSet):
    queryset = PolicyDocument.objects.prefetch_related('chunks').all().order_by('-effective_date')
    serializer_class = PolicyDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='search')
    def search_policies(self, request):
        """
        RAG policy chunk search returning ranked matching excerpts with chunk citations.
        """
        query = (request.data.get('query') or '').lower().strip()
        if not query:
            return Response({'error': 'Query string is required.'}, status=status.HTTP_400_BAD_REQUEST)

        keywords = query.split()
        chunks = PolicyChunk.objects.filter(policy__status__in=['ACTIVE', 'ACTIVE_DEMO']).select_related('policy')

        scored_chunks = []
        for c in chunks:
            score = 0
            text_lower = c.text.lower()
            topic_lower = c.topic.lower()
            for kw in keywords:
                if kw in topic_lower:
                    score += 3
                if kw in text_lower:
                    score += 1
            if score > 0:
                scored_chunks.append({
                    'chunk_id': c.id,
                    'policy_id': c.policy.id,
                    'policy_version': c.policy.version,
                    'topic': c.topic,
                    'text': c.text,
                    'relevance_score': score,
                    'citation': f"[{c.policy.title} v{c.policy.version} § {c.topic} ({c.id})]"
                })

        scored_chunks.sort(key=lambda x: x['relevance_score'], reverse=True)

        return Response({
            'query': query,
            'match_count': len(scored_chunks),
            'results': scored_chunks[:10],
            'uncertainty_disclaimer': 'Demonstration policy content for simulation only; not official institutional guidelines.'
        })


class PolicyChunkViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PolicyChunk.objects.select_related('policy').all()
    serializer_class = PolicyChunkSerializer
    permission_classes = [permissions.IsAuthenticated]
