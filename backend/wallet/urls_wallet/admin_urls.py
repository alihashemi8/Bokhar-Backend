# wallet/report_urls.py
from django.urls import path

from ..views.setting_payment_views import *  # ایمپورت ویوها از فایل views موجود در همین پوشه
from ..views.views import *

urlpatterns = [
    # ---------- مدیریت ترمینال‌ها ----------
    path(
        "terminals/",
        PaymentTerminalListCreateView.as_view(),
        name="terminal-list-create",
    ),
    path(
        "terminals/<int:pk>/",
        PaymentTerminalDetailView.as_view(),
        name="terminal-detail",
    ),
    # ---------- مدیریت حساب‌های بانکی ----------
    path(
        "bank-accounts/",
        BankAccountListCreateView.as_view(),
        name="bankaccount-list-create",
    ),
    path(
        "bank-accounts/<int:pk>/",
        BankAccountDetailView.as_view(),
        name="bankaccount-detail",
    ),
    # ---------- اتصال حساب بانکی به ترمینال ----------
    path(
        "terminals/<int:terminal_id>/bank-accounts/",
        TerminalBankAccountCreateView.as_view(),
        name="terminal-bankaccount-create",
    ),
    path(
        "terminal-bank-accounts/<int:pk>/",
        TerminalBankAccountUpdateDeleteView.as_view(),
        name="terminal-bankaccount-update-delete",
    ),
    # ---------- تسویه حساب ----------
    path(
        "terminals/<int:terminal_id>/settlement/",
        SettlementTriggerView.as_view(),
        name="trigger-settlement",
    ),
    path(
        "settlements/<int:id>/", SettlementListView.as_view(), name="settlement-detail"
    ),
]
