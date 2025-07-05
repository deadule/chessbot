import re
import datetime
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters, CallbackQueryHandler

from databaseAPI import rep_chess_db
from start import main_menu_reply_keyboard
from util import escape_special_symbols, construct_timetable_buttons


logger = logging.getLogger(__name__)


def parse_tournament_post(post: str, update: Update) -> dict | None:
    """
    Parse post from channel and return dict if this post have correct format:
    {
        summary: ...,
        date_time: datetime,
        address: ...,
    }
    """
    if post.startswith("📆 Расписание на неделю:\n\n") or post.startswith("📅 Расписание на неделю:\n\n") or post.startswith("📅📅📅📅📅📅📅 📅📅📅📅📅📅📅\n\n"):
        # update weakly timetable
        print(update)
        if update.channel_post:
            post = update.channel_post
            chat = post.chat
        else:
            post = update.message
            chat = post.forward_from_chat

        photo_id = max(post.photo, key = lambda x: x.height).file_id
        rep_chess_db.update_weakly_info(chat.username, post.message_id, photo_id)
        return dict()

    re_match = re.search(r"\n\d+.\d+.?\n\d+:\d+.?\nАдрес:.*$", post)
    if not re_match:
        return None

    string = re_match.group(0)
    string = string.split("\n")
    string.remove("")

    day, month = map(int, string[0].split(".")[0:2])

    date_time = datetime.datetime(
        datetime.date.today().year,
        month,
        day,
        *(map(int, string[1].split(":"))),
        0,
    )
    summary = escape_special_symbols(post.split("\n", 1)[0])
    address = escape_special_symbols(string[2].split(" ", 1)[1])

    return {
        "summary": summary,
        "date_time": date_time,
        "address": address,
    }


async def process_forwarded_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text:
        text = update.message.caption
    if not text:
        return

    tournament = parse_tournament_post(text, update)
    if tournament is None:
        await context.bot.send_message(update.effective_chat.id, "Пост не подходит под формат")
        return
    if not tournament:
        # It is weakly post
        await context.bot.send_message(update.effective_chat.id, "Запрос обработан. Проверьте, что все успешно.", reply_markup=main_menu_reply_keyboard(context))
        return
    if update.message.api_kwargs:
        tournament["tg_channel"] = update.message.api_kwargs["forward_from_chat"]["username"]
        tournament["message_id"] = update.message.api_kwargs["forward_from_message_id"]
    else:
        tournament["tg_channel"] = update.message.forward_from_chat.username
        tournament["message_id"] = update.message.forward_from_message_id

    rep_chess_db.add_tournament(**tournament)

    context.user_data["forwarded_state"] = None
    await context.bot.send_message(update.effective_chat.id, "Запрос обработан. Проверьте, что все успешно.", reply_markup=main_menu_reply_keyboard(context))


async def process_new_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Process new post in tg channel.
    If it is tournament announcement or weakly timetable - save it in database.
    Otherwise do nothing.
    """
    if not update.channel_post:
        return
    text = update.channel_post.text
    if not text:
        text = update.channel_post.caption

    if not text:
        return

    tournament = parse_tournament_post(text, update)
    if not tournament:
        return
    tournament["tg_channel"] = update.channel_post.chat.username
    tournament["message_id"] = update.channel_post.message_id
    rep_chess_db.add_tournament(**tournament)


async def process_edited_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.edited_channel_post:
        return
    text = update.edited_channel_post.text
    if not text:
        text = update.edited_channel_post.caption

    if not text:
        return

    tournament = parse_tournament_post(text, update)
    if not tournament:
        return

    tournament["tg_channel"] = update.edited_channel_post.chat.username
    tournament["message_id"] = update.edited_channel_post.message_id
    rep_chess_db.update_tournament(**tournament)


async def tournament_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, _, channel, message_id = query.data.split(":")

    await context.bot.forward_message(update.effective_chat.id, "@" + channel, int(message_id))
    short_timetable_buttons = context.user_data["timetable_buttons"][:-1] + [[InlineKeyboardButton("<< Назад", callback_data="go_main_timetable")]]
    await context.bot.send_message(
        update.effective_chat.id,
        "🌟  *_Анонсы мероприятий_*",
        reply_markup=InlineKeyboardMarkup(short_timetable_buttons),
        parse_mode="MarkdownV2"
    )


async def callback_main_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await main_message_handler(update, context)


async def main_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        telegram_id = update.message.from_user.id
    else:
        telegram_id = update.callback_query.from_user.id
    rep_chess_db.update_user_last_contact(telegram_id)

    today = datetime.date.today()
    tg_channel = rep_chess_db.get_tg_channel_on_tg_id(telegram_id)
    if not tg_channel:
        logger.error(f"CITIES ARE INCONSISTENT. User with telegram id = {telegram_id} has incorrect city id")
        return
    tournaments = rep_chess_db.get_tournaments(tg_channel, datetime.datetime(today.year, today.month, today.day, 0, 0, 0))
    message, inline_markup_buttons = construct_timetable_buttons(tournaments, "timetable_tournament")
    message = "🌟  *_Анонсы_*\n" + message
    inline_markup_buttons.append([InlineKeyboardButton("<< Назад", callback_data="go_main_menu")])
    context.user_data["timetable_buttons"] = inline_markup_buttons

    photo_file_id = rep_chess_db.get_photo_id(tg_channel)
    await context.bot.send_photo(
        update.effective_chat.id,
        photo_file_id,
        caption=message,
        reply_markup=InlineKeyboardMarkup(inline_markup_buttons),
        parse_mode="MarkdownV2"
    )


timetable_main_message_handler = MessageHandler(filters.Regex("^📅  Расписание$"), main_message_handler)


timetable_callback_handlers = [
    MessageHandler(filters.Regex("^📅  Расписание$"), main_message_handler),
    CallbackQueryHandler(tournament_handler, pattern="^timetable_tournament:*"),
    CallbackQueryHandler(callback_main_message_handler, pattern="^go_main_timetable$")
]
