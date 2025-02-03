from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)


async def admin_change_timetable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass


admin_change_timetable_handler = CallbackQueryHandler(admin_change_timetable, pattern="^admin_change_timetable$")
