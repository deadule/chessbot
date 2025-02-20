from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, ContextTypes

from databaseAPI import rep_chess_db
from start import go_main_menu


SUPER_ADMIN_ID = 928688258


admin_inline_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("Открыть регистрацию на турнир", callback_data="admin_open_registration")],
    [InlineKeyboardButton("Изменить ID игрока", callback_data="admin_change_public_id")],
    [InlineKeyboardButton("Добавить пост в расписание", callback_data="admin_update_timetable")],
    [InlineKeyboardButton("Удалить пост из расписания", callback_data="admin_delete_timetable")],
    [InlineKeyboardButton("Добавить пост для лагеря", callback_data="admin_add_camp")],
    [InlineKeyboardButton("Удалить пост для лагеря", callback_data="admin_delete_camp")],
    [InlineKeyboardButton("💀 Добавить нового админа", callback_data="admin_add_new_admin")],
    [InlineKeyboardButton("💀 Удалить админа", callback_data="admin_delete_admin")],
    [InlineKeyboardButton("💀 Удалить игрока из базы", callback_data="admin_delete_user")],
])


async def admin_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.message.from_user.id if update.message else update.callback_query.from_user.id

    rep_chess_db.update_user_last_contact(telegram_id)
    is_admin = any((rep_chess_db.is_admin(telegram_id), telegram_id == SUPER_ADMIN_ID))

    if not is_admin:
        await context.bot.send_message(update.effective_chat.id, "Хорошая попытка, но ты не админ :)")
        await go_main_menu(update, context)
        return
    await context.bot.send_message(update.effective_chat.id, "Опции админа:", reply_markup=admin_inline_keyboard)

admin_main_menu_handlers = [
    CommandHandler("admin", admin_main_menu)
]
