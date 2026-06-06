# Create your views here.
from django.core.cache import cache
from django.db.models import  Count, Sum
from rest_framework.response import Response
from rest_framework.views import APIView
from order.models import *
from products.permission import *


class DashboardView(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        cache_key = "dashboard_v2"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        orders = Order.objects.all().only(
            "id", "final_price", "status", "create_time"
        )

        stats = orders.aggregate(
            total_orders=Count("id"),
            total_revenue=Sum("final_price"),
        )

        today = timezone.now().date()
        today_revenue = orders.filter(
            create_time__date=today
        ).aggregate(total=Sum("final_price"))["total"] or 0

        last_orders = list(
            orders.select_related("user")
            .order_by("-create_time")[:10]
            .values(
                "id",
                "user__fullname",
                "final_price",
                "status",
                "create_time",
            )
        )

        data = {
            "stats": {
                "total_orders": stats["total_orders"] or 0,
                "total_revenue": stats["total_revenue"] or 0,
                "today_revenue": today_revenue,
            },
            "last_orders": last_orders,
        }

        cache.set(cache_key, data, 60)
        return Response(data)