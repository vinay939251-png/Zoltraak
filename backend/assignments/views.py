"""
Assignment and workload management views.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from assignments.models import QueueAssignment, AgentProfile
from assignments.serializers import QueueAssignmentSerializer, AgentProfileSerializer
from accounts.models import Account
from authentication.models import User
from audit.utils import log_audit


class QueueAssignmentViewSet(viewsets.ModelViewSet):
    queryset = QueueAssignment.objects.select_related('account', 'assigned_agent', 'account__customer').all()
    serializer_class = QueueAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]


class AgentProfileViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AgentProfile.objects.select_related('user').all()
    serializer_class = AgentProfileSerializer
    permission_classes = [permissions.IsAuthenticated]


class ReassignView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.role not in ['team_lead', 'administrator']:
            return Response({'error': 'Only Team Leads and Administrators can reassign accounts.'}, status=status.HTTP_403_FORBIDDEN)

        account_id = request.data.get('account_id')
        new_agent_username = request.data.get('agent_username')
        reason = request.data.get('reason', 'Supervisor reassignment')

        account = Account.objects.filter(id=account_id).first()
        if not account:
            return Response({'error': 'Account not found.'}, status=status.HTTP_404_NOT_FOUND)

        new_agent = User.objects.filter(username=new_agent_username).first()
        if not new_agent:
            return Response({'error': f'Agent {new_agent_username} not found.'}, status=status.HTTP_404_NOT_FOUND)

        prev_agent = account.assigned_agent
        account.assigned_agent = new_agent
        account.save()

        # Update assignment record
        qa, _ = QueueAssignment.objects.get_or_create(account=account)
        qa.assigned_agent = new_agent
        qa.assigned_by = user
        qa.routing_reason = reason
        qa.status = QueueAssignment.Status.ASSIGNED
        qa.save()

        log_audit(
            'ASSIGNMENT_CHANGED',
            account.id,
            f"Reassigned Account {account.id} from {prev_agent.username if prev_agent else 'Unassigned'} to {new_agent.username}",
            actor=user,
            details={'reason': reason, 'new_agent': new_agent.username}
        )

        return Response({
            'message': f"Account {account.id} successfully reassigned to {new_agent.username}.",
            'account_id': account.id,
            'assigned_agent': new_agent.username
        })


class OptimizeQueueView(APIView):
    """
    Constrained work-allocation optimizer (Section 10.5).
    Optimizes queue distribution across agents adhering to skills, capacity, and DNC constraints.
    Supports dry-run preview or live application.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from assignments.optimizer import optimizer

        strategy = request.data.get('strategy', 'balanced_recovery')
        apply_changes = bool(request.data.get('apply', False))

        if apply_changes and request.user.role not in ['team_lead', 'administrator']:
            return Response(
                {'error': 'Only Team Leads and Administrators can apply automated queue reassignments.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            result = optimizer.optimize_queue(
                strategy=strategy,
                apply_reassignments=apply_changes,
                actor_user=request.user
            )
            return Response(result)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

