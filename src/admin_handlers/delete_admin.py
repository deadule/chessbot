from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from databaseAPI import rep_chess_db
from admin_main_menu import SUPER_ADMIN_ID, admin_main_menu


async def process_deleting_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rep_id = update.message.text
    if not rep_id.isdigit():
        await update.message.reply_text("Не похоже на ID...")
        await delete_admin(update, context)
        return

    rep_id = int(rep_id)
    if rep_id < 0 or rep_id > 1000000:
        await update.message.reply_text("Можно нормальный ID пожалуйста")
        await delete_admin(update, context)
        return

    old_admin_name = rep_chess_db.remove_user_from_admins(rep_id)
    if old_admin_name is None:
        await update.message.reply_text("Юзера с данным ID не существует")
        await delete_admin(update, context)
        return

    if old_admin_name == "":
        await update.message.reply_text("Этот юзер не является админом")
        await delete_admin(update, context)
        return

    context.user_data["text_state"] = None
    await update.message.reply_text(f"Вы удалили из админов *{old_admin_name}*", parse_mode="Markdown")


async def delete_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        telegram_id = query.from_user.id
        await query.answer()
    else:
        telegram_id = update.message.from_user.id

    if not telegram_id == SUPER_ADMIN_ID:
        await context.bot.send_message(update.effective_chat.id, "Только Бог может это делать.")
        await admin_main_menu(update, context)
        return

    context.user_data["text_state"] = process_deleting_admin
    await context.bot.send_message(update.effective_chat.id, "Введите rep ID юзера, которого вы хотите удалить из админов:")


admin_delete_admin_handlers = [
    CallbackQueryHandler(delete_admin, "^admin_delete_admin$")
]
