import logging
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from products.permission import IsSeller
from django.core.cache import cache
from django.db.models import Count, Q, Prefetch

from products.models import Product

from .models import Order, OrderStatus, Address, OrderStatusLog
from .serializers import *
from .session import OrderSession
logger = logging.getLogger(__name__)



class CreateAddressView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddressSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info(f"آدرس جدید برای کاربر {request.user.id} ایجاد شد.")
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ListAddressAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddressDetailSerializer

    def get(self, request):
        addresses = Address.objects.filter(user=request.user)
        serializer = self.serializer_class(addresses, many=True)
        return Response({'data': serializer.data})


class UpdateAddressAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UpdateAddressSerializer

    def put(self, request, id):
        address = get_object_or_404(Address, id=id, user=request.user)
        serializer = self.serializer_class(address, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"data": serializer.data})


class DeleteAddressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, id):
        address = get_object_or_404(Address, id=id, user=request.user)
        address.delete()
        return Response({"message": "آدرس شما حذف شد."})
