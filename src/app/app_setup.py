import logging
import os
import sys
import datetime

from .app_file_utils import (
    determine_initial_data_storage_path,
    load_project_version as load_project_version_from_file_utils,
    STARTUP_TIME_FILENAME,
    get_config_file_path
)
from src.config.config_manager import (
    _load_config_module_from_path, config_exists_and_is_complete,
    ensure_config_file_is_present, validate_config_values
)
from .app_service_initializer import initialize_services_with_config
from .app_config_ui import run_config_ui
from src.config.config_definitions import ALL_USER_CONFIG_KEYS, CONFIG_FIELD_DEFINITIONS, LOG_LEVEL_OPTIONS
import src.app.app_config_holder as app_config_holder

logger = logging.getLogger(__name__)


def setup_logging(current_data_path: str, project_version: str, log_level_from_config: str | None = "INFO"):
    log_file_path = os.path.join(
        current_data_path, 'mediabot.log')
    effective_log_level_str = log_level_from_config if log_level_from_config in LOG_LEVEL_OPTIONS else "INFO"
    numeric_log_level = logging.getLevelName(effective_log_level_str.upper())
    if not isinstance(numeric_log_level, int):
        logger.warning(
            f"Invalid log level '{effective_log_level_str}' from config. Defaulting to INFO.")
        numeric_log_level = logging.INFO
        effective_log_level_str = "INFO"

    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            handler.close()

    root_logger.setLevel(numeric_log_level)
    logging.basicConfig(
        format=f"%(asctime)s - v{project_version} - %(name)s [{effective_log_level_str}] %(levelname)s - %(message)s (%(filename)s:%(lineno)d)",
        handlers=[
            logging.FileHandler(log_file_path, encoding='utf-8', mode='a'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.getLogger("httpx").setLevel(
        logging.INFO if numeric_log_level <= logging.INFO else numeric_log_level)
    logging.getLogger("telegram").setLevel(
        logging.INFO if numeric_log_level <= logging.INFO else numeric_log_level)
    if os.name == 'nt':
        logging.getLogger('comtypes').setLevel(
            logging.WARNING if numeric_log_level <= logging.WARNING else numeric_log_level)

    logger.info(f"--- Starting Media Bot Version: {project_version} ---")
    logger.info(f"Effective logging level set to: {effective_log_level_str}")

    logger.info(f"Using data path: {current_data_path}")
    logger.info(f"Python version: {sys.version.splitlines()[0]}")
    logger.info(f"OS: {os.name}, Platform: {sys.platform}")
    if getattr(sys, 'frozen', False):
        logger.info("Running as a PyInstaller bundled application.")


def record_startup_time(current_data_path: str):
    startup_time_file_path = os.path.join(
        current_data_path, STARTUP_TIME_FILENAME)
    try:
        with open(startup_time_file_path, "w") as f:
            f.write(datetime.datetime.now().isoformat())
        logger.info(
            f"Current startup time written to {startup_time_file_path}")
    except Exception as e:
        logger.error(
            f"Failed to write startup time to {startup_time_file_path}: {e}")


def check_pc_control_dependencies(config_file_path_in_data: str):
    try:
        if os.path.exists(config_file_path_in_data):
            temp_config_for_dep_check = _load_config_module_from_path(
                config_file_path_in_data)
            if getattr(temp_config_for_dep_check, "PC_CONTROL_ENABLED", False):
                missing_deps_for_pc_control = []
                try:
                    import pyautogui
                except ImportError:
                    missing_deps_for_pc_control.append("pyautogui")
                try:
                    from pycaw.pycaw import AudioUtilities
                except ImportError:
                    missing_deps_for_pc_control.append("pycaw")
                if missing_deps_for_pc_control:
                    warning_msg = f"PC Control feature is enabled, but MISSING dependencies: {', '.join(missing_deps_for_pc_control)}."
                    logger.warning(warning_msg)
                    print(
                        f"WARNING: {warning_msg} This feature will not work.")
    except Exception as e:
        logger.warning(f"Could not pre-check PC control dependencies: {e}")


def load_and_validate_config(target_config_file_path: str):
    if not os.path.exists(target_config_file_path):

        if not ensure_config_file_is_present(target_config_file_path):
            logger.critical(
                f"Config file could not be created at {target_config_file_path}. Exiting.")
            sys.exit(1)

    initial_values_for_ui = {}
    try_initial_load_for_ui = True
    if os.path.exists(target_config_file_path):
        try:
            temp_config_for_ui_load = _load_config_module_from_path(
                target_config_file_path)
            for key_ in ALL_USER_CONFIG_KEYS:
                default_val_for_key = CONFIG_FIELD_DEFINITIONS.get(
                    key_, {}).get("default", "")
                if CONFIG_FIELD_DEFINITIONS.get(key_, {}).get("type") in ["checkbutton_in_frame_title", "checkbutton"]:
                    default_val_for_key = bool(default_val_for_key)
                initial_values_for_ui[key_] = getattr(
                    temp_config_for_ui_load, key_, default_val_for_key)
                if CONFIG_FIELD_DEFINITIONS.get(key_, {}).get("type") in ["checkbutton_in_frame_title", "checkbutton"]:
                    initial_values_for_ui[key_] = bool(
                        initial_values_for_ui[key_])
        except Exception as e:
            logger.warning(
                f"Could not fully parse existing config for UI prefill ({target_config_file_path}): {e}. UI will use defaults.")
            try_initial_load_for_ui = False
    else:
        try_initial_load_for_ui = False

    if not try_initial_load_for_ui:
        for key_ in ALL_USER_CONFIG_KEYS:
            field_def = CONFIG_FIELD_DEFINITIONS.get(key_, {})
            default_val = field_def.get("default", "")
            if field_def.get("type") in ["checkbutton_in_frame_title", "checkbutton"]:
                default_val = bool(default_val)
            elif field_def.get("type") == "combobox" and key_ == "LOG_LEVEL":
                default_val = field_def.get("default", "INFO")
            initial_values_for_ui[key_] = default_val

    if not config_exists_and_is_complete(target_config_file_path):
        logger.warning(
            f"Config at '{target_config_file_path}' is missing, incomplete, or invalid. Launching Config UI.")
        print(f"Configuration is incomplete/invalid. Launching Config UI...")
        ui_result = run_config_ui(
            target_config_file_path, initial_values_for_ui)
        if not ui_result["saved"]:
            logger.info("Config UI was cancelled. Exiting.")
            sys.exit(1)
        logger.info(
            "Configuration saved via UI. Restarting is recommended for changes to take full effect.")
        print("Configuration saved. Please restart the application to apply all changes (especially if this was the first setup or log level changed).")
        sys.exit(0)

    try:
        current_config_module = _load_config_module_from_path(
            target_config_file_path)

        if not validate_config_values(current_config_module, target_config_file_path):
            logger.critical(
                f"Config file {target_config_file_path} is invalid even after potential UI run. Fix or delete to re-run UI. Exiting.")
            sys.exit(1)
        initialize_services_with_config(current_config_module)
        return current_config_module
    except Exception as e:
        logger.critical(
            f"CRITICAL error loading config from {target_config_file_path}: {e}", exc_info=True)
        sys.exit(1)


def perform_initial_setup():
    app_config_holder.PROJECT_VERSION = load_project_version_from_file_utils()
    project_version = app_config_holder.PROJECT_VERSION

    current_data_path = determine_initial_data_storage_path()

    config_file_path = get_config_file_path()

    loaded_config_module = load_and_validate_config(config_file_path)
    log_level_str_from_cfg = getattr(loaded_config_module, "LOG_LEVEL", "INFO")
    setup_logging(current_data_path, project_version, log_level_str_from_cfg)

    logger.info(f"Using config file: {config_file_path}")
    record_startup_time(current_data_path)
    check_pc_control_dependencies(config_file_path)

    telegram_bot_token = app_config_holder.get_telegram_bot_token()
    if not telegram_bot_token:
        logger.critical(
            "Telegram Bot Token not available after setup. Exiting.")
        sys.exit(1)

    return telegram_bot_token, current_data_path, project_version
