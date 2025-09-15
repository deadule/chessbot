from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from databaseAPI import rep_chess_db
from .main_menu_handler import main_menu_handler

from util import check_string


async def process_input_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async def send_error_and_resume(update: Update, context: ContextTypes.DEFAULT_TYPE, err_msg: str):
        message = await context.bot.send_message(update.effective_chat.id, err_msg, parse_mode="markdown")
        context.user_data["messages_to_delete"].extend([update.message.message_id, message.message_id])
        await change_name_handler(update, context)

    name = update.message.text
    if not name:
        await send_error_and_resume(update, context, "*Вы прислали что-то странное. Попробуйте ещё раз.*")
        return
    # Too long name
    if len(name) > 100:
        await send_error_and_resume(update, context, "*Странное имя. Попробуйте покороче.*")
        return

    if not check_string(name):
        await send_error_and_resume(update, context, "*Недопустимые символы в имени! Разрешены только буквы, цифры, пробел, -, !, ?*")
        return

    context.user_data["user_db_data"]["name"] = name
    context.user_data["text_state"] = None
    rep_chess_db.update_user_name(update.message.from_user.id, name)

    context.user_data["messages_to_delete"].append(update.message.message_id)
    # Output updated profile
    await main_menu_handler(update, context)


async def change_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    # save handler for text message
    context.user_data["text_state"] = process_input_name

    message = await context.bot.send_message(update.effective_chat.id, "*Введите имя:*", parse_mode="markdown")
    context.user_data["messages_to_delete"].append(message.message_id)


profile_change_name_handlers = [
    CallbackQueryHandler(change_name_handler, pattern="^profile_name$")
]
