from rest_framework.views import APIView

from order.models import *
from products.permission import IsSeller


class TopServicesView(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        limit = min(int(request.GET.get("limit", 10)), 50)
        cache_key = f"top_services_{limit}"

        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        qs = (
            OrderItem.objects
            .values("pricing_tab_id", "pricing_tab__tab_name")
            .annotate(usage_count=Count("id"))
            .order_by("-usage_count")[:limit]
        )

        response = {
            "results": list(qs)
        }

        cache.set(cache_key, response, 300)
        return Response(response)

from django.db.models import Count, Sum
from rest_framework.views import APIView

from products.permission import IsSeller


class TopCustomersView(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        limit = min(int(request.GET.get("limit", 10)), 50)
        cache_key = f"top_customers_{limit}"

        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        qs = (
            Order.objects
            .values("user_id", "user__fullname", "user__phone")
            .annotate(
                total_orders=Count("id"),
                total_spent=Sum("final_price"),
            )
            .order_by("-total_spent")[:limit]   # 👈 مهم: مشتری واقعی = پول نه تعداد
        )

        response = {
            "results": list(qs)
        }

        cache.set(cache_key, response, 300)
        return Response(response)


from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response

from users.models import *
from order.models import *
from products.permission import IsSeller


class CustomersWithoutOrdersView(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        limit = min(int(request.GET.get("limit", 20)), 100)
        cache_key = f"no_order_customers_{limit}"

        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        qs = (
            User.objects
            .filter(orders__isnull=True)
            .values("id", "fullname", "phone", "created_at")
            .order_by("created_at")[:limit]
        )

        response = {
            "results": list(qs)
        }

        cache.set(cache_key, response, 600)
        return Response(response)