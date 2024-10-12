import sqlite3
import os
from telegram import Update
from payment_handler import create_first_payment_with_saving, check_payment_status, handle_payment_confirmation


# Define the database path
DB_PATH = "users.db"
# Initialize the database and create the users table if it doesn't exist
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Create the users table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            authorized BOOLEAN
        )
    ''')
    conn.commit()
    conn.close()

# Add a new user to the database
def add_user(user_id, username):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Insert the user into the database with default 'authorized' status as False
    cursor.execute('INSERT INTO users (user_id, username, authorized) VALUES (?, ?, ?)', (user_id, username, False))
    conn.commit()
    conn.close()

# Check if the user is already in the database
def is_user_in_db(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Query the user
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()

    # Return True if user is found, otherwise False
    return user is not None

# Check if the user is authorized
def is_user_authorized(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Check if the user is authorized
    cursor.execute('SELECT authorized FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        return result[0]  # Return the 'authorized' status (True or False)
    return False

# Update the authorization status of the user
def update_authorization_status(user_id, authorized):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Update the authorization status of the user
    cursor.execute('UPDATE users SET authorized = ? WHERE user_id = ?', (authorized, user_id))
    conn.commit()
    conn.close()

# Confirm the payment and authorize the user after successful payment
def confirm_payment(user_id):
    """
    This function is called once the payment is confirmed.
    It updates the user's authorization status to True in the database.
    """
    update_authorization_status(user_id, True)
    print(f"User {user_id} is now authorized.")

# Handle user authorization during interaction with the bot
async def handle_authorization(update, context):
    user_id = update.effective_user.id
    username = update.effective_user.username

    if not is_user_in_db(user_id):
        # If the user is not in the database, add them
        add_user(user_id, username)
        await update.callback_query.message.reply_text(f"Welcome, {username}! You have been added to the database.")

    if is_user_authorized(user_id):
        # If the user is already authorized, allow access to paid content
        await update.callback_query.message.reply_text(f"Hello {username}, you are already authorized. Proceed to the next step.")
        return True
    else:
        # If the user is not authorized, explain the need for payment
        await update.callback_query.message.reply_text(f"User {username}, you are not yet authorized. Please proceed with payment to gain access.")
        
        # Trigger the payment process (handled by payment_handler)
        confirmation_url, payment_id = await create_first_payment_with_saving(user_id, amount=10.00)
        if confirmation_url:
            await update.callback_query.message.reply_text(f"Please complete the payment by following this link: {confirmation_url}")
        else:
            await update.callback_query.message.reply_text("There was an error processing your payment. Please try again later.")
        
        return False  # User is not authorized yet, payment required
