import datetime

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackQueryHandler, ContextTypes

import start
from databaseAPI import rep_chess_db
from util import construct_timetable_buttons


async def admin_open_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    today = datetime.date.today()
    today_start = datetime.datetime(today.year, today.month, today.day, 0, 0, 0)
    today_end = datetime.datetime(today.year, today.month, today.day, 23, 59, 59)
    tournaments = rep_chess_db.get_tournaments(today_start, today_end)
    message, buttons = construct_timetable_buttons(tournaments, "open_registration")
    message = "🌟  *_Сегодняшние Турниры:_*\n" + message
    buttons.append([InlineKeyboardButton("<< Назад", callback_data="go_main_menu")])
    await context.bot.send_message(
        update.effective_chat.id,
        message,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="MarkdownV2"
    )


async def open_tournament_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, tournament_id, _, _ = query.data.split(":")

    if "tournaments" not in context.bot_data:
        context.bot_data["tournaments"] = dict()

    tournament_key = f"tournament_{tournament_id}"
    if tournament_key in context.bot_data["tournaments"]:
        await context.bot.send_message(
            update.effective_chat.id,
            "На этот турнир уже открыта регистрация!"
        )
        return

    rep_chess_db.open_registration(tournament_id)
    tournament = rep_chess_db.get_tournament_on_id(tournament_id)

    context.bot_data["tournaments"][tournament_key] = tournament
    tournament_nicknames_key = f"tournament_{tournament["tournament_id"]}_nicknames"
    if tournament_nicknames_key not in context.bot_data:
        context.bot_data[tournament_nicknames_key] = set()
        context.bot_data[tournament_nicknames_key + "_users"] = dict()
    await context.bot.send_message(
        update.effective_chat.id,
        f"Регистрация на турнир *{tournament["summary"]}* открыта\! Проверьте, что кнопка *\"⚔ Записаться на турнир\"* работает",
        parse_mode="MarkdownV2",
        reply_markup=start.main_menu_reply_keyboard(context)
    )


admin_open_registration_handlers = [
    CallbackQueryHandler(admin_open_registration, pattern="^admin_open_registration$"),
    CallbackQueryHandler(open_tournament_registration, pattern="^open_registration:*")
]
