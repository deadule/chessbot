from telegram import Update
from telegram.ext import MessageHandler, ContextTypes, filters

import start


async def camp_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not start.camp_data["active"]:
        await update.message.reply_text("В данный момент нет активной записи в лагерь.", reply_markup=start.main_menu_reply_keyboard())
        return

    await context.bot.forward_message(
        update.effective_chat.id,
        "@" + start.camp_data["channel"],
        start.camp_data["message_id"]
    )


camp_callback_handlers = [MessageHandler(filters.Regex("^🏕 Лагерь$"), camp_post)]
