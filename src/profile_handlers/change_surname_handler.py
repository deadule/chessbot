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
from main_menu_handler import main_menu_handler


PROFILE_INPUT_SURNAME = 1


async def profile_surname_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["messages_to_delete"].append(query.message.message_id + 1)

    await context.bot.send_message(update.effective_chat.id, "Введите новое имя:")
    return PROFILE_INPUT_SURNAME


async def process_input_surname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    surname = update.message.text
    # Too long surname
    if len(surname) > 100:
        context.user_data["messages_to_delete"].extend([update.message.message_id, update.message.message_id + 1])
        await update.message.reply_text("Странная фамилия. Попробуйте покороче:")
        return await profile_surname_handler(update, context)

    context.user_data["surname"] = surname
    rep_chess_db.update_user_surname(update.message.from_user.id, surname)

    context.user_data["messages_to_delete"].append(update.message.message_id)
    # Output updated profile
    await main_menu_handler(update, context)
    return ConversationHandler.END


profile_change_surname_handler = ConversationHandler(
    [CallbackQueryHandler(profile_surname_handler, pattern="profile_surname")],
    {PROFILE_INPUT_SURNAME: [MessageHandler(filters.ALL, process_input_surname)]},
    [],
)
