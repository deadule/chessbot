from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackQueryHandler, ContextTypes

from databaseAPI import rep_chess_db
from .admin_main_menu import admin_inline_keyboard
from util import construct_timetable_buttons, check_string


def close_registration_keyboard(tournament_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Закрыть регистрацию", callback_data=f"admin_close_registration_confirmed:{tournament_id}")],
        [InlineKeyboardButton("<< Назад", callback_data="go_main_menu")]
    ])


async def process_deleted_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async def send_error_and_resume(update: Update, context: ContextTypes.DEFAULT_TYPE, err_msg: str):
        await context.bot.send_message(update.effective_chat.id, err_msg, parse_mode="markdown")
        await admin_delete_user_from_tournament(update, context)

    nickname = update.message.text
    context.user_data["text_state"] = None

    if not nickname:
        await send_error_and_resume(update, context, "*Вы прислали что-то странное. Попробуйте ещё раз.*")
        return
    # Too long nickname
    if len(nickname) > 100:
        await send_error_and_resume(update, context, "*Слишком длинный ник. Попробуйте покороче.*")
        return

    if not check_string(nickname):
        await send_error_and_resume(update, context, "*Недопустимые символы в нике! Разрешены только буквы, цифры, пробел, -, !, ?*")
        return

    tournament_id = context.user_data["admin_delete_user_from_tournament_id"]
    user_on_tournament = rep_chess_db.get_user_on_tournament_on_nickname(tournament_id, nickname)
    if not user_on_tournament:
        await send_error_and_resume(update, context, "*Такого ника нет в списке зарегистрировавшихся! Вы точно ввели ник верно?*")
        return

    rep_chess_db.delete_user_on_tournament(tournament_id, nickname)
    context.bot_data[f"tournament_{tournament_id}_nicknames"].remove(nickname)
    del context.bot_data[f"tournament_{tournament_id}_nicknames_users"][user_on_tournament["user_id"]]
    filtered = [s for s in context.bot_data[f"tournament_{tournament_id}_list"].split("\n") if nickname not in s]
    context.bot_data[f"tournament_{tournament_id}_list"] = "\n".join(filtered) + "\n"
    await context.bot.send_message(
        update.effective_chat.id,
        "Запрос успешно обработан. Проверьте новый список."
    )


async def ask_delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE, tournament: dict):
    context.user_data["admin_delete_user_from_tournament_id"] = tournament["tournament_id"]
    context.user_data["text_state"] = process_deleted_nickname
    await context.bot.send_message(
        update.effective_chat.id,
        f"Введите ник игрока, которого вы хотите удалить с турнира *{tournament["summary"]}*",
        parse_mode="MarkdownV2"
    )


async def admin_process_delete_user_timetable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, tournament_id, _, _ = query.data.split(":")
    await ask_delete_user(update, context, context.bot_data["tournaments"][f"tournament_{tournament_id}"])


async def admin_delete_user_from_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await ask_delete_user(update, context, tournament)
        return

    message, buttons = construct_timetable_buttons(context.bot_data["tournaments"].values(), "delete_user_timetable")

    message = "*Выберите, с какого турнира вы хотите удалить участника:*\n\n" + message

    await context.bot.send_message(
        update.effective_chat.id,
        message,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="MarkdownV2"
    )


admin_delete_user_from_tournament_handlers = [
    CallbackQueryHandler(admin_delete_user_from_tournament, pattern="^admin_delete_user_from_tournament$"),
    CallbackQueryHandler(admin_process_delete_user_timetable, pattern="^delete_user_timetable:*"),
]
