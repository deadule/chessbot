from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from databaseAPI import rep_chess_db
from start import active_tournament
from admin_main_menu import admin_inline_keyboard


async def admin_show_registered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    if not active_tournament["tournament_id"] or not rep_chess_db.get_tournament_on_id(active_tournament["tournament_id"])["registration"]:
        await context.bot.send_message(
            update.effective_chat.id,
            "Сейчас нет открытой регистрации на турнир!",
            reply_markup=admin_inline_keyboard
        )
        return

    registered_list = ""
    for user_on_tournament in rep_chess_db.get_registered_users(active_tournament["tournament_id"]):
        registered_list += f"{user_on_tournament[3]}, , {user_on_tournament[4]}, {user_on_tournament[8]}\n"

    if not registered_list:
        registered_list = "Упс... Ни одного участника не зарегистрировалось."
    await context.bot.send_message(
        update.effective_chat.id,
        registered_list
    )


admin_show_registered_handlers = [
    CallbackQueryHandler(admin_show_registered, pattern="^admin_show_registered$"),
]
