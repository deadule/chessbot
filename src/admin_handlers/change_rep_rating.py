from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from databaseAPI import rep_chess_db


async def process_changing_rep_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    input_parts = update.message.text.split()

    if len(input_parts) != 2:
        await send_error_and_prompt(update, context, error_text="Формат ввода неверный, попробуйте еще раз")
        return
    
    public_id, rep_rating = input_parts

    if not rep_rating.isdigit() or not public_id.isdigit():
        await send_error_and_prompt(update, context, error_text="*Не похоже что ID и рейтинг введены верно\\.*")
        return
    
    try:
        public_id = int(public_id)
        rep_rating = int(rep_rating)
    except ValueError:
        await send_error_and_prompt(update, context, error_text="*Неверный формат чисел, попробуй еще раз\\.*")
        return

    if rep_rating >= 3000:
        await send_error_and_prompt(update, context, error_text="*Вы уверены, что рейтинг игрока выше 3000\\?\\.*")
        return

    # rating of 100 is possible elo
    if rep_rating < 100:
        await send_error_and_prompt(update, context, error_text="*Рейтинг игрока ниже 100, все настолько плохо\\.\\.\\.?*")
        return
    
    context.user_data["text_state"] = None

    # send database query and check for ID's existence 
    try:
        rep_chess_db.update_user_rep_rating_with_rep_id(public_id, rep_rating)
        await update.message.reply_text("Рейтинг игрока обновлен.")
    except ValueError as err:
        await send_error_and_prompt(update, context, error_text="Игрока с таким rep ID не существует, не удалось обновить рейтинг\\.")


async def admin_change_rep_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    context.user_data["text_state"] = process_changing_rep_rating
    message = await context.bot.send_message(
        update.effective_chat.id,
        "Введите сначала rep ID и после новый rep рейтинг игрока через пробел:\n",
        parse_mode="MarkdownV2"
    )


admin_change_rep_rating_handlers = [
    CallbackQueryHandler(admin_change_rep_rating, pattern="^admin_change_rep_rating$")
]


# for DRY purposes
async def send_error_and_prompt(update, context, error_text):
    msg = await update.message.reply_text(error_text, parse_mode="MarkdownV2", disable_web_page_preview=True)
    await admin_change_rep_rating(update, context)
