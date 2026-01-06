from django.utils import timezone
from rest_framework import serializers



from .models import Category, Product, Size


# برای نمایش محصول
class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = ["id", "length", "width", "single_double"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "image"]


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    sizes = SizeSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "price",
            "new_price",
            "discount_percent",
            "category",
            "sizes",
            "image",
            "material",
            "expiration_date",
            "description",
            "service_type",
        ]


# update,creat
class ProductCreateSerializer(serializers.ModelSerializer):
    sizes = serializers.PrimaryKeyRelatedField(
        queryset=Size.objects.all(), many=True, required=False  # اختیاری
    )
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ["is_verified", "new_price"]

    def create(self, validated_data):
        sizes = validated_data.pop("sizes", [])
        expiration_date = validated_data.get("expiration_date", None)
        product = Product.objects.create(**validated_data)


        if product.discount_percent and not expiration_date:
            raise serializers.ValidationError("برای تخفیف باید تاریخ انقضا مشخص شود")

        if sizes:
            product.sizes.set(sizes)

        return product


class ProductUpdateSerializer(serializers.ModelSerializer):
    # تعریف فیلدها با required=False برای جلوگیری از خطای اجباری بودن موقع آپدیت
    material = serializers.CharField(required=False)
    service_type = serializers.CharField(required=False)
    price = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False)

    class Meta:
        model = Product
        fields = [
            "name",
            "price",
            "category",
            "sizes",
            "image",
            "material",
            "discount_percent",
            "description",
            "service_type",
            "expiration_date",

        ]
        read_only_fields = ["is_verified", "new_price"]

    def update(self, instance, validated_data):

        discount_percent = validated_data.get("discount_percent",instance.discount_percent)
        expiration_date = validated_data.get("expiration_date", instance.expiration_date)
        sizes = validated_data.pop("sizes", [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)



        if discount_percent and not expiration_date:
            raise serializers.ValidationError("برای تخفیف باید تاریخ انقضا مشخص شود")

        if sizes is not None:
            instance.sizes.set(sizes)

        instance.save()
        return instance
