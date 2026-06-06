# Create your views here.

from rest_framework.views import APIView
from products.permission import *

def get_week_number(day):
    if day <= 7:
        return 1
    elif day <= 14:
        return 2
    elif day <= 21:
        return 3
    return 4



class BaseReport(APIView):
    permission_classes = [IsSeller]

    def get_cached(self, key):
        return cache.get(key)

    def set_cache(self, key, value, timeout):
        cache.set(key, value, timeout)



class MonthlyTotalPriceReport(BaseReport):

    def get(self, request, year, month):
        cache_key = f"monthly_price_{year}_{month}"

        if cached := self.get_cached(cache_key):
            return Response(cached)

        qs = (
            Order.objects
            .filter(create_time__year=year, create_time__month=month)
            .annotate(day=ExtractDay("create_time"))
            .values("day")
            .annotate(total=Sum("final_price"))
        )

        week_data = {1: 0, 2: 0, 3: 0, 4: 0}

        for row in qs:
            week = get_week_number(row["day"])
            week_data[week] += row["total"] or 0

        response = {
            "labels": ["week_1", "week_2", "week_3", "week_4"],
            "values": list(week_data.values()),
        }

        self.set_cache(cache_key, response, 3600)
        return Response(response)


class MonthlyCountReport(BaseReport):

    def get(self, request, year, month):
        cache_key = f"monthly_count_{year}_{month}"

        if cached := self.get_cached(cache_key):
            return Response(cached)

        qs = (
            Order.objects
            .filter(create_time__year=year, create_time__month=month)
            .annotate(day=ExtractDay("create_time"))
            .values("day")
            .annotate(total=Count("id"))
        )

        week_data = {1: 0, 2: 0, 3: 0, 4: 0}

        for row in qs:
            week = get_week_number(row["day"])
            week_data[week] += row["total"]

        response = {
            "labels": ["week_1", "week_2", "week_3", "week_4"],
            "values": list(week_data.values()),
        }

        self.set_cache(cache_key, response, 3600)
        return Response(response)

class IncomeReportView(BaseReport):

    def get(self, request):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        cache_key = f"income_{start_date}_{end_date}"

        if cached := self.get_cached(cache_key):
            return Response(cached)

        orders = Order.objects.all()

        if start_date:
            orders = orders.filter(create_time__date__gte=start_date)
        if end_date:
            orders = orders.filter(create_time__date__lte=end_date)

        agg = orders.aggregate(
            orders_count=Count("id"),
            subtotal=Sum("subtotal_raw"),
            pickup=Sum("pickup_cost"),
            delivery=Sum("delivery_cost"),
            rush=Sum("rush_fee"),
            item_discount=Sum("total_item_discounts"),
            order_discount=Sum("order_discount_amount"),
            final=Sum("final_price"),
        )

        subtotal = agg["subtotal"] or 0
        pickup = agg["pickup"] or 0
        delivery = agg["delivery"] or 0
        rush = agg["rush"] or 0
        item_disc = agg["item_discount"] or 0
        order_disc = agg["order_discount"] or 0
        final = agg["final"] or 0

        gross = subtotal + pickup + delivery + rush
        discounts = item_disc + order_disc
        net = gross - discounts

        response = {
            "orders": agg["orders_count"],
            "gross_income": gross,
            "net_income": net,
            "discounts": discounts,
            "final_check": final,
        }

        self.set_cache(cache_key, response, 600)
        return Response(response)


from products.permission import IsSeller

from rest_framework.views import APIView


class WeeklySalesReport(APIView):
    permission_classes = [IsSeller]

    def get(self, request, year, month):

        cache_key = f"weekly_sales_{year}_{month}"

        if cached := cache.get(cache_key):
            return Response(cached)

        qs = (
            Order.objects
            .filter(
                create_time__year=year,
                create_time__month=month
            )
            .annotate(day=ExtractDay("create_time"))
            .values("day")
            .annotate(total_sales=Sum("final_price"))
        )

        week_data = {
            1: 0,
            2: 0,
            3: 0,
            4: 0,
        }

        for row in qs:
            week = get_week_number(row["day"])
            week_data[week] += row["total_sales"] or 0

        response = {
            "labels": [
                "Week 1",
                "Week 2",
                "Week 3",
                "Week 4",
                "Week 5",
            ],
            "values": list(week_data.values()),
        }

        cache.set(cache_key, response, 300)

        return Response(response)


