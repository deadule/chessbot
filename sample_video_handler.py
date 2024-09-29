import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

# Define the sample video file_id (replace with actual file_id)
sample_video_file_id = 'sample_video_file_id_here'

# Handle the "Посмотреть Пробное Видео" button
async def handle_sample_video(update: Update, context):
    query = update.callback_query
    await query.answer()

    logger.info(f"User {query.from_user.id} selected 'Посмотреть Пробное Видео'.")

    # Create return button to go back to the main menu
    return_kb = [
        [InlineKeyboardButton("Return", callback_data="return_main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(return_kb)

    # Send the sample video to the user
    await query.message.reply_video(
        video=sample_video_file_id,
        caption="Here is a sample video!",
        reply_markup=reply_markup,
        protect_content=True  # Prevent downloading/forwarding
    )

    logger.info(f"Sent sample video to user {query.from_user.id}.")
