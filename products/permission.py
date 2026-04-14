from rest_framework import permissions


class IsSeller(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):

        if request.method in permissions.SAFE_METHODS:
            return True

        return request.user.is_authenticated and request.user.role == "seller"
