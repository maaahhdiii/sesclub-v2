from rest_framework import permissions

class IsClubManagerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.is_administrator or request.user.is_club_manager

class IsClubMemberOrManager(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # obj is a Club
        if request.user.is_administrator:
            return True
        return obj.memberships.filter(user=request.user).exists()

class CanManageClub(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # obj is a Club
        if request.user.is_administrator:
            return True
        # Manager must be president/vice_president of THIS club
        return obj.memberships.filter(
            user=request.user, 
            internal_role__in=['president', 'vice_president'],
            status='approved'
        ).exists()
