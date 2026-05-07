from django.db import transaction
from rest_framework import serializers

from .models import *

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

class AddressDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ["id", "address", "city", "postcode", "title", "apartment_name","unit"]


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        exclude = ["user"]

    def validate(self, data):
        request = self.context.get("request")
        user = request.user

        if self.instance is None:
            if Address.objects.filter(user=user).count() >= 2:
                raise serializers.ValidationError(
                    "شما فقط می‌توانید حداکثر ۲ آدرس ثبت کنید."
                )

        return data

    def create(self, validated_data):
        request = self.context.get("request")
        return Address.objects.create(
            user=request.user,
            **validated_data
        )

class UpdateAddressSerializer(serializers.Serializer):
    city = serializers.CharField(required=False)
    postcode = serializers.IntegerField(required=False)
    title = serializers.CharField(required=False)
    apartment_name = serializers.CharField(required=False)
    address = serializers.CharField(required=False)
    unit = serializers.IntegerField(required=False)

    def update(self, instance, validated_data):

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        return instance




from django.db import transaction
from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404

from .models import (
    Order, OrderItem, OrderStatus,
    PickUpTemplate, DeliveryTemplate, Address
)
from discount.engine import DiscountEngine
from product.models import MaterialPrice, Size  # فرض بر این است که Size از product.models می‌آید
from .utils import (
    get_available_pickup_capacity,
    get_available_delivery_capacity
)
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
        cart = OrderSession(request)  # همان OrderSession شما

        if not list(cart):
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

        # ۲. قفل کردن قالب‌های ظرفیت و دریافت هزینه‌ها
        pickup_template = PickUpTemplate.objects.select_for_update().get(
            time_shift=validated_data['pickup_shift'],
            is_active=True
        )
        delivery_template = DeliveryTemplate.objects.select_for_update().get(
            time_shift=validated_data['delivery_shift'],
            is_active=True
        )



        # محاسبه نوع سفارش برای بررسی دقیق ظرفیت
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

        # ۳. ایجاد اولیه سفارش (وضعیت رزرو)
        order = Order(
            user=user,
            address=address,
            pickup_date=validated_data['pickup_date'],
            pickup_shift=validated_data['pickup_shift'],
            delivery_date=validated_data['delivery_date'],
            delivery_shift=validated_data['delivery_shift'],
            description=validated_data['description'],
            status=OrderStatus.PAID,

        )
        order.save()  # rush_fee, percent_fee, order_type داخل save محاسبه و ذخیره می‌شوند
        # محاسبه‌ی هزینه‌های ثابت تحویل‌گیری و تحویل‌دهی

        # ۴. حلقه روی آیتم‌های سبد خرید و ایجاد OrderItem با اعمال تخفیف‌ها
        engine = DiscountEngine(user=user)
        subtotal_raw = 0
        total_item_discounts = 0

        for item_data in cart:
            # item_data از __iter__ کلاس CartSession می‌آید.
            # اطمینان می‌دهیم که product و pricing_tab در دسترس هستند
            product = item_data.get('product')
            if not product:
                product = Product.objects.get(id=item_data['product_id'])

            pricing_tab_id = item_data['pricing_tab_id']
            pricing_tab = item_data.get('pricing_tab')
            if not pricing_tab:
                pricing_tab = ProductPricingTab.objects.get(id=pricing_tab_id)

            material_name = item_data['material']
            size_id = item_data.get('size')
            size = None
            if size_id:
                size = item_data.get('size_obj')
                if not size:
                    size = Size.objects.get(id=size_id)

            quantity = item_data['quantity']

            # قیمت پایه از MaterialPrice
            material_price = MaterialPrice.objects.get(
                pricing_tab=pricing_tab,
                material=material_name
            )
            base_price = material_price.price

            # محاسبه تخفیف‌های محصولی
            discount_result = engine.calculate_item_price(
                base_price=base_price,
                product=product,
                material=material_price,
                pricing_tab=pricing_tab,
            )

            original_price = discount_result.base_price
            item_discount = discount_result.base_discount_amount
            final_item_price = discount_result.final_price

            OrderItem.objects.create(
                order=order,
                product=product,
                size=size,
                pricing_tab=pricing_tab,
                material=material_name,
                quantity=quantity,
                original_price=original_price,
                item_discount=item_discount,
                price=final_item_price,
                applied_product_discount=discount_result.base_discount_instance,
            )

            subtotal_raw += original_price * quantity
            total_item_discounts += item_discount * quantity

        # ۵. ثبت جمع‌های مالی در سفارش
        order.subtotal_raw = subtotal_raw
        order.total_item_discounts = total_item_discounts
        order.subtotal_after_items = subtotal_raw - total_item_discounts
        order.pickup_cost = pickup_template.base_price + pickup_template.price_add
        order.delivery_cost = delivery_template.base_price + delivery_template.price_add + order.rush_fee
        # ۶. اعمال کوپن (در صورت ارسال)
        coupon_code = validated_data.get('coupon_code')
        if coupon_code:
            success, coupon_discount, coupon_instance = engine.apply_coupon(
                coupon_code,
                order.subtotal_after_items
            )
            if not success:
                raise serializers.ValidationError("کد تخفیف نامعتبر یا منقضی شده است")
            order.applied_coupon = coupon_instance
            order.order_discount_amount = coupon_discount
        else:
            order.order_discount_amount = 0

        # ۷. محاسبه قیمت نهایی با احتساب تمام هزینه‌ها
        after_items_and_coupon = order.subtotal_after_items - order.order_discount_amount

        # درصد فوری روی جمع (پس از تخفیف محصولی و کوپن)
        percent_amount = (after_items_and_coupon * order.percent_fee) // 100 if order.percent_fee else 0

        # قیمت نهایی = جمع آیتم‌ها + درصد فوری + هزینه ثابت فوری + هزینه پیکاپ + هزینه تحویل
        order.final_price = max(
            0,
            after_items_and_coupon
            + percent_amount
            + order.rush_fee
            + order.pickup_cost
            + order.delivery_cost
        )

        order.save()   # ذخیره نهایی با تمام فیلدها

        # ۸. پاک کردن سبد خرید
        cart.clear()

        return order












