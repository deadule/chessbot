from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, MessageHandler, filters

from databaseAPI import rep_chess_db
from util import escape_special_symbols
from change_profile_handler import change_profile_keyboard


profile_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("📝  Поменять данные", callback_data="change_profile_data")],
    [InlineKeyboardButton("<< Назад", callback_data="go_main_menu")],
])


async def change_profile_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.bot.send_message(
        update.effective_chat.id,
        "_Вы можете поменять свои данные:_",
        parse_mode="markdown",
        reply_markup=change_profile_keyboard
    )


def construct_profile_message(user_db_data: dict) -> str:
    def change_last_symbol(string: str, dst: str, src: str) -> str:
        """
        Change the last 'dst' symbol in string to 'src' symbol.
        """
        return src.join(string.rsplit(dst, 1))

    profile_str = f"👤 *_Ваш профиль:_*\n ├ ID:  `{user_db_data['public_id']}`\n"
    if user_db_data['nickname']:
        profile_str += f" ├ Ник:  `{escape_special_symbols(user_db_data['nickname'])}`\n"
    profile_str +=  f" ├ Имя:  `{escape_special_symbols(user_db_data['name'])}`\n"
    if user_db_data['surname']:
        profile_str += f" ├ Фамилия:  `{escape_special_symbols(user_db_data['surname'])}`\n"
    if user_db_data['age']:
        profile_str += f" ├ Возраст:  `{user_db_data['age']}`\n"
    profile_str = change_last_symbol(profile_str, "├", "└")
    profile_str += f"\n📊 *_Статистика:_*\n"
    profile_str += f" ├ Rep рейтинг:  `{user_db_data['rep_rating']}`\n"
    if user_db_data['lichess_rating']:
        profile_str += f" ├ Рейтинг [lichess](https://lichess.org/):  `{user_db_data['lichess_rating']}`\n"
    if user_db_data['chesscom_rating']:
        profile_str += f" ├ Рейтинг [chess\.com](https://chess.com/):  `{user_db_data['chesscom_rating']}`\n"
    profile_str = change_last_symbol(profile_str, "├", "└")
    return profile_str


async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.message.from_user.id
    user_db_data = rep_chess_db.get_user_on_telegram_id(telegram_id)
    rep_chess_db.update_user_last_contact(telegram_id)

    # Add user data in cache to not make database query every time
    context.user_data["user_db_data"] = user_db_data

    # Delete saved state because here we already don't expect that useful user message will come.
    context.user_data["text_state"] = None

    # Delete useless messages about correcting some data
    if "messages_to_delete" in context.user_data and context.user_data["messages_to_delete"]:
        await context.bot.delete_messages(update.effective_chat.id, context.user_data["messages_to_delete"])
    context.user_data["messages_to_delete"] = []

    profile_str = construct_profile_message(user_db_data)
    message = await update.message.reply_text(
        profile_str,
        parse_mode="MarkdownV2",
        disable_web_page_preview=True,
        reply_markup=profile_keyboard
    )
    context.user_data["messages_to_delete"].append(message.message_id)


profile_main_menu_handler = MessageHandler(filters.Regex("^👤 Профиль$"), main_menu_handler)
