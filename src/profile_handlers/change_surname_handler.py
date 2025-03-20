from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from databaseAPI import rep_chess_db
from main_menu_handler import main_menu_handler
from util import check_string


async def process_input_surname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async def send_error_and_resume(update: Update, context: ContextTypes.DEFAULT_TYPE, err_msg: str):
        message = await context.bot.send_message(update.effective_chat.id, err_msg, parse_mode="markdown")
        context.user_data["messages_to_delete"].extend([update.message.message_id, message.message_id])
        await profile_surname_handler(update, context)

    surname = update.message.text
    if not surname:
        await send_error_and_resume(update, context, "*Вы прислали что-то странное. Попробуйте ещё раз.*")
        return
    # Too long surname
    if len(surname) > 100:
        await send_error_and_resume(update, context, "*Странная фамилия. Попробуйте покороче.*")
        return

    if not check_string(surname):
        await send_error_and_resume(update, context, "*Недопустимые символы в фамилии! Разрешены только буквы, цифры, пробел, -, !, ?*")
        return

    context.user_data["user_db_data"]["surname"] = surname
    context.user_data["text_state"] = None
    rep_chess_db.update_user_surname(update.message.from_user.id, surname)

    context.user_data["messages_to_delete"].append(update.message.message_id)
    # Output updated profile
    await main_menu_handler(update, context)


async def profile_surname_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    # save handler for text message
    context.user_data["text_state"] = process_input_surname

    message = await context.bot.send_message(update.effective_chat.id, "*Введите фамилию:*", parse_mode="markdown")
    context.user_data["messages_to_delete"].append(message.message_id)


profile_change_surname_handlers = [
    CallbackQueryHandler(profile_surname_handler, pattern="^profile_surname$")
]
