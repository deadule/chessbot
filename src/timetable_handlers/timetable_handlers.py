import re
import datetime
from typing import List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters, CallbackQueryHandler

from databaseAPI import rep_chess_db
from start import main_menu_reply_keyboard


DIGITS_EMOJI = {
    0: "0⃣",
    1: "1⃣",
    2: "2⃣",
    3: "3⃣",
    4: "4⃣",
    5: "5⃣",
    6: "6⃣",
    7: "7⃣",
    8: "8⃣",
    9: "9⃣",
}


SPECIAL_SYMBOLS = [
  '\\',
  '_',
  '*',
  '[',
  ']',
  '(',
  ')',
  '~',
  '`',
  '>',
  '<',
  '&',
  '#',
  '+',
  '-',
  '=',
  '|',
  '{',
  '}',
  '.',
  '!',
]


def escape_special_symbols(string: str) -> str:
    for sym in SPECIAL_SYMBOLS:
        string = string.replace(sym, f"\\{sym}")
    return string


def parse_tournament_post(post: str) -> dict | None:
    """
    Parse post from channel and return dict if this post have correct format:
    {
        summary: ...,
        date_time: datetime,
        address: ...,
    }
    """
    re_match = re.search(r"\d+.\d+\n\d+:\d+\nАдрес:.*$", post)
    if not re_match:
        return None

    string = re_match.group(0)
    string = string.split("\n")

    day, month = map(int, string[0].split("."))

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

    tournament = parse_tournament_post(text)
    if not tournament:
        await context.bot.send_message(update.effective_chat.id, "Пост не подходит под формат")
        return

    if update.message.api_kwargs:
        tournament["tg_channel"] = update.message.api_kwargs["forward_from_chat"]["username"]
        tournament["message_id"] = update.message.api_kwargs["forward_from_message_id"]
    else:
        tournament["tg_channel"] = update.message.forward_from_chat.username
        tournament["message_id"] = update.message.forward_from_message_id

    rep_chess_db.add_tournament(**tournament)

    context.user_data["forwarded_state"] = None
    await context.bot.send_message(update.effective_chat.id, "Запрос обработан. Проверьте, что все успешно.", reply_markup=main_menu_reply_keyboard())


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

    if text.startswith("📅 Расписание на неделю:\n\n"):
        # update weakly timetable
        photo_id = max(update.channel_post.photo, key = lambda x: x.height).file_id
        rep_chess_db.update_weakly_info(update.channel_post.chat.username, update.channel_post.message_id, photo_id)
        return

    tournament = parse_tournament_post(text)
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

    tournament = parse_tournament_post(text)
    if not tournament:
        return

    tournament["tg_channel"] = update.edited_channel_post.chat.username
    tournament["message_id"] = update.edited_channel_post.message_id
    rep_chess_db.update_tournament(**tournament)


def construct_timetable(tournaments: List[datetime.datetime]) -> str:
    result_str = "🌟  *_Анонсы_*\n"
    result_markup = []

    for i, tournament in enumerate(tournaments, 1):
        if i % 5 == 1:
            result_markup.append([])
        text_number = DIGITS_EMOJI[i//10] if i >= 10 else ""
        text_number += DIGITS_EMOJI[i%10]
        result_str += f"\n{text_number}  __{tournament[5].strftime("%d\\.%m %H:%M")}__\n   *{tournament[4]}*\n"

        result_markup[-1].append(InlineKeyboardButton(text_number, callback_data=f"timetable_tournament:{tournament[1]}:{tournament[2]}"))
    result_markup.append([InlineKeyboardButton("<< Назад", callback_data="go_main_menu")])

    return result_str, InlineKeyboardMarkup(result_markup)


async def tournament_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, channel, message_id = query.data.split(":")

    await context.bot.forward_message(update.effective_chat.id, "@" + channel, int(message_id))
    await context.bot.send_message(update.effective_chat.id, "🌟  Анонсы", reply_markup=context.user_data["timetable_markup"])


async def main_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rep_chess_db.update_user_last_contact(update.message.from_user.id)

    today = datetime.date.today()
    tournaments = rep_chess_db.get_tournaments(datetime.datetime(today.year, today.month, today.day, 0, 0, 0))
    message, inline_markup = construct_timetable(tournaments)
    context.user_data["timetable_markup"] = inline_markup
    # TODO: Наверное, вещи по типу channel.username можно сохранять в context.
    photo_file_id = rep_chess_db.get_photo_id()
    await context.bot.send_photo(update.effective_chat.id, photo_file_id, caption=message, reply_markup=inline_markup, parse_mode="MarkdownV2")


timetable_main_message_handler = MessageHandler(filters.Regex("^📅  Расписание$"), main_message_handler)


timetable_callback_handlers = [
    MessageHandler(filters.Regex("^📅  Расписание$"), main_message_handler),
    CallbackQueryHandler(tournament_handler, pattern="^timetable_tournament:*"),
]
