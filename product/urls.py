from django.urls import path

from .views import *

urlpatterns = [
    path("products", ProductListView.as_view(), name="product-list"),
    path("products/<int:pk>", ProductDetailView.as_view(), name="product-detail"),
    path("products/create", ProductCreateView.as_view(), name="product-create"),
    path("product/update/<int:pk>", ProductUpdateView.as_view(), name="product-update"),
    path("product/delete/<int:pk>", ProductDeleteView.as_view(), name="product-delete"),

    path("search/", ProductSearchView.as_view(), name="product-search"),
]
