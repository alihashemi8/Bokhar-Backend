from django.urls import path
from ..address_views import *
urlpatterns = [


    # آدرس‌ها
    path("address/create/", CreateAddressView.as_view(), name="address_create"),
    path("address/list/", ListAddressAPIView.as_view(), name="address_list"),
    path("address/update/<int:id>/", UpdateAddressAPIView.as_view(), name="address_update"),
    path("address/delete/<int:id>/", DeleteAddressAPIView.as_view(), name="address_delete"),
    path("neshan/search/", NeshanSearchAPIView.as_view()),
    path("neshan/reverse/", NeshanReverseAPIView.as_view()),

]