# products/public_views.py

from rest_framework import generics
from .models import Category, Product
from .serializers import CategorySerializer, ProductListSerializer, ProductDetailSerializer


# ---------------------------
# PUBLIC: Category List
# ---------------------------
class PublicCategoryListView(generics.ListAPIView):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = []  # No authentication


# ---------------------------
# PUBLIC: Product List
# ---------------------------
class PublicProductListView(generics.ListAPIView):
    queryset = Product.objects.filter(status='active').select_related("category")
    serializer_class = ProductListSerializer
    permission_classes = []  # No authentication


# ---------------------------
# PUBLIC: Product Detail
# ---------------------------
class PublicProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.filter(status='active').select_related("category")
    serializer_class = ProductDetailSerializer
    permission_classes = []  # No authentication
