from telegram import InlineKeyboardButton
from datetime import datetime

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
