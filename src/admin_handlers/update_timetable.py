from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from timetable_handlers import process_forwarded_post


async def admin_update_timetable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    context.user_data["forwarded_state"] = process_forwarded_post
    await context.bot.send_message(
        update.effective_chat.id,
        "Перешлите пост, который нужно добавить в расписание."
    )


admin_update_timetable_handler = CallbackQueryHandler(admin_update_timetable, pattern="^admin_update_timetable$")
