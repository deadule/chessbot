import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CommandHandler
from config import TOKEN  # Replace with your actual config file for the bot token

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    handlers=[
        logging.FileHandler("upload_video.log"),  # Save logs to a file
        logging.StreamHandler()  # Output logs to console
    ]
)
logger = logging.getLogger(__name__)

# Start command handler to greet the user
async def start(update: Update, context):
    await update.message.reply_text("Hello! Send me a video to retrieve its file_id.")

# Handle receiving video messages and log the file_id
async def handle_received_video(update: Update, context):
    video = update.message.video
    if video:
        file_id = video.file_id
        file_size = video.file_size
        logger.info(f"Received video. file_id: {file_id}, file_size: {file_size} bytes")
        await update.message.reply_text(f"Video received!\nfile_id: {file_id}\nfile_size: {file_size} bytes")
    else:
        await update.message.reply_text("No video found in the message!")

# Main function to start the bot
def main():
    application = Application.builder().token(TOKEN).build()

    # Add handlers for start command and video uploads
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VIDEO, handle_received_video))

    # Start polling for updates
    application.run_polling()

if __name__ == '__main__':
    main()
