from _pytest import reports
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from report.urls import *
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("users.urls")),
    path("api/", include("products.urls")),  
    path("api/discounts/", include("discounts.urls")),
    path("api/cart/", include("order.urls_app.cart_urls")), 
    path("api/order/", include("order.urls_app.capacity_urls")),  
    path("api/notifications/", include("notifications.urls")),
    path("api/report/", include("report.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)