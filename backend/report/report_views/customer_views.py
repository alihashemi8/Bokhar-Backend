from django.db.models import Prefetch
from rest_framework import status

from products.permission import IsSeller

from ..pagination import Pagination  # Import pagination class


# لیست مشتریان و تعداد سفارششونو نشون میده و تلقنو اسمشونو
from django.db.models import Count, Sum
from rest_framework.views import APIView

class CustomersView(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        page_number = request.GET.get("page", 1)
        filter_name = request.GET.get("filter", "")  # یکی از فیلترها

        cache_key = f"customers_page_{page_number}_filter_{filter_name or 'none'}"
        data = cache.get(cache_key)
        if data is not None:
            return Response(data)

        customers = User.objects.all().exclude(role="seller")

        # تعداد سفارش
        customers = customers.annotate(number_of_orders=Count("orders"))

        # مجموع پول سفارش (اسم فیلد مبلغ را مطابق مدل خودت عوض کن)
        customers = customers.annotate(total_spent=Sum("orders__final_price"))

        # اعمال order بر اساس فیلتر
        if filter_name == "most_orders":
            customers = customers.order_by("-number_of_orders")
        elif filter_name == "least_orders":
            customers = customers.order_by("number_of_orders")
        elif filter_name == "most_spent":
            customers = customers.order_by("-total_spent")
        elif filter_name == "least_spent":
            customers = customers.order_by("total_spent")
        elif filter_name == "newest":
            # اسم فیلد تاریخ ایجاد کاربر را مطابق مدل خودت عوض کن
            customers = customers.order_by("-created_at")
        elif filter_name == "oldest":
            customers = customers.order_by("created_at")
        else:
            # پیش‌فرض
            customers = customers.order_by("-created_at")

        paginator = Pagination()
        paginated_customers = paginator.paginate_queryset(customers, request)

        data_list =[]
        for customer in paginated_customers:
            data_list.append(
                {
                    "fullname": customer.fullname,
                    "phone": customer.phone,
                    "number_of_orders": customer.number_of_orders,
                    # اگر خواستی پول هم برگردون:
                    "total_spent": customer.total_spent,
                }
            )

        response = paginator.get_paginated_response(data_list)
        cache.set(cache_key, response.data, 300)

        return Response(response.data)

# سرچ مشتریا بر اساس اسم و شمارشون
class SearchCustomersView(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        q = request.GET.get("q", "")
        if not q:
            return Response(
                {"detail": "پارامتر q ارسال نشده"}, status=status.HTTP_400_BAD_REQUEST
            )

        customers = User.objects.annotate(number_of_orders=Count("orders")).filter(
            Q(fullname__icontains=q) | Q(phone__icontains=q)
        )

        paginator = Pagination()
        paginated_customers = paginator.paginate_queryset(customers, request)

        data = []
        for customer in paginated_customers:
            data.append(
                {
                    "id": customer.id,
                    "fullname": customer.fullname,
                    "phone": customer.phone,
                    "number_of_orders": customer.number_of_orders,
                }
            )

        return paginator.get_paginated_response(data)


# جزییات  سفارش مشتری نشون میده
class CustomerDetailView(APIView):
    permission_classes = [IsSeller]

    def get(self, request, id):
        cache_key = f"customer_detail_{id}"
        response_data = cache.get(cache_key)

        if response_data is None:
            customer = get_object_or_404(User, id=id)

            orders = (
                Order.objects.filter(user=customer)
                .prefetch_related(
                    Prefetch(
                        "order_items",
                        queryset=OrderItem.objects.select_related("product"),
                    )
                )
                .order_by("-create_time")
            )

            # فقط کیف پول موجود را می‌خوانیم، ایجاد نمی‌کنیم
            wallet = Wallet.objects.filter(user=customer).first()
            wallet_available = wallet.available_balance if wallet else 0
            wallet_locked = wallet.locked_balance if wallet else 0

            total_final = 0
            orders_data = []

            for order in orders:
                total_final += order.final_price
                items = []
                order_items_total = 0

                for item in order.order_items.all():
                    item_total = item.price * item.quantity
                    order_items_total += item_total
                    items.append({
                        "product_name": item.product.title,
                        "quantity": item.quantity,
                        "price": item.price,
                        "total_price_item": item_total,
                    })

                orders_data.append({
                    "order_id": order.id,
                    "pickup_cost": order.pickup_cost,
                    "delivery_cost": order.delivery_cost,
                    "percent_fee": order.percent_fee,
                    "rush_fee": order.rush_fee,
                    "subtotal_raw": order.subtotal_raw,
                    "total_item_discounts": order.total_item_discounts,
                    "subtotal_after_items": order.subtotal_after_items,
                    "order_discount_amount": order.order_discount_amount,
                    "created_at": order.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "order_total_price": order_items_total,
                    "final_price": order.final_price,
                    "status": order.status,
                    "items": items,
                })

            response_data = {
                "fullname": customer.fullname,
                "total_price_all_orders": total_final,
                "orders": orders_data,
                "wallet_available": wallet_available,
                "locked_balance": wallet_locked,
            }

            cache.set(cache_key, response_data, 60)  #

        return Response(response_data)

from django.core.cache import cache
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
# جزییات تراکنش و کیف پول
from rest_framework.views import APIView


class WalletDetailView(APIView):
    permission_classes = [IsSeller]

    def get(self, request, user_id):
        cache_key = f"wallet_detail_{user_id}"
        data = cache.get(cache_key)

        if not data:
            user = get_object_or_404(User, id=user_id)
            wallet = Wallet.objects.filter(user=user).first()

            if wallet:
                transactions = (
                    Transaction.objects.filter(wallet=wallet)
                    .select_related("payment", "order")
                    .order_by("-created_at")
                )
                wallet_info = {
                    "available_balance": wallet.available_balance,
                    "locked_balance": wallet.locked_balance,
                    "is_active": wallet.is_active,
                }
            else:
                transactions = []
                wallet_info = {
                    "available_balance": 0,
                    "locked_balance": 0,
                    "is_active": False,
                }

            tx_list = []
            for tx in transactions:
                tx_list.append({
                    "uuid": str(tx.uuid),
                    "amount": tx.amount,
                    "type": tx.transaction_type,
                    "status": tx.status,
                    "description": tx.description,
                    "created_at": tx.created_at.isoformat(),
                    "order_id": tx.order_id,
                    "payment_uuid": str(tx.payment.uuid) if tx.payment else None,
                    "trace_id": str(tx.trace_id) if tx.trace_id else None,
                })

            data = {
                "user_id": user.id,
                "fullname": user.fullname,
                "phone": user.phone,
                "wallet": wallet_info,
                "transactions": tx_list,
            }
            cache.set(cache_key, data, 60)

        return Response(data)