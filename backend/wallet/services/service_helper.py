def create_audit_log(
    *,
    action,
    user=None,
    payment=None,
    withdrawal=None,
    old_data=None,
    new_data=None,
    ip=None,
    user_agent=""
):
    FinancialAuditLog.objects.create(
        action=action,
        user=user,
        payment=payment,
        withdrawal=withdrawal,
        old_data=old_data or {},
        new_data=new_data or {},
        ip_address=ip,
        user_agent=user_agent,
    )