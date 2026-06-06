# services/zarinpal_service.py
import json
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class ZarinPalService:
    """سرویس ارتباط با زرین‌پال"""

    def __init__(self):
        self.merchant_id = settings.ZARINPAL["MERCHANT_ID"]

        self.request_url = settings.ZARINPAL["REQUEST_URL"]
        self.verify_url = settings.ZARINPAL["VERIFY_URL"]
        self.payment_url = settings.ZARINPAL["PAYMENT_URL"]
        self.callback_url = settings.ZARINPAL["CALLBACK_URL"]

        self.access_token = settings.ZARINPAL.get("ACCESS_TOKEN")

        self.refund_url = settings.ZARINPAL.get(
            "REFUND_URL",
            "https://api.zarinpal.com/pg/v4/payment/refund.json"
        )

    # متد کمکی برای استخراج خطا (در هر دو حالت)
    def _extract_error(self, result: dict, default_message: str = "خطای ناشناخته"):
        """
        استخراج پیام خطا از پاسخ زرین‌پال
        زرین‌پال errors رو هم به صورت دیکشنری و هم لیست برمیگردونه
        """
        errors = result.get("errors", {})

        if isinstance(errors, list) and len(errors) > 0:
            # حالت لیستی
            return {
                "message": errors[0].get("message", default_message),
                "code": errors[0].get("code", -1),
            }
        elif isinstance(errors, dict):
            # حالت دیکشنری
            return {
                "message": errors.get("message", default_message),
                "code": errors.get("code", -1),
            }
        else:
            # هیچی
            return {"message": default_message, "code": -1}

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

        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        try:
            response = requests.post(
                self.request_url, data=json.dumps(data), headers=headers, timeout=30
            )

            # ⭐ بررسی HTTP Status
            if response.status_code != 200:
                logger.error(f"❌ HTTP {response.status_code} from Zarinpal")
                return {
                    "success": False,
                    "error": f"خطای سرور (HTTP {response.status_code})",
                    "code": response.status_code,
                }

            result = response.json()

            if result.get("data") and result["data"].get("authority"):
                authority = result["data"]["authority"]
                payment_url = f"{self.payment_url}{authority}"

                logger.info(f"✅ authority={authority}, amount={amount}")

                return {
                    "success": True,
                    "authority": authority,
                    "payment_url": payment_url,
                    "data": result["data"],
                }
            else:
                # ⭐ استفاده از متد کمکی
                error = self._extract_error(result)
                logger.error(f"❌ code={error['code']}, message={error['message']}")

                return {
                    "success": False,
                    "error": error["message"],
                    "code": error["code"],
                }

        except requests.exceptions.Timeout:
            logger.error("Timeout")
            return {
                "success": False,
                "error": "وقفه در ارتباط با درگاه پرداخت",
                "code": -100,
            }

        except requests.exceptions.ConnectionError:
            logger.error("Connection error")
            return {
                "success": False,
                "error": "عدم اتصال به درگاه پرداخت",
                "code": -101,
            }

        except json.JSONDecodeError:
            logger.error("Invalid JSON")
            return {"success": False, "error": "پاسخ نامعتبر از سرور", "code": -102}

        except Exception as e:
            logger.error(f"Unexpected: {str(e)}")
            return {"success": False, "error": "خطای غیرمنتظره", "code": -103}

    def verify_payment(self, authority: str, amount: int):
        """
        تایید تراکنش در زرین‌پال
        """
        data = {
            "merchant_id": self.merchant_id,
            "amount": amount,
            "authority": authority,
        }

        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        try:
            response = requests.post(
                self.verify_url, data=json.dumps(data), headers=headers, timeout=30
            )

            if response.status_code != 200:
                logger.error(f"❌ HTTP {response.status_code}")
                return {
                    "success": False,
                    "error": f"خطای سرور (HTTP {response.status_code})",
                    "code": response.status_code,
                }

            result = response.json()

            if result.get("data") and result["data"].get("ref_id"):
                ref_id = result["data"]["ref_id"]
                logger.info(f"✅ ref_id={ref_id}")

                return {"success": True, "ref_id": ref_id, "data": result["data"]}
            else:
                #  استفاده از متد کمکی
                error = self._extract_error(result, "تایید پرداخت ناموفق")
                logger.error(f"❌ code={error['code']}, message={error['message']}")

                return {
                    "success": False,
                    "error": error["message"],
                    "code": error["code"],
                }

        except requests.exceptions.Timeout:
            return {"success": False, "error": "وقفه در تایید پرداخت", "code": -200}

        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "عدم اتصال به درگاه", "code": -201}

        except Exception as e:
            logger.error(f"Verify error: {str(e)}")
            return {"success": False, "error": "خطا در تایید پرداخت", "code": -202}

    def request_settlement(
        self, account_id: str, amount: int, description: str
    ) -> dict:
        """
        ارسال درخواست تسویه (برداشت) به حساب بانکی مشخص

        :param account_id: شناسه حساب بانکی در زرین‌پال (IBAN یا gateway_account_id)
        :param amount: مبلغ به ریال (عدد صحیح)
        :param description: توضیحات تراکنش
        :return: دیکشنری شامل:
            - success: True/False
            - reference_id: شناسه پیگیری زرین‌پال (در صورت موفقیت)
            - error: پیام خطا (در صورت شکست)
        """
        data = {
            "merchant_id": self.merchant_id,
            "amount": amount,
            "iban": account_id,  # در زرین‌پال معمولاً حساب با IBAN مشخص می‌شود
            "description": description,
        }

        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        try:
            response = requests.post(
                self.settlement_url, data=json.dumps(data), headers=headers, timeout=30
            )

            # بررسی HTTP Status
            if response.status_code != 200:
                logger.error(f"❌ Settlement HTTP {response.status_code} from Zarinpal")
                return {
                    "success": False,
                    "error": f"خطای سرور (HTTP {response.status_code})",
                    "code": response.status_code,
                }

            result = response.json()

            # زرین‌پال معمولاً برای تسویه هم کد 100 (موفق) برمی‌گرداند
            if result.get("data") and result["data"].get("code") == 100:
                # شناسه پیگیری تسویه (id یا ref_id)
                reference_id = result["data"].get("id") or result["data"].get(
                    "ref_id", ""
                )
                logger.info(
                    f"✅ Settlement request created, reference_id={reference_id}"
                )

                return {
                    "success": True,
                    "reference_id": reference_id,
                    "data": result["data"],
                }
            else:
                # خطای سمت زرین‌پال
                error = self._extract_error(result, "تسویه ناموفق")
                logger.error(
                    f"❌ Settlement failed: code={error['code']}, message={error['message']}"
                )

                return {
                    "success": False,
                    "error": error["message"],
                    "code": error["code"],
                }

        except requests.exceptions.Timeout:
            logger.error("Settlement timeout")
            return {
                "success": False,
                "error": "وقفه در ارتباط با درگاه تسویه",
                "code": -300,
            }

        except requests.exceptions.ConnectionError:
            logger.error("Settlement connection error")
            return {"success": False, "error": "عدم اتصال به درگاه تسویه", "code": -301}

        except json.JSONDecodeError:
            logger.error("Invalid JSON in settlement response")
            return {"success": False, "error": "پاسخ نامعتبر از سرور", "code": -302}

        except Exception as e:
            logger.exception("Unexpected settlement error")
            return {"success": False, "error": "خطای غیرمنتظره در تسویه", "code": -303}

    def request_refund(
            self,
            session_id: str,
            amount: int,
            method: str,
            description: str = "CUSTOMER_REQUEST",
    ) -> dict:

        if not session_id:
            return {
                "success": False,
                "error": "session_id الزامی است",
                "code": -410,
            }

        if amount <= 0:
            return {
                "success": False,
                "error": "مبلغ استرداد نامعتبر است",
                "code": -411,
            }

        if not self.access_token:
            logger.error("ACCESS_TOKEN is missing")

            return {
                "success": False,
                "error": "تنظیمات استرداد ناقص است",
                "code": -412,
            }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "session_id": session_id,
            "amount": amount,
            "method": method,
            "description": description,
        }

        try:

            response = requests.post(
                self.refund_url,
                json=payload,
                headers=headers,
                timeout=30,
            )

            if response.status_code != 200:
                logger.error(
                    f"Refund HTTP Error: {response.status_code}"
                )

                return {
                    "success": False,
                    "error": f"خطای HTTP {response.status_code}",
                    "code": response.status_code,
                }

            result = response.json()

            data = result.get("data")

            if data:
                refund_id = (
                        data.get("id")
                        or data.get("refund_id")
                        or data.get("reference_id")
                )

                return {
                    "success": True,
                    "refund_id": refund_id,
                    "refund_amount": data.get(
                        "refund_amount",
                        amount,
                    ),
                    "data": data,
                }

            error = self._extract_error(
                result,
                "استرداد وجه ناموفق بود",
            )

            logger.error(
                f"Refund failed: "
                f"{error['code']} - {error['message']}"
            )

            return {
                "success": False,
                "error": error["message"],
                "code": error["code"],
            }

        except requests.exceptions.Timeout:

            logger.error("Refund timeout")

            return {
                "success": False,
                "error": "وقفه در ارتباط با زرین پال",
                "code": -400,
            }

        except requests.exceptions.ConnectionError:

            logger.error("Refund connection error")

            return {
                "success": False,
                "error": "عدم اتصال به زرین پال",
                "code": -401,
            }

        except json.JSONDecodeError:

            logger.error("Refund invalid JSON")

            return {
                "success": False,
                "error": "پاسخ نامعتبر از زرین پال",
                "code": -402,
            }

        except Exception as e:

            logger.exception(
                f"Unexpected refund error: {str(e)}"
            )

            return {
                "success": False,
                "error": "خطای غیرمنتظره در استرداد وجه",
                "code": -403,
            }