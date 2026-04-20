from rest_framework import serializers
from .models import Category, Product, ProductPricingTab, MaterialPrice
from discounts.utils import calculate_final_price
import json


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
    class Meta:
        model = Category
        fields = ['id', 'name', 'image']


# ----------------------------------------------------
# Product LIST (GET)
# ----------------------------------------------------
class ProductListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'title',
            'category',
            'status',
            'image',
            'base_price'
        ]


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
        base_pricing = obj.get_pricing_dict()
        final_output = {}

        for tab_name, tab_data in base_pricing.items():

            # گرفتن OBJECT رکورد تب از DB
            pricing_tab_obj = obj.pricing_tabs.get(tab_name=tab_name)

            tab_pricing = []

            for item in tab_data['materialPrices']:
                material_name = item['material']

                material_obj = pricing_tab_obj.material_prices.get(material=material_name)

                final_price = calculate_final_price(
                    obj,
                    pricing_tab_obj,
                    material_obj
                )

                tab_pricing.append({
                    "id": material_obj.id,              
                    "material": material_name,
                    "price": material_obj.price,
                    "base_price": material_obj.price,
                    "final_price": int(final_price),
                })

            final_output[tab_name] = {
                "id": pricing_tab_obj.id,          
                "sizeType": tab_data["sizeType"],
                "materialPrices": tab_pricing,
            }

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
