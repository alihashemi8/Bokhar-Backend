from django.urls import path
from ..capacity_views import *
app_name = "order"

urlpatterns = [

    path('rush-fee-settings/',
         RushFeeSettingListCreateView.as_view(),
         name='rush-fee-list-create'),
    path('rush-fee-settings/<int:pk>/',
         RushFeeSettingDetailView.as_view(),
         name='rush-fee-detail'),

    # Pickup Times
    path('api/pickup-times/',
         PickupTimeListCreateView.as_view(),
         name='pickup-time-list-create'),
    path('api/pickup-times/<int:pk>/',
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