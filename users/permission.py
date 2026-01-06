from rest_framework import permissions


class IsSeller(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated or request.user.role == "seller"
