# services/fraud.py


def calculate_risk(user, request):

    score = 0
    ip = request.META.get("REMOTE_ADDR")

    # تعداد تلاش‌های ناموفق
    failed = PaymentAttempt.objects.filter(
        payment__user=user,
        status=PaymentAttempt.Status.FAILED
    ).count()

    score += failed * 10

    # burst detection
    recent = PaymentAttempt.objects.filter(
        payment__user=user
    ).order_by("-id")[:5]

    if len(recent) == 5:
        score += 20

    # IP abuse
    ip_count = PaymentAttempt.objects.filter(
        payer_ip=ip
    ).count()

    if ip_count > 20:
        score += 30

    # user risk
    if not user.is_active:
        score += 100

    return score