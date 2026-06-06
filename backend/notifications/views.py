from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import *

# Create your models here.

# Create your views here.
# تاریخچه تراکنش
# اینو برای این کامنت کردم که مدل هنوز ران نگرفتیم
"""class HistoryWalletTransaction(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            cache_key = f"wallet_transaction_{user.id}"

            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached, status=status.HTTP_200_OK)

            wallet_transactions = (
                Transaction.objects
                .filter(user=user)
                .order_by("-created_at")
            )

            serializer = WalletTransactionSerializer(
                wallet_transactions,
                many=True,
                context={"request": request}
            )

            data = {
                "status": "success",
                "data": serializer.data,
                "count": wallet_transactions.count()
            }

            cache.set(cache_key, data, timeout=60)  # 60 ثانیه
            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
"""

"""class WalletDisplay(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        wallet = Wallet.objects.get_or_create(user=request.user)
        data = {
            "balance":wallet.available_balance,
            "lock_balance":wallet.locked_balance
        }
        return Response({"status": "success", "data":data}, status=status.HTTP_200_OK)"""


# تاریخچه سفارش
class HistoryOrder(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            # وضعیت سفارش
            status_filter = request.query_params.get("status", None)
            # تاریخ برای فیلتر سفارش ها
            date_from = request.query_params.get("date_from", None)
            date_to = request.query_params.get("date_to", None)

            orders = Order.objects.filter(user=user).order_by("-create_time")

            # اعمال فیلترها
            if status_filter:
                orders = orders.filter(status=status_filter)
            if date_from:
                orders = orders.filter(create_time__date__gte=date_from)
            if date_to:
                orders = orders.filter(create_time__date__lte=date_to)

            # بهینه‌سازی query

            orders = orders.prefetch_related("order_items__product")
            serializer = HistoryOrderSerializer(
                orders, many=True, context={"request": request}
            )
            return Response(
                {"status": "success", "data": serializer.data, "count": orders.count()},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# جزییات سفارش
class HistoryOrderDetail(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        try:
            user = request.user
            order = (
                Order.objects.filter(user=user, id=id)
                .prefetch_related(
                    "order_items",
                    "order_items__product",
                    "order_items__size",
                    "order_items__pricing_tab",
                    "order_items__applied_product_discount",
                )
                .first()
            )

            if not order:
                return Response(
                    {"status": "error", "message": "سفارش یافت نشد."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            items = []
            for oi in order.order_items.all():
                items.append(
                    {
                        "id": oi.id,
                        "product_id": oi.product_id,
                        "product_title": oi.product.title,
                        "material": oi.material,
                        "quantity": oi.quantity,
                        "size_id": oi.size.id if oi.size else None,
                        "pricing_tab_id": oi.pricing_tab.id if oi.pricing_tab else None,
                        "original_price": oi.original_price,
                        "item_discount": oi.item_discount,
                        "price": oi.price,
                        "applied_product_discount_id": oi.applied_product_discount_id,
                    }
                )

            data = {
                "order_id": order.id,
                "status": order.status,
                "order_type": order.order_type,
                "pickup_date": order.pickup_date,
                "pickup_shift": order.pickup_shift,
                "delivery_date": order.delivery_date,
                "delivery_shift": order.delivery_shift,
                "pickup_cost": order.pickup_cost,
                "delivery_cost": order.delivery_cost,
                "rush_fee": order.rush_fee,
                "percent_fee": order.percent_fee,
                "subtotal_raw": order.subtotal_raw,
                "total_item_discounts": order.total_item_discounts,
                "subtotal_after_items": order.subtotal_after_items,
                "order_discount_amount": order.order_discount_amount,
                "final_price": order.final_price,
                "paid_at": order.paid_at,
                "create_time": order.create_time,
                "description": order.description,
                "items": items,
            }

            return Response(
                {"status": "success", "data": data}, status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CouponListOrder(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        code = Coupon.objects.filter(user=user, is_active=True)
        coupon_list = []
        for c in code:
            coupon_list.append(
                {
                    "code": c.code,
                    "type": c.type,
                    "value": c.value,
                    "usage_limit": c.usage_limit,
                    "min": c.min_order_price,
                    "start": c.start_at,
                    "end": c.end_at,
                }
            )
        return Response(
                {"status": "success", "count": len(coupon_list), "data": coupon_list},
                status=status.HTTP_200_OK,
            )


class DiscountList(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()

        # دریافت ProductDiscountهای فعال
        product_discounts = ProductDiscount.objects.filter(is_active=True).filter(
            models.Q(start_at__isnull=True) | models.Q(start_at__lte=now),
            models.Q(end_at__isnull=True) | models.Q(end_at__gte=now),
        )

        product_discount_list = []
        for discount in product_discounts:
            target_type = None
            target_id = None
            target_name = None

            if discount.product:
                target_type = "product"
                target_id = discount.product.id
                target_name = str(discount.product)
            elif discount.category:
                target_type = "category"
                target_id = discount.category.id
                target_name = str(discount.category)
            elif discount.pricing_tab:
                target_type = "pricing_tab"
                target_id = discount.pricing_tab.id
                target_name = str(discount.pricing_tab)
            elif discount.material:
                target_type = "material"
                target_id = discount.material.id
                target_name = str(discount.material)

            product_discount_list.append(
                {
                    "id": discount.id,
                    "type": discount.type,
                    "value": discount.value,
                    "start_at": discount.start_at,
                    "end_at": discount.end_at,
                    "is_active": discount.is_active,
                    "target_type": target_type,
                    "target_id": target_id,
                    "target_name": target_name,
                }
            )

        # دریافت آخرین GlobalDiscount فعال
        global_discount = GlobalDiscount.get_active_global_discount()

        global_discount_data = None
        if global_discount:
            global_discount_data = {
                "id": global_discount.id,
                "type": global_discount.type,
                "value": global_discount.value,
                "start_at": global_discount.start_at,
                "end_at": global_discount.end_at,
                "is_active": global_discount.is_active,
            }

        return Response(
            {
                "product_discounts": product_discount_list,
                "global_discount": global_discount_data,
            }
        )


class DiscountListall(APIView):

    def get(self, request):
        now = timezone.now()

        # دریافت ProductDiscountهای فعال
        product_discounts = ProductDiscount.objects.filter(is_active=True).filter(
            models.Q(start_at__isnull=True) | models.Q(start_at__lte=now),
            models.Q(end_at__isnull=True) | models.Q(end_at__gte=now),
        )

        product_discount_list = []
        for discount in product_discounts:
            target_type = None
            target_id = None
            target_name = None

            if discount.product:
                target_type = "product"
                target_id = discount.product.id
                target_name = str(discount.product)
            elif discount.category:
                target_type = "category"
                target_id = discount.category.id
                target_name = str(discount.category)
            elif discount.pricing_tab:
                target_type = "pricing_tab"
                target_id = discount.pricing_tab.id
                target_name = str(discount.pricing_tab)
            elif discount.material:
                target_type = "material"
                target_id = discount.material.id
                target_name = str(discount.material)

            product_discount_list.append(
                {
                    "id": discount.id,
                    "type": discount.type,
                    "value": discount.value,
                    "start_at": discount.start_at,
                    "end_at": discount.end_at,
                    "is_active": discount.is_active,
                    "target_type": target_type,
                    "target_id": target_id,
                    "target_name": target_name,
                }
            )

        # دریافت آخرین GlobalDiscount فعال
        global_discount = GlobalDiscount.get_active_global_discount()

        global_discount_data = None
        if global_discount:
            global_discount_data = {
                "id": global_discount.id,
                "type": global_discount.type,
                "value": global_discount.value,
                "start_at": global_discount.start_at,
                "end_at": global_discount.end_at,
                "is_active": global_discount.is_active,
            }

        return Response(
            {
                "product_discounts": product_discount_list,
                "global_discount": global_discount_data,
            }
        )

