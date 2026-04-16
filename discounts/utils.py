from datetime import datetime
from .models import ProductDiscount, GlobalDiscount
from django.db import models

def calculate_final_price(product, pricing_dict):
    """
    pricing_dict = {
        "اتو": { "materialPrices": { "نخی": 20000, ... } },
        ...
    }
    """

    now = datetime.now()

    # تخفیف‌های مربوط به محصول / دسته / تب / جنس
    product_discounts = ProductDiscount.objects.filter(
        is_active=True
    ).filter(
        models.Q(category=product.category) |
        models.Q(product=product)
    )

    # تخفیف سراسری
    global_discount = GlobalDiscount.objects.filter(
        is_active=True,
        start_at__lte=now,
        end_at__gte=now
    ).first()

    result = {}

    for tab_name, tab_data in pricing_dict.items():
        result[tab_name] = {"materialPrices": {}}

        for material, base_price in tab_data["materialPrices"].items():
            final_price = base_price

            # 1) Product-level
            for d in product_discounts:

                if d.material and d.material != material:
                    continue

                if d.pricing_tab and d.pricing_tab.name != tab_name:
                    continue

                if d.type == "percent":
                    final_price -= (final_price * d.value) / 100
                else:
                    final_price -= d.value

            # 2) Global discount
            if global_discount:
                if global_discount.type == "percent":
                    final_price -= (final_price * global_discount.value) / 100
                else:
                    final_price -= global_discount.value

            final_price = max(final_price, 0)

            result[tab_name]["materialPrices"][material] = {
                "original": base_price,
                "final": int(final_price)
            }

    return result
