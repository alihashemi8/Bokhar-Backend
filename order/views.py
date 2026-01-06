from django.shortcuts import render
from .models import *
from order_session import *
from rest_framework.views import APIView
from rest_framework.response import Response
# Create your views here.
#نماش اطلاعات
class CartAPIView(APIView):
    def get(self, request):
        cart = CartSession(request)
        return Response({
            "cart": list(cart)
        })

class OrderAPIView(APIView):
    def get(self, request,id):
        order = get_object_or_404(OrderItem, id=id)
        return Response({"order": order})


class RemoveCartAPIView(APIView):
    def post(self, request, id_unique):
        cart = CartSession(request)
        cart.remove(id_unique)

        return Response(
            {
                "message": "تعداد محصول شما کم شد",
                "cart": list(cart)
            },
            status=status.HTTP_200_OK
        )

class AddOrderSession(APIView,id):
    def post(self,request,id):
        cart = Cart(request)
        product = Product.objects.get(id=id)
        data = OrderSission(data=request.data)
        if data.is_valid():
            size = data.validate_data['size']
            quantity = data.validate_data['quantity']
            material = data.validate_data['material']
            service = data.validate_data['service']
            cart.add_cart(product,size,material,service,quantity)
            return Response("ok")

class CreateOrderAPIView(APIView):


    def post(self, request):
        serializer = OrderCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response({"order_id": order.id})


