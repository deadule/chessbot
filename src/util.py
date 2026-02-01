from typing import Optional
from zoneinfo import ZoneInfo
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
import datetime as dt
from telegram.ext import ContextTypes
from telegram.error import TelegramError

# Symbols that should be used with "\" in telegram MarkdownV2 parse mode
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


def escape_special_symbols(string: str) -> str:
    for sym in SPECIAL_SYMBOLS:
        string = string.replace(sym, f"\\{sym}")
    return string


def check_string(string: str) -> bool:
    return all(char.isalnum() or char in {" ", "-", "!", "?"} for char in string)


def construct_timetable_buttons(tournaments: list[dict], callback_pattern: str) -> tuple[str, list[InlineKeyboardButton]]:
    """
    Construct list of tournaments as message and buttons for InlineKeyboardMarkup.
    Callback data for buttons have pattern <callback_pattern>:<tournament_id>:<channel>:<message_id>
    """
    result_str = ""
    result_markup = []
    print(tournaments, "\n\n\n\n")
    for i, tournament in enumerate(tournaments, 1):
        if i % 5 == 1:
            result_markup.append([])
        text_number = DIGITS_EMOJI[i//10] if i >= 10 else ""
        text_number += DIGITS_EMOJI[i%10]
        result_str += f"\n{text_number}  __{tournament["date_time"].strftime("%d\\.%m %H:%M")}__\n   *{tournament["summary"]}*\n"

        result_markup[-1].append(InlineKeyboardButton(text_number, callback_data=f"{callback_pattern}:{tournament["tournament_id"]}:{tournament["tg_channel"]}:{tournament["message_id"]}"))

    return result_str, result_markup

# telegram_ui
BACK_TO_MENU_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("<< Назад", callback_data="go_main_menu")]
])

def _track_cleanup_message(context: ContextTypes.DEFAULT_TYPE, message_id: int) -> None:
    context.user_data.setdefault("messages_to_delete", []).append(message_id)

async def _cleanup_tracked_messages(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
) -> None:
    message_ids = context.user_data.get("messages_to_delete") or []
    if not message_ids:
        return

    remaining_ids = []
    for message_id in message_ids[-50:]:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except TelegramError:
            remaining_ids.append(message_id)
    context.user_data["messages_to_delete"] = remaining_ids

async def _send_managed_message(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    chat_id: int,
    cleanup: bool = True,
    track: bool = True,
    **send_kwargs,
):
    if cleanup:
        await _cleanup_tracked_messages(context, chat_id)
    message = await context.bot.send_message(chat_id=chat_id, **send_kwargs)
    if track:
        _track_cleanup_message(context, message.message_id)
    return message

async def _reply_managed(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    cleanup: bool = True,
    track: bool = True,
    **reply_kwargs,
):
    chat_id = update.effective_chat.id
    if cleanup:
        await _cleanup_tracked_messages(context, chat_id)
    message = await update.message.reply_text(**reply_kwargs)
    if track:
        _track_cleanup_message(context, message.message_id)
    return message

# timezone and date

MOSCOW_TZ = ZoneInfo("Europe/Moscow")
UTC = ZoneInfo("UTC")

# helpers 

def _now_tz(tz: ZoneInfo = MOSCOW_TZ) -> dt.datetime:
    return dt.datetime.now(tz)

def _coerce_datetime(value: object, tz: ZoneInfo = MOSCOW_TZ) -> Optional[dt.datetime]:
    if isinstance(value, dt.datetime):
        result = value
    elif isinstance(value, str):
        try:
            result = dt.datetime.fromisoformat(value)
        except ValueError:
            return None
    else:
        return None
    if result.tzinfo is None:
        return result.replace(tzinfo=UTC).astimezone(tz)
    return result.astimezone(tz)