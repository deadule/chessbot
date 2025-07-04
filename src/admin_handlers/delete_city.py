from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackQueryHandler, ContextTypes

from databaseAPI import rep_chess_db
from start import main_menu_reply_keyboard


async def process_deleting_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # query is not empty, no other way to be in this function
    await query.answer()
    city = query.data.split("_")[3]

    rep_chess_db.delete_city(city)
    await context.bot.send_message(
        update.effective_chat.id,
        f"Город {city} удалён. Все люди, привязанные к этому городу, переправлены на Москву",
        reply_markup=main_menu_reply_keyboard(context)
    )


async def admin_delete_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    buttons = []
    for city in rep_chess_db.get_cities_names():
        buttons.append([InlineKeyboardButton(city, callback_data=f"admin_delete_city_{city}")])
    buttons.append([InlineKeyboardButton("<< Назад", callback_data="go_main_menu")])
    await context.bot.send_message(
        update.effective_chat.id,
        "Введите сначала тег канала города, начинающийся с @, затем через пробел название города",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


admin_delete_city_handlers = [
    CallbackQueryHandler(admin_delete_city, pattern="^admin_delete_city$"),
    CallbackQueryHandler(process_deleting_city, pattern="^admin_delete_city_*"),
]
