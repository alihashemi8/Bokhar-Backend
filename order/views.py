import logging
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from products.permission import IsSeller
from django.core.cache import cache
from django.db.models import Count, Q, Prefetch

from products.models import Product

from .models import Order, OrderStatus, Address, OrderStatusLog
from .serializers import *
from .session import OrderSession
from .serializers import AddToCartSerializer

logger = logging.getLogger(__name__)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import RushFeeSetting, PickUpTemplate, DeliveryTemplate
from .serializers import (
    RushFeeSettingSerializer,
    PickupTimeSerializer,
    DeliveryTimeSerializer,
    UpdateRushFeeSerializer,
    UpdatePickupTimeSerializer,
    UpdateDeliveryTimeSerializer
)


class RushFeeSettingListCreateView(APIView):
    """
    لیست و ایجاد تنظیمات تعرفه فوری
    """

    def get(self, request):
        rush_fees = RushFeeSetting.objects.all()
        serializer = RushFeeSettingSerializer(rush_fees, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = RushFeeSettingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RushFeeSettingDetailView(APIView):
    """
    دریافت، به‌روزرسانی و حذف یک تنظیمات تعرفه فوری خاص
    """

    def get_object(self, pk):
        return get_object_or_404(RushFeeSetting, pk=pk)

    def get(self, request, pk):
        rush_fee = self.get_object(pk)
        serializer = RushFeeSettingSerializer(rush_fee)
        return Response(serializer.data)

    def put(self, request, pk):
        rush_fee = self.get_object(pk)
        serializer = UpdateRushFeeSerializer(rush_fee, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        rush_fee = self.get_object(pk)
        serializer = UpdateRushFeeSerializer(rush_fee, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        rush_fee = self.get_object(pk)
        rush_fee.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PickupTimeListCreateView(APIView):
    """
    لیست و ایجاد ظرفیت‌های تحویل گرفتن
    """

    def get(self, request):
        pickup_times = PickUpTemplate.objects.all()
        serializer = PickupTimeSerializer(pickup_times, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PickupTimeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PickupTimeDetailView(APIView):
    """
    دریافت، به‌روزرسانی و حذف یک ظرفیت تحویل گرفتن خاص
    """

    def get_object(self, pk):
        return get_object_or_404(PickUpTemplate, pk=pk)

    def get(self, request, pk):
        pickup_time = self.get_object(pk)
        serializer = PickupTimeSerializer(pickup_time)
        return Response(serializer.data)

    def put(self, request, pk):
        pickup_time = self.get_object(pk)
        serializer = UpdatePickupTimeSerializer(pickup_time, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class DeliveryTimeListCreateView(APIView):
    """
    لیست و ایجاد زمان‌های تحویل
    """

    def get(self, request):
        delivery_times = DeliveryTemplate.objects.all()
        serializer = DeliveryTimeSerializer(delivery_times, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = DeliveryTimeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeliveryTimeDetailView(APIView):
    """
    دریافت، به‌روزرسانی و حذف یک زمان تحویل خاص
    """

    def get_object(self, pk):
        return get_object_or_404(DeliveryTemplate, pk=pk)

    def get(self, request, pk):
        delivery_time = self.get_object(pk)
        serializer = DeliveryTimeSerializer(delivery_time)
        return Response(serializer.data)

    def put(self, request, pk):
        delivery_time = self.get_object(pk)
        serializer = UpdateDeliveryTimeSerializer(delivery_time, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CartAPIView(APIView):
    def get(self, request):
        cart = OrderSession(request)
        return Response({"cart": list(cart)})


# حذف آیتم از سبد خرید
class RemoveCartAPIView(APIView):
    def post(self, request, id_unique):
        cart = OrderSession(request)
        cart.remove(id_unique)
        return Response(
            {"message": "تعداد محصول شما کم شد", "cart": list(cart)},
            status=status.HTTP_200_OK,
        )


# حذف کل سبد خرید
class DeleteCartAPIView(APIView):
    def post(self, request):
        cart = OrderSession(request)
        cart.clear()
        return Response(
            {"message": "سبد خرید شما خالی شد"},
            status=status.HTTP_200_OK,
        )


# افزودن محصول به Cart (Session)
class AddOrderSessionAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddToCartSerializer
    
    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = OrderSession(request)
        
        # گرفتن داده‌ها
        data = serializer.validated_data
        quantity = data.get("quantity", 1)
        material = data.get("material")
        service = data.get("service")  # این می‌شه pricing_tab.tab_name
        size_id = data.get("size")     # این می‌تونه null باشه
        
        # تبدیل size از ID به آبجکت (اگه وجود داشت)
        size = None
        if size_id:
            try:
                size = Size.objects.get(id=size_id)
            except Size.DoesNotExist:
                pass
        
        # فراخوانی متد add
        cart.add(
            product=product,
            size=size,          # می‌تونه None باشه
            material=material,
            service=service,    # مثل "اتو"
            quantity=quantity,
        )
        
        return Response(
            {"message": "محصول به سبد اضافه شد"}, 
            status=status.HTTP_200_OK
        )


# ایجاد سفارش از Cart
class CreateOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderCreateSerializer

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        logger.info(f"سفارش {order.id} توسط کاربر {request.user.id} ایجاد شد.")

        return Response(status=status.HTTP_201_CREATED)


# حذف یک سفارش (در حالت رزرو یا پرداخت نشده)
class DeleteOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        order = get_object_or_404(Order, id=id, user=request.user)
        # فقط سفارش‌های کنسل شده یا رزرو منقضی را می‌توان حذف کرد (یا منطق خودتان)
        if order.status not in [OrderStatus.RESERVED, OrderStatus.CANCELED]:
            return Response(
                {"error": "امکان حذف این سفارش وجود ندارد."},
                status=status.HTTP_400_BAD_REQUEST
            )
        order.delete()
        logger.info(f"سفارش {id} توسط کاربر {request.user.id} حذف شد.")
        return Response(status=status.HTTP_204_NO_CONTENT)


# آدرس‌ها
class CreateAddressView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddressSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info(f"آدرس جدید برای کاربر {request.user.id} ایجاد شد.")
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ListAddressAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddressDetailSerializer

    def get(self, request):
        addresses = Address.objects.filter(user=request.user)
        serializer = self.serializer_class(addresses, many=True)
        return Response({'data': serializer.data})


class UpdateAddressAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UpdateAddressSerializer

    def put(self, request, id):
        address = get_object_or_404(Address, id=id, user=request.user)
        serializer = self.serializer_class(address, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"data": serializer.data})


class DeleteAddressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, id):
        address = get_object_or_404(Address, id=id, user=request.user)
        address.delete()
        return Response({"message": "آدرس شما حذف شد."})




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


class DelivryStatusView(APIView):
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

class OrderCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = OrderCreateSerializer(
            data=request.data, 
            context={'request': request}
        )
        
        if serializer.is_valid():
            try:
                order = serializer.save()
                return Response({
                    "success": True,
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "final_price": order.final_price,
                    "status": order.status,
                    "message": "سفارش با موفقیت ثبت شد"
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response({
                    "success": False,
                    "error": str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
                
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
class UpdateCartItemAPIView(APIView):

    def patch(self, request, id_unique, *args, **kwargs):
        try:
            quantity = request.data.get('quantity')
            if quantity is None:
                return Response(
                    {"error": "quantity is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            quantity = int(quantity)
            if quantity < 0:
                return Response(
                    {"error": "quantity must be positive"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            cart = OrderSession(request)
            updated = cart.update_quantity(id_unique, quantity)
            
            if not updated:
                return Response(
                    {"error": "Item not found in cart"}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response({
                "message": "Quantity updated successfully",
                "items": list(cart),
                "total_price": cart.total_price()
            }, status=status.HTTP_200_OK)
            
        except ValueError:
            return Response(
                {"error": "Invalid quantity format"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class RemoveCartAPIView(APIView):
    def post(self, request, id_unique=None, *args, **kwargs):
        return self._remove_item(request, id_unique)
    
    def delete(self, request, id_unique=None, *args, **kwargs):
        return self._remove_item(request, id_unique)
    
    def _remove_item(self, request, id_unique):
        try:
            if not id_unique:
                return Response({"error": "id_unique required"}, status=400)
            
            cart = OrderSession(request)
            if id_unique not in cart.cart:
                return Response({"error": "Not found"}, status=404)
                
            cart.remove_cart(id_unique)
            return Response({
                "items": list(cart),
                "total_price": cart.total_price()
            })
        except Exception as e:
            return Response({"error": str(e)}, status=400)
