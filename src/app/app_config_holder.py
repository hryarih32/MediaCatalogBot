loaded_config = None
PROJECT_VERSION = "Unknown"

DEFAULT_ADD_MEDIA_MAX_SEARCH_RESULTS = 30
DEFAULT_ADD_MEDIA_ITEMS_PER_PAGE = 5

ROLE_ADMIN = "ADMIN"
ROLE_STANDARD_USER = "STANDARD_USER"

ROLE_REQUEST_ACCESS = "REQUEST_ACCESS"
ROLE_UNKNOWN = "UNKNOWN"


def set_config(config_module):
    global loaded_config
    loaded_config = config_module


def get_config():
    return loaded_config


def get_project_version():

    return PROJECT_VERSION


def get_chat_id_str():
    if loaded_config and hasattr(loaded_config, 'CHAT_ID'):
        return str(loaded_config.CHAT_ID)
    return None


def is_primary_admin(chat_id: int | str) -> bool:
    """Checks if the given chat_id is the primary admin defined in config."""
    primary_admin_chat_id_str = get_chat_id_str()
    if primary_admin_chat_id_str:
        return str(chat_id) == primary_admin_chat_id_str
    return False


def get_user_role(chat_id: int | str) -> str:
    """
    Determines the role of a user.
    In Phase 2, this will be basic: primary admin is ADMIN, others are STANDARD_USER for menu display.
    This will be expanded in later phases with a user management system.
    """
    if is_primary_admin(chat_id):
        return ROLE_ADMIN

    return ROLE_STANDARD_USER


def is_plex_enabled():
    if loaded_config and hasattr(loaded_config, 'PLEX_ENABLED'):
        return loaded_config.PLEX_ENABLED
    return False


def get_plex_url():
    if loaded_config and hasattr(loaded_config, 'PLEX_URL'):
        return loaded_config.PLEX_URL
    return None


def get_plex_token():
    if loaded_config and hasattr(loaded_config, 'PLEX_TOKEN'):
        return loaded_config.PLEX_TOKEN
    return None


def is_radarr_enabled():
    if loaded_config and hasattr(loaded_config, 'RADARR_ENABLED'):
        return loaded_config.RADARR_ENABLED
    return False


def get_radarr_base_api_url():
    if loaded_config and hasattr(loaded_config, 'RADARR_API_URL'):
        return loaded_config.RADARR_API_URL
    return None


def get_radarr_api_key():
    if loaded_config and hasattr(loaded_config, 'RADARR_API_KEY'):
        return loaded_config.RADARR_API_KEY
    return None


def is_sonarr_enabled():
    if loaded_config and hasattr(loaded_config, 'SONARR_ENABLED'):
        return loaded_config.SONARR_ENABLED
    return False


def get_sonarr_base_api_url():
    if loaded_config and hasattr(loaded_config, 'SONARR_API_URL'):
        return loaded_config.SONARR_API_URL
    return None


def get_sonarr_api_key():
    if loaded_config and hasattr(loaded_config, 'SONARR_API_KEY'):
        return loaded_config.SONARR_API_KEY
    return None


def is_script_enabled(script_number: int):
    if not 1 <= script_number <= 3:
        return False
    key = f"SCRIPT_{script_number}_ENABLED"
    if loaded_config and hasattr(loaded_config, key):
        return getattr(loaded_config, key)
    return False


def get_script_name(script_number: int):
    if not 1 <= script_number <= 3:
        return None
    key = f"SCRIPT_{script_number}_NAME"
    if loaded_config and hasattr(loaded_config, key):
        return getattr(loaded_config, key)
    return None


def get_script_path(script_number: int):
    if not 1 <= script_number <= 3:
        return None
    key = f"SCRIPT_{script_number}_PATH"
    if loaded_config and hasattr(loaded_config, key):
        return getattr(loaded_config, key)
    return None


def get_telegram_bot_token():
    if loaded_config and hasattr(loaded_config, 'TELEGRAM_BOT_TOKEN'):
        return loaded_config.TELEGRAM_BOT_TOKEN
    return None


