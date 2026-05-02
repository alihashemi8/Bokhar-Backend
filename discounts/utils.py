from django.db.models import Q
from django.utils import timezone

from .models import ProductDiscount, GlobalDiscount, Coupon


# -------------------------------------------------------
# اعمال تخفیف روی یک قیمت
# -------------------------------------------------------
def apply_discount(base_price, discount_type, value):
    """
    base_price: int
    discount_type: 'percent' or 'fixed'
    value: int
    """
    if discount_type == "percent":
        # استفاده از // برای جلوگیری از float در قیمت
        discount_amount = (base_price * value) // 100
        return max(0, base_price - discount_amount)
    # fixed
    return max(0, base_price - value)


# -------------------------------------------------------
# انتخاب بهترین تخفیف از یک queryset
# -------------------------------------------------------
def choose_best_discount(discounts, base_price):
    """
    از بین یک queryset (یا لیست) تخفیف، آنکه بیشترین اثر را در کاهش قیمت دارد انتخاب می‌شود.
    خروجی: (best_discount, best_price)
    """
    best_discount = None
    best_price = base_price

    for d in discounts:
        new_price = apply_discount(base_price, d.type, d.value)
        if new_price < best_price:
            best_price = new_price
            best_discount = d

    return best_discount, best_price


# -------------------------------------------------------
#   🔥 منطق اصلی انتخاب یک تخفیف (Single Winner)
#   خروجی: final_price, discount_obj, scope
# -------------------------------------------------------
def calculate_final_price(product, pricing_tab, material, **kwargs):
    base_price = material.price
    now = timezone.now()

    discount = (
        ProductDiscount.objects
        .filter(
            material=material,
            is_active=True,
            start_at__lte=now,
            end_at__gte=now,
        )
        .order_by("-id")
        .first()
    )

    if not discount:
        return base_price, None, None

    final_price = apply_discount(
        base_price,
        discount.type,
        discount.value
    )

    return final_price, discount, "material"
