import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters, CallbackQueryHandler

from databaseAPI import rep_chess_db
from .admin_main_menu import admin_main_menu
from video_processor import VideoProcessor

logger = logging.getLogger(__name__)

video_admin_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("📤 Загрузить видео", callback_data="admin_upload_video")],
    [InlineKeyboardButton("📋 Показать все видео", callback_data="admin_show_videos")],
    [InlineKeyboardButton("🗑️ Удалить видео", callback_data="admin_delete_video")],
    [InlineKeyboardButton("🏷️ Управление категориями", callback_data="admin_manage_categories")],
    [InlineKeyboardButton("<< Назад", callback_data="go_admin_menu")]
])

video_management_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("📤 Загрузить еще", callback_data="admin_upload_video")],
    [InlineKeyboardButton("📋 Показать все", callback_data="admin_show_videos")],
    [InlineKeyboardButton("<< Назад", callback_data="admin_video_management")]
])

async def admin_video_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show video management menu - ADMIN ONLY"""
    if update.message:
        telegram_id = update.message.from_user.id
        await update.message.reply_text(
            "🎥 **Управление видео** (Админ панель)\n\nВыберите действие:",
            reply_markup=video_admin_keyboard,
            parse_mode="Markdown"
        )
    else:
        telegram_id = update.callback_query.from_user.id
        await update.callback_query.edit_message_text(
            "🎥 **Управление видео** (Админ панель)\n\nВыберите действие:",
            reply_markup=video_admin_keyboard,
            parse_mode="Markdown"
        )

async def admin_start_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start video upload process - ADMIN ONLY"""
    query = update.callback_query
    await query.answer()
    context.user_data["file_state"] = admin_handle_video_upload
    context.user_data["text_state"] = None
    context.user_data["video_metadata"] = {}
    
    await query.edit_message_text(
        "📤 **Загрузка видео**\n\nОтправьте видео файл для загрузки.\n\n"
        "Поддерживаемые форматы: MP4, AVI, MOV, MKV\n"
        "Максимальный размер: 2GB\n\n"
        "Для отмены отправьте /cancel",
        parse_mode="Markdown"
    )

async def admin_handle_video_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle received video and extract file_id - ADMIN ONLY"""
    # Check for video message first, then document
    video = update.message.video
    if not video and update.message.document:
        # Check if document is a video file
        if update.message.document.mime_type and update.message.document.mime_type.startswith('video/'):
            # Create a video object from document
            video = update.message.document
    
    if not video:
        await update.message.reply_text("❌ Видео не найдено в сообщении! Пожалуйста, отправьте видео файл.")
        return
    
    try:
        file_id = video.file_id
        file_size = video.file_size
        file_name = video.file_name or "unknown"
        
        # For video messages, get duration and dimensions
        if hasattr(video, 'duration'):
            duration = video.duration
            width = video.width
            height = video.height
        else:
            # For document videos, we don't have these properties
            duration = 0
            width = 0
            height = 0
        
        file_size_mb = file_size / (1024 * 1024) if file_size else 0
        
        logger.info(f"Admin video upload: file_id={file_id}, size={file_size_mb:.2f}MB, duration={duration}s, resolution={width}x{height}")
        
        # Store video info in context for metadata collection
        context.user_data["video_metadata"]["original_file_id"] = file_id
        context.user_data["video_metadata"]["file_size"] = file_size_mb
        context.user_data["video_metadata"]["duration"] = duration
        context.user_data["video_metadata"]["resolution"] = f"{width}x{height}"
        context.user_data["video_metadata"]["file_name"] = file_name
        
        # Start metadata collection process
        context.user_data["file_state"] = None
        context.user_data["text_state"] = admin_collect_video_title
        
        # Build message with available info
        message_parts = ["✅ **Видео получено!**", "", f"📊 **Размер**: {file_size_mb:.2f} MB"]
        
        if duration > 0:
            message_parts.append(f"⏱️ **Длительность**: {duration} секунд")
        
        if width > 0 and height > 0:
            message_parts.append(f"📐 **Разрешение**: {width}x{height}")
        
        message_parts.extend([
            f"📝 **Имя файла**: {file_name}",
            "",
            "Теперь введите **название** для видео:"
        ])
        
        await update.message.reply_text(
            "\n".join(message_parts),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error processing admin video upload: {e}")
        await update.message.reply_text(f"❌ Ошибка при обработке видео: {str(e)}")
        context.user_data["file_state"] = None

async def admin_collect_video_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collect video title from user input"""
    title = update.message.text.strip()
    
    if not title:
        await update.message.reply_text("❌ Название не может быть пустым. Попробуйте еще раз:")
        return
    
    context.user_data["video_metadata"]["title"] = title
    context.user_data["text_state"] = admin_collect_video_description
    
    await update.message.reply_text(
        f"✅ Название: **{title}**\n\nТеперь введите **описание** для видео (или отправьте \"-\" чтобы пропустить):",
        parse_mode="Markdown"
    )

