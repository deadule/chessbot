from main_menu_handler import profile_main_menu_handler
from change_name_handler import profile_change_name_handler, process_input_name
from change_surname_handler import profile_change_surname_handler, process_input_surname
from change_lichess_rating_handler import profile_change_lichess_rating_handler, process_input_lichess_rating
from change_chesscom_rating_handler import profile_change_chesscom_rating_handler, process_input_chesscom_rating


profile_callback_handlers = [
    profile_main_menu_handler,
    profile_change_name_handler,
    profile_change_surname_handler,
    profile_change_lichess_rating_handler,
    profile_change_chesscom_rating_handler,
]

"""profile_message_handlers = [
    process_input_name,
    process_input_surname,
    process_input_chesscom_rating,
    process_input_lichess_rating,
]
"""