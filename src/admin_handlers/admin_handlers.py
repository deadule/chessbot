from admin_main_menu import admin_main_menu_handlers
from change_public_id import admin_change_public_id_handlers
from open_registration import admin_open_registration_handlers
from close_registration import admin_close_registration_handlers
from show_registered import admin_show_registered_handlers
from upload_results import admin_upload_results_handlers
from update_timetable import admin_update_timetable_handlers
from delete_timetable import admin_delete_timetable_handlers
from add_camp import admin_add_camp_handlers
from delete_camp import admin_delete_camp_handlers
from add_new_admin import admin_add_new_admin_handlers
from delete_admin import admin_delete_admin_handlers


admin_callback_handlers = admin_main_menu_handlers + \
admin_change_public_id_handlers + \
admin_open_registration_handlers + \
admin_close_registration_handlers + \
admin_show_registered_handlers + \
admin_upload_results_handlers + \
admin_update_timetable_handlers + \
admin_delete_timetable_handlers + \
admin_add_camp_handlers + \
admin_delete_camp_handlers + \
admin_add_new_admin_handlers + \
admin_delete_admin_handlers
