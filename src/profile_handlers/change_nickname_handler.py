from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from databaseAPI import rep_chess_db
from main_menu_handler import main_menu_handler


async def process_input_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nickname = update.message.text
    # Too long nickname
    if len(nickname) > 100:
        message = await update.message.reply_text("Слишком длинный ник. Попробуйте покороче.")
        context.user_data["messages_to_delete"].extend([update.message.message_id, message.message_id])
        await profile_nickname_handler(update, context)
        return

    context.user_data["nickname"] = nickname
    context.user_data["text_state"] = None
    rep_chess_db.update_user_nickname(update.message.from_user.id, nickname)

    context.user_data["messages_to_delete"].append(update.message.message_id)
    # Output updated profile
    await main_menu_handler(update, context)


async def profile_nickname_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    # save handler for text message
    context.user_data["text_state"] = process_input_nickname

    message = await context.bot.send_message(update.effective_chat.id, "*Введите ник:*", parse_mode="MarkdownV2")
    context.user_data["messages_to_delete"].append(message.message_id)


profile_change_nickname_handler = CallbackQueryHandler(
    profile_nickname_handler,
    pattern="profile_nickname"
)
