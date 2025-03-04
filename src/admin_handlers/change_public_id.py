from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from databaseAPI import rep_chess_db


async def process_changing_public_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async def send_error_and_resume(update: Update, context: ContextTypes.DEFAULT_TYPE, err_msg):
        await context.bot.send_message(update.effective_chat.id, err_msg, parse_mode="markdown")
        await admin_change_public_id(update, context)

    rep_ids = update.message.text.split()
    if len(rep_ids) != 2:
        await send_error_and_resume(update, context, "Прочитай формат ещё раз")
        return

    old_id, new_id = rep_ids

    if not old_id.isdigit() or not new_id.isdigit():
        await send_error_and_resume(update, context, "Это определённо не ID")
        return

    try:
        old_id, new_id = int(old_id), int(new_id)
    except ValueError:
        await send_error_and_resume(update, context, "Воу, это что такое? Попробуйте ещё раз")
        return

    if old_id < 1 or old_id >= 100000:
        await send_error_and_resume(update, context, "Старый ID не попадает в диапазон")
        return

    if new_id < 1 or new_id >= 100000:
        await send_error_and_resume(update, context, "Новый ID не попадает в диапазон")
        return

    ret = rep_chess_db.update_user_public_id(old_id, new_id)
    if ret == None:
        await send_error_and_resume(update, context, "Пользователя с таким ID не существует, попробуйте ещё раз")
        return

    if ret == False:
        await send_error_and_resume(update, context, "Этот ID уже занят игроком, попробуйте другой")
        return

    context.user_data["text_state"] = None
    await update.message.reply_text(
        "ID успешно изменён!\n\n *ВАЖНО! Пользователь должен написать команду /start для обновления*",
        parse_mode="markdown"
    )


async def admin_change_public_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    context.user_data["text_state"] = process_changing_public_id
    await context.bot.send_message(
        update.effective_chat.id,
        "Введите *два* rep ID игрока через *пробел*: сначала старый ID, потом через пробел новый ID.\n"
         "ID должен быть в диапазоне от 1 до 99999",
        parse_mode="markdown"
    )


admin_change_public_id_handlers = [
    CallbackQueryHandler(admin_change_public_id, pattern="^admin_change_public_id$")
]
