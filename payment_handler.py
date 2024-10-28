import uuid
from yookassa import Configuration, Payment
from auth_handler import confirm_payment

# Set your ЮKassa credentials
Configuration.account_id = '470344'
Configuration.secret_key = 'test_5HI6B6ul3M6PL7B09L2-T5xyeQZDkEt93zetnnAE4zE'

fixed_amount = 10.00  # Set the fixed amount for both initial and recurring payments

# Create the first payment with saving payment method enabled
async def create_first_payment_with_saving(user_id):
    try:
        # Create the first payment with save_payment_method set to True
        payment = Payment.create({
            "amount": {
                "value": f"{fixed_amount:.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": f"http://shahimatetokruto.ru"  # Replace with actual return URL
            },
            "capture": True,  # Immediately capture the payment
            "description": f"First payment for User {user_id}",
            "save_payment_method": True,  # Save payment method for future recurring payments
            "metadata": {
                "user_id": user_id  # Store metadata such as user_id
            }
        }, uuid.uuid4())

        # Extract confirmation URL and payment ID
        confirmation_url = payment.confirmation.confirmation_url
        payment_id = payment.id  # Save this for status checking and recurring payments
        return confirmation_url, payment_id
    except Exception as e:
        print(f"Error creating first payment: {e}")
        return None, None

# Create a recurring payment using the saved payment method
async def create_recurring_payment(payment_method_id, user_id):
    try:
        # Create a payment using the saved payment method ID
        payment = Payment.create({
            "amount": {
                "value": f"{fixed_amount:.2f}",
                "currency": "RUB"
            },
            "capture": True,  # Immediately capture the payment
            "description": f"Recurring payment for User {user_id}",
            "payment_method_id": payment_method_id  # Use the saved payment method ID
        }, uuid.uuid4())

        # Check the payment status
        if payment.status == "succeeded":
            print(f"Recurring payment for User {user_id} succeeded!")
            return True
        else:
            print(f"Recurring payment for User {user_id} failed: {payment.status}")
            return False
    except Exception as e:
        print(f"Error creating recurring payment: {e}")
        return False

# Function to handle payment confirmation
async def handle_payment_confirmation(payment_id, user_id):
    try:
        payment = Payment.find_one(payment_id)

        # Check if the payment was successful
        if payment.status == "succeeded":
            print(f"Payment for User {user_id} succeeded!")
            update_authorization_status(user_id, True)  # Authorize user in the database
            return True
        else:
            print(f"Payment for User {user_id} failed with status: {payment.status}")
            return False
    except Exception as e:
        print(f"Error confirming payment for User {user_id}: {e}")
        return False
