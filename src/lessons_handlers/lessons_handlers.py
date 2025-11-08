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

async def select_level_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Создаем клавиатуру для выбора уровня
    keyboard = [
        [InlineKeyboardButton("Начинающий", callback_data="level_beginner")],
        [InlineKeyboardButton("<< Назад", callback_data="go_lessons_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text="Выберите ваш уровень:",
        reply_markup=reply_markup
    )

async def show_videos_for_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show videos for selected level"""
    query = update.callback_query
    await query.answer()
    
    # Check if user has active subscription
    if not rep_chess_db.check_user_active_subscription(query.from_user.id):
        subscription_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌟 Оформить подписку", callback_data="subscription_menu")],
            [InlineKeyboardButton("<< Назад", callback_data="go_main_menu")]
        ])
        
        await query.edit_message_text(
            "🔒 **Доступ к урокам ограничен**\n\nДля доступа к видеоурокам необходимо оформить подписку.\n\nПерейдите в главное меню → Подписка для оформления.",
            reply_markup=subscription_keyboard,
            parse_mode="Markdown"
        )
        return
    
    # Extract level from callback data (e.g., "level_beginner" -> "Начинающий")
    level = "Начинающий"  # For now, we only have this level
    
    try:
        # Get videos for this level ordered by lesson number
        videos = rep_chess_db.get_videos_by_category_ordered(level)
        
        if not videos:
            await query.edit_message_text(
                f"📚 **{level}**\n\nВидео для этого уровня пока не загружены.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("<< Назад", callback_data="select_level")]
                ]),
                parse_mode="Markdown"
            )
            return
        
        # Create keyboard with videos (only show completed videos with lesson numbers)
        keyboard_buttons = []
        for video in videos:
            # Only show videos that are completed processing AND have lesson numbers
            if (video.get('processing_status') == 'completed' and 
                video.get('lesson_number') and 
                video['lesson_number'] != ''):
                lesson_text = f"Урок {video['lesson_number']}: {video['title']}"
                if len(lesson_text) > 50:
                    lesson_text = lesson_text[:47] + "..."
                keyboard_buttons.append([InlineKeyboardButton(
                    lesson_text,
                    callback_data=f"video_{video['id']}"
                )])
        
        keyboard_buttons.append([InlineKeyboardButton("<< Назад", callback_data="select_level")])
        
        video_keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        message_text = f"📚 **{level}**\n\nВыберите урок:\n\nВсего уроков: {len(keyboard_buttons) - 1 if len(keyboard_buttons) > 0 else 0}"
        
        await query.edit_message_text(
            message_text,
            reply_markup=video_keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await query.edit_message_text(
            f"❌ Ошибка при загрузке видео: {str(e)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("<< Назад", callback_data="select_level")]
            ])
        )

async def show_video_quality_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show quality selection for selected video"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Extract video ID from callback data
        video_id = int(query.data.split("_")[-1])
        
        # Get video from database
        video = rep_chess_db.get_video_by_id(video_id)
        if not video:
            await query.edit_message_text("❌ Видео не найдено.")
            return
        
        # Check if video is processed
        if video.get('processing_status') != 'completed':
            await query.edit_message_text(
                "⏳ **Видео еще обрабатывается**\n\nПожалуйста, подождите завершения обработки.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("<< Назад", callback_data="select_level")]
                ]),
                parse_mode="Markdown"
            )
            return
        
        # Create quality selection keyboard
        keyboard_buttons = []
        
        if video.get('file_id_480p') and video['file_id_480p'] != 'placeholder':
            keyboard_buttons.append([InlineKeyboardButton("Среднее качество", callback_data=f"quality_480p_{video_id}")])
        
        if video.get('file_id_1080p') and video['file_id_1080p'] != 'placeholder':
            keyboard_buttons.append([InlineKeyboardButton("Высокое качество", callback_data=f"quality_1080p_{video_id}")])
        
        if not keyboard_buttons:
            await query.edit_message_text(
                "❌ **Видео недоступно**\n\nОбработанные версии видео не найдены.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("<< Назад", callback_data="select_level")]
                ]),
                parse_mode="Markdown"
            )
            return
        
        keyboard_buttons.append([InlineKeyboardButton("<< Назад", callback_data="select_level")])
        quality_keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        await query.edit_message_text(
            f"""📚 **{video['title']}**

🏷️ **Категория**: {video['category']}
🔢 **Урок**: {video['lesson_number']}
📄 **Описание**: {video['description'] if video['description'] else 'не указано'}

Выберите качество видео:""",
            reply_markup=quality_keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await query.edit_message_text(
            f"❌ Ошибка при загрузке видео: {str(e)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("<< Назад", callback_data="select_level")]
            ])
        )

async def send_video_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send selected video to user with chosen quality"""
    query = update.callback_query
    await query.answer()
    
    # Check if user has active subscription
    if not rep_chess_db.check_user_active_subscription(query.from_user.id):
        subscription_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌟 Оформить подписку", callback_data="subscription_menu")],
            [InlineKeyboardButton("<< Назад", callback_data="go_main_menu")]
        ])
        
        await query.edit_message_text(
            "🔒 **Доступ к урокам ограничен**\n\nДля доступа к видеоурокам необходимо оформить подписку.\n\nПерейдите в главное меню → Подписка для оформления.",
            reply_markup=subscription_keyboard,
            parse_mode="Markdown"
        )
        return
    
    try:
        # Extract quality and video ID from callback data
        parts = query.data.split("_")
        quality = parts[1]  # 480p or 1080p
        video_id = int(parts[2])
        
        # Get video file_id for the selected quality
        file_id = rep_chess_db.get_video_file_id(video_id, quality)
        if not file_id:
            await query.edit_message_text("❌ Видео с выбранным качеством не найдено.")
            return
        
        # Get video info
        video = rep_chess_db.get_video_by_id(video_id)
        if not video:
            await query.edit_message_text("❌ Видео не найдено.")
            return
        
        # Send video to user
        await context.bot.send_video(
            chat_id=query.from_user.id,
            video=file_id,
            caption=f"""📚 **{video['title']}**

🏷️ **Категория**: {video['category']}
🔢 **Урок**: {video['lesson_number']}
📐 **Качество**: {quality}
📄 **Описание**: {video['description'] if video['description'] else 'не указано'}""",
            parse_mode="Markdown"
        )
        
        # Show navigation back to lessons
        await query.edit_message_text(
            "✅ Видео отправлено!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📚 Выбрать другой урок", callback_data="select_level")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="go_main_menu")]
            ])
        )
        
    except Exception as e:
        await query.edit_message_text(
            f"❌ Ошибка при отправке видео: {str(e)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("<< Назад", callback_data="select_level")]
            ])
        )

