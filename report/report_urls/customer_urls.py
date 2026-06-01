from django.urls import path
from ..report_views.customer_views import *

urlpatterns = [
    # 👥 لیست مشتریان + فیلترها (most_orders, most_spent, etc.)
    path("customers/", CustomersView.as_view(), name="customers-list"),

    # 🔎 سرچ مشتری
    path("customers/search/", SearchCustomersView.as_view(), name="customers-search"),

    # 👤 جزئیات کامل مشتری + سفارش‌ها
    path("customers/<int:id>/", CustomerDetailView.as_view(), name="customer-detail"),

    # 💰 جزئیات کیف پول + تراکنش‌ها
    path("wallet/<int:user_id>/", WalletDetailView.as_view(), name="wallet-detail"),
]