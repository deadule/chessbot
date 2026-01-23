import os
import uuid
import pytest
from yookassa import Configuration, Payment
from decimal import Decimal

Configuration.account_id = os.getenv("ACCOUNT_ID")
Configuration.secret_key = os.getenv("SECRET_KEY")

if not Configuration.account_id or not Configuration.secret_key:
    pytest.skip("YooKassa credentials not set", allow_module_level=True)

TELEGRAM_ID = 123456789
TEST_PHONE = "+79991234567"
SUBSCRIPTION_AMOUNT = Decimal("10.00")


def _money_str(amount: Decimal) -> str:
    return f"{amount:.2f}"


def _build_receipt(phone: str) -> dict:
    return {
        "customer": {"phone": phone},
        "items": [{
            "description": "Тестовая подписка",
            "quantity": "1.00",
            "amount": {"value": _money_str(SUBSCRIPTION_AMOUNT), "currency": "RUB"},
            "vat_code": 1,
            "payment_mode": "full_prepayment",
            "payment_subject": "service",
        }],
    }


def test_yookassa_recurring_payment_only():
    """Тест рекуррентного платежа, если payment_method_id уже известен."""

    PAYMENT_METHOD_ID = "pm_1234567890abcdef"

    payment = Payment.create({
        "amount": {"value": _money_str(SUBSCRIPTION_AMOUNT), "currency": "RUB"},
        "capture": True,
        "description": "Recurring payment test",
        "payment_method_id": PAYMENT_METHOD_ID,
        "receipt": _build_receipt(TEST_PHONE),
    }, str(uuid.uuid4()))

    assert payment.status == "succeeded"