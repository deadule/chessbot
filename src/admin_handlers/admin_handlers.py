from admin_main_menu import admin_main_menu_handler
from send_push import admin_send_push_handler
from change_timetable import admin_change_timetable_handler
from add_new_admin import admin_add_new_admin_handler
from delete_admin import admin_delete_admin_handler


admin_callback_handlers = [
    admin_main_menu_handler,
    admin_send_push_handler,
    admin_change_timetable_handler,
    admin_add_new_admin_handler,
    admin_delete_admin_handler,
]
