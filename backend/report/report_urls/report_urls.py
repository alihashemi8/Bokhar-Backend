from django.urls import path

from ..report_views.report_views import *

urlpatterns = [
    # 📊 Monthly 
    path("monthly/price/<int:year>/<int:month>/", MonthlyTotalPriceReport.as_view(), name="monthly-price-report"),
    path("monthly/count/<int:year>/<int:month>/", MonthlyCountReport.as_view(), name="monthly-count-report"),

    # 💰 Income
    path("income/", IncomeReportView.as_view(), name="income-report"),

    # 📈 Weekly
    path("weekly/sales/<int:year>/<int:month>/", WeeklySalesReport.as_view(), name="weekly-sales-report"),
    path("weekly/orders/<int:year>/<int:month>/", WeeklyOrdersReport.as_view(), name="weekly-orders-report"),

    # 🚚 Delivery
    path("delivery-performance/", DeliveryPerformanceView.as_view(), name="delivery-performance"),

    # 📥 Export
    path("export/income-excel/", ExportIncomeReportExcel.as_view(), name="export-income-csv"),

    # 📦 Total Orders
    path("total-orders/", TotalOrderReport.as_view(), name="total-order-report"),
]