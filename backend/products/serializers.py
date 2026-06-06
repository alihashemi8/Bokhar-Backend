from rest_framework import serializers
from .models import Category, Product, ProductPricingTab, MaterialPrice
from discounts.engine import *
import json
from .models import ProductPricingTab, MaterialPrice
from discounts.models import ProductDiscount


# ----------------------------------------------------
# MaterialPrice (Read Only)
# ----------------------------------------------------
class MaterialPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialPrice
        fields = ['material', 'price']


# ----------------------------------------------------
# PricingTab (Read Only)
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
    discount = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'image', 'discount']

    def get_discount(self, obj):
        d = getattr(obj, "discount", None)
        if not d:
            return None

        return {
            "id": d.id,
            "type": d.type,
            "value": d.value,
            "start_at": d.start_at,
            "end_at": d.end_at,
            "is_active": d.is_active,
        }

# ----------------------------------------------------
# Product LIST (GET)
# ----------------------------------------------------
class ProductListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    has_discount = serializers.SerializerMethodField()
    pricing = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id',
            'title',
            'category',
            'status',
            'image',
            'base_price',
            'has_discount',
            'pricing',
        ]
    def get_pricing(self, obj):
        request = self.context.get("request")
        serializer = ProductDetailSerializer(obj, context={"request": request})
        return serializer.data.get("pricing")


    def get_has_discount(self, obj):
        # تخفیف از دسته
        if hasattr(obj.category, "discount") and obj.category.discount:
            d = obj.category.discount
            if d.is_active:
                return True

        # تخفیف روی مواد (بدون محاسبه کامل)
        return ProductDiscount.objects.filter(
            product=obj,
            is_active=True
        ).exists()


# ----------------------------------------------------
# Product DETAIL (GET)
# ----------------------------------------------------
class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    pricing = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "title",
            "image",
            "category",
            "pricing",
            "status",
            "base_price",
            "created_at"
        ]

    def get_pricing(self, obj):
        request = self.context.get("request")
        user = request.user if request else None

        engine = DiscountEngine(user=user)

        pricing_tabs = obj.pricing_tabs.all()
        final_output = {}

        for tab in pricing_tabs:
            final_output[tab.tab_name] = {
                "id": tab.id,
                "sizeType": tab.size_type,
                "materialPrices": []
            }

            material_prices = tab.material_prices.all()

            for mp in material_prices:
                result = engine.calculate_item_price(
                    base_price=mp.price,
                    product=obj,
                    pricing_tab=tab,
                    material=mp,
                )

                discount_obj = result.base_discount_instance
                discount_scope = result.applied_discount_type

                data = {
                    "id": mp.id,
                    "material": mp.material,
                    "price": mp.price,
                    "final_price": result.final_price,
                    "has_discount": discount_obj is not None,
                    "discount_type": None,
                    "discount_value": None,
                    "discount_scope": discount_scope,
                    "discount_start_at": None,
                    "discount_end_at": None,
                }

                if discount_obj:
                    data["discount_type"] = discount_obj.type
                    data["discount_value"] = discount_obj.value
                    data["discount_start_at"] = discount_obj.start_at
                    data["discount_end_at"] = discount_obj.end_at

                final_output[tab.tab_name]["materialPrices"].append(data)

        return final_output



# ----------------------------------------------------
# Product CREATE / UPDATE
# ----------------------------------------------------
class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    pricing = serializers.JSONField(write_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'title',
            'category',
            'status',
            'image',
            'base_price',
            'pricing'
        ]

    # ---------------- CREATE ----------------
    def create(self, validated_data):
        pricing_raw = validated_data.pop('pricing', {})
        product = Product.objects.create(**validated_data)

        pricing_data = self._parse_pricing(pricing_raw)
        self._create_pricing(product, pricing_data)

        return product

    # ---------------- UPDATE ----------------
    def update(self, instance, validated_data):
        pricing_raw = validated_data.pop('pricing', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if pricing_raw is not None:
            instance.pricing_tabs.all().delete()
            pricing_data = self._parse_pricing(pricing_raw)
            self._create_pricing(instance, pricing_data)

        return instance

    # ---------------- PARSE PRICING ----------------
    def _parse_pricing(self, pricing_raw):
        if isinstance(pricing_raw, str):
            try:
                return json.loads(pricing_raw)
            except json.JSONDecodeError:
                raise serializers.ValidationError({
                    "pricing": "فرمت JSON نامعتبر است"
                })

        if not isinstance(pricing_raw, dict):
            raise serializers.ValidationError({
                "pricing": "فرمت قیمت‌گذاری نامعتبر است"
            })

        return pricing_raw

    # ---------------- CREATE PRICING TABS ----------------
    def _create_pricing(self, product, pricing_data):
        for tab_name, tab_data in pricing_data.items():

            material_prices = tab_data.get('materialPrices') or {}

            if not isinstance(material_prices, (dict, list)) or len(material_prices) == 0:
                continue

            pricing_tab = ProductPricingTab.objects.create(
                product=product,
                tab_name=tab_name,
                size_type=tab_data.get('sizeType', '')
            )

            if isinstance(material_prices, list):
                for item in material_prices:
                    material = item.get("material")
                    price = item.get("price")

                    if not material or price in [None, "", 0, "0"]:
                        continue

                    MaterialPrice.objects.create(
                        pricing_tab=pricing_tab,
                        material=material,
                        price=int(price)
                    )

            elif isinstance(material_prices, dict):
                for material, price in material_prices.items():
                    if price in [None, "", 0, "0"]:
                        continue

                    MaterialPrice.objects.create(
                        pricing_tab=pricing_tab,
                        material=material,
                        price=int(price)
                    )

    # ---------------- VALIDATION ----------------
    def validate_pricing(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("فرمت قیمت‌گذاری نامعتبر است")

        has_any_valid_tab = False

        for tab_name, tab_data in value.items():
            material_prices = tab_data.get('materialPrices', {})

            if isinstance(material_prices, dict):
                valid_prices = [
                    p for p in material_prices.values()
                    if p not in [None, "", 0, "0"]
                ]
                if valid_prices:
                    has_any_valid_tab = True

            elif isinstance(material_prices, list):
                valid_prices = [
                    item.get("price") for item in material_prices
                    if item.get("price") not in [None, "", 0, "0"]
                ]
                if valid_prices:
                    has_any_valid_tab = True

        if not has_any_valid_tab:
            raise serializers.ValidationError(
                "حداقل یک تب با یک جنس قیمت‌گذاری‌شده لازم است"
            )

        return value
