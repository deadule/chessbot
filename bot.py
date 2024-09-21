import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from config import TOKEN

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),  # Save logs to a file
        logging.StreamHandler()  # Output logs to console
    ]
)
logger = logging.getLogger(__name__)

# Start command handler
async def start(update: Update, context):
    logger.info(f"User {update.effective_user.id} started the bot.")
    
    # Greeting message and "Let's Try" button
    greet_kb = [
        [InlineKeyboardButton("Let's Try", callback_data="lets_try")]
    ]
    reply_markup = InlineKeyboardMarkup(greet_kb)

    await update.message.reply_text("Hello! Welcome to the bot.", reply_markup=reply_markup)
    logger.info(f"Greeting message sent to user {update.effective_user.id}.")

# Handle the "Let's Try" button
async def lets_try_handler(update: Update, context):
    query = update.callback_query
    await query.answer()

    logger.info(f"User {query.from_user.id} pressed 'Let's Try'.")

    # Creating buttons for the next section
    level_kb = [
        [InlineKeyboardButton("Amateur", callback_data="level_amateur")],
        [InlineKeyboardButton("Chmo", callback_data="level_chmo")],
        [InlineKeyboardButton("Loh Konkretniy", callback_data="level_loh")]
    ]
    reply_markup = InlineKeyboardMarkup(level_kb)

    # Send the level selection message
    await query.message.reply_text("Choose your level:", reply_markup=reply_markup)
    logger.info(f"Sent level selection options to user {query.from_user.id}.")

# Handle the level selection
async def level_handler(update: Update, context):
    query = update.callback_query
    await query.answer()

    logger.info(f"User {query.from_user.id} selected a level.")

    level_map = {
        'level_amateur': "You chose: Amateur",
        'level_chmo': "You chose: Chmo",
        'level_loh': "You chose: Loh Konkretniy"
    }

    # Respond with the chosen level
    chosen_level = level_map[query.data]
    await query.message.reply_text(chosen_level)
    logger.info(f"User {query.from_user.id} chose {chosen_level}.")

def main():
    # Initialize the application and dispatcher
    application = Application.builder().token(TOKEN).build()
    logger.info("Bot is starting...")

    # Add command and callback handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(lets_try_handler, pattern="lets_try"))
    application.add_handler(CallbackQueryHandler(level_handler, pattern="level_"))

    # Start polling for updates
    logger.info("Bot started. Now polling for updates.")
    application.run_polling()

if __name__ == '__main__':
    main()
