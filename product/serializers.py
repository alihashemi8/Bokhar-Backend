from django.utils import timezone
from rest_framework import serializers

from .models import Category, Product, Size


# برای نمایش محصول
class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = ["id", "meter", "single_double"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "image"]


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    size = SizeSerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "price",
            "price_meter",
            "new_price",
            "discount_percent",
            "category",
            "size",
            "image",
            "material",
            "expiration_date",
            "description",
            "service_type",
        ]


# update,creat
class ProductCreateSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ["is_verified", "new_price"]  # حذف price از read_only اگر میخوای API price قبول کنه

    def validate(self, data):
        price_meter = data.get("price_meter")
        price = data.get("price")
        size = data.get("size")
        discount_percent = data.get("discount_percent")
        expiration_date = data.get("expiration_date")

        # محصول متری
        if price_meter:
            if not size:
                raise serializers.ValidationError(
                    {"size": "برای محصول متری، سایز الزامی است"}
                )
        else:
            # محصول غیرمتری
            if not price:
                raise serializers.ValidationError(
                    {"price": "اگر قیمت متری نیست، قیمت الزامی است"}
                )

        # تخفیف
        if discount_percent and not expiration_date:
            raise serializers.ValidationError(
                {"expiration_date": "برای تخفیف، تاریخ انقضا الزامی است"}
            )

        return data


    def create(self, validated_data):
       expiration_date = validated_data.get("expiration_date", None)
       product = Product.objects.create(**validated_data)
       if product.discount_percent and not expiration_date: raise serializers.ValidationError(
           "برای تخفیف باید تاریخ انقضا مشخص شود")

       return product

class ProductUpdateSerializer(serializers.ModelSerializer):
    material = serializers.CharField(required=False)
    service_type = serializers.CharField(required=False)
    price_meter = serializers.IntegerField(required=False, min_value=0)
    price = serializers.IntegerField(required=False, min_value=1)
    name = serializers.CharField(required=False)

    class Meta:
        model = Product
        fields = [
            "name",
            "price",
            "category",
            "size",
            "price_meter",
            "image",
            "material",
            "discount_percent",
            "description",
            "service_type",
            "expiration_date",
        ]
        read_only_fields = ["is_verified", "new_price"]

    def update(self, instance, validated_data):
        discount_percent = validated_data.get("discount_percent", instance.discount_percent)
        expiration_date = validated_data.get("expiration_date", instance.expiration_date)

        price_meter = validated_data.get("price_meter", instance.price_meter)
        size = validated_data.get("size", instance.size)

        # Validation تخفیف قبل از تغییر instance
        if discount_percent and not expiration_date:
            raise serializers.ValidationError({
                "expiration_date": "برای تخفیف باید تاریخ انقضا مشخص شود"
            })

        # محاسبه price برای محصولات متری قبل از setattr
        if price_meter is not None and size and size.meter:
            validated_data["price"] = int(price_meter * size.meter)

        # اعمال تغییرات
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


