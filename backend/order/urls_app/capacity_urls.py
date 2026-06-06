from django.urls import path
from ..capacity_views import *
from rest_framework.permissions import IsAdminUser


urlpatterns = [
    # Rush Fee Settings (Singleton - فقط یک رکورد)
    path('rush-fee-settings/',
         RushFeeSettingView.as_view(),
         name='rush-fee-settings'),
    
    # Delivery Templates (Capacity Management)
    path('delivery-templates/',
         DeliveryTemplateListView.as_view(),
         name='delivery-templates'),
    path('delivery-templates/<int:pk>/update/',
         DeliveryTemplateUpdateView.as_view(),
         name='delivery-template-update'),
    
    # Capacity Check
    path('check-capacity/',
         CapacityCheckView.as_view(),
         name='check-capacity'),
    
    # Order Validation
    path('validate-order/',
         OrderValidationView.as_view(),
         name='validate-order'),
         
    # Pickup Times (existing - optional)
    path('pickup-times/',
         PickupTimeListCreateView.as_view(),
         name='pickup-time-list'),
    path('pickup-times/<int:pk>/',
         PickupTimeDetailView.as_view(),
         name='pickup-time-detail'),
         
    # Delivery Times (existing - optional)      
    path('delivery-times/',
         DeliveryTimeListCreateView.as_view(),
         name='delivery-time-list'),
    path('delivery-times/<int:pk>/',
         DeliveryTimeDetailView.as_view(),
         name='delivery-time-detail'),
]
