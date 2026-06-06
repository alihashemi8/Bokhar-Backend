from django.urls import include, path
from rest_framework.routers import DefaultRouter
from ..notif_views import *

router = DefaultRouter()
router.register(r"sms-logs", SmsLogViewSet, basename="smslog")
router.register(
    r"notifications-advertising", NotificationForAdvertisingViewSet, basename="notif-ad"
)
router.register(
    r"notifications-late", NotificationForLateViewSet, basename="notif-late"
),
router.register(r"orders/notify", OrderNotificationViewSet, basename="order-notify")

urlpatterns = [
    # IMPORTANT
    path("", NotificationsAPIView.as_view(), name="notifications"),

    path("", include(router.urls)),
]