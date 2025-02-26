from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import MessageHandler, CallbackQueryHandler, filters, ContextTypes

from start import main_menu_reply_keyboard, active_tournament
from databaseAPI import rep_chess_db
from util import check_string


def construct_nickname_keyboard(nickname) -> InlineKeyboardMarkup:
    if not nickname:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🚫 <не задан>", callback_data="permanent_nickname:")],
            [InlineKeyboardButton(f"📝 Ввести ник", callback_data="temporarily_nickname")],
            [InlineKeyboardButton(f"<< Назад", callback_data="go_main_menu")],
        ])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ {nickname}", callback_data=f"permanent_nickname:{nickname}")],
        [InlineKeyboardButton(f"📝 Ввести ник", callback_data="temporarily_nickname")],
        [InlineKeyboardButton(f"<< Назад", callback_data="go_main_menu")],
    ])


async def process_permanent_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, nickname = query.data.split(":")
    if not nickname:
        await context.bot.send_message(
            update.effective_chat.id,
            "У вас не задан постоянный ник! Для его добавления перейдите в \"👤 *Профиль*\"",
            parse_mode="markdown"
        )
        await ask_about_registration(update, context)
        return
    await context.bot.send_message(
        update.effective_chat.id,
        "Вы успешно зарегистрированы. Удачи на турнире!",
        reply_markup=main_menu_reply_keyboard()
    )

    games_played = context.user_data["user_db_data"]["games_played"]
    if games_played < 20:
        k_factor = 90 - games_played * 3
    else:
        k_factor = 30
    rep_chess_db.add_user_on_tournament(
        context.user_data["user_db_data"]["user_id"],
        active_tournament["tournament_id"],
        nickname,
        context.user_data["user_db_data"]["rep_rating"],
        k_factor
    )


async def reading_temp_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nickname = update.message.text
    if len(nickname) > 100:
        await update.message.reply_text("Слишком длинный ник. Попробуйте покороче.")
        await process_temp_nickname(update, context)
        return

    if not check_string(nickname):
        await context.bot.send_message(update.effective_chat.id, "Недопустимые символы в нике! Разрешены только буквы, цифры, пробел, -, !, ?")
        await process_temp_nickname(update, context)
        return

    context.user_data["text_state"] = None
    await context.bot.send_message(
        update.effective_chat.id,
        "Вы успешно зарегистрированы. Удачи на турнире!",
        reply_markup=main_menu_reply_keyboard()
    )

    games_played = context.user_data["user_db_data"]["games_played"]
    if games_played < 20:
        k_factor = 90 - games_played * 3
    else:
        k_factor = 30
    rep_chess_db.add_user_on_tournament(
        context.user_data["user_db_data"]["user_id"],
        active_tournament["tournament_id"],
        nickname,
        context.user_data["user_db_data"]["rep_rating"],
        k_factor
    )


async def process_temp_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    context.user_data["text_state"] = reading_temp_nickname
    await context.bot.send_message(update.effective_chat.id, "*Введите ваш ник на этот турнир:*", parse_mode="markdown")


async def ask_about_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not active_tournament["active"]:
        await context.bot.send_message(
            update.effective_chat.id,
            "Сейчас нет активной регистрации! Регистрация открывается за несколько минут до начала турнира.\n\n"
            "Если вы не успели записаться, подойдите к организатору.",
            reply_markup=main_menu_reply_keyboard()
        )
        return

    if update.message:
        telegram_id = update.message.from_user.id
    elif update.callback_query:
        telegram_id = update.callback_query.from_user.id
    if "user_db_data" not in context.user_data:
        context.user_data["user_db_data"] = rep_chess_db.get_user_on_telegram_id(telegram_id)

    nickname = context.user_data["user_db_data"]["nickname"]
    await context.bot.send_message(
        update.effective_chat.id,
        f"Вы хотите записаться на турнир\n{active_tournament["date_time"]} "
        f" *{active_tournament["summary"]}*\n\nВы уверены в этом?\n\n"
        "Тогда выберите свой постоянный ник или введите одноразовый:",
        reply_markup=construct_nickname_keyboard(nickname),
        parse_mode="markdown"
    )


registration_callback_handlers = [
    MessageHandler(filters.Regex("^⚔ Записаться на турнир$"), ask_about_registration),
    CallbackQueryHandler(process_permanent_nickname, "^permanent_nickname:"),
    CallbackQueryHandler(process_temp_nickname, "^temporarily_nickname$"),
]
