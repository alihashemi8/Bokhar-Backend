from django.urls import path
from ..cart_views import *  


urlpatterns = [
    # مشاهده سبد خرید
    path("", CartAPIView.as_view(), name="cart_list"),  # ✅ حذف cart/ از اول

    # افزودن محصول به سبد
    path("add/<int:product_id>/", AddOrderSessionAPIView.as_view(), name="cart_add"),  # ✅ حذف cart/

    # بروزرسانی تعداد یک آیتم
    path("update/<str:id_unique>/", UpdateCartItemAPIView.as_view(), name="cart_update_item"),  # ✅ حذف cart/

    # حذف یک آیتم
    path("remove/<str:id_unique>/", RemoveCartAPIView.as_view(), name="cart_remove_item"),  # ✅ حذف cart/

    # خالی کردن کل سبد
    path("delete/", DeleteCartAPIView.as_view(), name="cart_delete"),  # ✅ حذف cart/
]