async def lessons_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        telegram_id = update.message.from_user.id
    else:
        telegram_id = update.callback_query.from_user.id
    
    # Check if user has active subscription
    if not rep_chess_db.check_user_active_subscription(telegram_id):
        subscription_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌟 Оформить подписку", callback_data="subscription_menu")],
            [InlineKeyboardButton("<< Назад", callback_data="go_main_menu")]
        ])
        
        if update.message:
            await update.message.reply_text(
                "🔒 **Доступ к урокам ограничен**\n\nДля доступа к видеоурокам необходимо оформить подписку.\n\nПерейдите в главное меню → Подписка для оформления.",
                reply_markup=subscription_keyboard,
                parse_mode="Markdown"
            )
        else:
            await update.callback_query.edit_message_text(
                "🔒 **Доступ к урокам ограничен**\n\nДля доступа к видеоурокам необходимо оформить подписку.\n\nПерейдите в главное меню → Подписка для оформления.",
                reply_markup=subscription_keyboard,
                parse_mode="Markdown"
            )
        return
    
    # Show level selection for subscribed users
    level_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Начинающий", callback_data="level_beginner")],
        [InlineKeyboardButton("<< Назад", callback_data="go_main_menu")]
    ])
    
    if update.message:
        await update.message.reply_text(
            "📚 **Выберите уровень обучения:**",
            reply_markup=level_keyboard,
            parse_mode="Markdown"
        )
    else:
        await update.callback_query.edit_message_text(
            "📚 **Выберите уровень обучения:**",
            reply_markup=level_keyboard,
            parse_mode="Markdown"
        )

lessons_callback_handlers = [
    MessageHandler(filters.Regex("^🎯 Обучение$"), lessons_menu),
    CallbackQueryHandler(callback_lessons_menu_handler, pattern="^go_lessons_menu$"),
    CallbackQueryHandler(callback_level_choosing_menu_handler, pattern="^go_level_choosing_menu$"),
    
    CallbackQueryHandler(select_level_handler, pattern="^select_level$"),
    CallbackQueryHandler(show_videos_for_level, pattern="^level_"),
    CallbackQueryHandler(show_video_quality_selection, pattern="^video_"),
    CallbackQueryHandler(send_video_to_user, pattern="^quality_"),
    CallbackQueryHandler(select_level_handler, pattern="^go_level_choosing_menu$")
    ]


# среднее качество и высокое качество