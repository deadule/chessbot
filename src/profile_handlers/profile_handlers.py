from main_menu_handler import profile_main_menu_handler, profile_go_back_handler
from change_name_handler import profile_change_name_handler
from change_surname_handler import profile_change_surname_handler
from change_lichess_rating_handler import profile_change_lichess_rating_handler
from change_chesscom_rating_handler import profile_change_chesscom_rating_handler


profile_callback_handlers = [
    profile_go_back_handler,
    profile_main_menu_handler,
    profile_change_name_handler,
    profile_change_surname_handler,
    profile_change_lichess_rating_handler,
    profile_change_chesscom_rating_handler,
]
