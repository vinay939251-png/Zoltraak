"""
Demo authentication class supporting role switching and header-based actor identification.
Ensures zero-friction development/demonstration while enforcing role-based permissions.
"""
from rest_framework import authentication
from authentication.models import User


class DemoHeaderAuthentication(authentication.BaseAuthentication):
    """
    Authenticates requests using:
    1. 'X-Actor-User-Id' header (e.g. 'agent-001', 'lead-001', 'steward-001')
    2. 'X-Demo-Role' header (e.g. 'team_lead', 'data_steward')
    3. Session 'demo_user_id'
    4. Falls back to default Collections Agent
    """

    def authenticate(self, request):
        actor_id = request.headers.get('X-Actor-User-Id')
        role_header = request.headers.get('X-Demo-Role')
        session_user_id = request.session.get('demo_user_id') if hasattr(request, 'session') else None

        user = None

        if actor_id:
            user = User.objects.filter(username=actor_id).first()
            if not user:
                user = User.objects.filter(role=actor_id).first()
            if not user and str(actor_id).isdigit():
                user = User.objects.filter(id=int(actor_id)).first()
        elif session_user_id:
            user = User.objects.filter(username=session_user_id).first()
            if not user and str(session_user_id).isdigit():
                user = User.objects.filter(id=int(session_user_id)).first()
        elif role_header:
            user = User.objects.filter(role=role_header).first()

        if not user:
            # Fall back to default demo agent
            user = User.objects.filter(role=User.Role.COLLECTIONS_AGENT).first()
            if not user:
                user = User.objects.first()

        if user:
            return (user, None)
        return None
