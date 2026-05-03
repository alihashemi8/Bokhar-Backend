from dataclasses import dataclass
from typing import Optional, List, Tuple

from django.db.models import Q
from django.utils import timezone
from django.db import transaction

from .models import ProductDiscount, GlobalDiscount, Coupon


# ============================================================
# Result DTO
# ============================================================
@dataclass
class DiscountResult:
    base_price: int
    base_discount_amount: int
    base_discount_instance: Optional[ProductDiscount] = None
    coupon_instance: Optional[Coupon] = None
    coupon_discount_amount: int = 0
    final_price: Optional[int] = None
    applied_discount_type: Optional[str] = None

    def __post_init__(self):
        if self.final_price is None:
            self.final_price = max(
                self.base_price
                - self.base_discount_amount
                - self.coupon_discount_amount,
                0,
            )


# ============================================================
# Discount Engine
# ============================================================
class DiscountEngine:

    PRIORITY_MAP = {
        "product": 4,
        "category": 3,
        "pricing_tab": 2,
        "material": 1,
        "global": 0,
    }

    def __init__(self, user=None, now=None):
        self.user = user
        self.now = now or timezone.now()

    # --------------------------------------------------------

    def get_applicable_discounts(
        self,
        product=None,
        material=None,
        pricing_tab=None,
    ) -> List[Tuple[str, object]]:

        now = self.now
        filters = Q()

        if product:
            filters |= Q(product=product)
            if getattr(product, "category", None):
                filters |= Q(category=product.category)

        if pricing_tab:
            filters |= Q(pricing_tab=pricing_tab)

        if material:
            filters |= Q(material=material)

        candidates: List[Tuple[str, object]] = []

        if filters:
            discounts = (
                ProductDiscount.objects.filter(filters, is_active=True)
                .filter(
                    Q(start_at__isnull=True) | Q(start_at__lte=now),
                    Q(end_at__isnull=True) | Q(end_at__gte=now),
                )
            )

            for d in discounts:
                if product and d.product_id == getattr(product, "id", None):
                    candidates.append(("product", d))
                elif product and d.category_id == getattr(product.category, "id", None):
                    candidates.append(("category", d))
                elif pricing_tab and d.pricing_tab_id == pricing_tab.id:
                    candidates.append(("pricing_tab", d))
                elif material and d.material_id == material.id:
                    candidates.append(("material", d))

        global_discount = GlobalDiscount.get_active_global_discount()
        if global_discount:
            candidates.append(("global", global_discount))

        return candidates

    # --------------------------------------------------------

    def apply_coupon(self, code: str, current_price: int):
        try:
            coupon = Coupon.objects.select_for_update().get(
                code=code,
                is_active=True,
            )
        except Coupon.DoesNotExist:
            return False, 0, None

        if not coupon.is_valid_now(self.user, current_price):
            return False, 0, None

        discount_amount = coupon.calculate_discount(current_price)
        return True, discount_amount, coupon

    # --------------------------------------------------------

    @transaction.atomic
    def calculate_item_price(
        self,
        base_price: int,
        product=None,
        material=None,
        pricing_tab=None,
        coupon_code: Optional[str] = None,
    ) -> DiscountResult:

        candidates = self.get_applicable_discounts(
            product=product,
            material=material,
            pricing_tab=pricing_tab,
        )

        best_discount = None
        best_amount = 0
        best_type = None

        if candidates:

            def score(item):
                dtype, discount = item
                amount = discount.calculate_discount(base_price)
                priority = self.PRIORITY_MAP.get(dtype, 0)
                return amount, priority

            best_type, best_discount = max(candidates, key=score)
            best_amount = best_discount.calculate_discount(base_price)

        coupon_obj = None
        coupon_discount = 0

        if coupon_code:
            success, coupon_discount, coupon_obj = self.apply_coupon(
                coupon_code,
                base_price - best_amount,
            )
            if not success:
                coupon_discount = 0

        return DiscountResult(
            base_price=base_price,
            base_discount_amount=best_amount,
            base_discount_instance=best_discount,
            coupon_discount_amount=coupon_discount,
            coupon_instance=coupon_obj,
            applied_discount_type=best_type,
        )
