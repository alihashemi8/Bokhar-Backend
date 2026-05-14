from django.urls import path
from ..cart_views import *

app_name = "order"

urlpatterns = [
    # مشاهده سبد خرید
    path("cart/", CartAPIView.as_view(), name="cart_list"),

    # افزودن محصول به سبد
    path("cart/add/<int:product_id>/", AddOrderSessionAPIView.as_view(), name="cart_add"),

    # بروزرسانی تعداد یک آیتم (PATCH)  ← اضافه شد
    path("cart/update/<str:id_unique>/", UpdateCartItemAPIView.as_view(), name="cart_update_item"),

    # حذف یک آیتم (POST / DELETE)
    path("cart/remove/<str:id_unique>/", RemoveCartAPIView.as_view(), name="cart_remove_item"),

    # خالی کردن کل سبد
    path("cart/delete/", DeleteCartAPIView.as_view(), name="cart_delete"),
]