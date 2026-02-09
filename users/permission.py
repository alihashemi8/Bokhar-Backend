from rest_framework.permissions import BasePermission


class IsSeller(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated or request.user.role == "seller"
