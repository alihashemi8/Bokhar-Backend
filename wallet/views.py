from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from services_payment import *


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pay_with_wallet_view(request):

    service = PaymentService()
    cart = OrderSession(request)

    try:
        order = service.pay_with_wallet(request.user, cart, request.data)
        return Response({
            'success': True,
            'order_id': order.id,
            'message': 'سفارش با موفقیت ثبت شد'
        }, status=status.HTTP_201_CREATED)
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_wallet_charge_view(request):

    service = PaymentService(zarinpal_client=request.zarinpal)  # Assuming zarinpal is in request

    try:
        amount = request.data.get('amount')
        result = service.initiate_wallet_charge(request.user, int(amount))
        return Response(result)
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def verify_wallet_charge_view(request):

    authority = request.query_params.get('Authority')
    status_param = request.query_params.get('Status')
    amount = request.query_params.get('Amount')

    service = PaymentService(zarinpal_client=request.zarinpal)

    try:
        result = service.verify_wallet_charge(
            request.user,
            authority,
            int(amount),
            status_param
        )
        return Response(result)
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_order_payment_view(request):

    service = PaymentService(zarinpal_client=request.zarinpal)
    cart = OrderSession(request)

    try:
        result = service.initiate_order_payment(request.user, cart, request.data)
        return Response(result)
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_order_payment_view(request):

    authority = request.query_params.get('Authority')
    status_param = request.query_params.get('Status')
    amount = request.query_params.get('Amount')

    service = PaymentService(zarinpal_client=request.zarinpal)

    try:
        result = service.verify_order_payment(
            request,
            authority,
            int(amount),
            status_param
        )
        return Response(result)
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)