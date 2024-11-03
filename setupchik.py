from yookassa.domain.request.webhook_request import WebhookRequest
from webhook import Webhook  # Assuming the file containing `Webhook` class is named `webhook.py`

# Set the URL of your webhook endpoint
webhook_url = "https://shahimatetokruto.ru/yookassa-webhook"

# Parameters for webhook registration
params = {
    "event": "payment.succeeded",  # Event for successful payments
    "url": webhook_url             # Your publicly accessible webhook URL
}

# Register the webhook with Yookassa
response = Webhook.add(params)
print("Webhook added:", response)
