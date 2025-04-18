import logging
import os
import sys

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from databaseAPI import rep_chess_db

#from config import TOKEN
#from sample_video_handler import handle_sample_video, handle_video_level_selection
#from payment_handler import create_first_payment_with_saving, handle_payment_confirmation
#from find_level_handler import handle_find_level

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,  # Set to DEBUG for detailed output
    handlers=[
        logging.FileHandler("bot.log"),  # Save logs to a file
        logging.StreamHandler()  # Output logs to console
    ]
)
logger = logging.getLogger(__name__)

# Define the file_id for each video in different qualities (Replace with actual file_id)
videos = {
    'amateur': {
        '480p': 'BAACAgIAAxkBAANqZwAB78tI-rqQKNQcXED4DmE0qs2FAAIMVAACBeUISCwVSWpKiDVdNgQ',  # Replace with actual file_id
        '720p': 'BAACAgIAAxkBAANqZwAB78tI-rqQKNQcXED4DmE0qs2FAAIMVAACBeUISCwVSWpKiDVdNgQ',
        '1080p': 'BAACAgIAAxkBAANqZwAB78tI-rqQKNQcXED4DmE0qs2FAAIMVAACBeUISCwVSWpKiDVdNgQ'
    },
    'chmo': {
        '480p': 'AgAD8lMAAswRyUs',
        '720p': 'AgAD8lMAAswRyUs',
        '1080p': 'file_id_chmo_1080p'
    },
    'loh': {
        '480p': 'BAACAgIAAxkBAAMGZu6sLcqTvVAXC9CWzFNWDtJ9FbQAAvJTAAIgkHhLyPWR5tPsRAg2BA',
        '720p': 'BAACAgIAAxkBAAMGZu6sLcqTvVAXC9CWzFNWDtJ9FbQAAvJTAAIgkHhLyPWR5tPsRAg2BA',
        '1080p': 'file_id_loh_1080p'
    }
}

# Temporary storage to hold the user's selected level
user_selections = {}

# Helper function to create the main menu buttons
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Let's Try", callback_data="lets_try")],
        [InlineKeyboardButton("Посмотреть Пробное Видео", callback_data="sample_video")],
        [InlineKeyboardButton("Узнать свой Уровень", callback_data="find_level")]
    ])

# Start command handler
async def start(update: Update, context):
    try:
        logger.info(f"User {update.effective_user.id} started the bot.")
        
        # Greeting message with the three options
        await update.message.reply_text("Hello! Welcome to the bot.", reply_markup=main_menu_keyboard())
        logger.info(f"Greeting message sent to user {update.effective_user.id}.")
    except Exception as e:
        logger.error(f"Error in start handler: {e}")

# Handle the "Let's Try" button
async def lets_try_handler(update: Update, context):
    try:
        query = update.callback_query
        await query.answer()

        logger.info(f"User {query.from_user.id} pressed 'Let's Try'.")

        # Creating a button for the payment step
        payment_kb = [
            [InlineKeyboardButton("Proceed to Payment", callback_data="proceed_payment")],
            [InlineKeyboardButton("Return", callback_data="return_main_menu")]  # Return button
        ]
        reply_markup = InlineKeyboardMarkup(payment_kb)

        # Prompt for the payment option
        await query.message.reply_text("Please proceed to payment to unlock content:", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in lets_try_handler: {e}")

# Handle the payment step (after payment the user is authorized and proceeds to level selection)
async def handle_payment_step(update: Update, context):
    query = update.callback_query
    await query.answer()

    # Create payment and get the confirmation URL
    user_id = query.from_user.id
    confirmation_url, payment_id = await create_first_payment_with_saving(user_id)  # Fixed amount of 100 RUB

    if confirmation_url:
        # Send the payment link
        await query.message.reply_text(
            f"Click the link below to proceed with payment:\n{confirmation_url}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Proceed to Payment", url=confirmation_url)]
            ])
        )
    else:
        await query.message.reply_text("Payment creation failed. Please try again.")

# Handle the level selection after successful payment
async def handle_payment_confirmation(update: Update, context):
    query = update.callback_query
    await query.answer()

    logger.info(f"User {query.from_user.id} is proceeding after payment.")

    # Handle authorization from the auth_handler file
    authorized = await handle_authorization(update, context)

    if authorized:
        logger.info(f"User {query.from_user.id} is authorized after payment, proceeding to level selection.")
        # Proceed to level selection or course content
        await query.message.reply_text("You now have access to the course content!")
        logger.warning(f"Authorization failed for user {query.from_user.id}.")
        
        # Creating buttons for level selection, plus a return button
        level_kb = [
            [InlineKeyboardButton("Amateur", callback_data="level_amateur")],
            [InlineKeyboardButton("Chmo", callback_data="level_chmo")],
            [InlineKeyboardButton("Loh Konkретniy", callback_data="level_loh")],
            [InlineKeyboardButton("Return", callback_data="return_main_menu")]  # Return button
        ]
        reply_markup = InlineKeyboardMarkup(level_kb)
        
        # Send the level selection message
        await query.message.reply_text("Choose your level:", reply_markup=reply_markup)
    else:
        logger.error(f"User {query.from_user.id} could not be authorized after payment.")
        await query.message.reply_text("Authorization failed. Please try again.")

