from main_menu_handler import profile_main_menu_handlers
from change_age_handler import profile_change_age_handlers
from change_city_handler import profile_change_city_handlers
from change_name_handler import profile_change_name_handlers
from change_surname_handler import profile_change_surname_handlers
from change_nickname_handler import profile_change_nickname_handlers
from change_lichess_rating_handler import profile_change_lichess_rating_handlers
from change_chesscom_rating_handler import profile_change_chesscom_rating_handlers


profile_callback_handlers = profile_main_menu_handlers +\
    profile_change_age_handlers +\
    profile_change_city_handlers +\
    profile_change_name_handlers +\
    profile_change_surname_handlers +\
    profile_change_nickname_handlers +\
    profile_change_lichess_rating_handlers +\
    profile_change_chesscom_rating_handlers
