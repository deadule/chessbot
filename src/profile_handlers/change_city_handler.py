import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler

from databaseAPI import rep_chess_db
from .main_menu_handler import main_menu_handler


logger = logging.getLogger(__name__)


async def process_input_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # query is not empty, no other way to be in this function
    await query.answer()
    city = query.data.split("_")[2]

    city_id = rep_chess_db.get_id_on_city_name(city)
    if not city_id:
        logger.error(f"CITIES ARE INCONSISTENT! No city with id = {city_id}")
        return
    # TODO: Всерьёз подумать, что в юзера положить - строку или id. И как быть, если город удаляется?
    context.user_data["user_db_data"]["city_id"] = city_id
    rep_chess_db.update_user_city_id(update.callback_query.from_user.id, city_id)

    # Output updated profile
    await main_menu_handler(update, context)


async def profile_city_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    buttons = []
    for city in rep_chess_db.get_cities_names():
         # TODO: Возможно несколько в ряд?
        buttons.append([InlineKeyboardButton(city, callback_data=f"profile_city_{city}")])
    buttons.append([InlineKeyboardButton("<< Назад", callback_data="go_main_menu")])
    message = await context.bot.send_message(
        update.effective_chat.id,
        "*Выберите Ваш город. Исходя из него Вам будет показываться расписание*",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="markdown"
    )

    context.user_data["messages_to_delete"].append(message.message_id)


profile_change_city_handlers = [
    CallbackQueryHandler(profile_city_handler, pattern="^profile_city$"),
    CallbackQueryHandler(process_input_city, pattern="^profile_city_*"),
]
