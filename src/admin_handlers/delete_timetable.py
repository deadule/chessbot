from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
)

from databaseAPI import rep_chess_db
from start import main_menu_reply_keyboard


async def delete_timetable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rep_chess_db.remove_tournament(
        update.message.forward_from_chat.username,
        update.message.forward_from_message_id
    )
    context.user_data["forwarded_state"] = None
    await context.bot.send_message(update.effective_chat.id, "Запрос обработан.", reply_markup=main_menu_reply_keyboard)


async def admin_delete_timetable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    context.user_data["forwarded_state"] = delete_timetable
    await context.bot.send_message(
        update.effective_chat.id,
        "Перешлите пост, который нужно удалить из расписания. "
        "Если же вы уже удалили пост из канала, то я вам сочувсвую... "
        "Обращайтесь к админу, более адекватный способ пока не реализован."
    )


admin_delete_timetable_handler = CallbackQueryHandler(admin_delete_timetable, pattern="^admin_delete_timetable$")
