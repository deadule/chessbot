import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

# Define the sample video file_id for each level
sample_videos = {
    'level_1': 'AAMCAgADGQEBjAupZvk703rUlXtnNAwKe-_3U1112OMAAlpTAALMEclLAY6thrApV4gBAAdtAAM2BA',  # Example file_id
    # Add other levels as needed
}

# Helper function to create the action buttons
def action_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Let's Try", callback_data="lets_try")],
        [InlineKeyboardButton("Главное меню", callback_data="return_main_menu")]
    ])

# Handle the selection of a video based on the level
async def handle_sample_video(update: Update, context):
    query = update.callback_query
    await query.answer()

    # Add detailed logging
    logger.info(f"User {query.from_user.id} selected a video level. Callback data: {query.data}")

    # Determine which video to send based on the button clicked
    level_map = {
        'sample_level_1': 'level_1'
        # Add more levels if needed
    }

    selected_level = level_map.get(query.data)

    # If the selected level is invalid, log it and return
    if selected_level is None:
        logger.error(f"Invalid video level selected: {query.data}")
        await query.message.reply_text("Invalid video level selected.")
        return

    # Get the corresponding video_id
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
