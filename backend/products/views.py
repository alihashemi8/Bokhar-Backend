from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser ,JSONParser  
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import Category, Product
from .serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateUpdateSerializer
)
from .permission import IsSeller


# -----------------------
#   Category Views
# -----------------------

class CategoryListView(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        categories = Category.objects.filter(is_active=True)
        return Response(CategorySerializer(categories, many=True).data)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CategoryDetailView(APIView):
    permission_classes = [IsSeller]

    def delete(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# -----------------------
#   Product Views
# -----------------------

class ProductListView(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        products = Product.objects.all()
        return Response(ProductListSerializer(products, many=True).data)


class ProductDetailView(APIView):
    permission_classes = [IsSeller]

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        return Response(ProductDetailSerializer(product).data)


class ProductCreateView(APIView):
    permission_classes = [IsSeller]
    parser_classes = [MultiPartParser, FormParser,JSONParser]  

    def post(self, request):
        serializer = ProductCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            product = serializer.save()
            return Response(
                {
                    "detail": "سرویس با موفقیت ایجاد شد",
                    "data": ProductDetailSerializer(product).data
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductUpdateView(APIView):
    permission_classes = [IsSeller]
    parser_classes = [MultiPartParser, FormParser, JSONParser]  

    def put(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        serializer = ProductCreateUpdateSerializer(product, data=request.data, partial=True)

        if serializer.is_valid():
            product = serializer.save()
            return Response(
                {
                    "detail": "سرویس با موفقیت بروزرسانی شد",
                    "data": ProductDetailSerializer(product).data
                },
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductDeleteView(APIView):
    permission_classes = [IsSeller]

    def delete(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.delete()
        return Response({"message": "deleted"}, status=status.HTTP_200_OK)


class ProductSearchView(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        q = request.GET.get("q", "").strip()

        if not q:
            return Response(
                {"detail": "پارامتر q الزامی است"},
                status=status.HTTP_400_BAD_REQUEST
            )

        products = Product.objects.filter(
            Q(title__icontains=q) |
            Q(category__name__icontains=q),
            status="active"
        )

        return Response(ProductListSerializer(products, many=True).data)
