from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
)

from databaseAPI import rep_chess_db


async def admin_send_push(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass


admin_send_push_handler = CallbackQueryHandler(admin_send_push, pattern="^admin_send_push$")
