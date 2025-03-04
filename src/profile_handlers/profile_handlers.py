from main_menu_handler import profile_main_menu_handler
from change_profile_handler import profile_change_profile_handler
from change_age_handler import profile_change_age_handler
from change_name_handler import profile_change_name_handler
from change_surname_handler import profile_change_surname_handler
from change_nickname_handler import profile_change_nickname_handler
from change_lichess_rating_handler import profile_change_lichess_rating_handler
from change_chesscom_rating_handler import profile_change_chesscom_rating_handler


profile_callback_handlers = [
    profile_main_menu_handler,
    profile_change_profile_handler,
    profile_change_age_handler,
    profile_change_name_handler,
    profile_change_surname_handler,
    profile_change_nickname_handler,
    profile_change_lichess_rating_handler,
    profile_change_chesscom_rating_handler,
]
