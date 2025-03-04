from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from databaseAPI import rep_chess_db
from main_menu_handler import main_menu_handler


async def process_input_chesscom_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chesscom_rating = update.message.text
    if not chesscom_rating.isdigit():
        message = await update.message.reply_text("*Не похоже на рейтинг...*", parse_mode="markdown")
        context.user_data["messages_to_delete"].extend([update.message.message_id, message.message_id])
        await profile_chesscom_rating_handler(update, context)
        return

    chesscom_rating = int(chesscom_rating)
    if chesscom_rating >= 3000:
        message = await update.message.reply_text("*Хорошая попытка, Карлсен. Попробуй ещё раз.*", parse_mode="markdown")
        context.user_data["messages_to_delete"].extend([update.message.message_id, message.message_id])
        await profile_chesscom_rating_handler(update, context)
        return

    if chesscom_rating <= 100:
        message = await update.message.reply_text("*Сомневаюсь, что у вас такой рейтинг... Попробуй ещё раз.*", parse_mode="markdown")
        context.user_data["messages_to_delete"].extend([update.message.message_id, message.message_id])
        await profile_chesscom_rating_handler(update, context)
        return

    context.user_data["user_db_data"]["chesscom_rating"] = chesscom_rating
    context.user_data["text_state"] = None
    rep_chess_db.update_user_chesscom_rating(update.message.from_user.id, chesscom_rating)

    context.user_data["messages_to_delete"].append(update.message.message_id)
    # Output updated profile
    await main_menu_handler(update, context)


async def profile_chesscom_rating_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    # save handler for text message
    context.user_data["text_state"] = process_input_chesscom_rating

    message = await context.bot.send_message(update.effective_chat.id, "*Введите новый рейтинг [chess\.com](https://chess.com/):*", parse_mode="markdown", disable_web_page_preview=True)
    context.user_data["messages_to_delete"].append(message.message_id)


profile_change_chesscom_rating_handler = CallbackQueryHandler(
    profile_chesscom_rating_handler,
    pattern="^profile_chesscom_rating$"
)