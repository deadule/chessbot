from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackQueryHandler, ContextTypes

import start
from databaseAPI import rep_chess_db
from show_registered import admin_show_registered
from admin_main_menu import admin_inline_keyboard


close_registration_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("Закрыть регистрацию", callback_data="admin_close_registration_confirmed")],
    [InlineKeyboardButton("<< Назад", callback_data="go_main_menu")]
])


async def close_registration_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    start.active_tournament["active"] = False

    await context.bot.send_message(
        update.effective_chat.id,
        "Регистрация на турнир закрыта.\nСкопируйте этот список и вставьте в swisssystem.org:"
    )
    await admin_show_registered(update, context)
    rep_chess_db.close_registration(start.active_tournament["tournament_id"])


async def admin_close_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    if not start.active_tournament["active"]:
        await context.bot.send_message(
            update.effective_chat.id,
            "Сейчас нет открытой регистрации на турнир!",
            reply_markup=admin_inline_keyboard
        )
        return

    await context.bot.send_message(
        update.effective_chat.id,
        f"Вы уверены, что хотите закрыть регистрацию на турнир *{start.active_tournament["summary"]}*?",
        reply_markup=close_registration_keyboard,
        parse_mode="markdown"
    )


admin_close_registration_handlers = [
    CallbackQueryHandler(admin_close_registration, pattern="^admin_close_registration$"),
    CallbackQueryHandler(close_registration_confirmed, pattern="^admin_close_registration_confirmed*")
]
