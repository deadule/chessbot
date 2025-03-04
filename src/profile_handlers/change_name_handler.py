from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from databaseAPI import rep_chess_db
from main_menu_handler import main_menu_handler

from util import check_string


async def process_input_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    # Too long name
    if len(name) > 100:
        message = await update.message.reply_text("Странное имя. Попробуйте покороче.")
        context.user_data["messages_to_delete"].extend([update.message.message_id, message.message_id])
        await change_name_handler(update, context)
        return

    if not check_string(name):
        message = await context.bot.send_message("Недопустимые символы в имени! Разрешены только буквы, цифры, пробел, -, !, ?")
        context.user_data["messages_to_delete"].extend([update.message.message_id, message.message_id])
        await change_name_handler(update, context)
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


profile_change_name_handler = CallbackQueryHandler(
    change_name_handler,
    pattern="^profile_name$",
)
