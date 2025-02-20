import copy

from telegram import ReplyKeyboardMarkup, Update, KeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

from databaseAPI import rep_chess_db


# Save it in global except database because it is faster.
# To show camp button set "active" field to True.
# TODO: Перенести эти данные в context.bot_data - данные, общие для бота
camp_data = {
    "active": False,
    "channel": None,
    "message_id": None
}

active_tournament = {
    "active": False,
    "summary": None,
    "date_time": None
}


keyboard_buttons = [
    [KeyboardButton("📅  Расписание")],
    [KeyboardButton("👤 Профиль")],
]


base_main_menu_reply_keyboard = ReplyKeyboardMarkup(
    keyboard_buttons,
    resize_keyboard=True
)


def main_menu_reply_keyboard():
    if not camp_data["active"] and not active_tournament["active"]:
        return base_main_menu_reply_keyboard

    new_keyboard = copy(base_main_menu_reply_keyboard)
    if camp_data["active"]:
        new_keyboard += [[KeyboardButton("🏕 Лагерь")]]
    if active_tournament["active"]:
        new_keyboard += [[KeyboardButton("⚔ Зарегистрироваться")]]

    return ReplyKeyboardMarkup(new_keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.from_user.first_name
    # Register user if it doesn't exist
    rep_chess_db.register_user(update.message.from_user.id, name=name)
    # Greeting message and ReplyKeyboard options
    await update.message.reply_text(f"Привет, {name}!", reply_markup=main_menu_reply_keyboard())


async def go_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    await context.bot.send_message(update.effective_chat.id, "Вы в главном меню", reply_markup=main_menu_reply_keyboard())

start_handlers = [
    CommandHandler("start", start),
    CallbackQueryHandler(go_main_menu, "go_main_menu"),
]
