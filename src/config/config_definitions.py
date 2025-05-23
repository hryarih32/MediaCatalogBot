from enum import Enum


PC_CONTROL_ENABLED_KEY = "PC_CONTROL_ENABLED"


CONFIG_KEYS_LOGGING = [
    "LOG_LEVEL"
]


CONFIG_KEYS_CORE = [
    "TELEGRAM_BOT_TOKEN", "CHAT_ID"
]

CONFIG_KEYS_PLEX = ["PLEX_ENABLED", "PLEX_URL", "PLEX_TOKEN"]
CONFIG_KEYS_RADARR = ["RADARR_ENABLED", "RADARR_API_URL", "RADARR_API_KEY"]
CONFIG_KEYS_SONARR = ["SONARR_ENABLED", "SONARR_API_URL", "SONARR_API_KEY"]
CONFIG_KEYS_ABDM = ["ABDM_ENABLED", "ABDM_PORT"]
CONFIG_KEYS_SCRIPT_1 = ["SCRIPT_1_ENABLED", "SCRIPT_1_NAME", "SCRIPT_1_PATH"]
CONFIG_KEYS_SCRIPT_2 = ["SCRIPT_2_ENABLED", "SCRIPT_2_NAME", "SCRIPT_2_PATH"]
CONFIG_KEYS_SCRIPT_3 = ["SCRIPT_3_ENABLED", "SCRIPT_3_NAME", "SCRIPT_3_PATH"]
CONFIG_KEYS_PC_CONTROL = [PC_CONTROL_ENABLED_KEY]
CONFIG_KEYS_UI_BEHAVIOR = [
    "ADD_MEDIA_MAX_SEARCH_RESULTS", "ADD_MEDIA_ITEMS_PER_PAGE"]
CONFIG_KEYS_PLEX_LAUNCHER = ["PLEX_LAUNCHER_ENABLED",
                             "PLEX_LAUNCHER_NAME", "PLEX_LAUNCHER_PATH"]
CONFIG_KEYS_SONARR_LAUNCHER = [
    "SONARR_LAUNCHER_ENABLED", "SONARR_LAUNCHER_NAME", "SONARR_LAUNCHER_PATH"]
CONFIG_KEYS_RADARR_LAUNCHER = [
    "RADARR_LAUNCHER_ENABLED", "RADARR_LAUNCHER_NAME", "RADARR_LAUNCHER_PATH"]
CONFIG_KEYS_PROWLARR_LAUNCHER = [
    "PROWLARR_LAUNCHER_ENABLED", "PROWLARR_LAUNCHER_NAME", "PROWLARR_LAUNCHER_PATH"]
CONFIG_KEYS_TORRENT_LAUNCHER = [
    "TORRENT_LAUNCHER_ENABLED", "TORRENT_LAUNCHER_NAME", "TORRENT_LAUNCHER_PATH"]
CONFIG_KEYS_ABDM_LAUNCHER = [
    "ABDM_LAUNCHER_ENABLED", "ABDM_LAUNCHER_NAME", "ABDM_LAUNCHER_PATH"]


ALL_USER_CONFIG_KEYS = CONFIG_KEYS_CORE + \
    CONFIG_KEYS_PLEX + \
    CONFIG_KEYS_RADARR + \
    CONFIG_KEYS_SONARR + \
    CONFIG_KEYS_ABDM + \
    CONFIG_KEYS_SCRIPT_1 + \
    CONFIG_KEYS_SCRIPT_2 + \
    CONFIG_KEYS_SCRIPT_3 + \
    CONFIG_KEYS_PC_CONTROL + \
    CONFIG_KEYS_UI_BEHAVIOR + \
    CONFIG_KEYS_PLEX_LAUNCHER + \
    CONFIG_KEYS_SONARR_LAUNCHER + \
    CONFIG_KEYS_RADARR_LAUNCHER + \
    CONFIG_KEYS_PROWLARR_LAUNCHER + \
    CONFIG_KEYS_TORRENT_LAUNCHER + \
    CONFIG_KEYS_ABDM_LAUNCHER + \
    CONFIG_KEYS_LOGGING


