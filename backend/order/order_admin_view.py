import logging
from backend.products.permission import IsSeller
from django.core.cache import cache
from django.db.models import Q

from .models import Order, OrderStatus, OrderStatusLog

logger = logging.getLogger(__name__)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class PaidStatusView(APIView):
    permission_classes = [IsSeller]

    def get(self, request):

                cache_key = "paid_orders_list"
                cached_data = cache.get(cache_key)

                if cached_data is not None:
                    return Response(cached_data)

                orders = Order.objects.filter(status=OrderStatus.PAID)
                order_data = []
                for item in orders:
                    order_data.append({
                        "id": item.id,
                        "user": item.user.id,
                        "delivery": item.late_delivery,
                        "final_price": item.final_price,
                        "type_order": item.type_order,
                        "address": item.address,
                    })

                # ذخیره در کش به مدت
                cache.set(cache_key, order_data, 60)
                return Response(order_data)



class WashStatusView(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        cache_key = "wash_orders_list"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        orders = Order.objects.filter(status=OrderStatus.WASHING)
        order_data = []
        for item in orders:
            order_data.append({
                "id": item.id,
                "user": item.user.id,
                "delivery": item.late_delivery,
                "final_price": item.final_price,
                "type_order": item.type_order,
                "address": item.address,
            })

        # ذخیره در کش به مدت
        cache.set(cache_key, order_data, 60)
        return Response(order_data)

from django.utils import timezone


class DeliveryStatusView(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        now = timezone.now()
        # اولین روز ماه جاری
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # آخرین روز ماه جاری (با محاسبه ماه بعد منهای یک روز)
        if now.month == 12:
            next_month = now.replace(year=now.year+1, month=1, day=1)
        else:
            next_month = now.replace(month=now.month+1, day=1)
        end_of_month = next_month - timezone.timedelta(days=1)

        # کلید کش منحصر به ماه (مثلاً orders_list_2026_05)
        cache_key = f"orders_list_{now.year}_{now.month}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        orders = Order.objects.filter(
            status=OrderStatus.DELIVERED,
            created_at__range=(start_of_month, end_of_month)
        )
        order_data = []
        for item in orders:
            order_data.append({
                "id": item.id,
                "user": item.user.id,
                "delivery": item.late_delivery,
                "final_price": item.final_price,
                "type_order": item.type_order,
                "address": item.address,
            })

        cache.set(cache_key, order_data, 60)  # 120 ثانیه کش
        return Response(order_data)

class CancelStatusView(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        cache_key = "cancel_orders_list"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        orders = Order.objects.filter(status=OrderStatus.CANCELED)
        order_data = []
        for item in orders:
            order_data.append({
                "id": item.id,
                "user": item.user.id,
                "delivery": item.late_delivery,
                "final_price": item.final_price,
                "type_order": item.type_order,
                "address": item.address,
            })

        # ذخیره در کش به مدت
        cache.set(cache_key, order_data, 60)
        return Response(order_data)


class ReturnStatusView(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        cache_key = "return_orders_list"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        orders = Order.objects.filter(status=OrderStatus.RETURNED)
        order_data = []
        for item in orders:
            order_data.append({
                "id": item.id,
                "user": item.user.id,
                "delivery": item.late_delivery,
                "final_price": item.final_price,
                "type_order": item.type_order,
                "address": item.address,
            })

        # ذخیره در کش به مدت
        cache.set(cache_key, order_data, 60)
        return Response(order_data)

#تعییر وضعیت...


class UpdateStatusPickView(APIView):
    permission_classes = [IsSeller]

    def put(self, request):
        ids = request.data.get("ids")
        if not ids:
            return Response({"detail": "انتخاب کن"}, status=400)

        orders_to_update = Order.objects.filter(id__in=ids, status=OrderStatus.PAID)

        if not orders_to_update.exists():
            return Response({"detail": "سفارش پرداخت شده‌ای یافت نشد"}, status=404)

        # ثبت لاگ برای هر سفارش قبل از بروزرسانی
        for order in orders_to_update:
            OrderStatusLog.objects.create(
                user=request.user,
                order=order,
                from_status=OrderStatus.PAID,
                to_status=OrderStatus.PICKED_UP
            )

        # بروزرسانی وضعیت
        orders_to_update.update(status=OrderStatus.PICKED_UP)

        # پاک کردن کش مرتبط
        cache.delete("paid_orders_list")  # سفارش از PAID خارج شد

        return Response({
            "detail": f"{orders_to_update.count()} سفارش به وضعیت آماده تحویل تغییر یافت",
            "updated_count": orders_to_update.count()
        })


class UpdateStatusWashingView(APIView):
    permission_classes = [IsSeller]

    def put(self, request):
        ids = request.data.get("ids")
        if not ids:
            return Response({"detail": "انتخاب کن"}, status=400)

        orders_to_update = Order.objects.filter(id__in=ids, status=OrderStatus.PICKED_UP)

        if not orders_to_update.exists():
            return Response({"detail": "سفارشی با وضعیت آماده تحویل یافت نشد"}, status=404)

        # ثبت لاگ برای هر سفارش قبل از بروزرسانی
        for order in orders_to_update:
            OrderStatusLog.objects.create(
                user=request.user,
                order=order,
                from_status=OrderStatus.PICKED_UP,
                to_status=OrderStatus.WASHING
            )

        # بروزرسانی وضعیت
        orders_to_update.update(status=OrderStatus.WASHING)

        # پاک کردن کش مرتبط
        cache.delete("wash_orders_list")  # سفارش به WASHING وارد شد

        return Response({
            "detail": f"{orders_to_update.count()} سفارش به وضعیت در حال شستشو تغییر یافت",
            "updated_count": orders_to_update.count()
        })


class UpdateStatusDeliveryView(APIView):
    permission_classes = [IsSeller]

    def put(self, request):
        ids = request.data.get("ids")
        if not ids:
            return Response({"detail": "انتخاب کن"}, status=400)

        orders_to_update = Order.objects.filter(id__in=ids, status=OrderStatus.WASHING)

        if not orders_to_update.exists():
            return Response({"detail": "سفارشی با وضعیت در حال شستشو یافت نشد"}, status=404)

        # ثبت لاگ برای هر سفارش قبل از بروزرسانی
        for order in orders_to_update:
            OrderStatusLog.objects.create(
                user=request.user,
                order=order,
                from_status=OrderStatus.WASHING,
                to_status=OrderStatus.DELIVERED
            )

        # بروزرسانی وضعیت
        orders_to_update.update(status=OrderStatus.DELIVERED)

        # پاک کردن کش مرتبط
        now = timezone.now()
        cache.delete(f"orders_list_{now.year}_{now.month}")  # سفارش به DELIVERED ماه جاری وارد شد
        cache.delete("wash_orders_list")  # سفارش از WASHING خارج شد

        return Response({
            "detail": f"{orders_to_update.count()} سفارش به وضعیت تحویل شده تغییر یافت",
            "updated_count": orders_to_update.count()
        })


# ویو برای مشاهده تاریخچه وضعیت یک سفارش
class OrderStatusHistoryView(APIView):
    permission_classes = [IsSeller]

    def get(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({"detail": "سفارش یافت نشد"}, status=404)

        logs = OrderStatusLog.objects.filter(order=order).select_related('user')

        data = []
        for log in logs:
            data.append({
                "id": log.id,
                "user": log.user.get_full_name() or log.user.username,
                "from_status": log.from_status,
                "to_status": log.to_status,
                "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            })

        return Response({
            "order_id": order.id,
            "current_status": order.status,
            "history": data
        })

class SearchOrderView(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        q = request.GET.get("q", "")
        if not q:
            return Response(
                {"detail": "پارامتر q ارسال نشده"},
                status=status.HTTP_400_BAD_REQUEST
            )



        orders_queryset = Order.objects.select_related(
                "user", "address"
        ).filter(
                Q(user__fullname__icontains=q) |
                Q(user__phone__icontains=q) |
                Q(address__address__icontains=q) |
                Q(status__icontains=q)
        )

        orders_queryset = orders_queryset.order_by('-create_time')

        data = []
        for item in orders_queryset:
            data.append({
                "id": item.id,
                "user": item.user.id,
                "delivery": item.late_delivery,
                "final_price": item.final_price,
                "type_order": item.type_order,
                "address": item.address,

            })

        return Response(data)


