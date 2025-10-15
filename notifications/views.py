from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .models import Reminder, Transaction, Discount
from .serializers import ReminderSerializer, TransactionSerializer, DiscountSerializer

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

@api_view(["GET"])
@permission_classes([AllowAny])
def notifications(request):
    user = request.user if request.user.is_authenticated else None
    paginator = StandardResultsSetPagination()

    if user:
        reminders_qs = Reminder.objects.filter(user=user).order_by('-time')
        transactions_qs = Transaction.objects.filter(user=user).order_by('-date')
    else:
        reminders_qs = Reminder.objects.all().order_by('-time')[:3]
        transactions_qs = Transaction.objects.all().order_by('-date')[:3]

    reminders = paginator.paginate_queryset(reminders_qs, request)
    transactions = paginator.paginate_queryset(transactions_qs, request)
    discounts = Discount.objects.all()

    data = {
        "reminders": ReminderSerializer(reminders, many=True).data,
        "transactions": TransactionSerializer(transactions, many=True).data,
        "discounts": DiscountSerializer(discounts, many=True).data,
    }

    return paginator.get_paginated_response(data)
