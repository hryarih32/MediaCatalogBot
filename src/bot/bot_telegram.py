
import logging
from telegram import Update
from telegram.ext import (
    ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler,
    filters, Application, ConversationHandler
)
import re

from .bot_initialization import (
    show_or_edit_main_menu,
    send_or_edit_universal_status_message
)
from src.handlers.menu_handler_root import (
    main_menu_callback,
    handle_pending_search
)
import src.app.user_manager as user_manager
import src.app.app_config_holder as app_config_holder
from src.app.app_lifecycle import trigger_config_ui_from_bot
from src.bot.bot_callback_data import CallbackData

from src.handlers.radarr.menu_handler_radarr_controls import display_radarr_controls_menu
from src.handlers.radarr.menu_handler_library_management_radarr import display_radarr_queue_menu
from src.handlers.radarr.menu_handler_radarr_tools import display_radarr_library_maintenance_menu
from src.handlers.radarr.menu_handler_radarr_actions import handle_radarr_library_action
from src.handlers.radarr.menu_handler_radarr_add_search import radarr_add_media_page_callback
from src.handlers.radarr.menu_handler_radarr_add_flow import radarr_movie_selection_callback, radarr_customization_callback, RADARR_CB_PREFIX

from src.handlers.sonarr.menu_handler_sonarr_controls import display_sonarr_controls_menu
from src.handlers.sonarr.menu_handler_library_management_sonarr import display_sonarr_wanted_episodes_menu, display_sonarr_queue_menu as display_sonarr_queue_menu_lib_management
from src.handlers.sonarr.menu_handler_sonarr_tools import display_sonarr_library_maintenance_menu
from src.handlers.sonarr.menu_handler_sonarr_actions import handle_sonarr_library_action
from src.handlers.sonarr.menu_handler_sonarr_add_search import sonarr_add_media_page_callback
from src.handlers.sonarr.menu_handler_sonarr_add_flow import sonarr_show_selection_callback, sonarr_customization_callback, SONARR_CB_PREFIX

from src.handlers.plex.menu_handler_plex_controls import display_plex_controls_menu
from src.handlers.plex.menu_handler_plex_library_server_tools import display_plex_library_server_tools_menu
from src.handlers.plex.menu_handler_plex_main import (
    plex_now_playing_callback,
    plex_scan_libraries_select_callback,
    plex_scan_library_execute_callback,
    plex_refresh_library_metadata_select_callback,
    plex_refresh_library_metadata_execute_callback,
    plex_stop_stream_callback
)
from src.handlers.plex.menu_handler_plex_recently_added import (
    plex_recently_added_select_library_callback,
    plex_recently_added_show_results_menu
)
from src.handlers.plex.menu_handler_plex_search_init_results import plex_search_initiate_callback
from src.handlers.plex.menu_handler_plex_item_details import (
    plex_search_show_details_callback,
    plex_search_show_episode_details_callback,
    plex_search_refresh_item_metadata_callback
)
from src.handlers.plex.menu_handler_plex_show_navigation import (
    plex_search_list_seasons_callback,
    plex_search_list_episodes_callback
)
from src.handlers.plex.menu_handler_plex_server_tools import (
    display_plex_server_tools_sub_menu,
    handle_plex_server_action,
    plex_empty_trash_select_library_callback,
    plex_empty_trash_execute_callback
)

from src.handlers.pc_control.menu_handler_pc_root import display_pc_control_categories_menu
from src.handlers.pc_control.menu_handler_pc_media import display_media_sound_controls_menu, handle_media_sound_action, PC_CONTROL_CALLBACK_PREFIX as PC_MEDIA_PREFIX
from src.handlers.pc_control.menu_handler_pc_power import display_system_power_controls_menu, handle_power_action, PC_CONTROL_CALLBACK_PREFIX as PC_POWER_PREFIX

from src.handlers.menu_handler_launchers import (
    display_launchers_menu,
    handle_subgroup_selection,
    handle_dynamic_launcher_execution,
    handle_back_to_subgroups
)
from src.handlers.user_requests.menu_handler_my_requests import (
    display_my_requests_menu,
    display_my_request_detail
)
from src.handlers.admin_requests.menu_handler_admin_requests import (
    display_admin_pending_requests_menu,
    display_admin_request_details_view,
    admin_approve_request_callback,
    admin_reject_request_callback,
    handle_rejection_reason_input,
    cancel_rejection_reason,
    display_admin_history_requests_menu,
    ASK_REJECTION_REASON,
    HANDLE_REJECTION_REASON
)

