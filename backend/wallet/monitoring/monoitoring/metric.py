# wallet/monitoring/metrics.py
from prometheus_client import Counter
from prometheus_client import Histogram


# ==================================================
# Payment Counters
# ==================================================

PAYMENT_TOTAL = Counter(
    "payment_total",
    "Total payment requests",
)

PAYMENT_SUCCESS = Counter(
    "payment_success_total",
    "Total successful payments",
)

PAYMENT_FAILED = Counter(
    "payment_failed_total",
    "Total failed payments",
)

PAYMENT_CANCELED = Counter(
    "payment_canceled_total",
    "Total canceled payments",
)


# ==================================================
# Webhook Counters
# ==================================================

WEBHOOK_TOTAL = Counter(
    "webhook_total",
    "Total received webhooks",
)

WEBHOOK_SUCCESS = Counter(
    "webhook_success_total",
    "Total processed webhooks",
)

WEBHOOK_FAILED = Counter(
    "webhook_failed_total",
    "Total failed webhooks",
)


# ==================================================
# Verify Duration
# ==================================================

VERIFY_DURATION = Histogram(
    "payment_verify_seconds",
    "Time spent verifying payments",
)


# ==================================================
# Gateway Request Duration
# ==================================================

GATEWAY_REQUEST_DURATION = Histogram(
    "gateway_request_seconds",
    "Time spent requesting payment gateway",
)