import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

# Define the sample video file_id for each level (replace with actual file_id)
sample_videos = {
    'level_1': 'sample_video_file_id_level_1',
    'level_2': 'sample_video_file_id_level_2',
    'level_3': 'sample_video_file_id_level_3'
}

# Helper function to create the "Let's Try" and "Главное меню" buttons
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

    # Create buttons for the three video levels
    video_kb = [
        [InlineKeyboardButton("Видео для Уровня 1", callback_data="sample_level_1")],
        [InlineKeyboardButton("Видео для Уровня 2", callback_data="sample_level_2")],
        [InlineKeyboardButton("Видео для Уровня 3", callback_data="sample_level_3")]
    ]
    reply_markup = InlineKeyboardMarkup(video_kb)

    # Ask the user to choose a video level
    await query.message.reply_text("Выберите видео для вашего уровня:", reply_markup=reply_markup)

# Handle the selection of a video based on the level
async def handle_video_level_selection(update: Update, context):
    query = update.callback_query
    await query.answer()

    # Determine which video to send based on the button clicked
    level_map = {
        'sample_level_1': 'level_1',
        'sample_level_2': 'level_2',
        'sample_level_3': 'level_3'
    }

    selected_level = level_map[query.data]
    video_id = sample_videos[selected_level]

    # Send the video with action buttons ("Let's Try" and "Главное меню")
    await query.message.reply_video(
        video=video_id,
        caption=f"Вот видео для Уровня {selected_level[-1]}",
        reply_markup=action_buttons(),
        protect_content=True  # Prevent the user from downloading/forwarding the video
    )

    logger.info(f"Sent sample video for level {selected_level} to user {query.from_user.id}.")

