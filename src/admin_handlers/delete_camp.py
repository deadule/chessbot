from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

import start


async def add_camp_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        await context.bot.send_message(update.effective_chat.id, "Ниче не понял, попробуйте ещё раз.")
        return
    if update.message.text != "Удалить лагерь":
        await context.bot.send_message(update.effective_chat.id, "Ниче не понял, попробуйте ещё раз.")
        return

    start.camp_data["active"] = False
    context.user_data["forwarded_state"] = None
    await context.bot.send_message(update.effective_chat.id, "Запрос обработан. Проверьте, что все успешно.", reply_markup=start.main_menu_reply_keyboard())


async def admin_update_timetable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    context.user_data["text_state"] = add_camp_post
    await context.bot.send_message(
        update.effective_chat.id,
        "Вы уверены, что хотите удалить кнопку \"лагерь\"? Напишите \"Удалить лагерь\" для подтверждения."
    )


admin_delete_camp_handler = CallbackQueryHandler(admin_update_timetable, pattern="^admin_delete_camp$")
