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


PROFILE_INPUT_LICHESS_RATING = 1


async def profile_lichess_rating_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["messages_to_delete"].append(query.message.message_id + 1)

    await context.bot.send_message(update.effective_chat.id, "Введите новый рейтинг lichess:")
    return PROFILE_INPUT_LICHESS_RATING


async def process_input_lichess_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lichess_rating = update.message.text
    # Too long surname
    if not lichess_rating.isdigit():
        context.user_data["messages_to_delete"].extend([update.message.message_id, update.message.message_id + 1])
        await update.message.reply_text("Введите ваш рейтинг на lichess, пожалуйста:")
        return await profile_lichess_rating_handler(update, context)

    lichess_rating = int(lichess_rating)
    if lichess_rating >= 3000:
        context.user_data["messages_to_delete"].extend([update.message.message_id, update.message.message_id + 1])
        await update.message.reply_text("Хорошая попытка, Карлсен. Попробуй ещё раз:")
        return await profile_lichess_rating_handler(update, context)

    if lichess_rating <= 100:
        context.user_data["messages_to_delete"].extend([update.message.message_id, update.message.message_id + 1])
        await update.message.reply_text("Сомневаюсь, что у вас такой рейтинг... Попробуй ещё раз:")
        return await profile_lichess_rating_handler(update, context)
        
    context.user_data["lichess_rating"] = lichess_rating
    rep_chess_db.update_user_lichess_rating(update.message.from_user.id, lichess_rating)

    context.user_data["messages_to_delete"].append(update.message.message_id)
    # Output updated profile
    await main_menu_handler(update, context)
    return ConversationHandler.END


profile_change_lichess_rating_handler = ConversationHandler(
    [CallbackQueryHandler(profile_lichess_rating_handler, pattern="profile_lichess_rating")],
    {PROFILE_INPUT_LICHESS_RATING: [MessageHandler(filters.ALL, process_input_lichess_rating)]},
    [],
)
