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


def escape_special_symbols(string: str) -> str:
    for sym in SPECIAL_SYMBOLS:
        string = string.replace(sym, f"\\{sym}")
    return string


def check_string(string: str) -> bool:
    return all(char.isalnum() or char in {" ", "-", "!", "?"} for char in string)
