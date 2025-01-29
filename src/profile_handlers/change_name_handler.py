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


PROFILE_INPUT_NAME = 1


async def change_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        context.user_data["messages_to_delete"].append(query.message.message_id + 1)

        await context.bot.send_message(update.effective_chat.id, "Введите новое имя:")
        return PROFILE_INPUT_NAME


async def process_input_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    # Too long name
    if len(name) > 100:
        context.user_data["messages_to_delete"].extend([update.message.message_id, update.message.message_id + 1])
        await update.message.reply_text("Странное имя. Попробуйте покороче:")
        return await change_name_handler(update, context)

    context.user_data["name"] = name
    rep_chess_db.update_user_name(update.message.from_user.id, name)

    context.user_data["messages_to_delete"].append(update.message.message_id)
    # Output updated profile
    await main_menu_handler(update, context)
    return ConversationHandler.END


profile_change_name_handler = ConversationHandler(
    [CallbackQueryHandler(change_name_handler, pattern="profile_name")],
    {PROFILE_INPUT_NAME: [MessageHandler(filters.ALL, process_input_name)]},
    [],
)
