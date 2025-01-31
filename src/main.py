import logging
import os
import sys

from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, Update, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)


# Add to python path some directories
sys.path.insert(0, os.path.abspath("src"))
sys.path.insert(0, os.path.abspath(os.path.join("src", "profile_handlers")))


from databaseAPI import rep_chess_db
from profile_handlers import profile_callback_handlers


# Configure logging
logfile_dir = os.getenv("REPCHESS_LOG_PATH")
if not logfile_dir:
    print("Error: Can't find path to log directory.")
    print("Please set REPCHESS_LOG_PATH variable.")
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


main_menu_reply_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🙾  Расписание")],
        [KeyboardButton("👤 Профиль")],
    ],
    resize_keyboard=True
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.from_user.first_name
    # Register user if it doesn't exist
    rep_chess_db.register_user(update.message.from_user.id, name=name)
    # Greeting message and ReplyKeyboard options
    await update.message.reply_text(f"Привет, {name}!", reply_markup=main_menu_reply_keyboard)


async def global_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    For flexibility we have to process all text messages from user here and
    transfer it to suitable handlers. The current function for processing update
    is in context.user_data["state"]. If state = None, we can ignore message.
    """
    if "state" not in context.user_data:
        context.user_data["state"] = None

    if context.user_data["state"] == None:
        # this is useless message from user. It is not some answer for handlers.
        logger.info(f"IGNORE MESSAGE {update.message.text}")
        return

    await context.user_data["state"](update, context)


def start_tg_bot(token: str):
    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handlers(profile_callback_handlers)
    application.add_handler(MessageHandler(filters.ALL, global_message_handler))

    # never return
    application.run_polling()

    logger.info("Bot stopped")

    """
    rep_chess_db.register_user(
        telegram_id=1000,
        name="Максим",
        first_contact=datetime.datetime.now(),
        last_contact=datetime.datetime.now(),
        lichess_rating=1900
    )
    rep_chess_db.update_user_name(telegram_id=1000, name="NO Максим")
    rep_chess_db.update_user_chesscom_rating(telegram_id=1000, chesscom_rating=1600)"""


def main():
    # Init database
    rep_chess_db.initialize()

    # Get telegram token
    telegram_token_path = os.getenv("REPCHESS_TELEGRAM_BOT_TOKEN")
    if not telegram_token_path:
        logger.error("Can't find path to telegram token!")
        print("Please set REPCHESS_TELEGRAM_BOT_TOKEN variable.")
        sys.exit(1)
    if not os.path.isfile(telegram_token_path):
        logger.error("Can't find telegram token file!")
        sys.exit(1)
    with open(telegram_token_path, "r", encoding="utf-8") as f:
        token = f.readline().strip()

    # Start bot
    try:
        start_tg_bot(token)
    except Exception as e:
        logger.error(f"Error in main function: {e}", exc_info=True)


if __name__ == "__main__":
    main()