async def admin_collect_video_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collect video description from user input"""
    description = update.message.text.strip()
    
    if description == "-":
        description = ""
    
    context.user_data["video_metadata"]["description"] = description
    context.user_data["text_state"] = admin_collect_video_category
    
    # Get available categories from database
    categories = rep_chess_db.get_all_categories()
    
    if not categories:
        # If no categories exist, create default "Начинающий" category
        rep_chess_db.add_category("Начинающий")
        categories = ["Начинающий"]
    
    # Create keyboard with available categories
    keyboard_buttons = []
    for category in categories:
        keyboard_buttons.append([InlineKeyboardButton(
            category, 
            callback_data=f"category_{category}"
        )])
    
    # Add option to create new category
    keyboard_buttons.append([InlineKeyboardButton("➕ Создать новую категорию", callback_data="create_new_category")])
    
    category_keyboard = InlineKeyboardMarkup(keyboard_buttons)
    
    desc_text = f"Описание: **{description}**" if description else "Описание: *не указано*"
    
    await update.message.reply_text(
        f"✅ {desc_text}\n\nВыберите **категорию** для видео:",
        reply_markup=category_keyboard,
        parse_mode="Markdown"
    )

async def admin_collect_video_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category selection"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "create_new_category":
        # Handle new category creation
        context.user_data["text_state"] = admin_create_new_category
        await query.edit_message_text(
            "➕ **Создание новой категории**\n\nВведите название новой категории:",
            parse_mode="Markdown"
        )
        return
    
    # Extract category name from callback data
    if query.data.startswith("category_"):
        category = query.data.replace("category_", "")
        
        # Verify category exists
        if not rep_chess_db.category_exists(category):
            await query.edit_message_text("❌ Категория не найдена. Попробуйте еще раз.")
            return
        
        context.user_data["video_metadata"]["category"] = category
        context.user_data["text_state"] = admin_collect_video_lesson_number
        
        await query.edit_message_text(
            f"✅ Категория: **{category}**\n\nВведите **номер урока** для этого видео (или отправьте \"-\" для автоматического номера):",
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text("❌ Неверная категория. Попробуйте еще раз.")
        return

async def admin_create_new_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new category creation"""
    category_name = update.message.text.strip()
    
    if not category_name:
        await update.message.reply_text("❌ Название категории не может быть пустым. Попробуйте еще раз:")
        return
    
    # Check if category already exists
    if rep_chess_db.category_exists(category_name):
        await update.message.reply_text(f"❌ Категория **{category_name}** уже существует. Выберите другую или используйте существующую:")
        return
    
    # Create new category
    success = rep_chess_db.add_category(category_name)
    if not success:
        await update.message.reply_text("❌ Ошибка при создании категории. Попробуйте еще раз:")
        return
    
    # Set the new category and continue with video upload
    context.user_data["video_metadata"]["category"] = category_name
    context.user_data["text_state"] = admin_collect_video_lesson_number
    
    await update.message.reply_text(
        f"✅ Категория **{category_name}** создана!\n\nВведите **номер урока** для этого видео (или отправьте \"-\" для автоматического номера):",
        parse_mode="Markdown"
    )

