from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from databaseAPI import rep_chess_db
from main_menu_handler import main_menu_handler


async def process_input_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async def send_error_and_resume(update: Update, context: ContextTypes.DEFAULT_TYPE, err_msg: str):
        message = await context.bot.send_message(update.effective_chat.id, err_msg, parse_mode="markdown")
        context.user_data["messages_to_delete"].extend([update.message.message_id, message.message_id])
        await profile_age_handler(update, context)

    age = update.message.text
    if not age.isdigit():
        await send_error_and_resume(update, context, "*Не похоже на возраст... Попробуйте ещё раз*")
        return

    try:
        age = int(age)
    except ValueError:
        await send_error_and_resume(update, context, "*Что-то не то вы ввели. Попробуйте ещё раз*")
        return

    if age >= 100 or age < 5:
        await send_error_and_resume(update, context, "*Ну да, ну да. Так мы вам и поверили*")
        return

    context.user_data["user_db_data"]["age"] = age
    context.user_data["text_state"] = None
    rep_chess_db.update_user_age(update.message.from_user.id, age)

    context.user_data["messages_to_delete"].append(update.message.message_id)
    # Output updated profile
    await main_menu_handler(update, context)


async def profile_age_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    # save handler for text message
    context.user_data["text_state"] = process_input_age

    message = await context.bot.send_message(update.effective_chat.id, "*Введите свой возраст:*", parse_mode="markdown")
    context.user_data["messages_to_delete"].append(message.message_id)


profile_change_age_handler = CallbackQueryHandler(
    profile_age_handler,
    pattern="^profile_age$"
)
