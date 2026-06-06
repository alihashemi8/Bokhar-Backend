from .serializers import *


# serializers.py


#سفارشا وقتی که داخل سبد خرید هست نشون بده
class OrderCartItemSerializer(serializers.Serializer):
    id_unique = serializers.CharField()
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    pricing_tab_id = serializers.IntegerField()
    pricing_tab_service = serializers.CharField()

    # اگر در سشن size_obj داری، این هم می‌تونه نمایش داده بشه
    size_display = serializers.CharField(allow_null=True, required=False)
    material = serializers.CharField()

    quantity = serializers.IntegerField(min_value=1)
    price = serializers.CharField()  # چون در سشن str ذخیره شده
    total_price = serializers.IntegerField()  # int(item['price'])*quantity
#گل سبد
class OrderSessionSerializer(serializers.Serializer):
    items = OrderCartItemSerializer(many=True)
    total_price = serializers.IntegerField()




from django.db import transaction
from rest_framework import serializers
from django.shortcuts import get_object_or_404
from users.models import (
    Address
)
from discounts.engine import *
from products.models import *
from .utils import *
from  .session import *


class OrderCreateSerializer(serializers.Serializer):
    address_id = serializers.IntegerField(required=False)
    new_address = AddressSerializer(required=False)

    pickup_date = serializers.DateField()
    pickup_shift = serializers.CharField()
    delivery_date = serializers.DateField()
    delivery_shift = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    coupon_code = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if not data.get('address_id') and not data.get('new_address'):
            raise serializers.ValidationError("آدرس انتخاب یا ایجاد کنید")
        if data.get('address_id') and data.get('new_address'):
            raise serializers.ValidationError("فقط یکی از آدرس را ارسال کنید")
        return data

    @transaction.atomic
    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        cart = OrderSession(request)

        cart_items = list(cart)
        if not cart_items:
            raise serializers.ValidationError("سبد خرید خالی است")

        # ۱. آدرس
        if 'address_id' in validated_data:
            address = get_object_or_404(
                Address, id=validated_data['address_id'], user=user
            )
        else:
            addr_serializer = AddressSerializer(
                data=validated_data['new_address'], context=self.context
            )
            addr_serializer.is_valid(raise_exception=True)
            address = addr_serializer.save()

        # ۲. قفل کردن قالب‌های ظرفیت
        pickup_template = PickUpTemplate.objects.select_for_update().get(
            time_shift=validated_data['pickup_shift'],
            is_active=True
        )
        delivery_template = DeliveryTemplate.objects.select_for_update().get(
            time_shift=validated_data['delivery_shift'],
            is_active=True
        )

        # ۳. بررسی نوع سفارش و ظرفیت
        temp_order = Order(
            pickup_date=validated_data['pickup_date'],
            pickup_shift=validated_data['pickup_shift'],
            delivery_date=validated_data['delivery_date'],
            delivery_shift=validated_data['delivery_shift']
        )
        order_type = temp_order.order_range_type()

        available_pickup = get_available_pickup_capacity(
            validated_data['pickup_date'],
            validated_data['pickup_shift']
        )
        available_delivery = get_available_delivery_capacity(
            order_type,
            validated_data['delivery_date'],
            validated_data['delivery_shift']
        )

        if available_pickup <= 0:
            raise serializers.ValidationError("ظرفیت تحویل‌گیری تکمیل است")
        if available_delivery <= 0:
            raise serializers.ValidationError("ظرفیت تحویل‌دهی تکمیل است")

        # ۴. محاسبه هزینه‌های ثابت
        rush_fee = temp_order.calculate_rush_fee()
        percent_fee = temp_order.calculate_percent_fee()
        pickup_cost = pickup_template.base_price + pickup_template.price_add
        delivery_base = delivery_template.base_price + delivery_template.price_add

        # ۵. محاسبه آیتم‌ها
        engine = DiscountEngine(user=user)
        computed_items = []
        subtotal_raw = 0
        total_item_discounts = 0

        for item_data in cart_items:
            product = item_data.get('product') or Product.objects.get(id=item_data['product_id'])
            pricing_tab = item_data.get('pricing_tab') or ProductPricingTab.objects.get(id=item_data['pricing_tab_id'])

            material_name = item_data['material']
            size = None
            if item_data.get('size'):
                size = item_data.get('size_obj') or Size.objects.get(id=item_data['size'])

            quantity = item_data['quantity']

            material_price = MaterialPrice.objects.get(
                pricing_tab=pricing_tab,
                material=material_name
            )

            discount_result = engine.calculate_item_price(
                base_price=material_price.price,
                product=product,
                material=material_price,
                pricing_tab=pricing_tab,
            )

            computed_items.append({
                "product": product,
                "pricing_tab": pricing_tab,
                "size": size,
                "material_name": material_name,
                "quantity": quantity,
                "original_price": discount_result.base_price,
                "item_discount": discount_result.base_discount_amount,
                "final_item_price": discount_result.final_price,
                "applied_product_discount": discount_result.base_discount_instance,
            })

            subtotal_raw += discount_result.base_price * quantity
            total_item_discounts += discount_result.base_discount_amount * quantity

        # ۶. محاسبات بعد از حلقه
        subtotal_after_items = subtotal_raw - total_item_discounts

        # ۷. محاسبه قیمت نهایی اولیه (بدون کوپن)
        # این قیمت باید برای min_order_price چک بشه
        percent_amount_before_coupon = (subtotal_after_items * percent_fee) // 100 if percent_fee else 0
        delivery_cost_final = delivery_base + rush_fee

        final_price_before_coupon = max(
            0,
            subtotal_after_items +
            percent_amount_before_coupon +
            pickup_cost +
            delivery_cost_final
        )

        # ۸. اعمال کوپن با بررسی min_order_price روی قیمت نهایی
        coupon_code = validated_data.get('coupon_code')
        order_discount_amount = 0
        applied_coupon = None

        if coupon_code:
            # بررسی کوپن با قیمت نهایی (نه subtotal_after_items)
            success, coupon_discount, coupon_instance = engine.apply_coupon(
                coupon_code,
                final_price_before_coupon  # ← قیمت نهایی رو پاس میدیم
            )
            if not success:
                raise serializers.ValidationError(
                    f"کد تخفیف نامعتبر یا منقضی شده است. "
                    f"حداقل مبلغ سفارش: {coupon_instance.min_order_price:,} تومان"
                    if coupon_instance and coupon_instance.min_order_price
                    else "کد تخفیف نامعتبر یا منقضی شده است"
                )
            order_discount_amount = coupon_discount
            applied_coupon = coupon_instance

        # ۹. محاسبه قیمت نهایی با کوپن
        after_items_and_coupon = max(0, subtotal_after_items - order_discount_amount)

        # درصد فوری روی قیمت بعد از کوپن
        percent_amount = (after_items_and_coupon * percent_fee) // 100 if percent_fee else 0

        final_price = max(
            0,
            after_items_and_coupon +
            percent_amount +
            pickup_cost +
            delivery_cost_final
        )

        # ۱۰. برگردوندن نتیجه
        return {
            "address": address,
            "computed_items": computed_items,
            "pickup_template": pickup_template,
            "delivery_template": delivery_template,
            "subtotal_raw": subtotal_raw,
            "total_item_discounts": total_item_discounts,
            "subtotal_after_items": subtotal_after_items,
            "order_discount_amount": order_discount_amount,
            "applied_coupon": applied_coupon,
            "pickup_cost": pickup_cost,
            "delivery_cost": delivery_cost_final,
            "rush_fee": rush_fee,
            "percent_fee": percent_fee,
            "final_price": final_price,
            "description": validated_data.get("description", ""),
            "pickup_date": validated_data["pickup_date"],
            "pickup_shift": validated_data["pickup_shift"],
            "delivery_date": validated_data["delivery_date"],
            "delivery_shift": validated_data["delivery_shift"],
        }

class AddToCartSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, default=1)
    service = serializers.CharField(required=True)  # نام سرویس مثل "اتو"
    material = serializers.CharField(required=True) # نام جنس مثل "مخمل"
    size = serializers.IntegerField(required=False, allow_null=True)  # ID سایز