async def admin_collect_video_lesson_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collect lesson number from user input"""
    lesson_input = update.message.text.strip()
    
    if lesson_input == "-":
        # Auto-assign lesson number
        category = context.user_data["video_metadata"]["category"]
        lesson_number = rep_chess_db.get_next_lesson_number(category)
        context.user_data["video_metadata"]["lesson_number"] = lesson_number
        
        await update.message.reply_text(
            f"✅ Номер урока: **{lesson_number}** (автоматически)\n\n🎬 **Начинаю обработку видео...**\n\nВидео будет автоматически конвертировано в 480p и 1080p. Это может занять несколько минут.",
            parse_mode="Markdown"
        )
        # Call the function directly instead of setting it as text state
        await admin_save_video_and_process(update, context)
        return
    
    try:
        lesson_number = int(lesson_input)
        if lesson_number <= 0:
            await update.message.reply_text("❌ Номер урока должен быть положительным числом. Попробуйте еще раз:")
            return
        
        context.user_data["video_metadata"]["lesson_number"] = lesson_number
        
        await update.message.reply_text(
            f"✅ Номер урока: **{lesson_number}**\n\n🎬 **Начинаю обработку видео...**\n\nВидео будет автоматически конвертировано в 480p и 1080p. Это может занять несколько минут.",
            parse_mode="Markdown"
        )
        # Call the function directly instead of setting it as text state
        await admin_save_video_and_process(update, context)
        
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите корректный номер урока (число) или \"-\" для автоматического номера:")

async def admin_save_video_and_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save video to database and start processing"""
    try:
        metadata = context.user_data["video_metadata"]
        category = metadata["category"]
        lesson_number = metadata["lesson_number"]
    
        deleted_count = rep_chess_db.delete_videos_by_category_and_lesson(
            category=category,
            lesson_number=lesson_number,
            statuses=['pending', 'failed']
        )
        
        if deleted_count > 0:
            logger.info(
                f"Cleaned up {deleted_count} existing video(s) with category={category}, "
                f"lesson_number={lesson_number} before adding new video"
            )
        
        # Save video to database with pending status
        rep_chess_db.add_video(
            file_id_480p=None,
            file_id_1080p=None,
            title=metadata["title"],
            description=metadata["description"],
            category=category,
            lesson_number=lesson_number,
            original_file_id=metadata["original_file_id"],
            processing_status="pending"
        )
        
        # Get the video ID that was just created
        videos = rep_chess_db.get_videos_by_category(category)
        if not videos:
            await update.message.reply_text("❌ Ошибка: не удалось найти созданное видео.")
            return
        video_id = videos[-1]["id"]
        
        # Clear context data
        context.user_data["video_metadata"] = {}
        context.user_data["text_state"] = None
        
        # Show initial processing message
        cleanup_msg = f"\n\n(Удалено {deleted_count} старых видео с этим номером урока)" if deleted_count > 0 else ""
        initial_message = await update.message.reply_text(
            f"""🎬 **Начинаю обработку видео...**

📝 **{metadata['title']}**

Видео будет автоматически конвертировано в 480p и 1080p. Это может занять несколько минут.{cleanup_msg}""",
            reply_markup=video_management_keyboard,
            parse_mode="Markdown"
        )
        
        # Start background processing with the initial message
        asyncio.create_task(process_video_background(context.bot, video_id, metadata, update.effective_chat.id, initial_message))
        
    except Exception as e:
        logger.error(f"Error saving video to database: {e}")
        await update.message.reply_text(
            f"❌ Ошибка при сохранении видео: {str(e)}",
            reply_markup=video_management_keyboard
        )

