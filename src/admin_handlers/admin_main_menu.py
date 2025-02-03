from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, ContextTypes

from databaseAPI import rep_chess_db


SUPER_ADMIN_ID = 928688258

admin_inline_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("Послать сообщение всем пользователям", callback_data="admin_send_push")],
    [InlineKeyboardButton("Поменять недельное расписание", callback_data="admin_change_timetable")],
    [InlineKeyboardButton("Добавить видео", callback_data="admin_add_video")],
    [InlineKeyboardButton("Добавить мерч", callback_data="admin_add_merch")],
    [InlineKeyboardButton("☠ Добавить нового админа", callback_data="admin_add_new_admin")],
    [InlineKeyboardButton("☠ Удалить админа", callback_data="admin_delete_admin")],
    [InlineKeyboardButton("☠ Удалить игрока из базы", callback_data="admin_delete_user")],
])


"""admin_inline_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("27.01 19:00 The Hat", callback_data="admin_send_push")],
    [InlineKeyboardButton("27.01 20:00 Blanc", callback_data="admin_send_push")],
    [InlineKeyboardButton("28.01 20:00 новички Ровестник", callback_data="admin_change_timetable")],
    [InlineKeyboardButton("28.01 20:00 профессионалы", callback_data="admin_change_timetable")],
    [InlineKeyboardButton("28.01 20:00 Duck Chess Mandy's", callback_data="admin_add_video")],
    [InlineKeyboardButton("29.01 20:00 рапид Авангард", callback_data="admin_add_merch")],
    #[InlineKeyboardButton("☠ Добавить нового админа", callback_data="admin_add_new_admin")],
    #[InlineKeyboardButton("☠ Удалить админа", callback_data="admin_delete_admin")],
    #[InlineKeyboardButton("☠ Удалить игрока из базы", callback_data="admin_delete_user")],
])"""


async def admin_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.message.from_user.id if update.message else update.callback_query.from_user.id

    rep_chess_db.update_user_last_contact(telegram_id)
    is_admin = any((rep_chess_db.is_admin(telegram_id), telegram_id == SUPER_ADMIN_ID))

    if not is_admin:
        await context.bot.send_message(update.effective_chat.id, "Хорошая попытка, но ты не админ :)")
        return
    await context.bot.send_message(update.effective_chat.id, "Опции админа:", reply_markup=admin_inline_keyboard)

admin_main_menu_handler = CommandHandler("admin", admin_main_menu)
