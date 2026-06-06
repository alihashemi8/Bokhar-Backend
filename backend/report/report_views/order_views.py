# Create your views here.

from django.core.cache import cache
from django.db.models import Count
from rest_framework.response import Response
from rest_framework.views import APIView

from order.models import Order
from products.permission import *
from ..pagination import Pagination


# ======================
# ۱. جزئیات سفارش
# ======================
class OrderDetailView(APIView):
    permission_classes = [IsSeller]

    def get(self, request, id):
        try:
            order = Order.objects.select_related("user", "address").get(id=id)
        except Order.DoesNotExist:
            return Response(
                {"detail": "سفارش یافت نشد"}, status=404
            )

        # کش ثابت (۲۴ ساعت)
        fixed_key = f"order_detail_fixed_{id}"
        fixed_data = cache.get(fixed_key)
        if not fixed_data:
            gross_income = (
                order.subtotal_raw
                + order.pickup_cost
                + order.delivery_cost
                + order.rush_fee
            )
            total_discounts = order.total_item_discounts + order.order_discount_amount
            net_income = order.final_price

            fixed_data = {
                "id": order.id,
                "name": order.user.fullname,
                "phone": order.user.phone,
                "address": order.address.address_detail if order.address else "",
                "subtotal_raw": order.subtotal_raw,
                "total_item_discounts": order.total_item_discounts,
                "subtotal_after_items": order.subtotal_after_items,
                "order_discount_amount": order.order_discount_amount,
                "pickup_cost": order.pickup_cost,
                "delivery_cost": order.delivery_cost,
                "rush_fee": order.rush_fee,
                "total_discounts": total_discounts,
                "gross_income": gross_income,
                "net_income": net_income,
                "final_price": order.final_price,
                "created_at": order.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                "pickup_date": (
                    order.pickup_date.strftime("%Y-%m-%d") if order.pickup_date else ""
                ),
                "delivery_date": (
                    order.delivery_date.strftime("%Y-%m-%d %H:%M:%S")
                    if order.delivery_date
                    else ""
                ),
            }
            cache.set(fixed_key, fixed_data, timeout=86400)

        # کش متغیر (۶۰ ثانیه)
        dynamic_key = f"order_detail_dynamic_{id}"
        dynamic_data = cache.get(dynamic_key)
        if not dynamic_data:
            remaining = order.remaining_time
            remaining_hours = (
                max(0, int(remaining.total_seconds() // 3600)) if remaining else 0
            )
            is_late = remaining is not None and remaining.total_seconds() < 0
            dynamic_data = {
                "remaining_hours": remaining_hours,
                "is_late": is_late,
                "status": order.status,
            }
            cache.set(dynamic_key, dynamic_data, timeout=60)

        return Response({**fixed_data, **dynamic_data})


# ======================
# ۲. سفارش‌های امروز
# ======================
class OrderTodayView(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        seller = request.user
        today = timezone.now().date()
        page = request.GET.get("page", 1)
        cache_key = f"today_orders_{seller.id}_{today}_{page}"  # کش مجزا برای هر فروشنده

        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        orders = (
            Order.objects.select_related("user", "address")
            .filter(delivery_date=today)
            .order_by("delivery_date")
        )

        paginator = Pagination()
        page_obj = paginator.paginate_queryset(orders, request)

        data = [
            {
                "id": o.id,
                "name": o.user.fullname,
                "phone": o.user.phone,
                "address": o.address.address_detail if o.address else "",
                "pickup_date": (
                    o.pickup_date.strftime("%Y-%m-%d") if o.pickup_date else ""
                ),
                "final_price": o.final_price,
                "delivery_date": (
                    o.delivery_date.strftime("%Y-%m-%d %H:%M:%S")
                    if o.delivery_date
                    else ""
                ),
                "status": o.status,
            }
            for o in page_obj
        ]

        response = paginator.get_paginated_response(data).data
        cache.set(cache_key, response, 30)
        return Response(response)



# ======================
# ۶. گزارش وضعیت سفارش‌ها
# ======================
class OrderStatusDistributionView(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        seller = request.user
        cache_key = f"order_status_dist_{seller.id}"
        if cached := cache.get(cache_key):
            return Response(cached)

        status_counts = (
            Order.objects.values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        response_data = {item["status"]: item["count"] for item in status_counts}
        cache.set(cache_key, response_data, 120)
        return Response(response_data)




class OrderListView(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        seller = request.user

        page = request.GET.get("page", 1)
        status_filter = request.GET.get("status")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        sort_by = request.GET.get("sort_by", "create_time")
        order_dir = request.GET.get("order", "desc")

        valid_sort = {"final_price", "create_time", "pickup_date", "delivery_date"}
        if sort_by not in valid_sort:
            sort_by = "create_time"

        direction = "-" if order_dir == "desc" else ""

        cache_key = f"orders_list_{seller.id}_{page}_{status_filter}_{start_date}_{end_date}_{sort_by}_{order_dir}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        # 🔥 Query optimized
        qs = (
            Order.objects
            .select_related("user", "address")

        )

        # filters
        if status_filter:
            qs = qs.filter(status__in=status_filter.split(","))

        if start_date:
            qs = qs.filter(create_time__date__gte=start_date)

        if end_date:
            qs = qs.filter(create_time__date__lte=end_date)

        qs = qs.order_by(f"{direction}{sort_by}")

        paginator = Pagination()
        page_obj = paginator.paginate_queryset(qs, request)

        data = [
            {
                "id": o.id,
                "customer_name": o.user.fullname,
                "customer_phone": o.user.phone,
                "status": o.status,
                "final_price": o.final_price,
                "create_time": o.create_time.isoformat(),
                "pickup_date": o.pickup_date.isoformat() if o.pickup_date else None,
                "delivery_date": o.delivery_date.isoformat() if o.delivery_date else None,
                "order_type": o.order_type,
            }
            for o in page_obj
        ]

        response = paginator.get_paginated_response(data).data

        cache.set(cache_key, response, 120)

        return Response(response)

