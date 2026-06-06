# services/payment_state.py

from django.core.exceptions import ValidationError
from .state_machine import can_transition


def set_payment_status(payment, new_status):
    if not can_transition(payment.status, new_status):
        raise ValidationError(
            f"Invalid transition: {payment.status} -> {new_status}"
        )

    payment.status = new_status
    payment.save(update_fields=["status"])