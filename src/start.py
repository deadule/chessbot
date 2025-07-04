from telegram import ReplyKeyboardMarkup, Update, KeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

from databaseAPI import rep_chess_db


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


def main_menu_reply_keyboard(context: ContextTypes.DEFAULT_TYPE):
    if context.bot_data["camp_data"]["active"]:
        return reg_camp_main_menu_reply_keyboard
    return reg_main_menu_reply_keyboard


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.from_user.first_name
    # Register user if it doesn't exist
    rep_chess_db.register_user(update.message.from_user.id, name=name, city_id=1)
    if "messages_to_delete" in context.user_data:
        context.user_data["messages_to_delete"] = []
    # Greeting message and ReplyKeyboard options
    await update.message.reply_text(f"Привет, {name}!", reply_markup=main_menu_reply_keyboard(context))


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
