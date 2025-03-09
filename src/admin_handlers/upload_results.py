import datetime
import io
import csv
import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackQueryHandler, ContextTypes

from databaseAPI import rep_chess_db
from timetable_handlers import DIGITS_EMOJI


logger = logging.getLogger(__name__)


result_mapping = {
    "+": 1,
    "=": 0.5,
    "-": 0,
}


def process_game_results(tournament_id: int, results: tuple[dict]):
    """
    If any error appears - just throw an exception.
    It is no point to correctly process all the possible errors because
    we parse file that shouldn't contain any nonsence.
    """
    number_of_tours = int(max(tour for tour in results[0].keys() if tour.startswith("Тур #")).split("#")[1])
    for row in results:
        nickname = row["Имя"].strip()
        user_in_tournament = rep_chess_db.get_user_on_tournament_on_nickname(tournament_id, nickname)
        if not user_in_tournament or row["#"] <= 10:
            continue
        user_id = user_in_tournament["user_id"]
        games_played = 0

        for tour_number in range(1, number_of_tours + 1):
            str_res = row[f"Тур #{tour_number}"].strip()
            print(row, tour_number, str_res)
            if not str_res:
                continue
            games_played += 1
            float_res = result_mapping[str_res[0]]
            if "W" in str_res:
                black_user_in_tournament = rep_chess_db.get_user_on_tournament_on_nickname(tournament_id, results[int(str_res.split("W")[1]) - 1]["Имя"].strip())
                if not black_user_in_tournament:
                    continue
                black_user_id = black_user_in_tournament["user_id"]
                rep_chess_db.add_game(tournament_id, user_id, black_user_id, tour_number, float_res)
            if str_res.startswith("+BYE"):
                black_user_in_tournament = rep_chess_db.get_user_on_tournament_on_nickname(tournament_id, results[int(str_res.split("E")[1]) - 1]["Имя"].strip())
                if not black_user_in_tournament:
                    continue
                black_user_id = black_user_in_tournament["user_id"]
                rep_chess_db.add_game(tournament_id, user_id, black_user_id, tour_number, float_res)

        new_rating = int(row["Новый рейтинг"].strip())
        rep_chess_db.update_user_on_tournament(
            tournament_id,
            nickname,
            new_rating,
            int(row["#"].strip()),
            float(row["Очки"].strip().replace(",", "."))
        )
        rep_chess_db.update_user_games_played(user_id, games_played)
        rep_chess_db.update_user_rep_rating_with_user_id(user_id, new_rating)


def construct_short_timetable(tournaments: list[tuple]) -> tuple[str, InlineKeyboardMarkup]:
    result_str = "🌟  *_Турниры без загруженных результатов:_*\n"
    result_markup = []

    for i, tournament in enumerate(tournaments, 1):
        if i % 5 == 1:
            result_markup.append([])
        text_number = DIGITS_EMOJI[i//10] if i >= 10 else ""
        text_number += DIGITS_EMOJI[i%10]
        result_str += f"\n{text_number}  __{tournament[5].strftime("%d\\.%m %H:%M")}__\n   *{tournament[4]}*\n"

        result_markup[-1].append(InlineKeyboardButton(text_number, callback_data=f"upload_results:{tournament[0]}"))
    result_markup.append([InlineKeyboardButton("<< Назад", callback_data="go_main_menu")])

    return result_str, InlineKeyboardMarkup(result_markup)


async def process_tournament_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document.file_name.endswith(".csv"):
        await update.message.reply_text("Это что такое? Пришлите .csv файл, пожалуйста")
        return

    if "uploaded_tournament_id" not in context.user_data or not context.user_data["uploaded_tournament_id"]:
        await update.message.reply_text("Эээ... Что-то не так, как вы сюда попали? Попробуйте ещё раз")
        return

    file = await update.message.document.get_file()
    with io.BytesIO() as iofile:
        await file.download_to_memory(iofile)
        iofile.seek(0)
        with io.TextIOWrapper(iofile, encoding="utf-8-sig") as text_file:
            results = tuple(csv.DictReader(text_file, delimiter=";"))
            #try:
            process_game_results(context.user_data["uploaded_tournament_id"], results)
            """except Exception as e: # here it is ok I think
                await update.message.reply_text("Оу... Не получилось обработать файл. Вы уверены, что загрузили нужный файл?")
                logger.info(e)
                return"""

    rep_chess_db.results_uploaded(context.user_data["uploaded_tournament_id"])
    await update.message.reply_text("Результаты обработаны! Игроки могут посмотреть обновленный рейтинг.")

    context.user_data["file_state"] = None
    context.user_data["uploaded_tournament_id"] = None


async def upload_tournament_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    _, tournament_id = query.data.split(":")

    context.user_data["file_state"] = process_tournament_file
    context.user_data["uploaded_tournament_id"] = tournament_id

    await context.bot.send_message(
        update.effective_chat.id,
        "Пришлите .csv файл с результатами турнира",
    )


async def admin_upload_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    today = datetime.date.today()
    today_start = datetime.datetime(today.year, today.month, today.day, 0, 0, 0)
    yesterday = today_start - datetime.timedelta(days=1)
    today_end = datetime.datetime(today.year, today.month, today.day, 23, 59, 59)
    tournaments = rep_chess_db.get_tournaments(yesterday, today_end, results_uploaded=False)
    message, keyboard = construct_short_timetable(tournaments)
    await context.bot.send_message(update.effective_chat.id, message, reply_markup=keyboard, parse_mode="MarkdownV2")


admin_upload_results_handlers = [
    CallbackQueryHandler(admin_upload_results, pattern="^admin_upload_results$"),
    CallbackQueryHandler(upload_tournament_results, pattern="^upload_results:")
]
