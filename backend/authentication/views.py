"""
Authentication views supporting role inspection, demo user switching, and user listing.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, permissions, status
from authentication.models import User
from authentication.serializers import UserSerializer


class MeView(APIView):
    """Returns the currently authenticated actor, their permissions, and switchable demo personas."""

    def get(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            # Fallback for unauthenticated demo
            user = User.objects.filter(role=User.Role.COLLECTIONS_AGENT).first() or User.objects.first()

        switchable_users = User.objects.filter(is_active=True).values('id', 'username', 'first_name', 'last_name', 'role')

        permissions_map = {
            'can_view_all_accounts': user.role != User.Role.COLLECTIONS_AGENT,
            'can_approve_recommendation': user.role in [User.Role.TEAM_LEAD, User.Role.ADMINISTRATOR],
            'can_override_recommendation': user.role in [User.Role.TEAM_LEAD, User.Role.ADMINISTRATOR],
            'can_manage_identity': user.role in [User.Role.DATA_STEWARD, User.Role.ADMINISTRATOR],
            'can_manage_hardship': user.role in [User.Role.HARDSHIP_SPECIALIST, User.Role.TEAM_LEAD, User.Role.ADMINISTRATOR],
            'can_manage_policies': user.role in [User.Role.ADMINISTRATOR],
            'can_view_audit': True,
            'can_view_features_models': True,
        }

        return Response({
            'user': UserSerializer(user).data if user else None,
            'role': user.role if user else 'anonymous',
            'permissions': permissions_map,
            'switchable_users': list(switchable_users),
            'environment': 'DEMO',
        })


class SwitchUserView(APIView):
    """Allows demo operators and tests to switch active persona dynamically."""

    def post(self, request):
        username = request.data.get('username')
        role = request.data.get('role')

        user = None
        if username:
            user = User.objects.filter(username=username).first()
        elif role:
            user = User.objects.filter(role=role).first()

        if not user:
            return Response({'error': 'User not found matching criteria.'}, status=status.HTTP_404_NOT_FOUND)

        request.session['demo_user_id'] = user.username
        return Response({
            'message': f'Switched active actor to {user.username} ({user.role})',
            'user': UserSerializer(user).data
        })


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
