import logging
import datetime
import os
import sys

from databaseAPI import rep_chess_db

# Configure logging
logfile_dir = os.getenv("REPCHESS_LOG_PATH")
if not logfile_dir:
    print("Error: Can't find path to log directory.")
    print("Please set REPCHESS_LOG_PATH variable.")
    sys.exit(1)
logging.basicConfig(
    format="%(asctime)s %(name)s : %(levelname)s: %(message)s",
    level=logging.DEBUG,  # Set to DEBUG for detailed output
    handlers=[
        logging.FileHandler(os.path.join(logfile_dir, "bot.log")),  # Save logs to a file
        logging.StreamHandler()  # Output logs to console
    ]
)
logger = logging.getLogger(__name__)


def start_tg_bot(token: str):
    # if not exist!
    rep_chess_db.register_user(
        telegram_id=1000,
        name="Максим",
        first_contact=datetime.datetime.now(),
        last_contact=datetime.datetime.now(),
        lichess_rating=1900
    )
    import time
    time.sleep(0.5)
    rep_chess_db.update_user_name(telegram_id=1000, name="NO Максим")
    time.sleep(0.5)
    rep_chess_db.update_user_chesscom_rating(telegram_id=1000, chesscom_rating=1600)
    print(rep_chess_db.get_user_on_telegram_id(1000))


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
        token = f.readline()

    # Start bot
    try:
        start_tg_bot(token)
    except Exception as e:
        logger.error(f"Error in main function: {e}", exc_info=True)

    logger.info("Bot successfully started")


if __name__ == "__main__":
    main()