LOG_LEVEL_OPTIONS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

CONFIG_FIELD_DEFINITIONS = {

    "TELEGRAM_BOT_TOKEN": {"label": "Telegram Bot Token:", "type": "entry", "width": 60, "required": True},
    "CHAT_ID": {"label": "Your Telegram Chat ID (numerical):", "type": "entry", "width": 60, "required": True},
    "PLEX_ENABLED": {"label": "Enable Plex API Features", "type": "checkbutton_in_frame_title", "default": False},
    "PLEX_URL": {"label": "Plex API URL (e.g., http://localhost:32400):", "type": "entry", "width": 60, "depends_on": "PLEX_ENABLED", "required_if_enabled": "PLEX_ENABLED"},
    "PLEX_TOKEN": {"label": "Plex API Token:", "type": "entry", "width": 60, "depends_on": "PLEX_ENABLED", "required_if_enabled": "PLEX_ENABLED"},
    "RADARR_ENABLED": {"label": "Enable Radarr API Features", "type": "checkbutton_in_frame_title", "default": False},
    "RADARR_API_URL": {"label": "Radarr API URL (e.g., http://localhost:7878):", "type": "entry", "width": 60, "depends_on": "RADARR_ENABLED", "required_if_enabled": "RADARR_ENABLED"},
    "RADARR_API_KEY": {"label": "Radarr API Key:", "type": "entry", "width": 60, "depends_on": "RADARR_ENABLED", "required_if_enabled": "RADARR_ENABLED"},
    "SONARR_ENABLED": {"label": "Enable Sonarr API Features", "type": "checkbutton_in_frame_title", "default": False},
    "SONARR_API_URL": {"label": "Sonarr API URL (e.g., http://localhost:8989):", "type": "entry", "width": 60, "depends_on": "SONARR_ENABLED", "required_if_enabled": "SONARR_ENABLED"},
    "SONARR_API_KEY": {"label": "Sonarr API Key:", "type": "entry", "width": 60, "depends_on": "SONARR_ENABLED", "required_if_enabled": "SONARR_ENABLED"},
    PC_CONTROL_ENABLED_KEY: {"label": "Enable PC Keyboard/System Controls", "type": "checkbutton_in_frame_title", "default": False},
    "ABDM_ENABLED": {"label": "Enable AB Download Manager Integration", "type": "checkbutton_in_frame_title", "default": False},
    "ABDM_PORT": {"label": "ABDM API Port (default: 15151):", "type": "entry", "width": 10, "default": "15151", "depends_on": "ABDM_ENABLED", "required_if_enabled": "ABDM_ENABLED"},
    "SCRIPT_1_ENABLED": {"label": "Enable Script 1", "type": "checkbutton", "default": False},
    "SCRIPT_1_NAME": {"label": "Script 1 Button Name:", "type": "entry", "width": 40, "depends_on": "SCRIPT_1_ENABLED", "required_if_enabled": "SCRIPT_1_ENABLED"},
    "SCRIPT_1_PATH": {"label": "Script 1 Executable/Script Path:", "type": "file_path", "width": 40, "depends_on": "SCRIPT_1_ENABLED", "required_if_enabled": "SCRIPT_1_ENABLED"},
    "SCRIPT_2_ENABLED": {"label": "Enable Script 2", "type": "checkbutton", "default": False},
    "SCRIPT_2_NAME": {"label": "Script 2 Button Name:", "type": "entry", "width": 40, "depends_on": "SCRIPT_2_ENABLED", "required_if_enabled": "SCRIPT_2_ENABLED"},
    "SCRIPT_2_PATH": {"label": "Script 2 Executable/Script Path:", "type": "file_path", "width": 40, "depends_on": "SCRIPT_2_ENABLED", "required_if_enabled": "SCRIPT_2_ENABLED"},
    "SCRIPT_3_ENABLED": {"label": "Enable Script 3", "type": "checkbutton", "default": False},
    "SCRIPT_3_NAME": {"label": "Script 3 Button Name:", "type": "entry", "width": 40, "depends_on": "SCRIPT_3_ENABLED", "required_if_enabled": "SCRIPT_3_ENABLED"},
    "SCRIPT_3_PATH": {"label": "Script 3 Executable/Script Path:", "type": "file_path", "width": 40, "depends_on": "SCRIPT_3_ENABLED", "required_if_enabled": "SCRIPT_3_ENABLED"},
    "PLEX_LAUNCHER_ENABLED": {"label": "Enable Plex Launcher", "type": "checkbutton", "default": False},
    "PLEX_LAUNCHER_NAME": {"label": "Plex Button Name:", "type": "entry", "width": 40, "default": "Launch Plex", "depends_on": "PLEX_LAUNCHER_ENABLED", "required_if_enabled": "PLEX_LAUNCHER_ENABLED"},
    "PLEX_LAUNCHER_PATH": {"label": "Plex Executable Path:", "type": "file_path", "width": 40, "depends_on": "PLEX_LAUNCHER_ENABLED", "required_if_enabled": "PLEX_LAUNCHER_ENABLED"},
    "SONARR_LAUNCHER_ENABLED": {"label": "Enable Sonarr Launcher", "type": "checkbutton", "default": False},
    "SONARR_LAUNCHER_NAME": {"label": "Sonarr Button Name:", "type": "entry", "width": 40, "default": "Launch Sonarr", "depends_on": "SONARR_LAUNCHER_ENABLED", "required_if_enabled": "SONARR_LAUNCHER_ENABLED"},
    "SONARR_LAUNCHER_PATH": {"label": "Sonarr Executable Path:", "type": "file_path", "width": 40, "depends_on": "SONARR_LAUNCHER_ENABLED", "required_if_enabled": "SONARR_LAUNCHER_ENABLED"},
    "RADARR_LAUNCHER_ENABLED": {"label": "Enable Radarr Launcher", "type": "checkbutton", "default": False},
    "RADARR_LAUNCHER_NAME": {"label": "Radarr Button Name:", "type": "entry", "width": 40, "default": "Launch Radarr", "depends_on": "RADARR_LAUNCHER_ENABLED", "required_if_enabled": "RADARR_LAUNCHER_ENABLED"},
    "RADARR_LAUNCHER_PATH": {"label": "Radarr Executable Path:", "type": "file_path", "width": 40, "depends_on": "RADARR_LAUNCHER_ENABLED", "required_if_enabled": "RADARR_LAUNCHER_ENABLED"},
    "PROWLARR_LAUNCHER_ENABLED": {"label": "Enable Prowlarr Launcher", "type": "checkbutton", "default": False},
    "PROWLARR_LAUNCHER_NAME": {"label": "Prowlarr Button Name:", "type": "entry", "width": 40, "default": "Launch Prowlarr", "depends_on": "PROWLARR_LAUNCHER_ENABLED", "required_if_enabled": "PROWLARR_LAUNCHER_ENABLED"},
    "PROWLARR_LAUNCHER_PATH": {"label": "Prowlarr Executable Path:", "type": "file_path", "width": 40, "depends_on": "PROWLARR_LAUNCHER_ENABLED", "required_if_enabled": "PROWLARR_LAUNCHER_ENABLED"},
    "TORRENT_LAUNCHER_ENABLED": {"label": "Enable Torrent Client Launcher", "type": "checkbutton", "default": False},
    "TORRENT_LAUNCHER_NAME": {"label": "Torrent Client Button Name:", "type": "entry", "width": 40, "default": "Launch Torrent Client", "depends_on": "TORRENT_LAUNCHER_ENABLED", "required_if_enabled": "TORRENT_LAUNCHER_ENABLED"},
    "TORRENT_LAUNCHER_PATH": {"label": "Torrent Client Executable Path:", "type": "file_path", "width": 40, "depends_on": "TORRENT_LAUNCHER_ENABLED", "required_if_enabled": "TORRENT_LAUNCHER_ENABLED"},
    "ABDM_LAUNCHER_ENABLED": {"label": "Enable AB Download Manager Launcher", "type": "checkbutton", "default": False},
    "ABDM_LAUNCHER_NAME": {"label": "ABDM Button Name:", "type": "entry", "width": 40, "default": "Launch ABDM", "depends_on": "ABDM_LAUNCHER_ENABLED", "required_if_enabled": "ABDM_LAUNCHER_ENABLED"},
    "ABDM_LAUNCHER_PATH": {"label": "ABDM Executable Path:", "type": "file_path", "width": 40, "depends_on": "ABDM_LAUNCHER_ENABLED", "required_if_enabled": "ABDM_LAUNCHER_ENABLED"},
    "ADD_MEDIA_MAX_SEARCH_RESULTS": {"label": "Max API Search Results to Process (Radarr/Sonarr):", "type": "entry", "width": 10, "default": "30"},
    "ADD_MEDIA_ITEMS_PER_PAGE": {"label": "Items Per Page (Search Results & Plex Lists):", "type": "entry", "width": 10, "default": "5"},


    "LOG_LEVEL": {"label": "Logging Level:", "type": "combobox", "options": LOG_LEVEL_OPTIONS, "default": "INFO", "width": 15},
}