def is_pc_control_enabled():
    if loaded_config and hasattr(loaded_config, 'PC_CONTROL_ENABLED'):
        return loaded_config.PC_CONTROL_ENABLED
    return False


def get_add_media_max_search_results() -> int:
    if loaded_config and hasattr(loaded_config, 'ADD_MEDIA_MAX_SEARCH_RESULTS'):
        try:
            return int(loaded_config.ADD_MEDIA_MAX_SEARCH_RESULTS)
        except (ValueError, TypeError):
            return DEFAULT_ADD_MEDIA_MAX_SEARCH_RESULTS
    return DEFAULT_ADD_MEDIA_MAX_SEARCH_RESULTS


def get_add_media_items_per_page() -> int:
    if loaded_config and hasattr(loaded_config, 'ADD_MEDIA_ITEMS_PER_PAGE'):
        try:
            return int(loaded_config.ADD_MEDIA_ITEMS_PER_PAGE)
        except (ValueError, TypeError):
            return DEFAULT_ADD_MEDIA_ITEMS_PER_PAGE
    return DEFAULT_ADD_MEDIA_ITEMS_PER_PAGE


def _get_launcher_config_value(service_prefix: str, suffix: str, default=None):
    key = f"{service_prefix}_LAUNCHER_{suffix}"
    if loaded_config and hasattr(loaded_config, key):
        return getattr(loaded_config, key)
    return default


def is_service_launcher_enabled(service_prefix: str) -> bool:

    return bool(_get_launcher_config_value(service_prefix.upper(), "ENABLED", False))


def get_service_launcher_name(service_prefix: str) -> str | None:
    return _get_launcher_config_value(service_prefix.upper(), "NAME")


def get_service_launcher_path(service_prefix: str) -> str | None:
    return _get_launcher_config_value(service_prefix.upper(), "PATH")


def is_plex_launcher_enabled() -> bool: return is_service_launcher_enabled("PLEX")
def get_plex_launcher_name() -> str | None: return get_service_launcher_name("PLEX")
def get_plex_launcher_path() -> str | None: return get_service_launcher_path("PLEX")


def is_sonarr_launcher_enabled() -> bool: return is_service_launcher_enabled("SONARR")
def get_sonarr_launcher_name() -> str | None: return get_service_launcher_name("SONARR")
def get_sonarr_launcher_path() -> str | None: return get_service_launcher_path("SONARR")


def is_radarr_launcher_enabled() -> bool: return is_service_launcher_enabled("RADARR")
def get_radarr_launcher_name() -> str | None: return get_service_launcher_name("RADARR")
def get_radarr_launcher_path() -> str | None: return get_service_launcher_path("RADARR")


def is_prowlarr_launcher_enabled() -> bool: return is_service_launcher_enabled("PROWLARR")
def get_prowlarr_launcher_name(
) -> str | None: return get_service_launcher_name("PROWLARR")
def get_prowlarr_launcher_path(
) -> str | None: return get_service_launcher_path("PROWLARR")


def is_torrent_launcher_enabled() -> bool: return is_service_launcher_enabled("TORRENT")
def get_torrent_launcher_name() -> str | None: return get_service_launcher_name("TORRENT")
def get_torrent_launcher_path() -> str | None: return get_service_launcher_path("TORRENT")


def is_abdm_enabled():
    if loaded_config and hasattr(loaded_config, 'ABDM_ENABLED'):
        return loaded_config.ABDM_ENABLED
    return False


def get_abdm_port() -> int | None:
    if loaded_config and hasattr(loaded_config, 'ABDM_PORT'):
        try:
            return int(loaded_config.ABDM_PORT)
        except (ValueError, TypeError):
            return 15151
    return 15151


def is_abdm_launcher_enabled() -> bool: return is_service_launcher_enabled("ABDM")
def get_abdm_launcher_name() -> str | None: return get_service_launcher_name("ABDM")
def get_abdm_launcher_path() -> str | None: return get_service_launcher_path("ABDM")
