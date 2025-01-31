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


def construct_profile_message(user_db_data: dict) -> str:
    def change_last_symbol(string: str, dst: str, src: str) -> str:
        """
        Change the last 'dst' symbol in string to 'src' symbol.
        """
        return src.join(string.rsplit(dst, 1))

    profile_str = f"👤 *_Ваш профиль:_*\n├ ID:  `{user_db_data['user_id']}`\n├ Имя:  `{user_db_data['name']}`\n"
    if user_db_data['surname']:
        profile_str += f"├ Фамилия:  `{user_db_data['surname']}`\n"
    profile_str = change_last_symbol(profile_str, "├", "└")
    profile_str += f"\n📊 *_Статистика:_*\n"
    profile_str += f"├ Rep рейтинг:  `{user_db_data['rep_rating']}`\n"
    if user_db_data['lichess_rating']:
        profile_str += f"├ Рейтинг [lichess](https://lichess.org/):  `{user_db_data['lichess_rating']}`\n"
    if user_db_data['chesscom_rating']:
        profile_str += f"├ Рейтинг [chess\.com](https://chess.com/):  `{user_db_data['chesscom_rating']}`\n"
    profile_str = change_last_symbol(profile_str, "├", "└")
    return profile_str


async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_db_data = rep_chess_db.get_user_on_telegram_id(update.message.from_user.id)

    # Add user data in cache to not make query to database every time
    if "user_db_data" not in context.user_data:
        context.user_data["user_db_data"] = user_db_data

    # Delete useless messages about correcting some data
    if "messages_to_delete" in context.user_data:
        for message_id in context.user_data["messages_to_delete"]:
            await context.bot.delete_message(update.effective_chat.id, message_id)
    context.user_data["messages_to_delete"] = []

    profile_str = construct_profile_message(user_db_data)
    message = await update.message.reply_text(profile_str, parse_mode="MarkdownV2", disable_web_page_preview=True)
    context.user_data["messages_to_delete"].append(message.message_id)
    message = await update.message.reply_text("Можете поменять данные:", reply_markup=profile_inline_keyboard)
    context.user_data["messages_to_delete"].append(message.message_id)


profile_main_menu_handler = MessageHandler(filters.Regex("^👤 Профиль$"), main_menu_handler)
