from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackQueryHandler, ContextTypes

def check_chess_availability_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Проверить наличие шахмат у ведущих 👀", callback_data="check_chess_kits")],
        [InlineKeyboardButton("Я хочу взять/сдать наборы ♟️", callback_data="register_chess_kits")],
        [InlineKeyboardButton("<< Назад", callback_data="go_main_menu")]
    ])

async def check_chess_kits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    # нужно придумать куда это деть
    if "chess_sets" not in context.bot_data:
        context.bot_data["chess_sets"] = dict()

    total_kits = sum(
        int(data.get('count', 0))
        for data in context.bot_data["chess_sets"].values()
    )

    if total_kits == 0:
        await context.bot.send_message(update.effective_chat.id, "Кажется все на Селезневке...")
        return
    else :
        message = "Текущее распределение наборов:\n"
        for user, data in context.bot_data["chess_sets"].items():
            message += f"@{user}: {data['count']}\n"
        await context.bot.send_message(update.effective_chat.id, message)
    context.user_data["text_state"] = None
    

async def register_chess_kits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        context.user_data["text_state"] = process_chess_count
        await context.bot.send_message(update.effective_chat.id, "So you wanna take it, huh? How many?")
        
    
async def process_chess_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: 
        number = int(update.message.text)
    except ValueError:
        await context.bot.send_message(update.effective_chat.id, "Введи пж целое число")
        return

    username = update.message.from_user.username
    
    context.bot_data["chess_sets"][username] = {
        "count": number,
        "last_update": datetime.now()
    }
    await context.bot.send_message(update.effective_chat.id, f"✅ Записано: {username} - {number} набор(ов)")
    context.user_data["text_state"] = None

async def admin_check_chess_kits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Где шахматы 👾",
        reply_markup=check_chess_availability_keyboard()
    )

admin_check_chess_kits_handlers = [
    CallbackQueryHandler(admin_check_chess_kits, pattern="^admin_check_chess_kits$"),
    CallbackQueryHandler(check_chess_kits, pattern="^check_chess_kits$"),
    CallbackQueryHandler(register_chess_kits, pattern="^register_chess_kits$")
]