async def process_video_background(bot, video_id: int, metadata: dict, chat_id: int, initial_message=None):
    """Background task to process video with progress notifications"""
    progress_message = initial_message
    
    async def progress_callback(percentage: int, message: str):
        """Send progress updates to admin"""
        nonlocal progress_message
        try:
            # Create progress bar
            progress_bar = "█" * (percentage // 5) + "░" * (20 - percentage // 5)
            progress_text = f"🎬 **Обработка видео**\n\n📝 **{metadata['title']}**\n\n{message}\n\n`[{progress_bar}] {percentage}%`"
            
            if progress_message:
                # Edit existing message
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=progress_message.message_id,
                    text=progress_text,
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.warning(f"Failed to send progress update: {e}")
    
    try:
        processor = VideoProcessor(bot, progress_callback=progress_callback)
        
        # Check if FFmpeg is available
        if not processor.check_ffmpeg_available():
            # Delete video from database since FFmpeg is not available
            rep_chess_db.delete_video(video_id)
            
            error_msg = f"""❌ **Критическая ошибка обработки**

📝 **{metadata['title']}**

Видео не удалось обработать."""
            logger.error("FFmpeg is not available on the system")
            
            if progress_message:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=progress_message.message_id,
                    text=error_msg,
                    parse_mode="Markdown"
                )
            else:
                await bot.send_message(chat_id=chat_id, text=error_msg, parse_mode="Markdown")
            return
        
        # Process video
        file_id_480p, file_id_1080p = await processor.process_video(
            metadata["original_file_id"],
            video_id,
            metadata["title"],
            str(chat_id)
        )
        
        if file_id_480p and file_id_1080p:
            # Update database with processed file IDs
            rep_chess_db.update_video_quality(
                video_id,
                file_id_480p=file_id_480p,
                file_id_1080p=file_id_1080p,
                processing_status="completed"
            )
            
            # Build success message with video details
            message_parts = [
                "🎉 **Видео успешно обработано!**",
                "",
                f"📝 **Название**: {metadata['title']}",
                f"📄 **Описание**: {metadata['description'] if metadata['description'] else 'не указано'}",
                f"🏷️ **Категория**: {metadata['category']}",
                f"🔢 **Урок**: {metadata['lesson_number']}",
                f"📊 **Размер**: {metadata['file_size']:.2f} MB"
            ]
            
            # Only show duration if it's not 0
            if metadata.get("duration", 0) > 0:
                message_parts.append(f"⏱️ **Длительность**: {metadata['duration']} сек")
            
            # Only show resolution if it's not 0x0
            if metadata.get("resolution") and metadata["resolution"] != "0x0":
                message_parts.append(f"📐 **Разрешение**: {metadata['resolution']}")
            
            message_parts.extend([
                "",
                "🎬 **Доступные качества**:",
                "• 480p (среднее качество)",
                "• 1080p (высокое качество)",
                "",
                "Видео готово к просмотру!"
            ])
            
            success_msg = "\n".join(message_parts)
            
            logger.info(f"Video {video_id} processed successfully")
            
            if progress_message:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=progress_message.message_id,
                    text=success_msg,
                    parse_mode="Markdown",
                    reply_markup=video_management_keyboard
                )
            else:
                await bot.send_message(
                    chat_id=chat_id, 
                    text=success_msg, 
                    parse_mode="Markdown",
                    reply_markup=video_management_keyboard
                )
        else:
            # Delete failed video from database
            rep_chess_db.delete_video(video_id)
            
            error_msg = f"""❌ **Ошибка обработки видео**

📝 **{metadata['title']}**

Видео не удалось обработать."""
            
            logger.error(f"Video {video_id} processing failed - deleted from database")
            
            if progress_message:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=progress_message.message_id,
                    text=error_msg,
                    parse_mode="Markdown",
                    reply_markup=video_management_keyboard
                )
            else:
                await bot.send_message(
                    chat_id=chat_id, 
                    text=error_msg, 
                    parse_mode="Markdown",
                    reply_markup=video_management_keyboard
                )
            
    except Exception as e:
        # Delete failed video from database
        rep_chess_db.delete_video(video_id)
        
        error_msg = f"""❌ **Критическая ошибка обработки**

📝 **{metadata['title']}**

Видео не удалось обработать."""
        
        logger.error(f"Error in background video processing: {e}", exc_info=True)
        
        if progress_message:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=progress_message.message_id,
                text=error_msg,
                parse_mode="Markdown"
            )
        else:
            await bot.send_message(chat_id=chat_id, text=error_msg, parse_mode="Markdown")

