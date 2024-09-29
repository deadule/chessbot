import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

# Define the sample video file_id for each level (replace with actual file_id
sample_videos = {
    'level_1': 'AAMCAgADGQEBhuW8Zu6seD3g8jDpeSqFqufiWLJMA5wAAvFTAAIgkHhLRPKb2_1N9OoBAAdtAAM2BA
',
    'level_2': 'AAMCAgADGQEBhuW8Zu6seD3g8jDpeSqFqufiWLJMA5wAAvFTAAIgkHhLRPKb2_1N9OoBAAdtAAM2BA
',
    'level_3': 'AAMCAgADGQEBhuW8Zu6seD3g8jDpeSqFqufiWLJMA5wAAvFTAAIgkHhLRPKb2_1N9OoBAAdtAAM2BA
'
}

# Helper function to create the "Let's Try", "Главное меню", and "Return" buttons
def action_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Let's Try", callback_data="lets_try")],
        [InlineKeyboardButton("Главное меню", callback_data="return_main_menu")],
        [InlineKeyboardButton("Return", callback_data="sample_video_return_to_levels")]
    ])

# Return button for returning to the video level selection step
def video_level_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Видео для Уровня 1", callback_data="sample_level_1")],
        [InlineKeyboardButton("Видео для Уровня 2", callback_data="sample_level_2")],
        [InlineKeyboardButton("Видео для Уровня 3", callback_data="sample_level_3")],
        [InlineKeyboardButton("Return", callback_data="return_main_menu")]
    ])

# Handle the "Посмотреть Пробное Видео" button
async def handle_sample_video(update: Update, context):
    query = update.callback_query
    await query.answer()

    logger.info(f"User {query.from_user.id} selected 'Посмотреть Пробное Видео'.")

    # Display buttons for selecting the video levels
    await query.message.reply_text("Выберите видео для вашего уровня:", reply_markup=video_level_buttons())

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

    # Send the video with action buttons ("Let's Try", "Главное меню", and "Return")
    await query.message.reply_video(
        video=video_id,
        caption=f"Вот видео для Уровня {selected_level[-1]}",
        reply_markup=action_buttons(),
        protect_content=True  # Prevent the user from downloading/forwarding the video
    )

    logger.info(f"Sent sample video for level {selected_level} to user {query.from_user.id}.")

# Handle the return to the video level selection step
async def handle_return_to_video_levels(update: Update, context):
    query = update.callback_query
    await query.answer()

    # Return to the video level selection step
    await query.message.reply_text("Возврат к выбору видео для вашего уровня:", reply_markup=video_level_buttons())
    logger.info(f"User {query.from_user.id} returned to video level selection.")

