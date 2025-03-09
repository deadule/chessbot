from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton 
from telegram.ext import CallbackQueryHandler, ContextTypes

from databaseAPI import rep_chess_db
from start import active_tournament
from admin_main_menu import admin_inline_keyboard


new_registered_users_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("Показать только новых", callback_data="show_new_registered_users")]
])


async def show_new_registered_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    new_users = context.bot_data[f"tournament_{active_tournament["tournament_id"]}"].removeprefix(context.bot_data[f"tournament_{active_tournament["tournament_id"]}_prev"])
    print(context.bot_data[f"tournament_{active_tournament["tournament_id"]}_nicknames"])
    print(context.bot_data[f"tournament_{active_tournament["tournament_id"]}_nicknames_users"])
    print("\n\n\n\n\n\n\n\n")
    if not new_users:
        await context.bot.send_message(update.effective_chat.id, "Нет новых игроков, можете посмотреть предыдущий список")
        return
    await context.bot.send_message(update.effective_chat.id, new_users)


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
    registered_users = rep_chess_db.get_registered_users(active_tournament["tournament_id"])
    for user_on_tournament in registered_users:
        registered_list += f"{user_on_tournament[3]}, , {user_on_tournament[4]}, {user_on_tournament[8]}\n"

    if not registered_list:
        registered_list = "Упс... Ни одного участника не зарегистрировалось."
        return

    tournament_key = f"tournament_{active_tournament["tournament_id"]}"
    tournament_key_prev = f"tournament_{active_tournament["tournament_id"]}_prev"
    if tournament_key_prev not in context.bot_data:
        context.bot_data[tournament_key_prev] = ""
    else:
        context.bot_data[tournament_key_prev] = context.bot_data[tournament_key]
    context.bot_data[tournament_key] = registered_list

    await context.bot.send_message(update.effective_chat.id, f"Человек зарегистрировалось: {len(registered_users)}.")
    await context.bot.send_message(
        update.effective_chat.id,
        registered_list,
        reply_markup=new_registered_users_keyboard
    )


admin_show_registered_handlers = [
    CallbackQueryHandler(admin_show_registered, pattern="^admin_show_registered$"),
    CallbackQueryHandler(show_new_registered_users, pattern="^show_new_registered_users$")
]
