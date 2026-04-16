from django.db.models import Q
from django.utils import timezone
from .models import ProductDiscount, GlobalDiscount, Coupon


# -------------------------------------------------------
# اعمال تخفیف روی یک قیمت
# -------------------------------------------------------
def apply_discount(base_price, discount_type, value):
    if discount_type == "percent":
        return base_price - (base_price * value / 100)
    return max(0, base_price - value)


# -------------------------------------------------------
# انتخاب بهترین تخفیف از یک queryset
# -------------------------------------------------------
def choose_best_discount(discounts, base_price):
    best_discount = None
    best_price = base_price

    for d in discounts:
        new_price = apply_discount(base_price, d.type, d.value)
        if new_price < best_price:
            best_price = new_price
            best_discount = d

    return best_discount, best_price


# -------------------------------------------------------
# منطق اصلی انتخاب یک تخفیف (Single Winner)
# -------------------------------------------------------
def calculate_final_price(product, pricing_tab, material, user=None, coupon_code=None, order_total=None):
    now = timezone.now()
    base_price = material.price
    final_price = base_price

    # helper for time filters
    time_filter = (
        (Q(start_at__isnull=True) | Q(start_at__lte=now)) &
        (Q(end_at__isnull=True) | Q(end_at__gte=now))
    )

    # ---------------------------------------------------
    # 1) Product discount - product
    # ---------------------------------------------------
    p_product = ProductDiscount.objects.filter(
        Q(product=product), Q(is_active=True), time_filter
    )
    best, price = choose_best_discount(p_product, final_price)
    if best:
        final_price = price
        # product discount همیشه اولویت اول است → return نمی‌کنیم
        return final_price   # چون product level همیشه winner است

    # ---------------------------------------------------
    # 2) Product discount - category
    # ---------------------------------------------------
    p_category = ProductDiscount.objects.filter(
        Q(category=product.category), Q(is_active=True), time_filter
    )
    best, price = choose_best_discount(p_category, final_price)
    if best:
        final_price = price
        return final_price

    # ---------------------------------------------------
    # 3) Product discount - pricing tab
    # ---------------------------------------------------
    p_tab = ProductDiscount.objects.filter(
        Q(pricing_tab=pricing_tab), Q(is_active=True), time_filter
    )
    best, price = choose_best_discount(p_tab, final_price)
    if best:
        final_price = price
        return final_price

    # ---------------------------------------------------
    # 4) Product discount - material
    # ---------------------------------------------------
    p_material = ProductDiscount.objects.filter(
        Q(material=material), Q(is_active=True), time_filter
    )
    best, price = choose_best_discount(p_material, final_price)
    if best:
        final_price = price
        return final_price

    # ---------------------------------------------------
    # 5) Global Discount
    # ---------------------------------------------------
    globals_ = GlobalDiscount.objects.filter(Q(is_active=True), time_filter)
    best, price = choose_best_discount(globals_, final_price)
    if best:
        final_price = price
        return final_price

    # ---------------------------------------------------
    # 6) Coupon → باید روی final_price اعمال شود، نه base_price
    # ---------------------------------------------------
    if coupon_code:
        try:
            coup = Coupon.objects.get(code=coupon_code)
            if coup.is_valid_now(user=user, order_total=order_total):
                final_price = apply_discount(final_price, coup.type, coup.value)
                return final_price
        except Coupon.DoesNotExist:
            pass

    return final_price
