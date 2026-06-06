from django.urls import path
from ..report_views.order_views import *

urlpatterns = [
    path("orders/<int:id>/", OrderDetailView.as_view(), name="order-detail"),
    path("orders/today/", OrderTodayView.as_view(), name="orders-today"),
    path("orders/status-distribution/", OrderStatusDistributionView.as_view(), name="orders-status-distribution"),
    path("orders/", OrderListView.as_view(), name="orders-list"),
]