from django.db.models.functions import ExtractDay

class WeeklyOrdersReport(APIView):
    permission_classes = [IsSeller]

    def get(self, request, year, month):

        cache_key = f"weekly_orders_{year}_{month}"

        if cached := cache.get(cache_key):
            return Response(cached)

        qs = (
            Order.objects
            .filter(
                create_time__year=year,
                create_time__month=month
            )
            .annotate(day=ExtractDay("create_time"))
            .values("day")
            .annotate(total_orders=Count("id"))
        )

        week_data = {
            1: 0,
            2: 0,
            3: 0,
            4: 0,
        }

        for row in qs:
            week = get_week_number(row["day"])
            week_data[week] += row["total_orders"]

        response = {
            "labels": [
                "Week 1",
                "Week 2",
                "Week 3",
                "Week 4",
            ],
            "values": list(week_data.values()),
        }

        cache.set(cache_key, response, 300)

        return Response(response)


from django.utils import timezone
from datetime import timedelta
from rest_framework.views import APIView
from products.permission import IsSeller


class DeliveryPerformanceView(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        seller = request.user
        days = int(request.GET.get("days", 30))

        cache_key = f"delivery_perf_{seller.id}_{days}"
        if cached := cache.get(cache_key):
            return Response(cached)

        since = timezone.now() - timedelta(days=days)

        orders = Order.objects.filter(create_time__gte=since)

        total = orders.count()

        # فقط late ها رو دیتابیس حساب می‌کنیم (بدون loop)
        late_count = sum(
            1
            for o in orders.only("delivery_date", "pickup_shift")
            if o.delivery_deadline and o.delivery_date > o.delivery_deadline.date()
        )

        on_time_percent = round(
            ((total - late_count) / total) * 100, 1
        ) if total else 0

        response = {
            "period_days": days,
            "total_orders": total,
            "late_deliveries": late_count,
            "on_time_percent": on_time_percent,
        }

        cache.set(cache_key, response, 300)
        return Response(response)


from rest_framework.views import APIView


class Echo:
    def write(self, value):
        return value

from openpyxl import Workbook
from django.http import HttpResponse


class ExportIncomeReportExcel(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        orders = Order.objects.select_related("user").all()

        if start_date:
            orders = orders.filter(create_time__date__gte=start_date)

        if end_date:
            orders = orders.filter(create_time__date__lte=end_date)

        wb = Workbook()
        ws = wb.active
        ws.title = "Income Report"

        ws.append([
            "Order ID",
            "Date",
            "Customer",
            "Gross Income",
            "Discounts",
            "Final Price",
            "Status",
        ])

        for order in orders:
            gross = (
                order.subtotal_raw
                + order.pickup_cost
                + order.delivery_cost
                + order.rush_fee
            )

            discounts = (
                order.total_item_discounts
                + order.order_discount_amount
            )

            ws.append([
                order.id,
                order.create_time.strftime("%Y-%m-%d"),
                order.user.fullname,
                gross,
                discounts,
                order.final_price,
                order.status,
            ])

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        response[
            "Content-Disposition"
        ] = 'attachment; filename="income_report.xlsx"'

        wb.save(response)

        return response

from django.db.models import Count, Sum
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response

from order.models import *
from products.permission import IsSeller


class TotalOrderReport(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        cache_key = "total_order_report"

        if cached := cache.get(cache_key):
            return Response(cached)

        totals = Order.objects.aggregate(
            total_orders=Count("id"),
            total_revenue=Sum("final_price")
        )

        response = {
            "orders": totals["total_orders"] or 0,
            "revenue": totals["total_revenue"] or 0,
        }

        cache.set(cache_key, response, 120)
        return Response(response)