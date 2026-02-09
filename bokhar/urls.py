from django.contrib import admin
from django.urls import include, path

from order.urls import *
from product.urls import *
from users.urls import *

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("users.urls")),
    path("api/", include("notifications.urls")),
    path("api/", include("product.urls")),
    path("api/", include("order.urls")),
]
