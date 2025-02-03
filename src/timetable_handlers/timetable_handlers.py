from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from databaseAPI import rep_chess_db

CHANNEL = "@repchess"
# TODO: Перенести в БД, видимо?
MESSAGE_ID = 3846

async def main_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rep_chess_db.update_user_last_contact(update.message.from_user.id)
    await context.bot.forward_message(update.effective_chat.id, CHANNEL, MESSAGE_ID)

timetable_main_message_handler = MessageHandler(filters.Regex("^📅  Расписание$"), main_message_handler)

timetable_callback_handlers = [
    timetable_main_message_handler,
]