async def admin_show_uploaded_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of uploaded videos"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Get all videos from database
        all_videos = rep_chess_db.get_all_videos()
        
        # Filter out failed videos, placeholder videos, and videos without proper status
        videos = []
        for video in all_videos:
            status = video.get('processing_status', 'unknown')
            # Skip failed, unknown, or empty status
            if status in ['failed', 'unknown'] or not status:
                continue
            
            # Skip placeholder videos (videos with no actual content)
            if (not video.get('file_id_480p') or video.get('file_id_480p') == 'placeholder' or
                not video.get('file_id_1080p') or video.get('file_id_1080p') == 'placeholder'):
                continue
                
            videos.append(video)
        
        if not videos:
            await query.edit_message_text(
                "📋 **Загруженные видео**\n\nВидео пока не загружены.",
                reply_markup=video_management_keyboard,
                parse_mode="Markdown"
            )
            return
        
        # Group videos by category
        categories = {}
        for video in videos:
            category = video["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append(video)
        
        # Create message with video list
        message_text = "📋 **Загруженные видео**\n\n"
        
        for category, category_videos in categories.items():
            message_text += f"🏷️ **{category}** ({len(category_videos)} видео):\n"
            for video in category_videos:
                lesson_info = f"Урок {video['lesson_number']}" if video['lesson_number'] else "Без номера"
                
                # Show processing status
                status_emoji = {
                    "completed": "✅",
                    "pending": "⏳",
                    "failed": "❌"
                }.get(video.get('processing_status', 'unknown'), "❓")
                
                qualities = []
                if video.get('file_id_480p') and video['file_id_480p'] != 'placeholder':
                    qualities.append("480p")
                if video.get('file_id_1080p') and video['file_id_1080p'] != 'placeholder':
                    qualities.append("1080p")
                
                quality_text = f" ({', '.join(qualities)})" if qualities else ""
                status_text = f" [{video.get('processing_status', 'unknown')}]" if video.get('processing_status') != 'completed' else ""
                
                message_text += f"• {lesson_info}: {video['title']}{quality_text}{status_text} {status_emoji}\n"
                if video['description']:
                    message_text += f"  📄 {video['description'][:50]}{'...' if len(video['description']) > 50 else ''}\n"
            message_text += "\n"
        
        # Add pagination if needed (for now, just show all)
        if len(message_text) > 4000:  # Telegram message limit
            message_text = message_text[:3900] + "\n\n... (список обрезан)"
        
        await query.edit_message_text(
            message_text,
            reply_markup=video_management_keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error fetching videos: {e}")
        await query.edit_message_text(
            f"❌ Ошибка при получении списка видео: {str(e)}",
            reply_markup=video_management_keyboard
        )

async def admin_delete_video_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show delete video menu"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Get all videos from database
        videos = rep_chess_db.get_all_videos()
        
        if not videos:
            await query.edit_message_text(
                "🗑️ **Удаление видео**\n\nВидео для удаления не найдены.",
                reply_markup=video_management_keyboard,
                parse_mode="Markdown"
            )
            return
        
        # Create keyboard with video options (limit to first 10 for UI)
        keyboard_buttons = []
        for video in videos[:10]:  # Limit to 10 videos for UI
            lesson_info = f"Урок {video['lesson_number']}" if video['lesson_number'] else "Без номера"
            button_text = f"{lesson_info}: {video['title']}"
            if len(button_text) > 50:  # Telegram button text limit
                button_text = button_text[:47] + "..."
            keyboard_buttons.append([InlineKeyboardButton(
                button_text, 
                callback_data=f"delete_video_{video['id']}"
            )])
        
        # Add navigation buttons
        keyboard_buttons.append([InlineKeyboardButton("<< Назад", callback_data="admin_video_management")])
        
        delete_keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        message_text = f"🗑️ **Удаление видео**\n\nВыберите видео для удаления:\n\nВсего видео: {len(videos)}"
        if len(videos) > 10:
            message_text += f"\n(показаны первые 10)"
        
        await query.edit_message_text(
            message_text,
            reply_markup=delete_keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error fetching videos for deletion: {e}")
        await query.edit_message_text(
            f"❌ Ошибка при получении списка видео: {str(e)}",
            reply_markup=video_management_keyboard
        )

async def admin_confirm_delete_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle video deletion confirmation"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Extract video ID from callback data
        video_id = int(query.data.split("_")[-1])
        
        # Get video info
        video = rep_chess_db.get_video_by_id(video_id)
        if not video:
            await query.edit_message_text(
                "❌ Видео не найдено.",
                reply_markup=video_management_keyboard
            )
            return
        
        # Store video ID for confirmation
        context.user_data["video_to_delete"] = video_id
        
        # Create confirmation keyboard
        confirm_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_{video_id}")],
            [InlineKeyboardButton("❌ Отмена", callback_data="admin_delete_video")]
        ])
        
        # Get processing status and available qualities
        status_emoji = {
            "completed": "✅",
            "pending": "⏳", 
            "failed": "❌"
        }.get(video.get('processing_status', 'unknown'), "❓")
        
        qualities = []
        if video.get('file_id_480p') and video['file_id_480p'] != 'placeholder':
            qualities.append("480p")
        if video.get('file_id_1080p') and video['file_id_1080p'] != 'placeholder':
            qualities.append("1080p")
        
        quality_text = f" ({', '.join(qualities)})" if qualities else " (не обработано)"
        
        await query.edit_message_text(
            f"""🗑️ **Подтверждение удаления**

📝 **Название**: {video['title']}
🏷️ **Категория**: {video['category']}
🔢 **Урок**: {video['lesson_number'] if video['lesson_number'] else 'Без номера'}
🎬 **Статус**: {status_emoji} {video.get('processing_status', 'unknown')}{quality_text}
📄 **Описание**: {video['description'] if video['description'] else 'не указано'}

⚠️ **Вы уверены, что хотите удалить это видео?**

Это действие нельзя отменить!""",
            reply_markup=confirm_keyboard,
            parse_mode="Markdown"
        )
        
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing video ID from callback: {e}")
        await query.edit_message_text(
            "❌ Ошибка при обработке запроса.",
            reply_markup=video_management_keyboard
        )

async def admin_execute_delete_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute video deletion"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Extract video ID from callback data
        video_id = int(query.data.split("_")[-1])
        
        # Get video info before deletion
        video = rep_chess_db.get_video_by_id(video_id)
        if not video:
            await query.edit_message_text(
                "❌ Видео не найдено.",
                reply_markup=video_management_keyboard
            )
            return
        
        # Delete video from database
        success = rep_chess_db.delete_video(video_id)
        
        if success:
            lesson_info = f"Урок {video['lesson_number']}" if video['lesson_number'] else "Без номера"
            await query.edit_message_text(
                f"""✅ **Видео успешно удалено!**

📝 **Название**: {video['title']}
🏷️ **Категория**: {video['category']}
🔢 **Урок**: {lesson_info}

Видео было удалено из базы данных.""",
                reply_markup=video_management_keyboard,
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                "❌ Ошибка при удалении видео.",
                reply_markup=video_management_keyboard
            )
        
        # Clear context data
        context.user_data.pop("video_to_delete", None)
        
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing video ID from callback: {e}")
        await query.edit_message_text(
            "❌ Ошибка при обработке запроса.",
            reply_markup=video_management_keyboard
        )

async def admin_manage_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show category management menu"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Get all categories
        categories = rep_chess_db.get_all_categories()
        
        if not categories:
            await query.edit_message_text(
                "🏷️ **Управление категориями**\n\nКатегории не найдены.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Создать категорию", callback_data="admin_create_category")],
                    [InlineKeyboardButton("<< Назад", callback_data="admin_video_management")]
                ]),
                parse_mode="Markdown"
            )
            return
        
        # Create keyboard with categories
        keyboard_buttons = []
        for category in categories:
            # Count videos in this category
            videos_count = len(rep_chess_db.get_videos_by_category(category))
            button_text = f"{category} ({videos_count} видео)"
            if len(button_text) > 50:
                button_text = button_text[:47] + "..."
            keyboard_buttons.append([InlineKeyboardButton(
                button_text,
                callback_data=f"manage_category_{category}"
            )])
        
        # Add create and back buttons
        keyboard_buttons.append([InlineKeyboardButton("➕ Создать категорию", callback_data="admin_create_category")])
        keyboard_buttons.append([InlineKeyboardButton("<< Назад", callback_data="admin_video_management")])
        
        category_management_keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        await query.edit_message_text(
            f"🏷️ **Управление категориями**\n\nВыберите категорию для управления:\n\nВсего категорий: {len(categories)}",
            reply_markup=category_management_keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        await query.edit_message_text(
            f"❌ Ошибка при получении категорий: {str(e)}",
            reply_markup=video_admin_keyboard
        )

async def admin_create_category_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show create category menu"""
    query = update.callback_query
    await query.answer()
    
    context.user_data["text_state"] = admin_create_category_handler
    
    await query.edit_message_text(
        "➕ **Создание новой категории**\n\nВведите название новой категории:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("<< Назад", callback_data="admin_manage_categories")]
        ]),
        parse_mode="Markdown"
    )

async def admin_create_category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category creation"""
    category_name = update.message.text.strip()
    
    if not category_name:
        await update.message.reply_text("❌ Название категории не может быть пустым. Попробуйте еще раз:")
        return
    
    # Check if category already exists
    if rep_chess_db.category_exists(category_name):
        await update.message.reply_text(f"❌ Категория **{category_name}** уже существует. Выберите другое название:")
        return
    
    # Create new category
    success = rep_chess_db.add_category(category_name)
    if not success:
        await update.message.reply_text("❌ Ошибка при создании категории. Попробуйте еще раз:")
        return
    
    context.user_data["text_state"] = None
    
    await update.message.reply_text(
        f"✅ Категория **{category_name}** успешно создана!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏷️ Управление категориями", callback_data="admin_manage_categories")],
            [InlineKeyboardButton("<< Назад в видео", callback_data="admin_video_management")]
        ]),
        parse_mode="Markdown"
    )

