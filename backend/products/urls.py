# report_urls.py
from django.urls import path
from .views import *
from .public_views import (
    PublicCategoryListView,
    PublicProductListView,
    PublicProductDetailView,
)

urlpatterns = [
    # ----- PUBLIC API -----
    path("public/categories/", PublicCategoryListView.as_view(), name="public-category-list"),
    path("public/products/", PublicProductListView.as_view(), name="public-product-list"),
    path("public/products/<int:pk>/", PublicProductDetailView.as_view(), name="public-product-detail"),

    # ----- ADMIN API (فعلی تو) -----
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("categories/<int:pk>/", CategoryDetailView.as_view(), name="category-detail"),
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<int:pk>/", ProductDetailView.as_view(), name="product-detail"),
    path("products/create/", ProductCreateView.as_view(), name="product-create"),
    path("products/<int:pk>/update/", ProductUpdateView.as_view(), name="product-update"),
    path("products/<int:pk>/delete/", ProductDeleteView.as_view(), name="product-delete"),
    path("products/search/", ProductSearchView.as_view(), name="product-search"),
]
