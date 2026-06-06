from .engine import DiscountEngine

def calculate_final_price(*, product, pricing_tab=None, material=None):
    engine = DiscountEngine()
    result = engine.calculate_item_price(
        base_price=material.price,
        product=product,
        pricing_tab=pricing_tab,
        material=material,
    )
    return (
        result.final_price,
        result.base_discount_instance,
        result.applied_discount_type,
    )

def apply_discount(base_price: int, discount_type: str, value: int) -> int:
    if discount_type == "percent":
        return max(0, base_price - (base_price * value) // 100)
    return max(0, base_price - value)

