from telegram import Update
from telegram.ext import MessageHandler, ContextTypes, filters

from start import main_menu_reply_keyboard


async def camp_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.bot_data["camp_data"]["active"]:
        await update.message.reply_text("Сейчас нет активной записи в лагерь.", reply_markup=main_menu_reply_keyboard(context))
        return

    await context.bot.forward_message(
        update.effective_chat.id,
        "@" + context.bot_data["camp_data"]["channel"],
        context.bot_data["camp_data"]["message_id"]
    )


camp_callback_handlers = [MessageHandler(filters.Regex("^🏕 Лагерь$"), camp_post)]
