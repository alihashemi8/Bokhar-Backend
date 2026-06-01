from django.urls import path
from .urls import *
from django.urls import path, include

app_name = "report"

urlpatterns = [

    path('', include('report.report_urls.analytics_urls')),
    path('', include('report.report_urls.customer_urls')),
    path('', include('report.report_urls.dashboard_urls')),
    path('', include('report.report_urls.order_url')),
    path('', include('report.report_urls.report_urls')),

]
