import logging
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from product.permission import IsSeller
from django.core.cache import cache
from django.db.models import Count, Q, Prefetch

from product.models import Product

from .models import Order, OrderStatus, Address, OrderStatusLog
from .serializers import *
from .session import OrderSession

logger = logging.getLogger(__name__)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import RushFeeSetting, PickUpTemplate, DeliveryTemplate
from .capacity_serializers  import *

class RushFeeSettingListCreateView(APIView):
    """
    لیست و ایجاد تنظیمات تعرفه فوری
    """

    def get(self, request):
        rush_fees = RushFeeSetting.objects.all()
        serializer = RushFeeSettingSerializer(rush_fees, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = RushFeeSettingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RushFeeSettingDetailView(APIView):
    """
    دریافت، به‌روزرسانی و حذف یک تنظیمات تعرفه فوری خاص
    """

    def get_object(self, pk):
        return get_object_or_404(RushFeeSetting, pk=pk)

    def get(self, request, pk):
        rush_fee = self.get_object(pk)
        serializer = RushFeeSettingSerializer(rush_fee)
        return Response(serializer.data)

    def put(self, request, pk):
        rush_fee = self.get_object(pk)
        serializer = UpdateRushFeeSerializer(rush_fee, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        rush_fee = self.get_object(pk)
        serializer = UpdateRushFeeSerializer(rush_fee, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        rush_fee = self.get_object(pk)
        rush_fee.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PickupTimeListCreateView(APIView):
    """
    لیست و ایجاد ظرفیت‌های تحویل گرفتن
    """

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
    """
    دریافت، به‌روزرسانی و حذف یک ظرفیت تحویل گرفتن خاص
    """

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



class DeliveryTimeListCreateView(APIView):
    """
    لیست و ایجاد زمان‌های تحویل
    """

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
    """
    دریافت، به‌روزرسانی و حذف یک زمان تحویل خاص
    """

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