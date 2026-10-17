"""
Role-based permission classes enforcing Section 6 access rules across all API endpoints.
"""
from rest_framework import permissions
from authentication.models import User


class IsCollectionsAgent(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Role.COLLECTIONS_AGENT)


class IsTeamLead(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in [User.Role.TEAM_LEAD, User.Role.ADMINISTRATOR])


class IsHardshipSpecialist(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in [User.Role.HARDSHIP_SPECIALIST, User.Role.TEAM_LEAD, User.Role.ADMINISTRATOR])


class IsDataSteward(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in [User.Role.DATA_STEWARD, User.Role.ADMINISTRATOR])


class IsAdminUserRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Role.ADMINISTRATOR)


class CanViewAccount(permissions.BasePermission):
    """
    Agents can only view accounts explicitly assigned to them.
    Supervisors, Stewards, Hardship Specialists, and Admins can view all accounts.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.role != User.Role.COLLECTIONS_AGENT:
            return True
        # For an Account object:
        account = getattr(obj, 'account', obj)
        return account.assigned_agent_id == user.id