async def admin_manage_specific_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show specific category management options"""
    query = update.callback_query
    await query.answer()
    
    # Extract category name from callback data
    category_name = query.data.replace("manage_category_", "")
    
    try:
        # Get videos in this category
        videos = rep_chess_db.get_videos_by_category(category_name)
        
        await query.edit_message_text(
            f"🏷️ **Категория: {category_name}**\n\nКоличество видео: {len(videos)}\n\nВыберите действие:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Показать видео", callback_data=f"show_category_videos_{category_name}")],
                [InlineKeyboardButton("🗑️ Удалить категорию", callback_data=f"delete_category_{category_name}")],
                [InlineKeyboardButton("<< Назад к категориям", callback_data="admin_manage_categories")]
            ]),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error managing category {category_name}: {e}")
        await query.edit_message_text(
            f"❌ Ошибка при управлении категорией: {str(e)}",
            reply_markup=video_admin_keyboard
        )

async def admin_show_category_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show videos in specific category"""
    query = update.callback_query
    await query.answer()
    
    # Extract category name from callback data
    category_name = query.data.replace("show_category_videos_", "")
    
    try:
        videos = rep_chess_db.get_videos_by_category_ordered(category_name)
        
        if not videos:
            await query.edit_message_text(
                f"📋 **{category_name}**\n\nВидео в этой категории не найдены.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("<< Назад к категории", callback_data=f"manage_category_{category_name}")]
                ]),
                parse_mode="Markdown"
            )
            return
        
        # Create message with video list
        message_text = f"📋 **{category_name}**\n\n"
        for video in videos:
            lesson_info = f"Урок {video['lesson_number']}" if video['lesson_number'] else "Без номера"
            message_text += f"• {lesson_info}: {video['title']} ({video['quality']})\n"
            if video['description']:
                message_text += f"  📄 {video['description'][:50]}{'...' if len(video['description']) > 50 else ''}\n"
        
        # Add pagination if needed
        if len(message_text) > 4000:
            message_text = message_text[:3900] + "\n\n... (список обрезан)"
        
        await query.edit_message_text(
            message_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("<< Назад к категории", callback_data=f"manage_category_{category_name}")]
            ]),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error showing category videos: {e}")
        await query.edit_message_text(
            f"❌ Ошибка при получении видео: {str(e)}",
            reply_markup=video_admin_keyboard
        )

