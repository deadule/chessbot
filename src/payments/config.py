import os
from decimal import Decimal, InvalidOperation

def get_subscription_amount() -> Decimal:
    raw = Decimal(os.getenv("SUBSCRIPTION_AMOUNT"))
    if raw is None:
        raise RuntimeError("SUBSCRIPTION_AMOUNT must be set")
    
    try:
        amount = Decimal(raw)
    except InvalidOperation as e:
        raise ValueError(f"Invalid SUBSCRIPTION_AMOUNT '{raw}': {e}")
    
    if amount <= 0:
        raise ValueError("SUBSCRIPTION_AMOUNT must be positive")
    
    return amount.quantize(Decimal("0.01")) 