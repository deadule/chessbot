from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from databaseAPI import rep_chess_db
from admin_main_menu import admin_main_menu, SUPER_ADMIN_ID

async def process_adding_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rep_id = update.message.text
    if not rep_id.isdigit():
        await update.message.reply_text("*Не похоже на ID\.\.\.*", parse_mode="MarkdownV2", disable_web_page_preview=True)
        await admin_add_new_admin(update, context)
        return

    rep_id = int(rep_id)
    if rep_id < 0 or rep_id > 1000000:
        await update.message.reply_text("Можно нормальный ID пожалуйста")
        await admin_add_new_admin(update, context)
        return

    new_admin_name = rep_chess_db.set_user_as_admin(rep_id)
    if new_admin_name is None:
        await update.message.reply_text("Юзера с данным ID не существует")
        await admin_add_new_admin(update, context)
        return

    if new_admin_name == "":
        await update.message.reply_text("Этот юзер уже является админом")
        await admin_add_new_admin(update, context)
        return

    context.user_data["text_state"] = None
    await update.message.reply_text(f"Вы назначили админом *{new_admin_name}*", parse_mode="Markdown")


async def admin_add_new_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    context.user_data["text_state"] = process_adding_admin
    await context.bot.send_message(update.effective_chat.id, "Введите rep ID юзера, которого вы хотите сделать админом:")


admin_add_new_admin_handler = CallbackQueryHandler(admin_add_new_admin, pattern="^admin_add_new_admin$")
