from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from products.models import *

from .cart_serializer import *

logger = logging.getLogger(__name__)


class CartAPIView(APIView):
    permission_classes = [IsAuthenticated]  # اضافه شد

    def get(self, request):
        cart = OrderSession(request)
        return Response({"cart": list(cart)})


# حذف کل سبد خرید
class DeleteCartAPIView(APIView):
    permission_classes = [IsAuthenticated]  # اضافه شد

    def post(self, request):
        cart = OrderSession(request)
        cart.clear()
        return Response(
            {"message": "سبد خرید شما خالی شد"},
            status=status.HTTP_200_OK,
        )


# افزودن محصول به Cart (Session)
class AddOrderSessionAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddToCartSerializer

    def post(self, request, product_id):
        try:
            product = get_object_or_404(Product, id=product_id)

            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)

            cart = OrderSession(request)
            data = serializer.validated_data

            quantity = data.get("quantity", 1)
            material = data.get("material")
            service = data.get("service")
            size_id = data.get("size")

            # اعتبارسنجی سایز
            size = None
            if size_id:
                try:
                    size = Size.objects.get(id=size_id)
                except Size.DoesNotExist:
                    return Response(
                        {"error": "سایز انتخاب شده معتبر نیست"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # افزودن به سبد
            cart.add(
                product=product,
                size=size,
                material=material,
                service=service,
                quantity=quantity,
            )

            return Response({
                "message": "محصول با موفقیت به سبد خرید اضافه شد",
                "cart_summary": {
                    "total_items": len(list(cart)),
                    "total_price": cart.total_price()
                }
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error adding to cart: {e}")
            return Response(
                {"error": "خطا در افزودن محصول به سبد خرید"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UpdateCartItemAPIView(APIView):
    permission_classes = [IsAuthenticated]  # اضافه شد

    def patch(self, request, id_unique, *args, **kwargs):
        try:
            quantity = request.data.get('quantity')
            if quantity is None:
                return Response(
                    {"error": "quantity is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            quantity = int(quantity)
            if quantity < 0:
                return Response(
                    {"error": "quantity must be positive"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            cart = OrderSession(request)
            updated = cart.update_quantity(id_unique, quantity)

            if not updated:
                return Response(
                    {"error": "Item not found in cart"},
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response({
                "message": "Quantity updated successfully",
                "items": list(cart),
                "total_price": cart.total_price()
            }, status=status.HTTP_200_OK)

        except ValueError:
            return Response(
                {"error": "Invalid quantity format"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RemoveCartAPIView(APIView):
    permission_classes = [IsAuthenticated]  # اضافه شد

    def post(self, request, id_unique=None, *args, **kwargs):
        return self._remove_item(request, id_unique)

    def delete(self, request, id_unique=None, *args, **kwargs):
        return self._remove_item(request, id_unique)

    def _remove_item(self, request, id_unique):
        try:
            if not id_unique:
                return Response(
                    {"error": "id_unique required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            cart = OrderSession(request)
            
            # بررسی وجود آیتم (دسترسی به دیکشنری داخلی cart)
            if id_unique not in cart.cart:
                return Response(
                    {"error": "Item not found in cart"}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            # استفاده از delete_item برای حذف کامل (نه فقط کاهش تعداد)
            cart.delete_item(id_unique)
            
            return Response({
                "message": "Item removed successfully",
                "items": list(cart),
                "total_price": cart.total_price()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error removing cart item: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