# Handle the level selection
async def level_handler(update: Update, context):
    try:
        query = update.callback_query
        await query.answer()

        level_map = {
            'level_amateur': "You chose: Amateur",
            'level_chmo': "You chose: Chmo",
            'level_loh': "You chose: Loh Konkретniy"
        }

        chosen_level = level_map[query.data]
        user_selections[query.from_user.id] = query.data.split('_')[1]

        # Create buttons for quality selection
        quality_kb = [
            [InlineKeyboardButton("480p", callback_data="quality_480p")],
            [InlineKeyboardButton("720p", callback_data="quality_720p")],
            [InlineKeyboardButton("1080p", callback_data="quality_1080p")],
            [InlineKeyboardButton("Return", callback_data="lets_try")]  # Return button
        ]
        reply_markup = InlineKeyboardMarkup(quality_kb)

        # Ask the user to choose video quality
        await query.message.reply_text(f"{chosen_level}\nNow, choose the video quality:", reply_markup=reply_markup)
        logger.info(f"User {query.from_user.id} selected {chosen_level}.")
    except Exception as e:
        logger.error(f"Error in level_handler: {e}")

# Handle the video quality selection
async def quality_handler(update: Update, context):
    try:
        query = update.callback_query
        await query.answer()

        # Get the user's selected level and chosen quality
        user_id = query.from_user.id
        chosen_level = user_selections.get(user_id)

        if chosen_level:
            quality_map = {
                'quality_480p': '480p',
                'quality_720p': '720p',
                'quality_1080p': '1080p'
            }
            chosen_quality = quality_map[query.data]

            # Select the video based on level and quality
            video_id = videos[chosen_level][chosen_quality]

            # Return button
            buttons = [
                [InlineKeyboardButton("Return", callback_data="lets_try")]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)

            # Send the selected video
            await query.message.reply_text(f"Here is your video in {chosen_quality}:", reply_markup=reply_markup)
            await query.message.reply_video(
                video=video_id,
                protect_content=True  # Prevent the user from saving, forwarding, or downloading the video
            )
            logger.info(f"User {user_id} selected {chosen_quality} for {chosen_level}.")
        else:
            await query.message.reply_text("Please select a level first.")
            logger.warning(f"User {user_id} attempted to select a quality without selecting a level first.")
    except Exception as e:
        logger.error(f"Error in quality_handler: {e}")

# Handle the return button for the main menu
async def return_main_menu_handler(update: Update, context):
    try:
        query = update.callback_query
        await query.answer()

        # Return to the main menu
        await query.message.reply_text("Returning to the main menu.", reply_markup=main_menu_keyboard())
        logger.info(f"User {query.from_user.id} returned to the main menu.")
    except Exception as e:
        logger.error(f"Error in return_main_menu_handler: {e}")


def start_tg_bot():
    # Initialize the database for authorization
    """
    application = Application.builder().token(TOKEN).build()
    logger.info("Bot is starting...")

    # Add command and callback handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(lets_try_handler, pattern="lets_try"))
    application.add_handler(CallbackQueryHandler(handle_payment_step, pattern="proceed_payment"))
    application.add_handler(CallbackQueryHandler(handle_payment_confirmation, pattern="payment_confirmation"))
    application.add_handler(CallbackQueryHandler(level_handler, pattern="level_"))
    application.add_handler(CallbackQueryHandler(quality_handler, pattern="quality_"))
    application.add_handler(CallbackQueryHandler(return_main_menu_handler, pattern="return_main_menu"))

    # Import and add separate handlers for additional buttons
    application.add_handler(CallbackQueryHandler(handle_sample_video, pattern="sample_video"))
    application.add_handler(CallbackQueryHandler(handle_video_level_selection, pattern="sample_level_"))
    application.add_handler(CallbackQueryHandler(handle_find_level, pattern="find_level"))

    # Start polling for updates
    logger.info("Bot started. Now polling for updates.")
    application.run_polling()
    """

# Main function to start the bot and handlers
def main():
    telegram_token_path = os.getenv("REPCHESS_DB_PATH")
    if not telegram_token_path:
        logger.error("Can't find path to telegram token!")
        print("Please set REPCHESS_TELEGRAM_BOT_TOKEN variable.")
    try:
        start_tg_bot()
    except Exception as e:
        logger.error(f"Error in main function: {e}")

if __name__ == '__main__':
    main()
