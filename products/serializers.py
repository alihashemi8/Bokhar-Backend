from rest_framework import serializers
from .models import Category, Product, ProductPricingTab, MaterialPrice
import json


# ----------------------------------------------------
# MaterialPrice (Read Only for GET)
# ----------------------------------------------------
class MaterialPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialPrice
        fields = ['material', 'price']


# ----------------------------------------------------
# PricingTab (Read Only for GET)
# ----------------------------------------------------
class PricingTabSerializer(serializers.ModelSerializer):
    material_prices = MaterialPriceSerializer(many=True, read_only=True)
    
    class Meta:
        model = ProductPricingTab
        fields = ['tab_name', 'size_type', 'material_prices']


# ----------------------------------------------------
# Category
# ----------------------------------------------------
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'image']


# ----------------------------------------------------
# Product List (برای لیست ساده)
# ----------------------------------------------------
class ProductListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'title', 'category', 'status', 'image', 'base_price']


# ----------------------------------------------------
# Product Detail (GET /products/<id>)
# ----------------------------------------------------
class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    pricing = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = ['id', 'title', 'category', 'status', 'image', 'base_price', 'pricing', 'created_at']
    
    def get_pricing(self, obj):
        pricing_data = {}
        for tab in obj.pricing_tabs.all():
            pricing_data[tab.tab_name] = {
                'sizeType': tab.size_type,
                'materialPrices': [
                    {'material': mp.material, 'price': mp.price}
                    for mp in tab.material_prices.all()
                ]
            }
        return pricing_data



# ----------------------------------------------------
# Product Create / Update (POST - PUT)
# ----------------------------------------------------
class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    pricing = serializers.JSONField(write_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'title', 'category', 'status', 'image', 'base_price', 'pricing']
    

    # -----------------------------
    # CREATE
    # -----------------------------
    def create(self, validated_data):
        pricing_raw = validated_data.pop('pricing', None)
        product = Product.objects.create(**validated_data)

        # اگر فرانت رشته JSON فرستاده باشد → به dict تبدیل کن
        if pricing_raw is not None:
            if isinstance(pricing_raw, str):
                try:
                    pricing_data = json.loads(pricing_raw)
                except json.JSONDecodeError:
                    raise serializers.ValidationError({"pricing": "فرمت JSON نامعتبر است"})
            else:
                pricing_data = pricing_raw

            self._create_pricing(product, pricing_data)

        return product


    # -----------------------------
    # UPDATE
    # -----------------------------
    def update(self, instance, validated_data):
        pricing_raw = validated_data.pop('pricing', None)

        # آپدیت فیلدهای معمولی
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # اگر pricing آپدیت شده
        if pricing_raw is not None:
            instance.pricing_tabs.all().delete()

            if isinstance(pricing_raw, str):
                try:
                    pricing_data = json.loads(pricing_raw)
                except json.JSONDecodeError:
                    raise serializers.ValidationError({"pricing": "فرمت JSON نامعتبر است"})
            else:
                pricing_data = pricing_raw

            self._create_pricing(instance, pricing_data)

        return instance


    # -----------------------------
    # CREATE PRICING TABS + MATERIAL PRICES
    # -----------------------------
    def _create_pricing(self, product, pricing_data):
        for tab_name, tab_data in pricing_data.items():

            pricing_tab = ProductPricingTab.objects.create(
                product=product,
                tab_name=tab_name,
                size_type=tab_data.get('sizeType', '')
            )

            material_prices = tab_data.get('materialPrices', {})

            # حالت آرایه (فرانت)
            if isinstance(material_prices, list):
                for item in material_prices:
                    MaterialPrice.objects.create(
                        pricing_tab=pricing_tab,
                        material=item.get("material"),
                        price=int(item.get("price", 0))
                    )

            # حالت دیکشنری (اگر جایی لازم شد)
            elif isinstance(material_prices, dict):
                for material, price in material_prices.items():
                    MaterialPrice.objects.create(
                        pricing_tab=pricing_tab,
                        material=material,
                        price=int(price) if price else 0
                    )



    # -----------------------------
    # VALIDATION
    # -----------------------------
    def validate_pricing(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("فرمت قیمت‌گذاری نامعتبر است")

        if len(value) == 0:
            raise serializers.ValidationError("حداقل یک تب قیمت‌گذاری باید پر شود")

        for tab_name, tab_data in value.items():
            if not isinstance(tab_data, dict):
                raise serializers.ValidationError(f"داده تب {tab_name} نامعتبر است")

            material_prices = tab_data.get('materialPrices')

            # حالت آرایه
            if isinstance(material_prices, list):
                if len(material_prices) == 0:
                    raise serializers.ValidationError(
                        f"حداقل یک جنس برای تب «{tab_name}» انتخاب کنید"
                    )

            # حالت دیکشنری
            elif isinstance(material_prices, dict):
                if len(material_prices) == 0:
                    raise serializers.ValidationError(
                        f"حداقل یک جنس برای تب «{tab_name}» انتخاب کنید"
                    )

            else:
                raise serializers.ValidationError(
                    f"فرمت materialPrices در تب «{tab_name}» نامعتبر است"
                )

        return value
