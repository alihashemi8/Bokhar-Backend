from django.urls import path
from ..report_views.analytics import *

urlpatterns = [
    # 📊 Services
    path("analytics/top-services/", TopServicesView.as_view(), name="top-services"),

    # 👑 Customers
    path("analytics/top-customers/", TopCustomersView.as_view(), name="top-customers"),

    # 💤 inactive customers
    path("analytics/customers/no-orders/", CustomersWithoutOrdersView.as_view(), name="customers-no-orders"),
]