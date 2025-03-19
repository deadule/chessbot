from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from start import main_menu_reply_keyboard


async def add_camp_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "camp_data" not in context.bot_data:
        context.bot_data["camp_data"] = dict()
    if update.message.api_kwargs:
        context.bot_data["camp_data"]["channel"] = update.message.api_kwargs["forward_from_chat"]["username"]
        context.bot_data["camp_data"]["message_id"] = update.message.api_kwargs["forward_from_message_id"]
    else:
        context.bot_data["camp_data"]["channel"] = update.message.forward_from_chat.username
        context.bot_data["camp_data"]["message_id"] = update.message.forward_from_message_id
    context.bot_data["camp_data"]["active"] = True

    context.user_data["forwarded_state"] = None
    await context.bot.send_message(update.effective_chat.id, "Запрос обработан. Проверьте, что все успешно.", reply_markup=main_menu_reply_keyboard(context))


async def admin_update_timetable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    context.user_data["forwarded_state"] = add_camp_post
    await context.bot.send_message(
        update.effective_chat.id,
        "Перешлите пост, который нужно привязать к кнопке \"лагерь\"."
    )


admin_add_camp_handlers = [
    CallbackQueryHandler(admin_update_timetable, pattern="^admin_add_camp$")
]
