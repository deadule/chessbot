import logging
from os import getenv
import uuid
from decimal import Decimal
from typing import Optional, Tuple
from yookassa import Configuration, Payment

logger = logging.getLogger(__name__)

ACCOUNT_ID = getenv("ACCOUNT_ID")
SECRET_KEY = getenv("SECRET_KEY")
RETURN_URL = getenv("PAYMENT_RETURN_URL", "https://t.me/repchessbot")
SUBSCRIPTION_AMOUNT = Decimal(getenv("SUBSCRIPTION_AMOUNT"))
CURRENCY = "RUB"

if ACCOUNT_ID and SECRET_KEY:
    Configuration.account_id = ACCOUNT_ID
    Configuration.secret_key = SECRET_KEY
else:
    logger.warning("YooKassa credentials missing: ACCOUNT_ID/SECRET_KEY")


def _money_str(amount: Decimal) -> str:
    return f"{amount:.2f}"


def _build_receipt(phone: str) -> dict:
    return {
        "customer": {"phone": phone},
        "items": [
            {
                "description": "Месячная подписка",
                "quantity": "1.00",
                "amount": {
                    "value": _money_str(SUBSCRIPTION_AMOUNT),
                    "currency": CURRENCY,
                },
                "vat_code": 1,
                "payment_mode": "full_prepayment",
                "payment_subject": "service",
            }
        ],
    }

class YooKassaClient:
    @staticmethod
    def create_subscription_payment(
        telegram_id: int,
        phone: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Создаёт платёж с сохранением метода оплаты (для автопродления).
        Возвращает (confirmation_url, payment_id) или (None, None) при ошибке.
        """
        try:
            payment = Payment.create(
                {
                    "amount": {
                        "value": _money_str(SUBSCRIPTION_AMOUNT),
                        "currency": CURRENCY,
                    },
                    "confirmation": {
                        "type": "redirect",
                        "return_url": RETURN_URL,
                    },
                    "save_payment_method": True,
                    "capture": True,
                    "description": f"Subscription payment for user {telegram_id}",
                    "metadata": {"telegram_id": telegram_id},
                    "receipt": _build_receipt(phone),
                },
                str(uuid.uuid4()),
            )
            return payment.confirmation.confirmation_url, payment.id
        except Exception as e:
            logger.error(
                "Failed to create subscription payment for user %s: %s",
                telegram_id,
                e,
                exc_info=True,
            )
            return None, None

    @staticmethod
    def create_recurring_payment(
        payment_method_id: str,
        telegram_id: int,
        phone: str,
    ) -> Optional[Payment]:
        """Создаёт рекуррентный платёж без подтверждения."""
        try:
            payment = Payment.create(
                {
                    "amount": {
                        "value": _money_str(SUBSCRIPTION_AMOUNT),
                        "currency": CURRENCY,
                    },
                    "capture": True,
                    "description": f"Recurring subscription for user {telegram_id}",
                    "payment_method_id": payment_method_id,
                    "metadata": {"telegram_id": telegram_id},
                    "receipt": _build_receipt(phone),
                },
                str(uuid.uuid4()),
            )
            return payment
        except Exception as e:
            logger.error(
                "Failed to create recurring payment for user %s (method %s): %s",
                telegram_id,
                payment_method_id,
                e,
                exc_info=True,
            )
            return None

    @staticmethod
    def get_payment(payment_id: str) -> Optional[Payment]:
        """Получает статус платежа по ID."""
        try:
            return Payment.find_one(payment_id)
        except Exception as e:
            logger.error(
                "Failed to fetch payment %s: %s", payment_id, e, exc_info=True
            )
            return None