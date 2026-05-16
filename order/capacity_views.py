import logging
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import datetime, timedelta

from .models import RushFeeSetting, PickUpTemplate, DeliveryTemplate, Order
from .capacity_serializers import *

logger = logging.getLogger(__name__)


class RushFeeSettingView(APIView):
    """
    GET/PUT تنظیمات تعرفه فوری - فقط یک رکورد (Singleton)
    - GET: همه کاربران لاگین‌کرده می‌تونن ببینن
    - PUT: فقط ادمین می‌تونه تغییر بده
    """
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAdminUser()]
    
    def get_object(self):
        obj, created = RushFeeSetting.objects.get_or_create(
            pk=1,
            defaults={
                "fee_24h": 50000,
                "fee_48h": 25000,
                "percent_24h": 0,
                "percent_48h": 0,
                "is_24h_enabled": True,
                "is_48h_enabled": True,
            }
        )
        return obj

    def get(self, request):
        """دریافت تنظیمات - فقط کاربر لاگین‌کرده"""
        setting = self.get_object()
        serializer = RushFeeSettingSerializer(setting)
        return Response(serializer.data)

    def put(self, request):
        """به‌روزرسانی تنظیمات - فقط ادمین"""
        setting = self.get_object()
        serializer = RushFeeSettingSerializer(setting, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeliveryTemplateListView(APIView):
    """
    لیست تمپلیت‌های تحویل (ظرفیت‌ها)
    """
    permission_classes = [IsAuthenticated]  # همه کاربران لاگین‌کرده می‌تونن ببینن
    
    def get(self, request):
        templates = DeliveryTemplate.objects.all()
        serializer = DeliveryTemplateSerializer(templates, many=True)
        return Response(serializer.data)


class DeliveryTemplateUpdateView(APIView):
    """
    آپدیت ظرفیت تمپلیت - فقط ادمین
    """
    permission_classes = [IsAdminUser]
    
    def put(self, request, pk):
        template = get_object_or_404(DeliveryTemplate, pk=pk)
        # فقط فیلدهای ظرفیت رو آپدیت می‌کنیم
        allowed_fields = ['urgent_24_capacity', 'urgent_48_capacity', 'disabled_dates', 'base_price', 'price_add', 'is_active']
       
        print("🔴 Request data:", request.data)
        print("🔴 Request data type:", type(request.data))
        data = {k: v for k, v in request.data.items() if k in allowed_fields}
        print("🔴 Filtered data:", data)
        print("🔴 disabled_dates in data:", 'disabled_dates' in data)
        if 'disabled_dates' in data:
            print("🔴 disabled_dates value:", data['disabled_dates'])
            print("🔴 disabled_dates type:", type(data['disabled_dates']))
        serializer = DeliveryTemplateSerializer(template, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CapacityCheckView(APIView):
    """
    چک کردن ظرفیت باقیمانده برای یک تاریخ
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        date_str = request.query_params.get('date')
        shift = request.query_params.get('shift')  # '24h' یا '48h'
        
        if not date_str:
            return Response(
                {'error': 'date parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # شمردن سفارشات موجود
        if shift == '24h':
            orders_count = Order.objects.filter(
                pickup_date=target_date,
                status__in=['paid', 'picked_up', 'washing'],
            ).exclude(
                order_type__icontains='عادی'
            ).filter(
                order_type__icontains='24'
            ).count()
        elif shift == '48h':
            orders_count = Order.objects.filter(
                pickup_date=target_date,
                status__in=['paid', 'picked_up', 'washing'],
                order_type__icontains='48'
            ).count()
        else:
            orders_count = Order.objects.filter(
                pickup_date=target_date,
                status__in=['paid', 'picked_up', 'washing']
            ).count()
        
        # گرفتن ظرفیت از تمپلیت
        template = DeliveryTemplate.objects.first()
        if not template:
            return Response(
                {'error': 'No delivery template found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # محاسبه ظرفیت باقیمانده
        if shift == '24h':
            capacity = template.urgent_24_capacity
        elif shift == '48h':
            capacity = template.urgent_48_capacity
        else:
            capacity = template.urgent_24_capacity + template.urgent_48_capacity
            
        remaining = max(0, capacity - orders_count)
        
        return Response({
            'date': date_str,
            'shift': shift,
            'capacity': capacity,
            'used': orders_count,
            'remaining': remaining,
            'is_full': remaining == 0
        })


class OrderValidationView(APIView):
    """
    اعتبارسنجی سفارش قبل از ثبت (قیمت‌گذاری و ظرفیت)
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        data = request.data
        pickup_date = data.get('pickup_date')
        delivery_date = data.get('delivery_date')
        subtotal = data.get('subtotal', 0)
        
        if not pickup_date or not delivery_date:
            return Response(
                {'error': 'pickup_date and delivery_date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # محاسبه نوع سفارش (24h/48h/عادی)
        try:
            p_date = datetime.strptime(pickup_date, '%Y-%m-%d')
            d_date = datetime.strptime(delivery_date, '%Y-%m-%d')
            hours_diff = (d_date - p_date).total_seconds() / 3600
        except ValueError:
            return Response(
                {'error': 'Invalid date format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        response_data = {
            'valid': True,
            'delivery_type': 'normal',
            'base_price': subtotal,
            'rush_fee': 0,
            'rush_fee_percent': 0,
            'total_price': subtotal,
            'warnings': []
        }
        
        # تعیین نوع سفارش و هزینه
        settings = RushFeeSetting.objects.first()

        if not settings:
            return Response(response_data)

        if hours_diff <= 24 and settings.is_24h_enabled:
            response_data['delivery_type'] = '24h'

            if settings.percent_24h > 0:
                fee = int(subtotal * settings.percent_24h / 100)
                response_data['rush_fee_percent'] = settings.percent_24h
            else:
                fee = settings.fee_24h

            response_data['rush_fee'] = fee
            response_data['total_price'] = subtotal + fee

        elif hours_diff <= 48 and settings.is_48h_enabled:
            response_data['delivery_type'] = '48h'

            if settings.percent_48h > 0:
                fee = int(subtotal * settings.percent_48h / 100)
                response_data['rush_fee_percent'] = settings.percent_48h
            else:
                fee = settings.fee_48h

            response_data['rush_fee'] = fee
            response_data['total_price'] = subtotal + fee

        # چک کردن ظرفیت
        template = DeliveryTemplate.objects.first()
        if template:
            if response_data['delivery_type'] == '24h':
                current = Order.objects.filter(
                    pickup_date=pickup_date,
                    order_type__icontains='24',
                    status__in=['paid', 'picked_up', 'washing']
                ).count()
                if current >= template.urgent_24_capacity:
                    response_data['valid'] = False
                    response_data['error'] = 'ظرفیت سفارش ۲۴ ساعته برای این تاریخ تکمیل است'
                    
            elif response_data['delivery_type'] == '48h':
                current = Order.objects.filter(
                    pickup_date=pickup_date,
                    order_type__icontains='48',
                    status__in=['paid', 'picked_up', 'washing']
                ).count()
                if current >= template.urgent_48_capacity:
                    response_data['valid'] = False
                    response_data['error'] = 'ظرفیت سفارش ۴۸ ساعته برای این تاریخ تکمیل است'
        
        return Response(response_data)


class PickupTimeListCreateView(APIView):
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        pickup_times = PickUpTemplate.objects.all()
        serializer = PickupTimeSerializer(pickup_times, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PickupTimeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PickupTimeDetailView(APIView):
    permission_classes = [IsAdminUser]
    
    def get_object(self, pk):
        return get_object_or_404(PickUpTemplate, pk=pk)

    def get(self, request, pk):
        pickup_time = self.get_object(pk)
        serializer = PickupTimeSerializer(pickup_time)
        return Response(serializer.data)

    def put(self, request, pk):
        pickup_time = self.get_object(pk)
        serializer = UpdatePickupTimeSerializer(pickup_time, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        pickup_time = self.get_object(pk)
        pickup_time.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DeliveryTimeListCreateView(APIView):
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        delivery_times = DeliveryTemplate.objects.all()
        serializer = DeliveryTimeSerializer(delivery_times, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = DeliveryTimeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeliveryTimeDetailView(APIView):
    permission_classes = [IsAdminUser]
    
    def get_object(self, pk):
        return get_object_or_404(DeliveryTemplate, pk=pk)

    def get(self, request, pk):
        delivery_time = self.get_object(pk)
        serializer = DeliveryTimeSerializer(delivery_time)
        return Response(serializer.data)

    def put(self, request, pk):
        delivery_time = self.get_object(pk)
        serializer = UpdateDeliveryTimeSerializer(delivery_time, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    def delete(self, request, pk):
        delivery_time = self.get_object(pk)
        delivery_time.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
