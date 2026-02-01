from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackQueryHandler, ContextTypes

from databaseAPI import rep_chess_db
from .show_registered import show_registered_users
from .admin_main_menu import admin_inline_keyboard
from util import construct_timetable_buttons


def close_registration_keyboard(tournament_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Закрыть регистрацию", callback_data=f"admin_close_registration_confirmed:{tournament_id}")],
        [InlineKeyboardButton("<< Назад", callback_data="go_main_menu")]
    ])


async def close_registration_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, tournament_id = query.data.split(":")

    del context.bot_data["tournaments"][f"tournament_{tournament_id}"]
    await context.bot.send_message(
        update.effective_chat.id,
        "Регистрация на турнир закрыта.\nСкопируйте этот список и вставьте в swisssystem.org:"
    )
    await show_registered_users(update, context, tournament_id)
    rep_chess_db.close_registration(tournament_id)


async def ask_closing_registration(update: Update, context: ContextTypes.DEFAULT_TYPE, tournament: dict):
    await context.bot.send_message(
        update.effective_chat.id,
        f"Вы уверены, что хотите закрыть регистрацию на турнир *{tournament["summary"]}*?",
        reply_markup=close_registration_keyboard(tournament["tournament_id"]),
        parse_mode="MarkdownV2"
    )


async def admin_process_closing_tournament_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, tournament_id, _, _ = query.data.split(":")
    await ask_closing_registration(update, context, context.bot_data["tournaments"][f"tournament_{tournament_id}"])


async def admin_close_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    if not context.bot_data["tournaments"]:
        await context.bot.send_message(
            update.effective_chat.id,
            "Сейчас нет открытой регистрации на турнир!",
            reply_markup=admin_inline_keyboard
        )
        return

    if len(context.bot_data["tournaments"]) == 1:
        tournament = next(iter(context.bot_data["tournaments"].values()))
        await ask_closing_registration(update, context, tournament)
        return

    message, buttons = construct_timetable_buttons(context.bot_data["tournaments"].values(), "close_reg_timetable")

    message = "*Выберите, регистрацию на какой турнир вы хотите закрыть:*\n\n" + message

    await context.bot.send_message(
        update.effective_chat.id,
        message,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="MarkdownV2"
    )


admin_close_registration_handlers = [
    CallbackQueryHandler(admin_close_registration, pattern="^admin_close_registration$"),
    CallbackQueryHandler(admin_process_closing_tournament_id, pattern="^close_reg_timetable:*"),
    CallbackQueryHandler(close_registration_confirmed, pattern="^admin_close_registration_confirmed:*")
]
