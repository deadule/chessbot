from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from databaseAPI import rep_chess_db


async def process_changing_public_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rep_ids = update.message.text.split(" ")
    if len(rep_ids) != 2:
        await update.message.reply_text("Прочитай формат ещё раз")
        await admin_change_public_id(update, context)
        return

    old_id, new_id = rep_ids

    if not old_id.isdigit() or not new_id.isdigit():
        await update.message.reply_text("Это определённо не ID")
        await admin_change_public_id(update, context)
        return

    old_id, new_id = int(old_id), int(new_id)
    if old_id < 1 or old_id >= 100000:
        await update.message.reply_text("Старый ID не попадает в диапазон")
        await admin_change_public_id(update, context)
        return

    if new_id < 1 or new_id >= 100000:
        await update.message.reply_text("Новый ID не попадает в диапазон")
        await admin_change_public_id(update, context)
        return

    is_free = rep_chess_db.update_user_public_id(old_id, new_id)
    if not is_free:
        await update.message.reply_text("Этот ID уже занят игроком, попробуйте другой")
        await admin_change_public_id(update, context)
        return

    context.user_data["text_state"] = None
    await update.message.reply_text("Запрос обработан. Проверьте, что все успешно.")


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
