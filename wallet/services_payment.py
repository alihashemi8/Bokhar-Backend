from django.db import transaction, DatabaseError, models
from django.utils import timezone
from rest_framework.exceptions import ValidationError
import logging

from order.serializers import OrderCreateSerializer
from order.models import Order, OrderItem, OrderStatus, OrderStatusLog
from .models import Wallet, WalletTransaction, Payment
from order.session import *
logger = logging.getLogger(__name__)


class PaymentService:

    def __init__(self, zarinpal_client=None):

        self.zarinpal = zarinpal_client

    def pay_with_wallet(self, user, cart, validated_data):
        try:
            with transaction.atomic():
                # 1. Validate cart
                cart_items = list(cart)
                if not cart_items:
                    raise ValidationError("سبد خرید خالی است")

                # 2. Calculate pricing
                pricing = self._calculate_pricing(validated_data, cart.request)

                final_price = pricing["final_price"]


                # 4. Lock and verify wallet balance
                wallet = Wallet.objects.select_for_update(nowait=True).get(user=user)

                if wallet.balance < final_price:
                    raise ValidationError(
                        f"موجودی ناکافی. "
                        f"نیاز: {final_price:,} | "
                        f"موجودی: {wallet.balance:,}"
                    )

                # 5. Deduct from wallet
                previous_balance = wallet.balance
                wallet.balance -= final_price
                wallet.save(update_fields=['balance'])

                # 6. Create order and items
                order = self._create_order(user, pricing)

                # 7. Record wallet transaction
                self._create_wallet_transaction(wallet, order, final_price)

                # 8. Clear cart
                cart.clear()

                # 9. Log success
                logger.info(
                    f"✅ Wallet payment: "
                    f"user={user.id}, "
                    f"order={order.id}, "
                    f"amount={final_price:,}, "
                    f"balance: {previous_balance:,} → {wallet.balance:,}"
                )

                return order

        except Wallet.DoesNotExist:
            raise ValidationError("کیف پول شما پیدا نشد")
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"❌ Payment failed for user={user.id}: {str(e)}", exc_info=True)
            raise ValidationError("خطا در پردازش پرداخت. لطفاً دوباره تلاش کنید.")

    # WALLET CHARGE

    def initiate_wallet_charge(self, user, amount: int) -> dict:

        if amount < 100000:
            raise ValidationError("حداقل مبلغ شارژ 100,000 تومان است")

        logger.info(f"💰 Initiating wallet charge: user={user.id}, amount={amount:,}")

        payment = Payment.objects.create(
            user=user,
            amount=amount,
            status=Payment.Status.INITIATED,
            payment_type='wallet_charge',
            order=None,
        )

        description = f"شارژ کیف پول - کاربر: {user.phone}"
        result = self.zarinpal.request_payment(
            amount=amount,
            description=description,
            mobile=user.phone,
        )

        # Handle gateway response
        if not result['success']:
            payment.status = Payment.Status.FAILED
            payment.response_code = result.get('code', -1)
            payment.extra_data = {
                'error': result.get('error', 'خطای ناشناخته'),
                'error_code': result.get('code'),
            }
            payment.save()

            logger.error(f"❌ Charge initiation failed: {result.get('error')}")
            raise ValidationError(f"خطا در ایجاد درگاه پرداخت: {result.get('error')}")

        # Save authority and return payment URL
        payment.authority = result['authority']
        payment.extra_data = payment.extra_data or {}
        payment.extra_data.update({
            'request_data': result.get('data', {}),
            'payment_url': result['payment_url'],
        })
        payment.save()

        logger.info(f"✅ Charge initiated: authority={result['authority']}, payment_id={payment.id}")

        return {
            'success': True,
            'payment_url': result['payment_url'],
            'authority': result['authority'],
            'amount': amount,
            'payment_id': payment.id,
        }

    @transaction.atomic
    def verify_wallet_charge(self, user, authority: str, amount: int, status: str) -> dict:

        logger.info(f" Verifying charge: authority={authority}, amount={amount:,}, status={status}")

        try:
            payment = Payment.objects.select_for_update().get(
                authority=authority,
                user=user,
                status=Payment.Status.INITIATED,
                payment_type='wallet_charge',
            )
        except Payment.DoesNotExist:
            logger.error(f"❌ Payment not found: authority={authority}")
            raise ValidationError("تراکنش یافت نشد یا قبلاً پردازش شده است")

        if status != 'OK':
            self._mark_payment_cancelled(payment, status)
            logger.info(f"ℹ️ Payment cancelled by user: authority={authority}")
            return {
                'success': False,
                'message': 'پرداخت توسط کاربر لغو شد',
                'authority': authority,
            }

        verify_result = self.zarinpal.verify_payment(authority, amount)

        if not verify_result['success']:
            self._mark_payment_failed(payment, verify_result)
            logger.error(f"❌ Verification failed: {verify_result.get('error')}")
            raise ValidationError(f"تایید پرداخت ناموفق: {verify_result.get('error')}")

        # Successful payment - update wallet balance
        ref_id = verify_result['ref_id']
        payment = self._mark_payment_successful(payment, ref_id, verify_result)

        wallet, previous_balance = self._credit_wallet(user, amount)

        wallet_transaction = WalletTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            transaction_type=WalletTransaction.TransactionType.DEPOSIT,
            authority=authority,
            ref_id=ref_id,
            order=None,
        )

        logger.info(
            f"✅ Charge completed successfully!\n"
            f"   User: {user.id} ({user.phone})\n"
            f"   Amount: {amount:,} Tomans\n"
            f"   Ref ID: {ref_id}\n"
            f"   Balance: {previous_balance:,} → {wallet.balance:,}\n"
            f"   Payment ID: {payment.id}\n"
            f"   Transaction ID: {wallet_transaction.id}"
        )

        return {
            'success': True,
            'message': f'کیف پول شما با موفقیت {amount:,} تومان شارژ شد',
            'amount': amount,
            'previous_balance': previous_balance,
            'new_balance': wallet.balance,
            'ref_id': ref_id,
            'payment_id': payment.id,
            'transaction_id': wallet_transaction.id,
        }

    # ========== DIRECT PAYMENT WITH ZARINPAL ==========

    def initiate_order_payment(self, user, cart, validated_data) -> dict:
        """
        Initiate direct payment via ZarinPal for order

        Args:
            user: User instance
            cart: OrderSession instance
            validated_data: Validated data

        Returns:
            dict: Payment gateway URL and details
        """
        cart_items = list(cart)
        if not cart_items:
            raise ValidationError("سبد خرید خالی است")

        # Calculate pricing
        pricing = self._calculate_pricing(validated_data, cart.request)
        final_price = pricing["final_price"]

        # Create pending payment record
        payment = Payment.objects.create(
            user=user,
            amount=final_price,
            status=Payment.Status.INITIATED,
            payment_type='order_payment',
            order=None,
            extra_data={'pricing_data': pricing},
        )

        # Request payment gateway
        description = f"پرداخت سفارش - کاربر: {user.phone}"
        result = self.zarinpal.request_payment(
            amount=final_price,
            description=description,
            mobile=user.phone,
        )

        if not result['success']:
            payment.status = Payment.Status.FAILED
            payment.response_code = result.get('code', -1)
            payment.extra_data = {
                **payment.extra_data,
                'error': result.get('error', 'خطای ناشناخته'),
                'error_code': result.get('code'),
            }
            payment.save()

            logger.error(f"❌ Order payment initiation failed: {result.get('error')}")
            raise ValidationError(f"خطا در ایجاد درگاه پرداخت: {result.get('error')}")

        payment.authority = result['authority']
        payment.extra_data = {
            **payment.extra_data,
            'request_data': result.get('data', {}),
            'payment_url': result['payment_url'],
        }
        payment.save()

        logger.info(f"✅ Order payment initiated: authority={result['authority']}, payment_id={payment.id}")

        return {
            'success': True,
            'payment_url': result['payment_url'],
            'authority': result['authority'],
            'amount': final_price,
            'payment_id': payment.id,
        }

    @transaction.atomic
    def verify_order_payment(self, request, authority: str, amount: int, status: str) -> dict:
        """
        Verify order payment and create order

        Args:
            request: HTTP request object
            authority: Payment authority code
            amount: Amount in Tomans
            status: Callback status

        Returns:
            dict: Order information
        """
        logger.info(f"🔍 Verifying order payment: authority={authority}, amount={amount:,}, status={status}")

        user = request.user

        try:
            payment = Payment.objects.select_for_update().get(
                authority=authority,
                user=user,
                status=Payment.Status.INITIATED,
                payment_type='order_payment',
            )
        except Payment.DoesNotExist:
            logger.error(f"❌ Payment not found: authority={authority}")
            raise ValidationError("تراکنش یافت نشد یا قبلاً پردازش شده است")

        # Handle cancelled payment
        if status != 'OK':
            self._mark_payment_cancelled(payment, status)
            logger.info(f"ℹ️ Payment cancelled by user: authority={authority}")
            return {
                'success': False,
                'message': 'پرداخت توسط کاربر لغو شد',
                'authority': authority,
            }

        # Verify with ZarinPal
        verify_result = self.zarinpal.verify_payment(authority, amount)

        if not verify_result['success']:
            self._mark_payment_failed(payment, verify_result)
            logger.error(f"❌ Verification failed: {verify_result.get('error')}")
            raise ValidationError(f"تایید پرداخت ناموفق: {verify_result.get('error')}")

        # Payment verified - create order
        ref_id = verify_result['ref_id']
        payment = self._mark_payment_successful(payment, ref_id, verify_result)

        # Get pricing data from payment
        pricing = payment.extra_data.get('pricing_data', {})

        # Create order
        order = self._create_order(user, pricing)

        # Link order to payment
        payment.order = order
        payment.save()

        # Record payment transaction
        wallet = Wallet.objects.select_for_update().get(user=user)
        wallet_transaction = WalletTransaction.objects.create(
            wallet=wallet,
            order=order,
            amount=amount,
            transaction_type=WalletTransaction.TransactionType.PAYMENT,
            ref_id=ref_id,
        )

        # Clear cart
        cart = OrderSession(request)
        cart.clear()

        logger.info(
            f"✅ Order payment completed!\n"
            f"   User: {user.id} ({user.phone})\n"
            f"   Order: {order.id}\n"
            f"   Amount: {amount:,}\n"
            f"   Ref ID: {ref_id}"
        )

        return {
            'success': True,
            'message': 'پرداخت با موفقیت انجام شد',
            'order_id': order.id,
            'ref_id': ref_id,
            'amount': amount,
            'payment_id': payment.id,
        }

    # ========== HELPER METHODS ==========

    def _calculate_pricing(self, validated_data, request):
        """Calculate order pricing"""
        serializer = OrderCreateSerializer(
            data=validated_data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        return serializer.save()

    def _create_order(self, user, pricing):
        """Create order from pricing data"""
        order = Order.objects.create(
            user=user,
            address=pricing["address"],
            pickup_date=pricing["pickup_date"],
            pickup_shift=pricing["pickup_shift"],
            delivery_date=pricing["delivery_date"],
            delivery_shift=pricing["delivery_shift"],
            description=pricing.get("description", ""),
            status=OrderStatus.PAID,
            rush_fee=pricing["rush_fee"],
            percent_fee=pricing["percent_fee"],
            subtotal_raw=pricing["subtotal_raw"],
            total_item_discounts=pricing["total_item_discounts"],
            subtotal_after_items=pricing["subtotal_after_items"],
            pickup_cost=pricing["pickup_cost"],
            delivery_cost=pricing["delivery_cost"],
            order_discount_amount=pricing["order_discount_amount"],
            applied_coupon=pricing["applied_coupon"],
            final_price=pricing["final_price"],
            paid_at=timezone.now(),
        )

        # Set order type
        order.order_type = order.order_range_type()
        order.save(update_fields=['order_type'])

        # Create order items
        self._create_order_items(order, pricing)

        # Create status log
        user = user.objects.get_or_create(phone='12345678901' , user_name = 'system')
        OrderStatusLog.objects.create(
            user= user,
            order=order,
            to_status=OrderStatus.PAID,
            timestamp=timezone.now()
        )

        # Update coupon if used
        if pricing["applied_coupon"]:
            coupon = pricing["applied_coupon"]
            coupon.used_count = models.F('used_count') + 1
            coupon.save(update_fields=['used_count'])

        return order

    def _create_order_items(self, order, pricing):
        """Create order items in bulk"""
        order_items = [
            OrderItem(
                order=order,
                product=item["product"],
                size=item["size"],
                pricing_tab=item["pricing_tab"],
                material=item["material_name"],
                quantity=item["quantity"],
                original_price=item["original_price"],
                item_discount=item["item_discount"],
                price=item["final_item_price"],
                applied_product_discount=item["applied_product_discount"],
            )
            for item in pricing["computed_items"]
        ]
        OrderItem.objects.bulk_create(order_items)

    def _create_wallet_transaction(self, wallet, order, amount):
        """Record wallet payment transaction"""
        return WalletTransaction.objects.create(
            wallet=wallet,
            order=order,
            amount=amount,
            transaction_type=WalletTransaction.TransactionType.PAYMENT
        )

    def _mark_payment_cancelled(self, payment, status):
        """Mark payment as cancelled"""
        payment.status = Payment.Status.FAILED
        payment.response_code = -1
        payment.extra_data = {
            **(payment.extra_data or {}),
            'callback_status': status,
            'cancelled_at': timezone.now().isoformat(),
        }
        payment.save()

    def _mark_payment_failed(self, payment, verify_result):
        """Mark payment as failed"""
        payment.status = Payment.Status.FAILED
        payment.response_code = verify_result.get('code', -1)
        payment.extra_data = {
            **(payment.extra_data or {}),
            'verify_error': verify_result.get('error'),
            'verify_code': verify_result.get('code'),
            'failed_at': timezone.now().isoformat(),
        }
        payment.save()

    def _mark_payment_successful(self, payment, ref_id, verify_result):
        """Mark payment as successful"""
        payment.status = Payment.Status.SUCCESS
        payment.ref_id = ref_id
        payment.response_code = 0
        payment.extra_data = {
            **(payment.extra_data or {}),
            'verify_data': verify_result.get('data', {}),
            'verified_at': timezone.now().isoformat(),
        }
        payment.save()
        return payment

    def _credit_wallet(self, user, amount):
        """Credit user's wallet"""
        wallet = Wallet.objects.select_for_update().get(user=user)
        previous_balance = wallet.balance
        wallet.balance = models.F('balance') + amount
        wallet.save()
        wallet.refresh_from_db()
        return wallet, previous_balance