from src.handlers.access_request_handler import handle_request_access_button
from src.handlers.admin_access_handler import (
    display_pending_access_requests_menu as admin_display_access_reqs,
    handle_approve_access_request_initiate,
    handle_approve_access_request_assign_role,
    handle_deny_access_request
)

logger = logging.getLogger(__name__)


async def delete_user_message_if_exists(update: Update):

    if update.message:
        try:
            await update.message.delete()
            logger.info(
                f"Deleted user command message {update.message.message_id} from chat {update.message.chat_id}")
        except Exception as e:
            logger.warning(
                f"Could not delete user command message {update.message.message_id} from chat {update.message.chat_id}: {e}")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    if not update.effective_user or not update.message or not update.effective_chat:
        logger.warning("start_command missing effective_user/message/chat.")
        return
    chat_id = update.effective_chat.id
    user_manager.update_username_if_placeholder(
        str(chat_id), update.effective_user)
    user_role = app_config_holder.get_user_role(str(chat_id))
    await delete_user_message_if_exists(update)
    if user_role == app_config_holder.ROLE_ADMIN or user_role == app_config_holder.ROLE_STANDARD_USER:
        logger.info(
            f"/start command received from user {chat_id} with role {user_role}")
        await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)
        status_text = "Main menu displayed."
        if user_role == app_config_holder.ROLE_STANDARD_USER:
            status_text = "Welcome! Select an option from the menu."
        await send_or_edit_universal_status_message(context.bot, chat_id, status_text, parse_mode=None, force_send_new=True)
    elif user_role == app_config_holder.ROLE_UNKNOWN:
        logger.info(
            f"/start command from unknown user {chat_id}. Displaying menu with Request Access button.")
        await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)
        await send_or_edit_universal_status_message(context.bot, chat_id, "Your access is restricted. You can request access using the button above.", parse_mode=None, force_send_new=True)
    else:
        primary_admin_chat_id = app_config_holder.get_chat_id_str()
        if not primary_admin_chat_id:
            await send_or_edit_universal_status_message(context.bot, chat_id, "Bot is not fully configured.", parse_mode=None, force_send_new=True)
            return
        logger.info(
            f"/start command from user {chat_id} with unexpected role {user_role}.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "Your access level is currently undefined. Please contact an administrator.", parse_mode=None, force_send_new=True)


async def home_command(

    update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: await start_command(update, context)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    if not update.effective_user or not update.message:
        return
    chat_id = update.effective_chat.id
    await delete_user_message_if_exists(update)
    if not app_config_holder.is_primary_admin(str(chat_id)):
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied. This command is for the bot administrator.", parse_mode=None)
        return
    logger.info(f"/settings command received from primary admin {chat_id}")
    await send_or_edit_universal_status_message(context.bot, chat_id, "⚙️ Opening settings panel...", parse_mode=None)
    await trigger_config_ui_from_bot(context.application)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    if not update.effective_user or not update.message or not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    user_manager.update_username_if_placeholder(
        str(chat_id), update.effective_user)
    await delete_user_message_if_exists(update)
    user_role = app_config_holder.get_user_role(str(chat_id))
    if user_role not in [app_config_holder.ROLE_ADMIN, app_config_holder.ROLE_STANDARD_USER]:
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied.", parse_mode=None)
        return
    logger.info(
        f"/status command received from user {chat_id} (Role: {user_role})")
    await send_or_edit_universal_status_message(context.bot, chat_id, "⏳ Current bot status is being refreshed...", force_send_new=True, parse_mode=None)


async def radarr_queue_menu_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    query = update.callback_query
    page = 1
    if query.data.startswith(CallbackData.CMD_RADARR_QUEUE_PAGE_PREFIX.value):
        try:
            page = int(query.data.replace(
                CallbackData.CMD_RADARR_QUEUE_PAGE_PREFIX.value, ""))
        except ValueError:
            page = 1
    elif query.data == CallbackData.CMD_RADARR_QUEUE_REFRESH.value:
        page = 1

    await display_radarr_queue_menu(update, context, page=page)


async def sonarr_queue_menu_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    query = update.callback_query
    page = 1
    if query.data.startswith(CallbackData.CMD_SONARR_QUEUE_PAGE_PREFIX.value):
        try:
            page = int(query.data.replace(
                CallbackData.CMD_SONARR_QUEUE_PAGE_PREFIX.value, ""))
        except ValueError:
            page = 1
    elif query.data == CallbackData.CMD_SONARR_QUEUE_REFRESH.value:
        page = 1

    await display_sonarr_queue_menu_lib_management(update, context, page=page)


async def cb_no_op_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()


def setup_handlers(application: Application):
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("home", home_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("status", status_command))

    application.add_handler(CallbackQueryHandler(
        handle_subgroup_selection, pattern=rf"^{CallbackData.CMD_LAUNCHER_SUBGROUP_PREFIX.value}.+$"))
    application.add_handler(CallbackQueryHandler(
        handle_dynamic_launcher_execution, pattern=rf"^{CallbackData.CMD_LAUNCH_DYNAMIC_PREFIX.value}.+$"))
    application.add_handler(CallbackQueryHandler(
        handle_back_to_subgroups, pattern=f"^{CallbackData.CMD_LAUNCHERS_BACK_TO_SUBGROUPS.value}$"))

    application.add_handler(CallbackQueryHandler(display_my_request_detail,
                            pattern=rf"^{CallbackData.MY_REQUEST_DETAIL_PREFIX.value}[0-9a-fA-F-]+$"))

    application.add_handler(CallbackQueryHandler(
        handle_request_access_button, pattern=f"^{CallbackData.CMD_REQUEST_ACCESS.value}$"))
    application.add_handler(CallbackQueryHandler(
        admin_display_access_reqs, pattern=f"^{CallbackData.CMD_ADMIN_VIEW_ACCESS_REQUESTS.value}$"))

    application.add_handler(CallbackQueryHandler(admin_display_access_reqs,
                            pattern=rf"^{CallbackData.ACCESS_REQUEST_ADMIN_PAGE_PREFIX.value}\d+$"))
    application.add_handler(CallbackQueryHandler(handle_approve_access_request_initiate,
                            pattern=rf"^{CallbackData.ACCESS_REQUEST_APPROVE_PREFIX.value}.+$"))
    application.add_handler(CallbackQueryHandler(
        handle_deny_access_request, pattern=rf"^{CallbackData.ACCESS_REQUEST_DENY_PREFIX.value}.+$"))
    application.add_handler(CallbackQueryHandler(handle_approve_access_request_assign_role,
                            pattern=rf"^{CallbackData.ACCESS_REQUEST_ASSIGN_ROLE_PREFIX.value}.+$"))

    application.add_handler(CallbackQueryHandler(
        plex_now_playing_callback, pattern=f"^{CallbackData.CMD_PLEX_VIEW_NOW_PLAYING.value}$"))
    application.add_handler(CallbackQueryHandler(plex_recently_added_select_library_callback,
                            pattern=f"^{CallbackData.CMD_PLEX_VIEW_RECENTLY_ADDED.value}$"))
    application.add_handler(CallbackQueryHandler(display_plex_library_server_tools_menu,
                            pattern=f"^{CallbackData.CMD_PLEX_LIBRARY_SERVER_TOOLS.value}$"))

    application.add_handler(CallbackQueryHandler(display_plex_server_tools_sub_menu,
                            pattern=f"^{CallbackData.CMD_PLEX_SERVER_TOOLS_SUB_MENU.value}$"))
    application.add_handler(CallbackQueryHandler(plex_scan_libraries_select_callback,
                            pattern=f"^{CallbackData.CMD_PLEX_SCAN_LIBRARIES_SELECT.value}$"))
    application.add_handler(CallbackQueryHandler(plex_refresh_library_metadata_select_callback,
                            pattern=f"^{CallbackData.CMD_PLEX_REFRESH_LIBRARY_METADATA_SELECT.value}$"))
    application.add_handler(CallbackQueryHandler(handle_plex_server_action,
                            pattern=f"^{CallbackData.CMD_PLEX_CLEAN_BUNDLES.value}$|^{CallbackData.CMD_PLEX_OPTIMIZE_DB.value}$|^{CallbackData.CMD_PLEX_SERVER_INFO.value}$"))
    application.add_handler(CallbackQueryHandler(plex_empty_trash_select_library_callback,
                            pattern=f"^{CallbackData.CMD_PLEX_EMPTY_TRASH_SELECT_LIBRARY.value}$"))

    application.add_handler(CallbackQueryHandler(
        cb_no_op_handler, pattern=f"^{CallbackData.CB_NO_OP.value}$"))

    rejection_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            admin_reject_request_callback, pattern=rf"^{CallbackData.CMD_ADMIN_REJECT_REQUEST_PREFIX.value}[0-9a-fA-F-]+$")],
        states={ASK_REJECTION_REASON: [MessageHandler(
            filters.TEXT & ~filters.COMMAND, handle_rejection_reason_input)], },
        fallbacks=[CommandHandler('cancel', cancel_rejection_reason), CommandHandler(

            'skip', handle_rejection_reason_input)],
        map_to_parent={ConversationHandler.END: ConversationHandler.END}
    )
    application.add_handler(rejection_conv_handler)

    application.add_handler(CallbackQueryHandler(display_admin_pending_requests_menu,
                            pattern=rf"^{CallbackData.ADMIN_REQUESTS_PENDING_PAGE_PREFIX.value}\d+$"))
    application.add_handler(CallbackQueryHandler(display_admin_request_details_view,
                            pattern=rf"^{CallbackData.CMD_ADMIN_VIEW_REQUEST_PREFIX.value}[0-9a-fA-F-]+$"))
    application.add_handler(CallbackQueryHandler(admin_approve_request_callback,
                            pattern=rf"^{CallbackData.CMD_ADMIN_APPROVE_REQUEST_PREFIX.value}[0-9a-fA-F-]+$"))
    application.add_handler(CallbackQueryHandler(display_admin_history_requests_menu,
                            pattern=f"^{CallbackData.CMD_ADMIN_REQUEST_HISTORY_MENU.value}$"))
    application.add_handler(CallbackQueryHandler(display_admin_history_requests_menu,
                            pattern=rf"^{CallbackData.ADMIN_REQUESTS_HISTORY_PAGE_PREFIX.value}\d+$"))

    application.add_handler(CallbackQueryHandler(
        radarr_queue_menu_wrapper, pattern=f"^{CallbackData.CMD_RADARR_VIEW_QUEUE.value}$"))
    application.add_handler(CallbackQueryHandler(display_radarr_library_maintenance_menu,
                            pattern=f"^{CallbackData.CMD_RADARR_LIBRARY_MAINTENANCE.value}$"))
    application.add_handler(CallbackQueryHandler(

        radarr_queue_menu_wrapper, pattern=rf"^{CallbackData.CMD_RADARR_QUEUE_PAGE_PREFIX.value}\d+$"))
    application.add_handler(CallbackQueryHandler(

        radarr_queue_menu_wrapper, pattern=f"^{CallbackData.CMD_RADARR_QUEUE_REFRESH.value}$"))
    application.add_handler(CallbackQueryHandler(
        handle_radarr_library_action, pattern=RADARR_ACTIONS_REGEX))
    application.add_handler(CallbackQueryHandler(radarr_add_media_page_callback,
                            pattern=rf"^{CallbackData.RADARR_ADD_MEDIA_PAGE_PREFIX.value}\d+$"))
    application.add_handler(CallbackQueryHandler(
        radarr_movie_selection_callback, pattern=rf"^{CallbackData.RADARR_SELECT_PREFIX.value}\d+$"))
    application.add_handler(CallbackQueryHandler(
        radarr_movie_selection_callback, pattern=rf"^{CallbackData.RADARR_REQUEST_PREFIX.value}\d+$"))
    application.add_handler(CallbackQueryHandler(
        radarr_customization_callback, pattern=rf"^{RADARR_CB_PREFIX}"))

    application.add_handler(CallbackQueryHandler(
        sonarr_queue_menu_wrapper, pattern=f"^{CallbackData.CMD_SONARR_VIEW_QUEUE.value}$"))
    application.add_handler(CallbackQueryHandler(
        display_sonarr_wanted_episodes_menu, pattern=f"^{CallbackData.CMD_SONARR_VIEW_WANTED.value}$"))
    application.add_handler(CallbackQueryHandler(display_sonarr_library_maintenance_menu,
                            pattern=f"^{CallbackData.CMD_SONARR_LIBRARY_MAINTENANCE.value}$"))
    application.add_handler(CallbackQueryHandler(display_sonarr_wanted_episodes_menu,
                            pattern=rf"^{CallbackData.CMD_SONARR_WANTED_PAGE_PREFIX.value}\d+$"))
    application.add_handler(CallbackQueryHandler(

        display_sonarr_wanted_episodes_menu, pattern=f"^{CallbackData.CMD_SONARR_WANTED_REFRESH.value}$"))
    application.add_handler(CallbackQueryHandler(

        sonarr_queue_menu_wrapper, pattern=rf"^{CallbackData.CMD_SONARR_QUEUE_PAGE_PREFIX.value}\d+$"))
    application.add_handler(CallbackQueryHandler(

        sonarr_queue_menu_wrapper, pattern=f"^{CallbackData.CMD_SONARR_QUEUE_REFRESH.value}$"))
    application.add_handler(CallbackQueryHandler(
        handle_sonarr_library_action, pattern=SONARR_ACTIONS_REGEX))
    application.add_handler(CallbackQueryHandler(sonarr_add_media_page_callback,
                            pattern=rf"^{CallbackData.SONARR_ADD_MEDIA_PAGE_PREFIX.value}\d+$"))
    application.add_handler(CallbackQueryHandler(
        sonarr_show_selection_callback, pattern=rf"^{CallbackData.SONARR_SELECT_PREFIX.value}\d+$"))
    application.add_handler(CallbackQueryHandler(
        sonarr_show_selection_callback, pattern=rf"^{CallbackData.SONARR_REQUEST_PREFIX.value}\d+$"))
    application.add_handler(CallbackQueryHandler(
        sonarr_customization_callback, pattern=rf"^{SONARR_CB_PREFIX}"))

    application.add_handler(CallbackQueryHandler(plex_recently_added_show_results_menu,
                            pattern=rf"^{CallbackData.CMD_PLEX_RECENTLY_ADDED_SHOW_ITEMS_FOR_LIB_PREFIX.value}\d+$"))
    application.add_handler(CallbackQueryHandler(plex_recently_added_show_results_menu,
                            pattern=rf"^{CallbackData.CMD_PLEX_RECENTLY_ADDED_PAGE_PREFIX.value}\d+_\d+$"))
    application.add_handler(CallbackQueryHandler(plex_scan_library_execute_callback,
                            pattern=rf"^{CallbackData.CMD_PLEX_SCAN_LIBRARY_PREFIX.value}(all|\d+)$"))
    application.add_handler(CallbackQueryHandler(plex_refresh_library_metadata_execute_callback,
                            pattern=rf"^{CallbackData.CMD_PLEX_REFRESH_LIBRARY_METADATA_PREFIX.value}(all|\d+)$"))
    application.add_handler(CallbackQueryHandler(plex_empty_trash_execute_callback,
                            pattern=rf"^{CallbackData.CMD_PLEX_EMPTY_TRASH_EXECUTE_PREFIX.value}(all|\d+)$"))
    application.add_handler(CallbackQueryHandler(
        plex_stop_stream_callback, pattern=rf"^{CallbackData.CMD_PLEX_STOP_STREAM_PREFIX.value}.+"))
    application.add_handler(CallbackQueryHandler(plex_search_list_episodes_callback,
                            pattern=rf"^{CallbackData.CMD_PLEX_SEARCH_LIST_EPISODES_PREFIX.value}\d+_\d+$"))
    application.add_handler(CallbackQueryHandler(plex_search_show_episode_details_callback,
                            pattern=rf"^{CallbackData.CMD_PLEX_SEARCH_SHOW_EPISODE_DETAILS_PREFIX.value}\d+$"))
    application.add_handler(CallbackQueryHandler(plex_search_refresh_item_metadata_callback,
                            pattern=rf"^{CallbackData.CMD_PLEX_SEARCH_REFRESH_ITEM_METADATA_PREFIX.value}\d+$"))
    application.add_handler(CallbackQueryHandler(plex_search_list_seasons_callback,
                            pattern=rf"^{CallbackData.CMD_PLEX_SEARCH_LIST_SEASONS_PREFIX.value}\d+$"))
    application.add_handler(CallbackQueryHandler(plex_search_show_details_callback,
                            pattern=rf"^{CallbackData.CMD_PLEX_SEARCH_SHOW_DETAILS_PREFIX.value}\d+$"))

    application.add_handler(CallbackQueryHandler(
        display_media_sound_controls_menu, pattern=f"^{CallbackData.CMD_PC_SHOW_MEDIA_SOUND_MENU.value}$"))
    application.add_handler(CallbackQueryHandler(display_system_power_controls_menu,
                            pattern=f"^{CallbackData.CMD_PC_SHOW_SYSTEM_POWER_MENU.value}$"))
    application.add_handler(CallbackQueryHandler(
        handle_media_sound_action, pattern=rf"^{PC_MEDIA_PREFIX}(?!shutdown|restart|no_op_info).*"))
    application.add_handler(CallbackQueryHandler(
        handle_media_sound_action, pattern=rf"^{PC_MEDIA_PREFIX}no_op_info$"))
    application.add_handler(CallbackQueryHandler(
        handle_power_action, pattern=rf"^{PC_POWER_PREFIX}(shutdown|restart)"))

    application.add_handler(CallbackQueryHandler(
        display_my_requests_menu, pattern=rf"^{CallbackData.MY_REQUESTS_PAGE_PREFIX.value}\d+$"))

    root_menu_exact_match_patterns = [
        CallbackData.CMD_HOME_BACK.value, CallbackData.CMD_SETTINGS.value,
        CallbackData.CMD_ADD_MOVIE_INIT.value, CallbackData.CMD_ADD_SHOW_INIT.value,
        CallbackData.CMD_ADD_DOWNLOAD_INIT.value,
        CallbackData.CMD_LAUNCHERS_MENU.value,
        CallbackData.CMD_PC_CONTROL_ROOT.value,
        CallbackData.CMD_RADARR_CONTROLS.value, CallbackData.CMD_SONARR_CONTROLS.value,
        CallbackData.CMD_PLEX_CONTROLS.value,

        CallbackData.CMD_PLEX_MENU_BACK.value,

        CallbackData.RADARR_CANCEL.value,

        CallbackData.SONARR_CANCEL.value,
        CallbackData.CMD_MY_REQUESTS_MENU.value, CallbackData.CMD_ADMIN_REQUESTS_MENU.value,
        CallbackData.CMD_PLEX_INITIATE_SEARCH.value,

    ]
    regex_root_menu_exact_triggers = "^(" + "|".join(f"({re.escape(item)})" for item in list(
        dict.fromkeys(root_menu_exact_match_patterns))) + ")$"
    application.add_handler(CallbackQueryHandler(
        main_menu_callback, pattern=regex_root_menu_exact_triggers))

    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_pending_search))
    logger.info(
        "Telegram bot handlers configured with Phase C access request system.")


