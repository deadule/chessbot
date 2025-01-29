import logging
import os
import sys

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ForceReply
from telegram.ext import (
    ApplicationBuilder,
    ConversationHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from databaseAPI import rep_chess_db


profile_inline_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("Имя", callback_data="profile_name")],
    [InlineKeyboardButton("Фамилия", callback_data="profile_surname")],
    [InlineKeyboardButton("рейтинг lichess", callback_data="profile_lichess_rating")],
    [InlineKeyboardButton("рейтинг chess.com", callback_data="profile_chesscom_rating")],
])


async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TODO: Красиво вывести инфу о пользователе
    # Возможно сохранить в context.user_data[...] все поля

    if "messages_to_delete" in context.user_data:
        print(context.user_data["messages_to_delete"], "\n\n\n\n\n\n\n\n")
        for message_id in context.user_data["messages_to_delete"]:
            await context.bot.delete_message(update.effective_chat.id, message_id)
    context.user_data["messages_to_delete"] = [
        update.message.message_id + 1,
        update.message.message_id + 2
    ]
    await update.message.reply_text("Тут инфа о юзере типа.\nИмя, фамилия, рейтинг")
    await update.message.reply_text("Можете поменять данные:", reply_markup=profile_inline_keyboard)


profile_main_menu_handler = MessageHandler(filters.Regex("^👤 Профиль$"), main_menu_handler)
