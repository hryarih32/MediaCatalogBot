
from enum import Enum


class CallbackData(str, Enum):

    CMD_SETTINGS = "cmd_settings"
    CMD_HOME_BACK = "cmd_home_back"

    CMD_ADD_MOVIE_INIT = "cmd_add_movie_init"
    CMD_ADD_SHOW_INIT = "cmd_add_show_init"
    CMD_ADD_DOWNLOAD_INIT = "cmd_add_download_init"

    CMD_RADARR_CONTROLS = "cmd_radarr_controls"
    CMD_SONARR_CONTROLS = "cmd_sonarr_controls"
    CMD_PLEX_CONTROLS = "cmd_plex_controls"
    CMD_PC_CONTROL_ROOT = "cmd_pc_control_root"

    CMD_RADARR_VIEW_QUEUE = "cmd_radarr_view_queue"
    CMD_RADARR_LIBRARY_MAINTENANCE = "cmd_radarr_library_maintenance"
    RADARR_ADD_MEDIA_PAGE_PREFIX = "radarr_add_page_"
    RADARR_SELECT_PREFIX = "radarr_select_"
    RADARR_REQUEST_PREFIX = "radarr_request_"
    RADARR_CANCEL = "radarr_cancel_add"
    CMD_RADARR_QUEUE_PAGE_PREFIX = "radarr_queue_page_"
    CMD_RADARR_QUEUE_REFRESH = "cmd_radarr_queue_refresh"
    CMD_RADARR_QUEUE_ITEM_ACTIONS_MENU_PREFIX = "radarr_q_actions_menu_"
    CMD_RADARR_QUEUE_ITEM_REMOVE_NO_BLOCKLIST_PREFIX = "radarr_q_rem_noblock_"
    CMD_RADARR_QUEUE_ITEM_BLOCKLIST_ONLY_PREFIX = "radarr_q_block_only_"
    CMD_RADARR_QUEUE_ITEM_BLOCKLIST_SEARCH_PREFIX = "radarr_q_block_search_"

    CMD_RADARR_QUEUE_BACK_TO_LIST = "radarr_q_back_to_list"
    CMD_RADARR_SCAN_FILES = "cmd_radarr_scan_files"
    CMD_RADARR_UPDATE_METADATA = "cmd_radarr_update_metadata"
    CMD_RADARR_RENAME_FILES = "cmd_radarr_rename_files"

    CMD_SONARR_VIEW_QUEUE = "cmd_sonarr_view_queue"
    CMD_SONARR_VIEW_WANTED = "cmd_sonarr_view_wanted"
    CMD_SONARR_LIBRARY_MAINTENANCE = "cmd_sonarr_library_maintenance"
    SONARR_ADD_MEDIA_PAGE_PREFIX = "sonarr_add_page_"
    SONARR_SELECT_PREFIX = "sonarr_select_"
    SONARR_REQUEST_PREFIX = "sonarr_request_"
    SONARR_CANCEL = "sonarr_cancel_add"
    CMD_SONARR_QUEUE_PAGE_PREFIX = "sonarr_queue_page_"
    CMD_SONARR_QUEUE_REFRESH = "cmd_sonarr_queue_refresh"
    CMD_SONARR_QUEUE_ITEM_ACTIONS_MENU_PREFIX = "sonarr_q_actions_menu_"
    CMD_SONARR_QUEUE_ITEM_REMOVE_NO_BLOCKLIST_PREFIX = "sonarr_q_rem_noblock_"
    CMD_SONARR_QUEUE_ITEM_BLOCKLIST_ONLY_PREFIX = "sonarr_q_block_only_"
    CMD_SONARR_QUEUE_ITEM_BLOCKLIST_SEARCH_PREFIX = "sonarr_q_block_search_"

    CMD_SONARR_QUEUE_BACK_TO_LIST = "sonarr_q_back_to_list"
    CMD_SONARR_SEARCH_WANTED_ALL_NOW = "cmd_sonarr_search_wanted_all_now"
    CMD_SONARR_WANTED_REFRESH = "cmd_sonarr_wanted_refresh"
    CMD_SONARR_WANTED_PAGE_PREFIX = "sonarr_wanted_page_"
    CMD_SONARR_WANTED_SEARCH_EPISODE_PREFIX = "sonarr_wanted_search_ep_"
    CMD_SONARR_SCAN_FILES = "cmd_sonarr_scan_files"
    CMD_SONARR_UPDATE_METADATA = "cmd_sonarr_update_metadata"
    CMD_SONARR_RENAME_FILES = "cmd_sonarr_rename_files"

    CMD_PLEX_VIEW_NOW_PLAYING = "cmd_plex_view_now_playing"
    CMD_PLEX_VIEW_RECENTLY_ADDED = "cmd_plex_view_recently_added"
    CMD_PLEX_INITIATE_SEARCH = "cmd_plex_initiate_search"
    CMD_PLEX_LIBRARY_SERVER_TOOLS = "cmd_plex_library_server_tools"
    CMD_PLEX_STOP_STREAM_PREFIX = "cmd_plex_stop_stream_"
    CMD_PLEX_RECENTLY_ADDED_SHOW_ITEMS_FOR_LIB_PREFIX = "cmd_plex_recent_items_lib_"
    CMD_PLEX_RECENTLY_ADDED_PAGE_PREFIX = "plex_ra_page_"
    CMD_PLEX_SEARCH_SHOW_DETAILS_PREFIX = "cmd_plex_search_details_"
    CMD_PLEX_SEARCH_REFRESH_ITEM_METADATA_PREFIX = "cmd_plex_search_refresh_item_"
    CMD_PLEX_SEARCH_LIST_SEASONS_PREFIX = "cmd_plex_list_seasons_"
    CMD_PLEX_SEARCH_LIST_EPISODES_PREFIX = "cmd_plex_list_episodes_"
    CMD_PLEX_SEARCH_SHOW_EPISODE_DETAILS_PREFIX = "cmd_plex_show_ep_details_"
    CMD_PLEX_MENU_BACK = "cmd_plex_menu_back"
    CMD_PLEX_SCAN_LIBRARIES_SELECT = "cmd_plex_scan_select_lib"
    CMD_PLEX_SCAN_LIBRARY_PREFIX = "cmd_plex_scan_lib_"
    CMD_PLEX_REFRESH_LIBRARY_METADATA_SELECT = "cmd_plex_refresh_select_lib"
    CMD_PLEX_REFRESH_LIBRARY_METADATA_PREFIX = "cmd_plex_refresh_lib_"
    CMD_PLEX_SERVER_TOOLS_SUB_MENU = "cmd_plex_server_tools_sub_menu"
    CMD_PLEX_CLEAN_BUNDLES = "cmd_plex_clean_bundles"
    CMD_PLEX_EMPTY_TRASH_SELECT_LIBRARY = "cmd_plex_empty_trash_select_lib"
    CMD_PLEX_EMPTY_TRASH_EXECUTE_PREFIX = "cmd_plex_empty_trash_exec_"
    CMD_PLEX_OPTIMIZE_DB = "cmd_plex_optimize_db"
    CMD_PLEX_SERVER_INFO = "cmd_plex_server_info"

    CMD_PC_SHOW_MEDIA_SOUND_MENU = "cmd_pc_show_media_sound"
    CMD_PC_SHOW_SYSTEM_POWER_MENU = "cmd_pc_show_system_power"

    CMD_MY_REQUESTS_MENU = "cmd_my_requests_menu"
    MY_REQUESTS_PAGE_PREFIX = "my_req_page_"
    MY_REQUEST_DETAIL_PREFIX = "my_req_detail_"

    CMD_ADMIN_REQUESTS_MENU = "cmd_admin_requests_menu"
    ADMIN_REQUESTS_PENDING_PAGE_PREFIX = "admin_req_pending_page_"
    CMD_ADMIN_VIEW_REQUEST_PREFIX = "admin_view_req_"
    CMD_ADMIN_APPROVE_REQUEST_PREFIX = "admin_approve_req_"
    CMD_ADMIN_REJECT_REQUEST_PREFIX = "admin_reject_req_"
    CMD_ADMIN_REQUEST_HISTORY_MENU = "admin_req_hist_menu"
    ADMIN_REQUESTS_HISTORY_PAGE_PREFIX = "admin_req_hist_page_"

    CMD_LAUNCHERS_MENU = "cmd_launchers_menu"
    CMD_LAUNCHER_SUBGROUP_PREFIX = "cb_launcher_sg_"
    CMD_LAUNCH_DYNAMIC_PREFIX = "cb_launch_dyn_"
    CMD_LAUNCHERS_BACK_TO_SUBGROUPS = "cb_launchers_back_to_sg"

    CMD_REQUEST_ACCESS = "cmd_request_access"
    CMD_ADMIN_VIEW_ACCESS_REQUESTS = "cmd_admin_view_access_reqs"

    ACCESS_REQUEST_ADMIN_PAGE_PREFIX = "admin_access_req_page_"
    ACCESS_REQUEST_APPROVE_PREFIX = "acc_req_approve_"
    ACCESS_REQUEST_DENY_PREFIX = "acc_req_deny_"
    ACCESS_REQUEST_ASSIGN_ROLE_PREFIX = "acc_req_assign_role_"

    CMD_ADMIN_MANAGE_USERS_MENU = "cmd_admin_manage_users"
    CMD_ADMIN_USER_PAGE_PREFIX = "admin_user_page_"
    CMD_ADMIN_USER_SELECT_FOR_EDIT_PREFIX = "admin_user_edit_"
    CMD_ADMIN_USER_CHANGE_ROLE_PREFIX = "admin_user_role_"
    CMD_ADMIN_USER_REMOVE_PREFIX = "admin_user_remove_"  # Remains for direct removal
    # Changed from send_msg
    CMD_ADMIN_CREATE_TICKET_FOR_USER_INIT_PREFIX = "admin_create_ticket_init_"
    CMD_ADMIN_USER_ADD_INIT = "admin_user_add_init"

    CMD_USER_VIEW_ADMIN_MESSAGE_PREFIX = "user_view_admin_msg_"
    CMD_USER_MARK_ADMIN_MESSAGE_READ_PREFIX = "user_mark_admin_msg_read_"
    CMD_USER_REPLY_TO_ADMIN_INIT_PREFIX = "user_reply_admin_init_"

    CMD_ADMIN_VIEW_USER_REPLY_PREFIX = "admin_view_user_reply_"
    CMD_ADMIN_MARK_USER_REPLY_READ_PREFIX = "admin_mark_user_reply_read_"
    CMD_ADMIN_END_REPLY_THREAD_PREFIX = "admin_end_reply_thread_"

    # --- Ticketing System ---
    CMD_TICKETS_MENU = "cmd_tickets_menu"
    CMD_USER_VIEW_TICKET_PREFIX = "user_view_ticket_"
    # Placeholder for Phase 2
    CMD_USER_REPLY_TO_TICKET_INIT_PREFIX = "user_reply_ticket_init_"
    CMD_USER_CLOSE_TICKET_PREFIX = "user_close_ticket_"  # Placeholder for Phase 2
    CMD_USER_NEW_TICKET_INIT = "user_new_ticket_init"  # Placeholder for Phase 2

    # New for admin viewing a specific ticket
    CMD_ADMIN_VIEW_TICKET_PREFIX = "admin_view_ticket_"
    # Placeholder for admin reply
    CMD_ADMIN_REPLY_TO_TICKET_INIT_PREFIX = "admin_reply_ticket_init_"
    # Placeholder for admin closing
    CMD_ADMIN_CLOSE_TICKET_PREFIX = "admin_close_ticket_"
    # For admin ticket list pagination
    CMD_ADMIN_TICKETS_PAGE_PREFIX = "admin_tickets_page_"

    CB_NO_OP = "cb_no_op"
