import datetime

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackQueryHandler, ContextTypes

import start
from databaseAPI import rep_chess_db
from timetable_handlers import DIGITS_EMOJI


def construct_short_timetable(tournaments: list[tuple]) -> tuple[str, InlineKeyboardMarkup]:
    """
    Return string and InlineKeyboardMarkup representing timetable of tournaments.
    """
    result_str = "🌟  *_Сегодняшние Турниры:_*\n"
    result_markup = []

    for i, tournament in enumerate(tournaments, 1):
        if i % 5 == 1:
            result_markup.append([])
        text_number = DIGITS_EMOJI[i//10] if i >= 10 else ""
        text_number += DIGITS_EMOJI[i%10]
        result_str += f"\n{text_number}  __{tournament[5].strftime("%d\\.%m %H:%M")}__\n   *{tournament[4]}*\n"

        result_markup[-1].append(InlineKeyboardButton(text_number, callback_data=f"open_registration:{tournament[0]}"))
    result_markup.append([InlineKeyboardButton("<< Назад", callback_data="go_main_menu")])

    return result_str, InlineKeyboardMarkup(result_markup)


async def admin_open_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    today = datetime.date.today()
    today_start = datetime.datetime(today.year, today.month, today.day, 0, 0, 0)
    today_end = datetime.datetime(today.year, today.month, today.day, 23, 59, 59)
    tournaments = rep_chess_db.get_tournaments(today_start, today_end)
    message, keyboard = construct_short_timetable(tournaments)
    await context.bot.send_message(update.effective_chat.id, message, reply_markup=keyboard, parse_mode="MarkdownV2")


async def open_tournament_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, tournament_id = query.data.split(":")
    rep_chess_db.open_registration(tournament_id)
    tournament = rep_chess_db.get_tournament_on_id(tournament_id)

    if start.active_tournament["active"]:
        await context.bot.send_message(
            update.effective_chat.id,
            "Уже есть активная регистрация на турнир! Завершите сначала регистрацию на предыдущий:\n"
            f"{start.active_tournament["date_time"]} - *{start.active_tournament["summary"]}*"
        )
        return

    start.active_tournament["tournament_id"] = tournament["tournament_id"]
    start.active_tournament["summary"] = tournament["summary"]
    start.active_tournament["date_time"] = tournament["date_time"]
    start.active_tournament["active"] = True
    tournament_nicknames_key = f"tournament_{tournament["tournament_id"]}_nicknames"
    if tournament_nicknames_key not in context.bot_data:
        context.bot_data[tournament_nicknames_key] = set()
        context.bot_data[tournament_nicknames_key + "_users"] = dict()
    await context.bot.send_message(
        update.effective_chat.id,
        f"Регистрация на турнир *{start.active_tournament["summary"]}* открыта! Проверьте, что кнопка *\"⚔ Записаться на турнир\"* работает",
        parse_mode="markdown",
        reply_markup=start.main_menu_reply_keyboard(context)
    )


admin_open_registration_handlers = [
    CallbackQueryHandler(admin_open_registration, pattern="^admin_open_registration$"),
    CallbackQueryHandler(open_tournament_registration, pattern="^open_registration:*")
]
