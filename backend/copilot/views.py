"""
Copilot API views for grounded interactive conversation, SQL execution provenance, and feedback.
"""
from rest_framework.views import APIView
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from copilot.models import CopilotSession, CopilotQuery
from copilot.serializers import CopilotSessionSerializer, CopilotQuerySerializer
from copilot.service import CopilotService


class CopilotQueryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        query_text = request.data.get('query')
        customer_id = request.data.get('customer_id')
        session_id = request.data.get('session_id')

        result = CopilotService.process_query(
            query_text=query_text,
            user=request.user,
            customer_id=customer_id,
            session_id=session_id
        )

        return Response(result, status=status.HTTP_200_OK)


class CopilotSessionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CopilotSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = CopilotSession.objects.prefetch_related('queries').all()
        if user.is_authenticated and user.role == 'collections_agent':
            qs = qs.filter(user=user)
        return qs.order_by('-created_at')


class CopilotFeedbackView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        query_id = request.data.get('query_id')
        feedback = request.data.get('feedback')  # 'UP', 'DOWN'
        notes = request.data.get('notes', '')

        if not query_id:
            return Response({'error': 'query_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        cq = CopilotQuery.objects.filter(id=query_id).first()
        if not cq:
            return Response({'error': 'Copilot query not found.'}, status=status.HTTP_404_NOT_FOUND)

        cq.feedback = feedback
        cq.feedback_notes = notes
        cq.save()

        return Response({'message': 'Feedback successfully recorded.', 'query_id': str(cq.id)})
