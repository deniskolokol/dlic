from rest_framework import permissions
from api.exceptions import APIUserDoesNotPaid


class HasPaidTime(permissions.BasePermission):
    """
    Check for user's billing
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS or request.user.is_paid:
            return True
        raise APIUserDoesNotPaid()


class IsSuperUser(permissions.BasePermission):
    """
    Allows access only to superusers.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_superuser
