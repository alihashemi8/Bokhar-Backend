from rest_framework import permissions


class IsSeller(permissions.BasePermission):
    """
    اجازه:
    - همه کاربران می‌توانند GET بزنند
    - فقط کاربرانی که role='seller' هستند اجازه POST, PUT, DELETE دارند
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return (
            request.user.is_authenticated and 
            request.user.role == "seller"
        )

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return (
            request.user.is_authenticated and 
            request.user.role == "seller"
        )
