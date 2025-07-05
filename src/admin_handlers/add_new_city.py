from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from databaseAPI import rep_chess_db
from start import main_menu_reply_keyboard


async def process_adding_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async def send_error_and_resume(update: Update, context: ContextTypes.DEFAULT_TYPE, err_msg):
        await context.bot.send_message(update.effective_chat.id, err_msg, parse_mode="markdown")
        await admin_add_new_city(update, context)

    tg_channel, city = update.message.text.split(" ", maxsplit=1)

    if not tg_channel.startswith("@"):
        await send_error_and_resume(update, context, "Тег канала должен начинаться с @. Попробуйте заново.")
        return
    tg_channel = tg_channel[1:]
    if len(tg_channel) < 4 or len(tg_channel) > 100:
        await send_error_and_resume(update, context, "Ну вы серьёзно думаете, что такой тег существует? Попробуйте ещё раз.")
        return
    if len(city) < 3 or len(city) > 40:
        await send_error_and_resume(update, context, "Ну вы серьёзно думаете, что такой город существует? Попробуйте ещё раз.")
        return

    rep_chess_db.add_city(tg_channel, city)
    context.user_data["text_state"] = None
    await update.message.reply_text(f"Вы добавили город {city} с каналом {tg_channel}", reply_markup=main_menu_reply_keyboard(context))


async def admin_add_new_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    context.user_data["text_state"] = process_adding_city
    await context.bot.send_message(
        update.effective_chat.id,
        "Введите сначала тег канала города, начинающийся с @, затем через пробел название города"
    )


admin_add_new_city_handlers = [
    CallbackQueryHandler(admin_add_new_city, pattern="^admin_add_new_city$")
]
