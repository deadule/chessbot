from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from databaseAPI import rep_chess_db
from main_menu_handler import main_menu_handler
from util import check_string


async def process_input_surname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    surname = update.message.text
    # Too long surname
    if len(surname) > 100:
        message = await update.message.reply_text("Странная фамилия. Попробуйте покороче.")
        context.user_data["messages_to_delete"].extend([update.message.message_id, message.message_id])
        await profile_surname_handler(update, context)

    if not check_string(surname):
        message = await context.bot.send_message("Недопустимые символы в фамилии! Разрешены только буквы, цифры, пробел, -, !, ?")
        context.user_data["messages_to_delete"].extend([update.message.message_id, message.message_id])
        await profile_surname_handler(update, context)
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


profile_change_surname_handler = CallbackQueryHandler(
    profile_surname_handler,
    pattern="^profile_surname$"
)
