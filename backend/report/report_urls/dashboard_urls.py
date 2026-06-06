from django.urls import path
from ..report_views.dashboard_views import *

urlpatterns = [
    # 📊 داشبورد اصلی فروشنده
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
]