class SearchType(str, Enum):
    MOVIE = "movie"
    TV = "tv"


class CallbackData(str, Enum):
    CMD_ADD_DOWNLOAD_INIT = "cmd_add_download_init"

    CMD_SETTINGS = "cmd_settings"
    CMD_HOME_BACK = "cmd_home_back"

    CMD_ADD_MOVIE_INIT = "cmd_add_movie_init"
    CMD_ADD_SHOW_INIT = "cmd_add_show_init"

    CMD_RADARR_CONTROLS = "cmd_radarr_controls"
    CMD_SONARR_CONTROLS = "cmd_sonarr_controls"
    CMD_PLEX_CONTROLS = "cmd_plex_controls"

    CMD_RADARR_VIEW_QUEUE = "cmd_radarr_view_queue"
    CMD_RADARR_LIBRARY_MAINTENANCE = "cmd_radarr_library_maintenance"
    RADARR_ADD_MEDIA_PAGE_PREFIX = "radarr_add_page_"
    RADARR_SELECT_PREFIX = "radarr_select_"
    RADARR_CANCEL = "radarr_cancel_add"
    CMD_RADARR_QUEUE_PAGE_PREFIX = "radarr_queue_page_"
    CMD_RADARR_QUEUE_REFRESH = "cmd_radarr_queue_refresh"
    CMD_RADARR_QUEUE_ITEM_ACTIONS_MENU_PREFIX = "radarr_q_actions_menu_"
    CMD_RADARR_QUEUE_ITEM_REMOVE_NO_BLOCKLIST_PREFIX = "radarr_q_rem_noblock_"
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
    SONARR_CANCEL = "sonarr_cancel_add"
    CMD_SONARR_QUEUE_PAGE_PREFIX = "sonarr_queue_page_"
    CMD_SONARR_QUEUE_REFRESH = "cmd_sonarr_queue_refresh"
    CMD_SONARR_QUEUE_ITEM_ACTIONS_MENU_PREFIX = "sonarr_q_actions_menu_"
    CMD_SONARR_QUEUE_ITEM_REMOVE_NO_BLOCKLIST_PREFIX = "sonarr_q_rem_noblock_"
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

    CMD_LAUNCHERS_MENU = "cmd_launchers_menu"
    CMD_LAUNCH_PLEX = "cmd_launch_plex"
    CMD_LAUNCH_SONARR = "cmd_launch_sonarr"
    CMD_LAUNCH_RADARR = "cmd_launch_radarr"
    CMD_LAUNCH_PROWLARR = "cmd_launch_prowlarr"
    CMD_LAUNCH_TORRENT = "cmd_launch_torrent"
    CMD_LAUNCH_ABDM = "cmd_launch_abdm"
    CMD_SCRIPT_1 = "cmd_script_1"
    CMD_SCRIPT_2 = "cmd_script_2"
    CMD_SCRIPT_3 = "cmd_script_3"

    CMD_PC_CONTROL_ROOT = "cmd_pc_control_root"
    CMD_PC_SHOW_MEDIA_SOUND_MENU = "cmd_pc_show_media_sound"
    CMD_PC_SHOW_SYSTEM_POWER_MENU = "cmd_pc_show_system_power"
