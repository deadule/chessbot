from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton 
from telegram.ext import CallbackQueryHandler, ContextTypes

from databaseAPI import rep_chess_db
from util import construct_timetable_buttons
from admin_main_menu import admin_inline_keyboard


def new_registered_users_keyboard(tournament_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Показать только новых", callback_data=f"show_new_registered_users:{tournament_id}")]
    ])


async def show_new_registered_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, tournament_id = query.data.split(":")

    new_users = context.bot_data[f"tournament_{tournament_id}_list"].removeprefix(context.bot_data[f"tournament_{tournament_id}_list_prev"])
    if not new_users:
        await context.bot.send_message(update.effective_chat.id, "Нет новых игроков, можете посмотреть предыдущий список")
        return
    await context.bot.send_message(update.effective_chat.id, new_users)


async def admin_ask_show_registered(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await show_registered_users(update, context, next(iter(context.bot_data["tournaments"].values()))["tournament_id"])
        return

    message, buttons = construct_timetable_buttons(context.bot_data["tournaments"].values(), "show_reg_timetable")

    message = "*Выберите турнир, для которого вы хотите посмотреть список:*\n" + message

    await context.bot.send_message(
        update.effective_chat.id,
        message,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="MarkdownV2"
    )


async def admin_process_reg_tournament_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, tournament_id, _, _ = query.data.split(":")

    await show_registered_users(update, context, tournament_id)


async def show_registered_users(update: Update, context: ContextTypes.DEFAULT_TYPE, tournament_id: int):
    registered_list = ""
    registered_users = rep_chess_db.get_registered_users(tournament_id)
    for i, user_on_tournament in enumerate(registered_users, 1):
        registered_list += f"{i}, {user_on_tournament[3]}, , {user_on_tournament[4]}, {user_on_tournament[8]}\n"

    if not registered_list:
        await context.bot.send_message(update.effective_chat.id, "Упс... Ни одного участника не зарегистрировалось.")
        return

    tournament_key_list = f"tournament_{tournament_id}_list"
    tournament_key_prev = f"tournament_{tournament_id}_list_prev"
    if tournament_key_prev not in context.bot_data:
        context.bot_data[tournament_key_prev] = ""
    else:
        context.bot_data[tournament_key_prev] = context.bot_data[tournament_key_list]
    context.bot_data[tournament_key_list] = registered_list

    await context.bot.send_message(
        update.effective_chat.id,
        registered_list,
        reply_markup=new_registered_users_keyboard(tournament_id)
    )


admin_show_registered_handlers = [
    CallbackQueryHandler(admin_ask_show_registered, pattern="^admin_show_registered$"),
    CallbackQueryHandler(admin_process_reg_tournament_id, pattern="^show_reg_timetable:*"),
    CallbackQueryHandler(show_new_registered_users, pattern="^show_new_registered_users:*")
]
