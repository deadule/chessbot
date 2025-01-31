from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters


CHANNEL = "@repchess"
# TODO: Перенести в файл, видимо?
MESSAGE_ID = 846

async def main_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("У меня нет прав для пересылки расписания :(")
    #await context.bot.forward_message(update.effective_chat.id, CHANNEL, MESSAGE_ID)

timetable_main_message_handler = MessageHandler(filters.Regex("^🙾  Расписание$"), main_message_handler)

timetable_callback_handlers = [
    timetable_main_message_handler,
]
