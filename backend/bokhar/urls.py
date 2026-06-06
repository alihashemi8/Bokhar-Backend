from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from report.urls import *
from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from django.urls import include, path


urlpatterns = [
    #--------------------------------------------api---------------------------
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),

    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),

    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    #----------------------------------app url-------------------------------
    path("admin/", admin.site.urls),
    path("api/", include("users.urls")),
    path("api/", include("products.urls")),
    path("api/discounts/", include("discounts.urls")),
    path("api/cart/", include("order.urls_app.cart_urls")),
    path("api/order/", include("order.urls_app.capacity_urls")),
    path("api/notifications/", include("notifications.urls")),
    path("api/report/", include("report.urls")),
    path("metrics/", include("django_prometheus.urls")),


]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)