from telegram import ReplyKeyboardMarkup, Update, KeyboardButton
from telegram.ext import ContextTypes

from databaseAPI import rep_chess_db


main_menu_reply_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📅  Расписание")],
        [KeyboardButton("👤 Профиль")],
    ],
    resize_keyboard=True
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.from_user.first_name
    # Register user if it doesn't exist
    rep_chess_db.register_user(update.message.from_user.id, name=name)
    # Greeting message and ReplyKeyboard options
    await update.message.reply_text(f"Привет, {name}!", reply_markup=main_menu_reply_keyboard)
