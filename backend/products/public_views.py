from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Category, Product, ProductPricingTab, MaterialPrice
from .serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer
)

from discounts.utils import *


# ---------------------------
# PUBLIC: Category List
# ---------------------------
class PublicCategoryListView(generics.ListAPIView):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = []  # Public access


# ---------------------------
# PUBLIC: Product List
# ---------------------------
class PublicProductListView(generics.ListAPIView):
    queryset = Product.objects.filter(status='active').select_related("category")
    serializer_class = ProductListSerializer
    permission_classes = []  # Public access


# ---------------------------
# PUBLIC: Product Detail
# ---------------------------
class PublicProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.filter(status='active').select_related("category")
    serializer_class = ProductDetailSerializer
    permission_classes = []  # Public access



# ---------------------------
# PUBLIC: Final price API
# ---------------------------
@api_view(["GET"])
def product_final_price(request, product_id, tab_id, material_id):
    """
    Returns the final price of a product with the strongest discount applied.
    Supports coupon codes.
    """

    product = Product.objects.get(id=product_id)
    tab = ProductPricingTab.objects.get(id=tab_id)
    material = MaterialPrice.objects.get(id=material_id)

    coupon = request.query_params.get("coupon")

    final_price = calculate_final_price(
        product=product,
        pricing_tab=tab,
        material=material,
        user=request.user if request.user.is_authenticated else None,
        coupon_code=coupon
    )

    return Response({
        "product_id": product_id,
        "pricing_tab_id": tab_id,
        "material_id": material_id,
        "final_price": final_price
    })
