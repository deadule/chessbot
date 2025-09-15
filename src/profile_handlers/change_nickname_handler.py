from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from databaseAPI import rep_chess_db
from .main_menu_handler import main_menu_handler
from util import check_string


async def process_input_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async def send_error_and_retry(err_msg: str):
        message = await context.bot.send_message(update.effective_chat.id, err_msg, parse_mode="markdown")
        if "messages_to_delete" in context.user_data:
            context.user_data["messages_to_delete"].extend([update.message.message_id, message.message_id])

    nickname = update.message.text.strip() if update.message and update.message.text else ""

    if not nickname:
        await send_error_and_retry("*Ой, что-то не получилось записать, попробуйте ещё раз!*")
        return
    if len(nickname) > 60:
        await send_error_and_retry("*Попробуйте чуть покороче 👀*")
        return
    if not check_string(nickname):
        await send_error_and_retry("*Мы так не сможем записать. Используйте только буквы, цифры, пробел, -, !, ?*")
        return

    if "user_db_data" in context.user_data:
        context.user_data["user_db_data"]["nickname"] = nickname
    rep_chess_db.update_user_nickname(update.message.from_user.id, nickname)

    context.user_data["text_state"] = None

    if "messages_to_delete" in context.user_data:
        context.user_data["messages_to_delete"].append(update.message.message_id)

    await update.message.reply_text(
        f"Отлично! Теперь вы известны как *{nickname}*! 🎉",
        parse_mode="markdown",
    )

    await main_menu_handler(update, context)


async def profile_nickname_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    # save handler for text message
    context.user_data["text_state"] = process_input_nickname

    message = await context.bot.send_message(update.effective_chat.id, "*Введите ник:*", parse_mode="markdown")
    context.user_data["messages_to_delete"].append(message.message_id)

profile_change_nickname_handlers = [
    CallbackQueryHandler(profile_nickname_handler, pattern="^profile_nickname$"),
]
