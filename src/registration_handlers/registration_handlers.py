from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import MessageHandler, CallbackQueryHandler, filters, ContextTypes

from start import main_menu_reply_keyboard
from databaseAPI import rep_chess_db
from util import check_string, construct_timetable_buttons


def construct_nickname_keyboard(nickname) -> InlineKeyboardMarkup:
    if not nickname:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🚫 <постоянный не задан>", callback_data="permanent_nickname:")],
            [InlineKeyboardButton(f"📝 Ввести ник", callback_data="temporarily_nickname")],
            [InlineKeyboardButton(f"<< Назад", callback_data="go_main_menu")],
        ])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ {nickname}", callback_data=f"permanent_nickname:{nickname}")],
        [InlineKeyboardButton(f"📝 Ввести ник", callback_data="temporarily_nickname")],
        [InlineKeyboardButton(f"<< Назад", callback_data="go_main_menu")],
    ])


async def update_and_save_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE, nickname: str):
    tournament_nicknames_key = f"tournament_{context.user_data["active_tournament"]["tournament_id"]}_nicknames"
    tournament_nicknames_users_key = tournament_nicknames_key + "_users"
    user_id = context.user_data["user_db_data"]["user_id"]
    if user_id in context.bot_data[tournament_nicknames_users_key]:
        context.bot_data[tournament_nicknames_key].remove(context.bot_data[tournament_nicknames_users_key][user_id])
    context.bot_data[tournament_nicknames_users_key][user_id] = nickname
    context.bot_data[tournament_nicknames_key].add(nickname)

    await context.bot.send_message(
        update.effective_chat.id,
        "Вы успешно зарегистрированы. Удачи на турнире!",
        reply_markup=main_menu_reply_keyboard(context)
    )

    games_played = context.user_data["user_db_data"]["games_played"]
    if games_played < 20:
        k_factor = 90 - games_played * 3
    else:
        k_factor = 30
    rep_chess_db.add_user_on_tournament(
        user_id,
        context.user_data["active_tournament"]["tournament_id"],
        nickname,
        context.user_data["user_db_data"]["rep_rating"],
        k_factor
    )


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

    if nickname in context.bot_data[f"tournament_{context.user_data["active_tournament"]["tournament_id"]}_nicknames"]:
        await context.bot.send_message(update.effective_chat.id, "Увы, такой ник уже используется в этом турнире! Попробуйте другой")
        await ask_about_registration(update, context)
        return
    await update_and_save_nickname(update, context, nickname)


async def reading_temp_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async def send_error_and_resume(update: Update, context: ContextTypes.DEFAULT_TYPE, err_msg: str):
        await context.bot.send_message(update.effective_chat.id, err_msg, parse_mode="markdown")
        await process_temp_nickname(update, context)

    if not update.message:
        # It is a strange update, maybe editing some message for God just know what reasons. Ignore it.
        return

    nickname = update.message.text
    if len(nickname) > 100:
        await send_error_and_resume(update, context, "*Слишком длинный ник. Попробуйте покороче.*")
        return

    if not check_string(nickname):
        await send_error_and_resume(update, context, "*Недопустимые символы в нике! Разрешены только буквы, цифры, пробел, -, !, ?*")
        return

    context.user_data["text_state"] = None

    if nickname in context.bot_data[f"tournament_{context.user_data["active_tournament"]["tournament_id"]}_nicknames"]:
        await send_error_and_resume(update, context, "*Увы, такой ник уже используется в этом турнире! Попробуйте другой*")
        return
    await update_and_save_nickname(update, context, nickname)


async def process_temp_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    context.user_data["text_state"] = reading_temp_nickname
    await context.bot.send_message(update.effective_chat.id, "*Введите ваш ник на этот турнир:*", parse_mode="markdown")


async def choose_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE, tournament: dict):
    nickname = context.user_data["user_db_data"]["nickname"]
    await context.bot.send_message(
        update.effective_chat.id,
        f"Вы хотите записаться на турнир\n__{tournament["date_time"].strftime("%d\\.%m %H:%M")}__ "
        f" *{tournament["summary"]}*\n\nВы уверены в этом?\n\n"
        "Тогда выберите свой постоянный ник или введите одноразовый:",
        reply_markup=construct_nickname_keyboard(nickname),
        parse_mode="MarkdownV2"
    )


async def choose_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, tournament_id, _, _ = query.data.split(":")

    tournament = context.bot_data["tournaments"][f"tournament_{tournament_id}"]
    context.user_data["active_tournament"] = tournament
    await choose_nickname(update, context, tournament)


async def ask_about_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        telegram_id = update.message.from_user.id
    else:
        telegram_id = update.callback_query.from_user.id
    context.user_data["user_db_data"] = rep_chess_db.get_user_on_telegram_id(telegram_id)
    rep_chess_db.update_user_last_contact(telegram_id)
    if "tournaments" not in context.bot_data or len(context.bot_data["tournaments"]) < 1:
        await context.bot.send_message(
            update.effective_chat.id,
            "*Сейчас нет открытой регистрации!*\n\nРегистрация открывается за несколько минут до начала турнира.\n"
            "Если вы не успели записаться, подойдите к организатору.",
            reply_markup=main_menu_reply_keyboard(context),
            parse_mode="markdown"
        )
        return

    if "user_db_data" not in context.user_data:
        context.user_data["user_db_data"] = rep_chess_db.get_user_on_telegram_id(telegram_id)

    if len(context.bot_data["tournaments"]) == 1:
        tournament = next(iter(context.bot_data["tournaments"].values()))
        context.user_data["active_tournament"] = tournament
        await choose_nickname(update, context, tournament)
        return

    message, buttons = construct_timetable_buttons(list(context.bot_data["tournaments"].values()), "registration_tournament")
    message = "*Выберите турнир, на который вы хотите зарегистрироваться*\n" + message
    buttons.append([InlineKeyboardButton("<< Назад", callback_data="go_main_menu")])
    await context.bot.send_message(
        update.effective_chat.id,
        message,
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


registration_callback_handlers = [
    MessageHandler(filters.Regex("^⚔ Записаться на турнир$"), ask_about_registration),
    CallbackQueryHandler(process_permanent_nickname, "^permanent_nickname:"),
    CallbackQueryHandler(choose_tournament, "^registration_tournament:"),
    CallbackQueryHandler(process_temp_nickname, "^temporarily_nickname$"),
]
