import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

# Handle the "Узнать свой Уровень" butto
async def handle_find_level(update: Update, context):
    query = update.callback_query
    await query.answer()

    logger.info(f"User {query.from_user.id} selected 'Узнать свой Уровень'.")

    # Create return button to go back to the main menu
    return_kb = [
        [InlineKeyboardButton("Return", callback_data="return_main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(return_kb)

    # For now, just send a simple message with the return button
    await query.message.reply_text("We are calculating your level... Please wait!", reply_markup=reply_markup)

    logger.info(f"Sent level info to user {query.from_user.id}.")