async def admin_confirm_delete_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm category deletion"""
    query = update.callback_query
    await query.answer()
    
    # Extract category name from callback data
    category_name = query.data.replace("delete_category_", "")
    
    try:
        # Get videos in this category
        videos = rep_chess_db.get_videos_by_category(category_name)
        videos_count = len(videos)
        
        await query.edit_message_text(
            f"🗑️ **Подтверждение удаления категории**\n\n"
            f"🏷️ **Категория**: {category_name}\n"
            f"📊 **Количество видео**: {videos_count}\n\n"
            f"⚠️ **ВНИМАНИЕ!** Это действие удалит категорию и ВСЕ видео в ней!\n\n"
            f"Вы уверены, что хотите удалить категорию **{category_name}**?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_category_{category_name}")],
                [InlineKeyboardButton("❌ Отмена", callback_data=f"manage_category_{category_name}")]
            ]),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error confirming category deletion: {e}")
        await query.edit_message_text(
            f"❌ Ошибка при подтверждении удаления: {str(e)}",
            reply_markup=video_admin_keyboard
        )

async def admin_execute_delete_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute category deletion"""
    query = update.callback_query
    await query.answer()
    
    # Extract category name from callback data
    category_name = query.data.replace("confirm_delete_category_", "")
    
    try:
        # Get videos count before deletion
        videos = rep_chess_db.get_videos_by_category(category_name)
        videos_count = len(videos)
        
        # Delete category and all its videos
        success = rep_chess_db.delete_category(category_name)
        
        if success:
            await query.edit_message_text(
                f"✅ **Категория успешно удалена!**\n\n"
                f"🏷️ **Категория**: {category_name}\n"
                f"📊 **Удалено видео**: {videos_count}\n\n"
                f"Категория и все связанные видео были удалены из базы данных.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏷️ Управление категориями", callback_data="admin_manage_categories")],
                    [InlineKeyboardButton("<< Назад в видео", callback_data="admin_video_management")]
                ]),
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                "❌ Ошибка при удалении категории.",
                reply_markup=video_admin_keyboard
            )
        
    except Exception as e:
        logger.error(f"Error executing category deletion: {e}")
        await query.edit_message_text(
            f"❌ Ошибка при удалении категории: {str(e)}",
            reply_markup=video_admin_keyboard
        )

