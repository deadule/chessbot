import uuid
from yookassa import Configuration, Payment
from auth_handler import confirm_payment


# Set your ЮKassa credentials
Configuration.account_id = '470344'
Configuration.secret_key = 'test_5HI6B6ul3M6PL7B09L2-T5xyeQZDkEt93zetnnAE4zE'

# Define a fixed amount for payments
fixed_amount = 10.00  # Fixed amount for both initial and recurring payments (10.00 RUB)

# Create the first payment with redirect confirmation and save the payment method
async def create_first_payment_with_saving(user_id):
    """
    Create the first payment and save the payment method for future recurring payments.
    """
    try:
        # Create the first payment with save_payment_method set to True
        payment = Payment.create({
            "amount": {
                "value": f"{fixed_amount:.2f}",  # Set the fixed amount for the first payment
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",  # Redirect user to ЮKassa for payment
                "return_url": f"https://example.com/payment/confirmation/{user_id}"  # Adjust this return URL
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
        print(f"Error creating payment: {e}")
        return None, None

# Create a recurring payment using the saved payment method
async def create_recurring_payment(payment_method_id, user_id):
    """
    Create a recurring payment using the saved payment method.
    """
    try:
        # Create a payment using the saved payment method ID
        payment = Payment.create({
            "amount": {
                "value": f"{fixed_amount:.2f}",  # Set the fixed amount for recurring payments
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
    """
    Check the payment status and extract payment_method_id if payment is successful and the method is saved.
    """
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

# Function to confirm the payment and authorize the user
async def handle_payment_confirmation(payment_id, user_id):
    """
    Handle payment confirmation by checking the payment status and authorizing the user if the payment is successful.
    """
    try:
        payment = Payment.find_one(payment_id)

        # Check if the payment was successful
        if payment.status == "succeeded":
            print(f"Payment for User {user_id} succeeded!")

            # Update the user's authorization status to True in the database
            confirm_payment(user_id)
            
            return True
        else:
            print(f"Payment for User {user_id} failed with status: {payment.status}")
            return False
    except Exception as e:
        print(f"Error confirming payment for User {user_id}: {e}")
        return False

# Cancel a recurring payment
async def cancel_recurring_payment(payment_method_id, user_id):
    """
    Cancel the recurring payment by invalidating the saved payment method.
    """
    try:
        # There isn't a specific API method to cancel the payment method in ЮKassa, but you can stop using the payment_method_id
        # You can also record this cancellation in your own database to prevent further payments
        print(f"User {user_id}'s subscription has been canceled. Payment method ID {payment_method_id} is no longer used.")
        return True
    except Exception as e:
        print(f"Error canceling subscription for User {user_id}: {e}")
        return False
