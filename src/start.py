from telegram import ReplyKeyboardMarkup, Update, KeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

from databaseAPI import rep_chess_db


# Save it in global except database because it is faster.
# To show camp button set "active" field to True.
# TODO: Возможно, перенести эти данные в context.bot_data - данные, общие для бота
camp_data = {
    "active": False,
    "channel": None,
    "message_id": None
}

active_tournament = {
    "active": False,
    "tournament_id": None,
    "summary": None,
    "date_time": None
}


reg_main_menu_reply_keyboard = ReplyKeyboardMarkup([
        [KeyboardButton("📅  Расписание")],
        [KeyboardButton("👤 Профиль")],
        [KeyboardButton("⚔ Записаться на турнир")],
    ],
    resize_keyboard=True
)


reg_camp_main_menu_reply_keyboard = ReplyKeyboardMarkup([
        [KeyboardButton("📅  Расписание")],
        [KeyboardButton("👤 Профиль"), KeyboardButton("🏕 Лагерь")],
        [KeyboardButton("⚔ Записаться на турнир")],
    ],
    resize_keyboard=True
)


def main_menu_reply_keyboard():
    if camp_data["active"]:
        return reg_camp_main_menu_reply_keyboard
    return reg_main_menu_reply_keyboard


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.from_user.first_name
    # Register user if it doesn't exist
    rep_chess_db.register_user(update.message.from_user.id, name=name)
    if "messages_to_delete" in context.user_data:
        context.user_data["messages_to_delete"] = []
    # Greeting message and ReplyKeyboard options
    await update.message.reply_text(f"Привет, {name}!", reply_markup=main_menu_reply_keyboard())


async def go_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    await context.bot.send_message(
        update.effective_chat.id,
        "_Вы в главном меню_",
        reply_markup=main_menu_reply_keyboard(),
        parse_mode="markdown"
    )

start_handlers = [
    CommandHandler("start", start),
    CallbackQueryHandler(go_main_menu, "go_main_menu"),
]
