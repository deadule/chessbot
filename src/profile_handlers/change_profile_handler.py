from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, CallbackQueryHandler


change_profile_keyboard = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📝  Ник", callback_data="profile_nickname"),
        InlineKeyboardButton("📝  Возраст", callback_data="profile_age"),
    ],
    [
        InlineKeyboardButton("📝  Имя", callback_data="profile_name"),
        InlineKeyboardButton("📝  Фамилия", callback_data="profile_surname"),
    ],
    [
        InlineKeyboardButton("♞  lichess", callback_data="profile_lichess_rating"),
        InlineKeyboardButton("♟️  chess.com", callback_data="profile_chesscom_rating")
    ],
    [InlineKeyboardButton("<< Назад", callback_data="go_main_menu")],
])


async def change_profile_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    message = await context.bot.send_message(
        update.effective_chat.id,
        "_Вы можете поменять свои данные:_",
        parse_mode="markdown",
        reply_markup=change_profile_keyboard
    )
    context.user_data["messages_to_delete"].append(message.message_id)


profile_change_profile_handler = CallbackQueryHandler(
    change_profile_data,
    pattern="^change_profile_data$"
)
