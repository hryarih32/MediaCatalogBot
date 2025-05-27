
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

CONFIG_KEYS_PC_CONTROL = [PC_CONTROL_ENABLED_KEY]
CONFIG_KEYS_UI_BEHAVIOR = [
    "ADD_MEDIA_MAX_SEARCH_RESULTS", "ADD_MEDIA_ITEMS_PER_PAGE"]

ALL_USER_CONFIG_KEYS = list(dict.fromkeys(
    CONFIG_KEYS_CORE +
    CONFIG_KEYS_PLEX +
    CONFIG_KEYS_RADARR +
    CONFIG_KEYS_SONARR +
    CONFIG_KEYS_ABDM +

    CONFIG_KEYS_PC_CONTROL +
    CONFIG_KEYS_UI_BEHAVIOR +
    CONFIG_KEYS_LOGGING
))

LOG_LEVEL_OPTIONS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

CONFIG_FIELD_DEFINITIONS = {

    "TELEGRAM_BOT_TOKEN": {"label": "Telegram Bot Token:", "type": "entry", "width": 60, "required": True, "group": "core"},
    "CHAT_ID": {"label": "Primary Admin Telegram Chat ID (numerical):", "type": "entry", "width": 60, "required": True, "group": "core"},

    "LOG_LEVEL": {"label": "Logging Level:", "type": "combobox", "options": LOG_LEVEL_OPTIONS, "default": "INFO", "width": 15, "group": "general"},
    PC_CONTROL_ENABLED_KEY: {"label": "Enable PC Keyboard/System Controls", "type": "checkbutton_in_frame_title", "default": False, "group": "general"},
    "ADD_MEDIA_MAX_SEARCH_RESULTS": {"label": "Max API Search Results to Process (Radarr/Sonarr):", "type": "entry", "width": 10, "default": 30, "group": "general"},
    "ADD_MEDIA_ITEMS_PER_PAGE": {"label": "Items Per Page (Search Results & Plex Lists):", "type": "entry", "width": 10, "default": 5, "group": "general"},

    "PLEX_ENABLED": {"label": "Enable Plex API Features", "type": "checkbutton_in_frame_title", "default": False, "group": "api_plex"},
    "PLEX_URL": {"label": "Plex API URL (e.g., http://localhost:32400):", "type": "entry", "width": 60, "depends_on": "PLEX_ENABLED", "required_if_enabled": "PLEX_ENABLED", "group": "api_plex"},
    "PLEX_TOKEN": {"label": "Plex API Token:", "type": "entry", "width": 60, "depends_on": "PLEX_ENABLED", "required_if_enabled": "PLEX_ENABLED", "group": "api_plex"},

    "RADARR_ENABLED": {"label": "Enable Radarr API Features", "type": "checkbutton_in_frame_title", "default": False, "group": "api_radarr"},
    "RADARR_API_URL": {"label": "Radarr API URL (e.g., http://localhost:7878):", "type": "entry", "width": 60, "depends_on": "RADARR_ENABLED", "required_if_enabled": "RADARR_ENABLED", "group": "api_radarr"},
    "RADARR_API_KEY": {"label": "Radarr API Key:", "type": "entry", "width": 60, "depends_on": "RADARR_ENABLED", "required_if_enabled": "RADARR_ENABLED", "group": "api_radarr"},

    "SONARR_ENABLED": {"label": "Enable Sonarr API Features", "type": "checkbutton_in_frame_title", "default": False, "group": "api_sonarr"},
    "SONARR_API_URL": {"label": "Sonarr API URL (e.g., http://localhost:8989):", "type": "entry", "width": 60, "depends_on": "SONARR_ENABLED", "required_if_enabled": "SONARR_ENABLED", "group": "api_sonarr"},
    "SONARR_API_KEY": {"label": "Sonarr API Key:", "type": "entry", "width": 60, "depends_on": "SONARR_ENABLED", "required_if_enabled": "SONARR_ENABLED", "group": "api_sonarr"},

    "ABDM_ENABLED": {"label": "Enable AB Download Manager Integration", "type": "checkbutton_in_frame_title", "default": False, "group": "api_abdm"},
    "ABDM_PORT": {"label": "ABDM API Port (default: 15151):", "type": "entry", "width": 10, "default": 15151, "depends_on": "ABDM_ENABLED", "required_if_enabled": "ABDM_ENABLED", "group": "api_abdm"},

}


class SearchType(str, Enum):
    MOVIE = "movie"
    TV = "tv"
