from urllib.parse import urlparse

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
)

from databaseAPI import rep_chess_db
from start import main_menu_reply_keyboard


async def delete_forwarded_timetable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rep_chess_db.remove_tournament(
        update.message.forward_from_chat.username,
        update.message.forward_from_message_id
    )
    context.user_data["forwarded_state"] = None
    await context.bot.send_message(update.effective_chat.id, "Запрос обработан. Проверьте, что все успешно.", reply_markup=main_menu_reply_keyboard())


async def delete_link_timetable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        parsed_url = urlparse(update.message.text)
    except ValueError:
        update.message.reply_text("Ты описание выше вообще читал? Что ты мне впариваешь?")
        return

    try:
        _, channel, message_id = parsed_url[2].split("/")
    except Exception:
        update.message.reply_text("Что-то странное ты прислал. Обратись к админу, если думаешь, что что-то не так")
        return

    if not message_id.isdigit():
        update.message.reply_text("Что-то странное ты прислал. Обратись к админу, если думаешь, что что-то не так")
        return

    rep_chess_db.remove_tournament(channel, int(message_id))
    await context.bot.send_message(update.effective_chat.id, "Запрос обработан. Проверьте, что все успешно.", reply_markup=main_menu_reply_keyboard())


async def admin_delete_timetable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    context.user_data["forwarded_state"] = delete_forwarded_timetable
    context.user_data["text_state"] = delete_link_timetable
    await context.bot.send_message(
        update.effective_chat.id,
        "Перешлите пост, который нужно удалить из расписания. "
        "Либо пришлите ссылку на пост. Нажмите на пост, \"Копировать ссылку\" и вставьте сюда. "
        "Если же вы уже удалили пост из канала, то я вам сочувсвую... "
        "Обращайтесь к админу, более адекватный способ пока не реализован."
    )


admin_delete_timetable_handlers = [
    CallbackQueryHandler(admin_delete_timetable, pattern="^admin_delete_timetable$")
]