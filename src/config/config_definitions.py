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
