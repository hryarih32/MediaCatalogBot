
import os
import sys
import logging
import json
import shutil

logger = logging.getLogger(__name__)

APP_NAME = "MediaBot"
PROJECT_VERSION = "Unknown"
RESOLVED_PROJECT_ROOT_PATH = None
RESOLVED_DATA_STORAGE_PATH = None
VERSION_FILE_PATH_CACHE = None
CONFIG_TEMPLATE_PATH_CACHE = None
ICO_FILE_PATH_CACHE = None

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
    return get_data_storage_path()


def get_config_file_path():
    return os.path.join(get_data_storage_path(), 'config.py')


def get_requests_file_path():
    return os.path.join(get_data_storage_path(), REQUESTS_FILE_NAME)


def get_bot_state_file_path():
    return os.path.join(get_data_storage_path(), BOT_STATE_FILE_NAME)


def get_bundled_or_local_resource_path(relative_path_from_root: str, subfolder: str | None = None):
    filename = os.path.basename(relative_path_from_root)
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS if hasattr(
            sys, '_MEIPASS') else os.path.dirname(sys.executable)
        res_path_meipass_sub = os.path.join(
            base_dir, subfolder, filename) if subfolder else os.path.join(base_dir, filename)
        if os.path.exists(res_path_meipass_sub):
            return res_path_meipass_sub

        res_path_exe_dir_sub = os.path.join(os.path.dirname(
            sys.executable), subfolder, filename) if subfolder else os.path.join(os.path.dirname(sys.executable), filename)
        if os.path.exists(res_path_exe_dir_sub):
            return res_path_exe_dir_sub
        return res_path_meipass_sub
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


def get_search_results_file_path(filename: str):
    return os.path.join(get_data_storage_path(), 'search_results', filename)


def load_project_version():
    global PROJECT_VERSION
    try:
        version_path = get_version_file_path()
        if os.path.exists(version_path):
            with open(version_path, 'r') as f:
                PROJECT_VERSION = f.read().strip()
        else:
            PROJECT_VERSION = "Dev"
            logger.warning(
                f"VERSION file not found at '{version_path}'. Using default '{PROJECT_VERSION}'.")
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
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable), 'MediaCatalog.py')
    else:
        return os.path.join(get_project_root(), 'MediaCatalog.py')


def get_requirements_file_path():
    return os.path.join(get_project_root(), 'requirements', 'requirements.txt')


def load_json_data(file_path: str) -> dict | list | None:
    """Loads data from a JSON file, with fallback to .bak file."""
    backup_file_path = file_path + ".bak"

    paths_to_try = [file_path]

    if os.path.exists(backup_file_path):
        paths_to_try.append(backup_file_path)

    for current_path in paths_to_try:
        if os.path.exists(current_path):
            try:
                with open(current_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(
                        f"Successfully loaded JSON data from {current_path}")

                    if current_path == backup_file_path and data is not None:
                        logger.warning(
                            f"Main file {file_path} was missing or corrupt. Loaded from backup {backup_file_path}. Attempting to restore main file.")

                        if save_json_data(file_path, data, create_backup=False):
                            logger.info(
                                f"Successfully restored {file_path} from backup.")
                        else:
                            logger.error(
                                f"Failed to restore {file_path} from backup. Using data from backup for this session.")
                    return data.copy() if isinstance(data, (dict, list)) else data
            except (json.JSONDecodeError, IOError) as e:
                logger.error(
                    f"Error loading JSON data from {current_path}: {e}.")

            except Exception as e_gen:
                logger.error(
                    f"Unexpected error loading JSON from {current_path}: {e_gen}", exc_info=True)
        else:
            logger.debug(
                f"File not found at {current_path} during load attempt.")

    logger.warning(
        f"All attempts to load JSON data from {file_path} (and its backup) failed. Returning None.")
    return None


def save_json_data(file_path: str, data: dict | list, create_backup: bool = True) -> bool:
    """Saves data to a JSON file atomically and creates a backup."""
    temp_file_path = file_path + ".tmp"
    backup_file_path = file_path + ".bak"

    try:
        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        with open(temp_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

        if create_backup and os.path.exists(file_path):
            try:
                shutil.copy2(file_path, backup_file_path)
                logger.debug(
                    f"Created backup of {file_path} at {backup_file_path}")
            except Exception as e_backup:
                logger.warning(
                    f"Could not create backup for {file_path}: {e_backup}")

        os.replace(temp_file_path, file_path)

        data_len = "N/A"
        if isinstance(data, list):
            data_len = str(len(data))
        elif isinstance(data, dict):
            data_len = str(len(data.keys()))
        logger.info(f"Saved JSON data to {file_path} (items/keys: {data_len})")
        return True

    except IOError as e_io:
        logger.error(f"IOError saving JSON data to {file_path}: {e_io}")
    except Exception as e_gen:
        logger.error(
            f"Unexpected error saving JSON data to {file_path}: {e_gen}", exc_info=True)
    finally:
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError as e_rem:
                logger.error(
                    f"Could not remove temp file {temp_file_path} after save attempt: {e_rem}")
    return False


def load_requests_data() -> list:
    """Loads media requests from requests.json."""
    requests_list_data = load_json_data(get_requests_file_path())
    if isinstance(requests_list_data, list):
        return requests_list_data

    elif requests_list_data is None:
        logger.info(
            f"{REQUESTS_FILE_NAME} not found or empty/corrupt. Initializing as empty list.")
        save_requests_data([])
        return []
    else:
        logger.warning(
            f"{REQUESTS_FILE_NAME} content was not a list. Re-initializing as empty list.")
        save_requests_data([])
        return []


def save_requests_data(requests_list: list) -> bool:
    """Saves media requests to requests.json."""
    if not isinstance(requests_list, list):
        logger.error(
            f"Attempted to save non-list data to {REQUESTS_FILE_NAME}. Aborting save.")
        return False
    return save_json_data(get_requests_file_path(), requests_list)
