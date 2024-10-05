import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

# Define the file_id for each video (Replace with actual file_id)
sample_videos = {
    'level_1': 'BAACAgIAAxkBAANqZwAB78tI-rqQKNQcXED4DmE0qs2FAAIMVAACBeUISCwVSWpKiDVdNgQ',  # Replace with actual file_id
    'level_2': 'BAACAgIAAxkBAANqZwAB78tI-rqQKNQcXED4DmE0qs2FAAIMVAACBeUISCwVSWpKiDVdNgQ',  # Replace with actual file_id
    'level_3': 'BAACAgIAAxkBAANqZwAB78tI-rqQKNQcXED4DmE0qs2FAAIMVAACBeUISCwVSWpKiDVdNgQ'  # Replace with actual file_id
}

# Helper function to create the action buttons
def action_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Let's Try", callback_data="lets_try")],
        [InlineKeyboardButton("Главное меню", callback_data="return_main_menu")]
    ])

# Handle the "Посмотреть Пробное Видео" button
async def handle_sample_video(update: Update, context):
    query = update.callback_query
    await query.answer()

    logger.info(f"User {query.from_user.id} selected 'Посмотреть Пробное Видео'.")

    # Create buttons for selecting a video for each level
    video_kb = [
        [InlineKeyboardButton("Видео для Уровня 1", callback_data="sample_level_1")],
        [InlineKeyboardButton("Видео для Уровня 2", callback_data="sample_level_2")],
        [InlineKeyboardButton("Видео для Уровня 3", callback_data="sample_level_3")],
        [InlineKeyboardButton("Return", callback_data="return_main_menu")]  # Add return button
    ]
    reply_markup = InlineKeyboardMarkup(video_kb)

    # Ask the user to choose a video level
    await query.message.reply_text("Выберите видео для вашего уровня:", reply_markup=reply_markup)

# Handle the selection of a video based on the level
async def handle_video_level_selection(update: Update, context):
    query = update.callback_query
    await query.answer()

    logger.info(f"User {query.from_user.id} selected a video level. Callback data: {query.data}")

    # Mapping callback data to video levels
    level_map = {
        'sample_level_1': 'level_1',
        'sample_level_2': 'level_2',
        'sample_level_3': 'level_3'
    }

    # Get the selected level from the callback data
    selected_level = level_map.get(query.data)

    # If the selected level is invalid, log it and return
    if selected_level is None:
        logger.error(f"Invalid video level selected: {query.data}")
        await query.message.reply_text("Invalid video level selected.")
        return

    # Get the corresponding video_id from sample_videos
    video_id = sample_videos.get(selected_level)

    # If no video_id exists, log it and return
    if video_id is None:
        logger.error(f"No video found for level {selected_level}")
        await query.message.reply_text(f"No video found for level {selected_level}.")
        return

    # Send the video and log the action
    try:
        await query.message.reply_video(
            video=video_id,
            caption=f"Вот видео для Уровня {selected_level[-1]}",
            reply_markup=action_buttons(),
            protect_content=True  # Prevent downloading/forwarding
        )
        logger.info(f"Sent sample video for level {selected_level} to user {query.from_user.id}.")
    except Exception as e:
        logger.error(f"Failed to send video for level {selected_level}. Error: {e}")
        await query.message.reply_text(f"Failed to send video for level {selected_level}. Please try again.")
