from telegram import ReplyKeyboardMarkup, Update, KeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

from databaseAPI import rep_chess_db
from profile_handlers.change_nickname_handler import process_input_nickname

reg_main_menu_reply_keyboard = ReplyKeyboardMarkup([
        [KeyboardButton("📅  Расписание"), KeyboardButton("👤 Профиль")],
        [KeyboardButton("🎯 Обучение"), KeyboardButton("⚔ Записаться на турнир")],
        [KeyboardButton("🌟 Подписка")],
    ],
    resize_keyboard=True
)

reg_camp_main_menu_reply_keyboard = ReplyKeyboardMarkup([
        [KeyboardButton("📅  Расписание"), KeyboardButton("👤 Профиль")],
        [KeyboardButton("🎯 Обучение"), KeyboardButton("🌟 Подписка")],
        [KeyboardButton("⚔ Записаться на турнир"), KeyboardButton("🏕 Лагерь")],
    ],
    resize_keyboard=True
)


def main_menu_reply_keyboard(context: ContextTypes.DEFAULT_TYPE):
    if "camp_data" not in context.bot_data:
        return reg_main_menu_reply_keyboard
    if context.bot_data["camp_data"]["active"]:
        return reg_camp_main_menu_reply_keyboard
    return reg_main_menu_reply_keyboard


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.from_user.first_name
    # Register user if it doesn't exist
    rep_chess_db.register_user(update.message.from_user.id, name=name, city_id=None)
    if "messages_to_delete" in context.user_data:
        context.user_data["messages_to_delete"] = []
    else:
        context.user_data["messages_to_delete"] = []

    if nickname := rep_chess_db.check_for_user_in_db_return_nickname(update.message.from_user.id):
        await update.message.reply_text(f"Привет, {nickname}!", reply_markup=main_menu_reply_keyboard(context))
    else:
        message = await update.message.reply_text(
"""
Привет! Мы еще не знакомы, Мы - REP CHESS, Самое крутое шахматное комьюнити! ♟️✨
У нас на турнирах все играют под никнеймами 👾. У нас например есть Мэр, Доджер, Ортур, Женек и Леха Доместос 👀
Придумай ник для себя и мы его запишем!
Не беспокойся насчет первого выбора, ник всегда можно сменить в профиле.
"""
        )
        context.user_data["messages_to_delete"].append(message.message_id)
        context.user_data["text_state"] = process_input_nickname

async def go_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    await context.bot.send_message(
        update.effective_chat.id,
        "_Вы в главном меню_",
        reply_markup=main_menu_reply_keyboard(context),
        parse_mode="markdown"
    )

start_handlers = [
    CommandHandler("start", start),
    CallbackQueryHandler(go_main_menu, "go_main_menu"),
]
