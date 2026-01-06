from rest_framework import serializers
from .models import *
from products.models import *
from .order_session import *


# نمایش سبد خرید
class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        models = Order
        fields = '__all__'


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__'

class AddressCreateSerializer(serializers.ModelSerializer):
    street = serializers.CharField(max_length=250,required=False)
    city = serializers.CharField(max_length=50,required=False)
    state = serializers.CharField(max_length=50,required=False)
    title = serializers.CharField(max_length=100,required=False)
    postcode =serializers.CharField(max_length=20,required=False)

    class Meta:
        model = Address
        exclude = ('user',)

    def update(self, instance, validated_data):
       instance.city = validated_data.get('city', instance.city)
       instance.street = validated_data.get('street', instance.street)
       instance.postcode = validated_data.get('postcode', instance.postcode)
       instance.title = validated_data.get('title', instance.title)

       instance.save()

       return instance

# گرفتن اطلاعات
class OrderCreateSerializer(serializers.ModelSerializer):
    address = AddressCreateSerializer(required=False)
    class Meta:
        model = Order
        fields = ["address"]

    def create(self, validated_data):
        request = self.context['request']
        cart = Cart(request)

        order = Order.objects.create(
            user=request.user,
            total_price=cart.total_price()
        )

        for item in cart:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                size=item.get('size'),
                service_type=item.get('service'),
                material=item.get('material'),
                quantity=item['quantity'],
                price=item['price']
            )

        cart.remove()
        return order


class OrderSission(serializers.Serializer):
    size = serializers.CharField(max_length=50)
    quantity = serializers.IntegerField()
    price = serializers.PosetiveIntegerField()
    service = serializers.CharField(max_length=50)
    material = serializers.CharField(max_length=50)