RADARR_ACTIONS_REGEX = "^(" + "|".join(re.escape(e.value) for e in [CallbackData.CMD_RADARR_SCAN_FILES, CallbackData.CMD_RADARR_UPDATE_METADATA, CallbackData.CMD_RADARR_RENAME_FILES, CallbackData.CMD_RADARR_QUEUE_BACK_TO_LIST,]) + \
    f"|{re.escape(CallbackData.CMD_RADARR_QUEUE_ITEM_ACTIONS_MENU_PREFIX.value)}[0-9a-zA-Z_.-]+" + f"|{re.escape(CallbackData.CMD_RADARR_QUEUE_ITEM_REMOVE_NO_BLOCKLIST_PREFIX.value)}[0-9a-zA-Z_.-]+" + \
    f"|{re.escape(CallbackData.CMD_RADARR_QUEUE_ITEM_BLOCKLIST_SEARCH_PREFIX.value)}[0-9a-zA-Z_.-]+" + ")$"
SONARR_ACTIONS_REGEX = "^(" + "|".join(re.escape(e.value) for e in [CallbackData.CMD_SONARR_SCAN_FILES, CallbackData.CMD_SONARR_UPDATE_METADATA, CallbackData.CMD_SONARR_RENAME_FILES, CallbackData.CMD_SONARR_SEARCH_WANTED_ALL_NOW, CallbackData.CMD_SONARR_QUEUE_BACK_TO_LIST,]) + \
    f"|{re.escape(CallbackData.CMD_SONARR_WANTED_SEARCH_EPISODE_PREFIX.value)}[0-9]+" + f"|{re.escape(CallbackData.CMD_SONARR_QUEUE_ITEM_ACTIONS_MENU_PREFIX.value)}[0-9a-zA-Z_.-]+" + \
    f"|{re.escape(CallbackData.CMD_SONARR_QUEUE_ITEM_REMOVE_NO_BLOCKLIST_PREFIX.value)}[0-9a-zA-Z_.-]+" + \
    f"|{re.escape(CallbackData.CMD_SONARR_QUEUE_ITEM_BLOCKLIST_SEARCH_PREFIX.value)}[0-9a-zA-Z_.-]+" + ")$"
