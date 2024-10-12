import uuid
from yookassa import Configuration, Payment
from auth_handler import confirm_payment, update_authorization_status

# Set your ЮKassa credentials
Configuration.account_id = '470344'
Configuration.secret_key = 'test_5HI6B6ul3M6PL7B09L2-T5xyeQZDkEt93zetnnAE4zE'

# Create the first payment with saving payment method enabled
async def create_first_payment_with_saving(user_id):
    try:
        # Fixed amount for subscription (100 RUB)
        fixed_amount = 10.00

        # Create the first payment with save_payment_method set to True
        payment = Payment.create({
            "amount": {
                "value": f"{fixed_amount:.2f}",  # Fixed amount of 100 RUB
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",  # Redirect user to ЮKassa for payment
                "return_url": f"https://yourbot.com/payment/confirmation/{user_id}"  # Replace with your actual bot URL
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

# Function to confirm the first payment and save the payment method for future use
async def handle_payment_confirmation(payment_id, user_id):
    try:
        payment = Payment.find_one(payment_id)

        # Check if the payment was successful
        if payment.status == "succeeded":
            print(f"First payment for User {user_id} succeeded!")

            # Save the payment method ID for recurring payments
            if payment.payment_method.saved:
                payment_method_id = payment.payment_method.id
                print(f"Payment method saved for User {user_id}. Payment Method ID: {payment_method_id}")
                
                # Authorize the user after successful payment
                confirm_payment(user_id)

                # Return the saved payment method ID
                return payment_method_id
            else:
                print(f"Payment method not saved for User {user_id}")
                return None
        else:
            print(f"First payment for User {user_id} failed with status: {payment.status}")
            return None
    except Exception as e:
        print(f"Error confirming first payment for User {user_id}: {e}")
        return None

# Create a recurring payment using the saved payment method
async def create_recurring_payment(payment_method_id, user_id):
    try:
        # Fixed amount for subscription (100 RUB)
        recurring_amount = 10.00

        # Create a payment using the saved payment method ID
        payment = Payment.create({
            "amount": {
                "value": f"{recurring_amount:.2f}",  # Fixed amount of 100 RUB
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

# Check payment method saved status and extract payment_method_id
async def check_payment_status(payment_id):
    try:
        payment = Payment.find_one(payment_id)

        # Check if the payment method was saved
        if payment.payment_method.saved:
            payment_method_id = payment.payment_method.id
            print(f"Saved payment method ID: {payment_method_id}")
            return payment_method_id
        else:
            print(f"Payment method was not saved.")
            return None
    except Exception as e:
        print(f"Error checking payment status: {e}")
        return None
