from django.contrib import admin
from django.urls import include, path

#from order.urls import *
from product.urls import *
from users.urls import *
from home.urls import *
from discount.urls import *
from order.urls import *
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("users.urls")),
    path("api/", include("product.urls")),
path("api/discounts/", include("discount.urls")),
    path("api/", include("order.urls")),
    path("", include("home.urls")),
]
