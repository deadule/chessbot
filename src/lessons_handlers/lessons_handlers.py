from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, error, KeyboardButton
from telegram.ext import ContextTypes, MessageHandler, filters, CallbackQueryHandler

from databaseAPI import rep_chess_db
from start import main_menu_reply_keyboard

lessons_keyboard_main = InlineKeyboardMarkup([
    [InlineKeyboardButton("🎯 Обучение", callback_data="lessons_menu")],
    [InlineKeyboardButton("<< Назад", callback_data="go_main_menu")],
])

lessons_keyboard_level = InlineKeyboardMarkup([
    [InlineKeyboardButton("Выбор уровня", callback_data="select_level")],
    [InlineKeyboardButton("<< Назад", callback_data="go_lessons_menu")],
])

# choose_video_handler

lessons_keyboard_quality = InlineKeyboardMarkup([
    [InlineKeyboardButton("В каком качестве скачать видео?", callback_data="select_quality")],
    [InlineKeyboardButton("<< Назад", callback_data="go_level_choosing_menu")],
])

async def callback_lessons_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await lessons_menu(update, context)

async def callback_level_choosing_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await select_level_handler(update, context)

async def callback_quality_choosing_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await select_quality_handler(update, context)

async def select_level_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Создаем клавиатуру для выбора уровня
    keyboard = [
        [InlineKeyboardButton("Начинающий", callback_data="level_beginner")],
        [InlineKeyboardButton("Продолжающий", callback_data="level_intermediate")],
        [InlineKeyboardButton("<< Назад", callback_data="go_lessons_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text="Выберите ваш уровень:",
        reply_markup=reply_markup
    )

async def choose_video_handler():
    # create keyboard for videos
    # select select_quality_handler(video_id)
    pass

async def select_quality_handler(video_id):
    # bot.sendMessage()
    # request to db
    # low quality (480p)
    # high video quality (maximum vq)
    pass

async def create_keyboard_for_videos():
    pass

async def lessons_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        telegram_id = update.message.from_user.id
    else:
        telegram_id = update.callback_query.from_user.id
    await update.message.reply_text(
                "Доступные уроки:",
                reply_markup=lessons_keyboard_main
            )
    # user_db_data = rep_chess_db.get_user_on_telegram_id(telegram_id)
    # rep_chess_db.update_user_last_contact(telegram_id)

    # # Add user data in cache to not make database query every time
    # context.user_data["user_db_data"] = user_db_data



    # if user[subscription][status] = active
    # else: 
    #  'Для доступа к урокам нужно оформить подписку! Перейдите в главное меню -> подписка для ее оформления'
    # InlineKeyboardButton("Завершить")
    # 


lessons_callback_handlers = [
    MessageHandler(filters.Regex("^🎯 Обучение$"), lessons_menu),
    CallbackQueryHandler(callback_lessons_menu_handler, pattern="^go_lessons_menu$"),
    CallbackQueryHandler(callback_level_choosing_menu_handler, pattern="^go_level_choosing_menu$"),
    
    CallbackQueryHandler(select_level_handler, pattern="^select_level$"),
    CallbackQueryHandler(select_quality_handler, pattern="^select_quality$")
    ]