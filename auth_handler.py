import sqlite3
import os
from telegram import Update

# Define the database path
DB_PATH = "users.db"

# Initialize the database (create the users table if it doesn't exist)
def init_db():
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                authorized BOOLEAN
            )
        ''')
        conn.commit()
        conn.close()

# Check if a user is already in the database
def is_user_in_db(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

# Add a new user to the database
def add_user(user_id, username):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (user_id, username, authorized) VALUES (?, ?, ?)", 
                   (user_id, username, False))
    conn.commit()
    conn.close()

# Update user authorization status
def authorize_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET authorized = ? WHERE user_id = ?", (True, user_id))
    conn.commit()
    conn.close()

# Check if the user is authorized
def is_user_authorized(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT authorized FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == 1

# Handle the authorization process when "Let's Try" is clicked
async def handle_authorization(update: Update, context):
    user_id = update.effective_user.id
    username = update.effective_user.username

    if not is_user_in_db(user_id):
        # If the user is not in the database, add them
        add_user(user_id, username)
        await update.callback_query.message.reply_text(f"Welcome, {username}! You have been added to the database.")

    if is_user_authorized(user_id):
        # If the user is authorized, proceed to the next step (level selection)
        await update.callback_query.message.reply_text(f"Hello {username}, you are already authorized.")
        return True
    else:
        # If the user is not authorized, authorize them and proceed
        await update.callback_query.message.reply_text(f"User {username}, you are not authorized. Contact admin for access.")
        authorize_user(user_id)
        await update.callback_query.message.reply_text(f"User {username} is now authorized.")
        return True
