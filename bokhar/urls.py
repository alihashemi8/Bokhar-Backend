from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("users.urls")),
    path("api/", include("products.urls")),  
    path("api/discounts/", include("discounts.urls")),
    path("api/cart/", include("order.cart_urls")), 
    path("api/notifications/", include("notifications.urls")),
]
# این قسمت برای نمایش فایل‌های media در حالت Development (DEBUG=True) هست
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)