async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unified text handler for admin video management"""
    # Only handle text messages if we're in a video management text state
    if ("text_state" in context.user_data and 
        context.user_data["text_state"] and 
        context.user_data["text_state"].__name__ in [
            'admin_collect_video_title',
            'admin_collect_video_description', 
            'admin_collect_video_category',
            'admin_collect_video_lesson_number'
        ]):
        # Call the appropriate handler based on current state
        await context.user_data["text_state"](update, context)
    else:
        # Not in video management state, let other handlers process this
        return

async def admin_cancel_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel video upload process"""
    context.user_data["file_state"] = None
    context.user_data["text_state"] = None
    context.user_data.pop("video_metadata", None)
    
    await update.message.reply_text(
        "❌ Загрузка видео отменена.",
        reply_markup=video_admin_keyboard
    )

async def callback_admin_video_management_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_video_management(update, context)

async def callback_admin_start_upload_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_start_upload(update, context)

async def callback_admin_show_videos_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_show_uploaded_videos(update, context)

async def callback_admin_delete_video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_delete_video_menu(update, context)

async def callback_admin_confirm_delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_confirm_delete_video(update, context)

async def callback_admin_execute_delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_execute_delete_video(update, context)

async def callback_admin_category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_collect_video_category(update, context)

async def callback_admin_save_video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_save_video_and_process(update, context)

async def callback_admin_manage_categories_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_manage_categories(update, context)

async def callback_admin_create_category_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_create_category_menu(update, context)

async def callback_admin_manage_specific_category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_manage_specific_category(update, context)

async def callback_admin_show_category_videos_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_show_category_videos(update, context)

async def callback_admin_confirm_delete_category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_confirm_delete_category(update, context)

async def callback_admin_execute_delete_category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_execute_delete_category(update, context)

admin_video_management_handlers = [
    CallbackQueryHandler(callback_admin_video_management_handler, pattern="^admin_video_management$"),
    CallbackQueryHandler(callback_admin_start_upload_handler, pattern="^admin_upload_video$"),
    CallbackQueryHandler(callback_admin_show_videos_handler, pattern="^admin_show_videos$"),
    CallbackQueryHandler(callback_admin_delete_video_handler, pattern="^admin_delete_video$"),
    CallbackQueryHandler(callback_admin_confirm_delete_handler, pattern="^delete_video_"),
    CallbackQueryHandler(callback_admin_execute_delete_handler, pattern="^confirm_delete_"),
    CallbackQueryHandler(callback_admin_category_handler, pattern="^category_"),
    CallbackQueryHandler(callback_admin_manage_categories_handler, pattern="^admin_manage_categories$"),
    CallbackQueryHandler(callback_admin_create_category_menu_handler, pattern="^admin_create_category$"),
    CallbackQueryHandler(callback_admin_manage_specific_category_handler, pattern="^manage_category_"),
    CallbackQueryHandler(callback_admin_show_category_videos_handler, pattern="^show_category_videos_"),
    CallbackQueryHandler(callback_admin_confirm_delete_category_handler, pattern="^delete_category_"),
    CallbackQueryHandler(callback_admin_execute_delete_category_handler, pattern="^confirm_delete_category_"),
    CallbackQueryHandler(admin_main_menu, pattern="^go_admin_menu$"),
    MessageHandler(filters.Regex("^/cancel$"), admin_cancel_upload),
]
