import logging
import os
import sys

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
    PicklePersistence,
)


# Add to python path some directories
sys.path.insert(0, os.path.abspath("src"))
sys.path.insert(0, os.path.abspath(os.path.join("src", "profile_handlers")))
sys.path.insert(0, os.path.abspath(os.path.join("src", "admin_handlers")))
sys.path.insert(0, os.path.abspath(os.path.join("src", "timetable_handlers")))
sys.path.insert(0, os.path.abspath(os.path.join("src", "camp_handlers")))
sys.path.insert(0, os.path.abspath(os.path.join("src", "registration_handlers")))


from start import start_handlers
from databaseAPI import rep_chess_db
from admin_handlers import admin_callback_handlers
from profile_handlers import profile_callback_handlers
from timetable_handlers import timetable_callback_handlers, process_new_post, process_edited_post
from camp_handlers import camp_callback_handlers
from registration_handlers import registration_callback_handlers


# Configure logging
logfile_dir = os.getenv("REPCHESS_LOG_DIR")
if not logfile_dir:
    print("Error: Can't find path to log directory.")
    print("Please set REPCHESS_LOG_DIR variable.")
    sys.exit(1)
logging.basicConfig(
    format="%(asctime)s %(name)s : %(levelname)s: %(message)s",
    level=logging.DEBUG,
    handlers=[
        logging.FileHandler(os.path.join(logfile_dir, "bot.log")),  # Save logs to a file
        logging.StreamHandler()  # Output logs to console
    ]
)
logger = logging.getLogger(__name__)


async def global_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    For flexibility we have to process all text messages from user here and
    transfer it to suitable handlers. The current function for processing update
    is in context.user_data["text_state"]. If text_state = None, we can ignore message.
    """
    # The new post in group was published
    if update.channel_post:
        await process_new_post(update, context)
        return
    # Post was edited in group
    if update.edited_channel_post:
        await process_edited_post(update, context)
        return

    if not context.user_data:
        await context.bot.send_message(update.effective_chat.id, "Бот обновился, введите или нажмите на команду /start")
        return
    # If there was expectations of other messages - remove them.
    if "forwarded_state" in context.user_data:
        context.user_data["forwarded_state"] = None

    if "file_state" in context.user_data:
        context.user_data["file_state"] = None

    if "text_state" not in context.user_data or context.user_data["text_state"] == None:
        # this is useless message from user. It is not some answer for handlers.
        logger.info(f"IGNORE MESSAGE {update.message.text}")
        return

    await context.user_data["text_state"](update, context)


async def global_forwarded_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # If it is forwarded message in channel - just ignore it.
    if update.channel_post or update.edited_channel_post:
        return
    if not context.user_data:
        update.message.reply_text("Бот обновился, введите или нажмите на команду /start")
        return
    # If there was expectations of other messages - remove them.
    if "text_state" in context.user_data:
        context.user_data["text_state"] = None

    if "file_state" in context.user_data:
        context.user_data["file_state"] = None

    if "forwarded_state" not in context.user_data or context.user_data["forwarded_state"] == None:
        # this is useless message from user. It is not some answer for handlers.
        if update.channel_post:
            logger.info(f"IGNORE FORWARDED channel post {update.channel_post.text}")
        elif update.message:
            logger.info(f"IGNORE FORWARDED message {update.message.text}")
        return

    await context.user_data["forwarded_state"](update, context)


async def global_file_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data:
        update.message.reply_text("Бот обновился, введите или нажмите на команду /start")
        return
    # If there was expectations of other messages - remove them.
    if "forwarded_state" in context.user_data:
        context.user_data["forwarded_state"] = None

    if "text_state" in context.user_data:
        context.user_data["text_state"] = None

    if "file_state" not in context.user_data or context.user_data["file_state"] == None:
        logger.info(f"IGNORE FILE MESSAGE {update.message}")

    await context.user_data["file_state"](update, context)


def start_tg_bot(token: str):
    application = ApplicationBuilder().token(token).build()

    application.add_handlers(start_handlers)
    application.add_handlers(admin_callback_handlers)
    application.add_handlers(profile_callback_handlers)
    application.add_handlers(timetable_callback_handlers)
    application.add_handlers(camp_callback_handlers)
    application.add_handlers(registration_callback_handlers)
    application.add_handler(MessageHandler(filters.Document.ALL, global_file_message_handler))
    application.add_handler(MessageHandler(filters.FORWARDED, global_forwarded_message_handler))
    application.add_handler(MessageHandler(filters.ALL, global_message_handler))

    # never return
    application.run_polling()

    logger.info("Bot stopped")


def main():
    # Init database
    rep_chess_db.initialize()

    # Get telegram token
    telegram_token = os.getenv("REPCHESS_TELEGRAM_BOT_TOKEN")
    if not telegram_token:
        logger.error("Can't find path to telegram token!")
        print("Please set REPCHESS_TELEGRAM_BOT_TOKEN variable.")
        sys.exit(1)

    # Start bot
    try:
        start_tg_bot(telegram_token)
    except Exception as e:
        logger.error(f"Error in main function: {e}", exc_info=True)


if __name__ == "__main__":
    main()
