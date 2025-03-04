from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from databaseAPI import rep_chess_db
from main_menu_handler import main_menu_handler


async def process_input_lichess_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async def send_error_and_resume(update: Update, context: ContextTypes.DEFAULT_TYPE, err_msg: str):
        message = await update.message.reply_text(err_msg, parse_mode="markdown")
        context.user_data["messages_to_delete"].extend([update.message.message_id, message.message_id])
        await profile_lichess_rating_handler(update, context)

    lichess_rating = update.message.text
    if not lichess_rating.isdigit():
        await send_error_and_resume(update, context, "*Не похоже на рейтинг...*")
        return

    try:
        lichess_rating = int(lichess_rating)
    except ValueError:
        await send_error_and_resume(update, context, "*Воу, это что такое? Попробуйте ещё раз*")
        return

    if lichess_rating >= 3000:
        await send_error_and_resume(update, context, "*Хорошая попытка, Карлсен. Попробуй ещё раз.*")
        return

    if lichess_rating <= 100:
        await send_error_and_resume(update, context, "*Сомневаюсь, что у вас такой рейтинг... Попробуй ещё раз.*")
        return

    context.user_data["user_db_data"]["lichess_rating"] = lichess_rating
    context.user_data["text_state"] = None
    rep_chess_db.update_user_lichess_rating(update.message.from_user.id, lichess_rating)

    context.user_data["messages_to_delete"].append(update.message.message_id)
    # Output updated profile
    await main_menu_handler(update, context)


async def profile_lichess_rating_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    # save handler for text message
    context.user_data["text_state"] = process_input_lichess_rating

    message = await context.bot.send_message(update.effective_chat.id, "*Введите новый рейтинг [lichess](https://lichess.org/):*", parse_mode="markdown", disable_web_page_preview=True)
    context.user_data["messages_to_delete"].append(message.message_id)


profile_change_lichess_rating_handler = CallbackQueryHandler(
    profile_lichess_rating_handler,
    pattern="^profile_lichess_rating$"
)
