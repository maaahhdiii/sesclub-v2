from rest_framework import permissions

class IsAdministrator(permissions.BasePermission):
    """
    Allows access only to administrators.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_administrator)


class IsClubManager(permissions.BasePermission):
    """
    Allows access only to club managers.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_club_manager)


class IsStudent(permissions.BasePermission):
    """
    Allows access only to students.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_student)
