from django.urls import path
from .views import *

app_name = "order"

urlpatterns = [
    # سبد خرید
    path("cart/", CartAPIView.as_view(), name="cart_list"),
    path("cart/remove/<str:id_unique>/", RemoveCartAPIView.as_view(), name="cart_remove_item"),
    path("cart/delete/", DeleteCartAPIView.as_view(), name="cart_delete"),
    path("cart/add/<int:product_id>/", AddOrderSessionAPIView.as_view(), name="cart_add"),
    path('cart/<str:id_unique>/', UpdateCartItemAPIView.as_view(), name='update_cart_item'),

    # سفارش
    path("order/create/", CreateOrderAPIView.as_view(), name="order_create"),
    path("order/delete/<int:id>/", DeleteOrderAPIView.as_view(), name="order_delete"),


    # آدرس‌ها
    path("address/create/", CreateAddressView.as_view(), name="address_create"),
    path("address/list/", ListAddressAPIView.as_view(), name="address_list"),
    path("address/update/<int:id>/", UpdateAddressAPIView.as_view(), name="address_update"),
    path("address/delete/<int:id>/", DeleteAddressAPIView.as_view(), name="address_delete"),

    path('orders/update-status/pick/', UpdateStatusPickView.as_view(), name='update-status-pick'),
    path('orders/update-status/washing/', UpdateStatusWashingView.as_view(), name='update-status-washing'),
    path('orders/update-status/delivery/', UpdateStatusDeliveryView.as_view(), name='update-status-delivery'),
    path('orders/<int:order_id>/status-history/',OrderStatusHistoryView.as_view(), name='order-status-history'),

    path("products/search/", SearchOrderView.as_view(), name="product-search"),
    path('rush-fee-settings/',
         RushFeeSettingListCreateView.as_view(),
         name='rush-fee-list-create'),
    path('rush-fee-settings/<int:pk>/',
         RushFeeSettingDetailView.as_view(),
         name='rush-fee-detail'),

    # Pickup Times
    path('pickup-times/',
         PickupTimeListCreateView.as_view(),
         name='pickup-time-list-create'),
    path('pickup-times/<int:pk>/',
         PickupTimeDetailView.as_view(),
         name='pickup-time-detail'),

    # Delivery Times
    path('delivery-times/',
         DeliveryTimeListCreateView.as_view(),
         name='delivery-time-list-create'),
    path('delivery-times/<int:pk>/',
         DeliveryTimeDetailView.as_view(),
         name='delivery-time-detail'),

]