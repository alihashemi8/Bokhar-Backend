# services/state_machine.py

ALLOWED_TRANSITIONS = {
    "INITIATED": {"PENDING", "FAILED"},
    "PENDING": {"PROCESSING", "CANCELED", "FAILED"},
    "PROCESSING": {"PAID", "FAILED"},
    "FAILED": set(),
    "CANCELED": set(),
    "PAID": set(),
}


def can_transition(from_status, to_status):
    return to_status in ALLOWED_TRANSITIONS.get(from_status, set())