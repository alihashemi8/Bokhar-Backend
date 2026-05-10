# services/zarinpal_service.py
import json
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class ZarinPalService:
    """سرویس ارتباط با زرین‌پال"""

    def __init__(self):
        self.merchant_id = settings.ZARINPAL['MERCHANT_ID']
        self.request_url = settings.ZARINPAL['REQUEST_URL']
        self.verify_url = settings.ZARINPAL['VERIFY_URL']
        self.payment_url = settings.ZARINPAL['PAYMENT_URL']
        self.callback_url = settings.ZARINPAL['CALLBACK_URL']

    # متد کمکی برای استخراج خطا (در هر دو حالت)
    def _extract_error(self, result: dict, default_message: str = 'خطای ناشناخته'):
        """
        استخراج پیام خطا از پاسخ زرین‌پال
        زرین‌پال errors رو هم به صورت دیکشنری و هم لیست برمیگردونه
        """
        errors = result.get('errors', {})

        if isinstance(errors, list) and len(errors) > 0:
            # حالت لیستی
            return {
                'message': errors[0].get('message', default_message),
                'code': errors[0].get('code', -1)
            }
        elif isinstance(errors, dict):
            # حالت دیکشنری
            return {
                'message': errors.get('message', default_message),
                'code': errors.get('code', -1)
            }
        else:
            # هیچی
            return {
                'message': default_message,
                'code': -1
            }

    # --------------------------------------------------------
    def request_payment(self, amount: int, description: str, mobile: str = None):
        """
        درخواست ایجاد تراکنش در زرین‌پال
        """
        data = {
            "merchant_id": self.merchant_id,
            "amount": amount,
            "description": description,
            "callback_url": self.callback_url,
        }

        if mobile:
            data["mobile"] = mobile

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        try:
            response = requests.post(
                self.request_url,
                data=json.dumps(data),
                headers=headers,
                timeout=30
            )

            # ⭐ بررسی HTTP Status
            if response.status_code != 200:
                logger.error(f"❌ HTTP {response.status_code} from Zarinpal")
                return {
                    'success': False,
                    'error': f'خطای سرور (HTTP {response.status_code})',
                    'code': response.status_code
                }

            result = response.json()

            if result.get('data') and result['data'].get('authority'):
                authority = result['data']['authority']
                payment_url = f"{self.payment_url}{authority}"

                logger.info(f"✅ authority={authority}, amount={amount}")

                return {
                    'success': True,
                    'authority': authority,
                    'payment_url': payment_url,
                    'data': result['data']
                }
            else:
                # ⭐ استفاده از متد کمکی
                error = self._extract_error(result)
                logger.error(f"❌ code={error['code']}, message={error['message']}")

                return {
                    'success': False,
                    'error': error['message'],
                    'code': error['code']
                }

        except requests.exceptions.Timeout:
            logger.error("Timeout")
            return {'success': False, 'error': 'وقفه در ارتباط با درگاه پرداخت', 'code': -100}

        except requests.exceptions.ConnectionError:
            logger.error("Connection error")
            return {'success': False, 'error': 'عدم اتصال به درگاه پرداخت', 'code': -101}

        except json.JSONDecodeError:
            logger.error("Invalid JSON")
            return {'success': False, 'error': 'پاسخ نامعتبر از سرور', 'code': -102}

        except Exception as e:
            logger.error(f"Unexpected: {str(e)}")
            return {'success': False, 'error': 'خطای غیرمنتظره', 'code': -103}

    def verify_payment(self, authority: str, amount: int):
        """
        تایید تراکنش در زرین‌پال
        """
        data = {
            "merchant_id": self.merchant_id,
            "amount": amount,
            "authority": authority,
        }

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        try:
            response = requests.post(
                self.verify_url,
                data=json.dumps(data),
                headers=headers,
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"❌ HTTP {response.status_code}")
                return {
                    'success': False,
                    'error': f'خطای سرور (HTTP {response.status_code})',
                    'code': response.status_code
                }

            result = response.json()

            if result.get('data') and result['data'].get('ref_id'):
                ref_id = result['data']['ref_id']
                logger.info(f"✅ ref_id={ref_id}")

                return {
                    'success': True,
                    'ref_id': ref_id,
                    'data': result['data']
                }
            else:
                #  استفاده از متد کمکی
                error = self._extract_error(result, 'تایید پرداخت ناموفق')
                logger.error(f"❌ code={error['code']}, message={error['message']}")

                return {
                    'success': False,
                    'error': error['message'],
                    'code': error['code']
                }

        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'وقفه در تایید پرداخت', 'code': -200}

        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': 'عدم اتصال به درگاه', 'code': -201}

        except Exception as e:
            logger.error(f"Verify error: {str(e)}")
            return {'success': False, 'error': 'خطا در تایید پرداخت', 'code': -202}






