from django.urls import path
from .urls_app import *
from django.urls import path, include

app_name = "order"

urlpatterns = [

    path('', include('order.urls_app.admin_url')),
    path('', include('order.urls_app.address_url')),
    path('', include('order.urls_app.cart_urls')),

    path('', include('order.urls_app.capacity_url')),

]