import os
import sys
import logging
import json

logger = logging.getLogger(__name__)

APP_NAME = "MediaBot"
PROJECT_VERSION = "Unknown"
RESOLVED_PROJECT_ROOT_PATH = None
RESOLVED_DATA_STORAGE_PATH = None
VERSION_FILE_PATH_CACHE = None
CONFIG_TEMPLATE_PATH_CACHE = None
ICO_FILE_PATH_CACHE = None
STARTUP_TIME_FILENAME = "msg_last_startup_time.txt"
REQUESTS_FILE_NAME = "requests.json"

BOT_STATE_FILE_NAME = "bot_state.json"


def get_project_root():
    global RESOLVED_PROJECT_ROOT_PATH
    if RESOLVED_PROJECT_ROOT_PATH is None:
        if getattr(sys, 'frozen', False):
            RESOLVED_PROJECT_ROOT_PATH = os.path.dirname(sys.executable)
        else:
            RESOLVED_PROJECT_ROOT_PATH = os.path.abspath(

                os.path.join(os.path.dirname(__file__), '..', '..'))
    return RESOLVED_PROJECT_ROOT_PATH


def get_data_storage_path():
    global RESOLVED_DATA_STORAGE_PATH
    if RESOLVED_DATA_STORAGE_PATH is None:
        project_root = get_project_root()

        data_dir = os.path.join(project_root, 'data')
        RESOLVED_DATA_STORAGE_PATH = os.path.normpath(data_dir)
        try:
            os.makedirs(RESOLVED_DATA_STORAGE_PATH, exist_ok=True)
            search_results_dir = os.path.join(
                RESOLVED_DATA_STORAGE_PATH, 'search_results')
            os.makedirs(search_results_dir, exist_ok=True)
        except OSError as e:
            logger.critical(
                f"CRITICAL: Could not access or create data storage path '{RESOLVED_DATA_STORAGE_PATH}': {e}. Exiting.")

            sys.exit(
                f"Fatal error: Cannot access or create data storage directory: {e}")
        logger.info(f"Data storage path set to: {RESOLVED_DATA_STORAGE_PATH}")
    return RESOLVED_DATA_STORAGE_PATH


def determine_initial_data_storage_path():
    """Ensures data storage path is resolved and created if needed."""
    return get_data_storage_path()


def get_config_file_path():
    """Returns the path to the actual config.py (data/config.py)"""
    return os.path.join(get_data_storage_path(), 'config.py')


def get_requests_file_path():
    """Returns the path to requests.json in the data directory."""
    return os.path.join(get_data_storage_path(), REQUESTS_FILE_NAME)


def get_bot_state_file_path():
    """Returns the path to bot_state.json in the data directory."""
    return os.path.join(get_data_storage_path(), BOT_STATE_FILE_NAME)


def get_bundled_or_local_resource_path(relative_path_from_root: str, subfolder: str | None = None):
    """
    Gets path to a resource.
    - If bundled: looks in _MEIPASS or next to executable.
    - If not bundled: looks in project_root / [subfolder] / relative_path_from_root_filename.
    `relative_path_from_root` is the filename (e.g., 'VERSION', 'ico.ico').
    `subfolder` is the subfolder relative to project root (e.g., 'resources', 'config_templates').
    """
    filename = os.path.basename(
        relative_path_from_root)

    if getattr(sys, 'frozen', False):

        if hasattr(sys, '_MEIPASS'):
            res_path_meipass = os.path.join(sys._MEIPASS, filename)
            if os.path.exists(res_path_meipass):
                return res_path_meipass

        res_path_executable_dir = os.path.join(
            os.path.dirname(sys.executable), filename)
        if os.path.exists(res_path_executable_dir):
            return res_path_executable_dir

        return os.path.join(sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable), filename)
    else:
        project_root = get_project_root()
        if subfolder:
            return os.path.join(project_root, subfolder, filename)
        return os.path.join(project_root, filename)


def get_version_file_path():
    global VERSION_FILE_PATH_CACHE
    if VERSION_FILE_PATH_CACHE is None:

        VERSION_FILE_PATH_CACHE = get_bundled_or_local_resource_path('VERSION')
    return VERSION_FILE_PATH_CACHE


def get_config_template_path():
    global CONFIG_TEMPLATE_PATH_CACHE
    if CONFIG_TEMPLATE_PATH_CACHE is None:
        CONFIG_TEMPLATE_PATH_CACHE = get_bundled_or_local_resource_path(
            'config.py.default', subfolder='config_templates')
    return CONFIG_TEMPLATE_PATH_CACHE


def get_ico_file_path():
    global ICO_FILE_PATH_CACHE
    if ICO_FILE_PATH_CACHE is None:
        ICO_FILE_PATH_CACHE = get_bundled_or_local_resource_path(
            'ico.ico', subfolder='resources')
    return ICO_FILE_PATH_CACHE


def get_startup_time_file_path():
    return os.path.join(get_data_storage_path(), STARTUP_TIME_FILENAME)


def get_search_results_file_path(filename: str):
    """Returns path for temporary search result files (Radarr/Sonarr)."""
    return os.path.join(get_data_storage_path(), 'search_results', filename)


def load_project_version():
    global PROJECT_VERSION
    try:
        version_path_to_try = get_version_file_path()
        if os.path.exists(version_path_to_try):
            with open(version_path_to_try, 'r') as f:
                PROJECT_VERSION = f.read().strip()
        else:
            PROJECT_VERSION = "Dev"
            logger.warning(
                f"VERSION file not found at '{version_path_to_try}'. Using '{PROJECT_VERSION}'.")
    except Exception as e:
        PROJECT_VERSION = "ErrorLoadingVersion"
        logger.warning(f"Could not load project version: {e}")
    return PROJECT_VERSION


def get_project_version():
    global PROJECT_VERSION
    if PROJECT_VERSION == "Unknown":
        load_project_version()
    return PROJECT_VERSION


def get_base_path_for_exec():
    return get_project_root()


def get_main_script_path():
    """Returns the path to MediaCatalog.py (now in project root)."""
    if getattr(sys, 'frozen', False):

        return os.path.join(sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable), 'MediaCatalog.py')
    else:
        return os.path.join(get_project_root(), 'MediaCatalog.py')


def get_requirements_file_path():
    """Returns the path to requirements.txt, now in requirements/"""
    return os.path.join(get_project_root(), 'requirements', 'requirements.txt')


def load_requests_data() -> list:
    """Loads media requests from requests.json."""
    req_file = get_requests_file_path()
    if os.path.exists(req_file):
        try:
            with open(req_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(
                f"Error loading requests data from {req_file}: {e}. Returning empty list.")

            return []
    return []


def save_requests_data(requests_list: list) -> bool:
    """Saves media requests to requests.json."""
    req_file = get_requests_file_path()
    try:

        with open(req_file, 'w', encoding='utf-8') as f:
            json.dump(requests_list, f, indent=4)
        logger.info(f"Saved {len(requests_list)} requests to {req_file}")
        return True
    except IOError as e:
        logger.error(f"Error saving requests data to {req_file}: {e}")
        return False
