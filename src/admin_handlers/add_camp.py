from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

import start


async def add_camp_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.api_kwargs:
        start.camp_data["channel"] = update.message.api_kwargs["forward_from_chat"]["username"]
        start.camp_data["message_id"] = update.message.api_kwargs["forward_from_message_id"]
    else:
        start.camp_data["channel"] = update.message.forward_from_chat.username
        start.camp_data["message_id"] = update.message.forward_from_message_id
    start.camp_data["active"] = True

    context.user_data["forwarded_state"] = None
    await context.bot.send_message(update.effective_chat.id, "Запрос обработан. Проверьте, что все успешно.", reply_markup=start.main_menu_reply_keyboard())


async def admin_update_timetable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    context.user_data["forwarded_state"] = add_camp_post
    await context.bot.send_message(
        update.effective_chat.id,
        "Перешлите пост, который нужно привязать к кнопке \"лагерь\"."
    )


admin_add_camp_handler = CallbackQueryHandler(admin_update_timetable, pattern="^admin_add_camp$")
