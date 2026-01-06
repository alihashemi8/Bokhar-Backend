from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import *
from .permission import *
from .serializers import *

from django.db.models import Q

class ProductListView(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        products = Product.objects.filter(is_verified=True)
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


class ProductDetailView(APIView):
    permission_classes = [IsSeller]

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk, is_verified=True)
        serializer = ProductSerializer(product)
        return Response(serializer.data)


class ProductCreateView(APIView):
    permission_classes = [IsSeller]
    serializer_class = ProductCreateSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():

            serializer.save()
            return Response(
                {"detail": "محصول با موفقیت اضافه شد.", "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductUpdateView(APIView):
    permission_classes = [IsSeller]
    serializer_class = ProductUpdateSerializer

    def put(self, request, pk):
        product = get_object_or_404(Product, pk=pk)

        serializer = self.serializer_class(product, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"detail": "محصول با موفقیت آپدیت شد", "data": serializer.data},
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductDeleteView(APIView):
    permission_classes = [IsSeller]

    def delete(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductSearchView(APIView):
    def get(self, request):
        q = request.GET.get("q", "")
        if not q:
            return Response({"detail": "پارامتر q ارسال نشده"}, status=400)

        products = Product.objects.filter(
            Q(name__icontains=q) |
            Q(service_type__icontains=q) |
            Q(category__name__icontains=q),
            is_verified=True
        )

        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)