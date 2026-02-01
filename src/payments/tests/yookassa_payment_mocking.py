from unittest.mock import patch, Mock
import uuid
from yookassa import Payment

from payments.yookassa_client import _build_receipt

def test_yookassa_recurring_payment_only():
    """Тест логики рекуррентного платежа с моком YooKassa."""
    PAYMENT_METHOD_ID = "3110a8f1-000f-5001-9000-1427bbd524e2"
    TEST_PHONE = "+79253713026"

    mock_payment = Mock()
    mock_payment.status = "succeeded"
    mock_payment.id = str(uuid.uuid4())

    with patch.object(Payment, 'create', return_value=mock_payment) as mock_create:
        payment = Payment.create({
            "amount": {"value": "1000.00", "currency": "RUB"},
            "capture": True,
            "description": "Recurring payment test",
            "payment_method_id": PAYMENT_METHOD_ID,
            "receipt": _build_receipt(TEST_PHONE),
        }, str(uuid.uuid4()))

        mock_create.assert_called_once()
        call_args = mock_create.call_args[0][0]
        assert call_args["payment_method_id"] == PAYMENT_METHOD_ID
        assert call_args["amount"]["value"] == "1000.00"

        # Assert result
        assert payment.status == "succeeded"