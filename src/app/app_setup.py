
import logging
import os
import sys
import logging.handlers
import datetime
import importlib.util

from .app_file_utils import (
    determine_initial_data_storage_path,
    load_project_version as load_project_version_from_file_utils,
    get_config_file_path,
    get_config_template_path,
    load_requests_data,  # Keep for media requests
    load_tickets_data  # New import
)
from src.config.config_manager import (
    _load_config_module_from_path, config_exists_and_is_complete,
    ensure_config_file_is_present, validate_config_values,
    regenerate_config_from_template
)
from .app_service_initializer import initialize_services_with_config
from .app_config_ui import run_config_ui
from src.config.config_definitions import ALL_USER_CONFIG_KEYS, CONFIG_FIELD_DEFINITIONS, LOG_LEVEL_OPTIONS
import src.app.app_config_holder as app_config_holder
import src.app.user_manager as user_manager

logger = logging.getLogger(__name__)


def setup_logging(current_data_path: str, project_version: str, log_level_from_config: str | None = "INFO"):
    log_dir = os.path.join(current_data_path, 'log')
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError as e:

        print(
            f"Warning: Could not create log directory {log_dir}: {e}. Logging to main data directory.")
        log_dir = current_data_path
    log_file_path = os.path.join(
        log_dir, 'mediabot.log')
    effective_log_level_str = log_level_from_config if log_level_from_config in LOG_LEVEL_OPTIONS else "INFO"
    numeric_log_level = logging.getLevelName(effective_log_level_str.upper())
    if not isinstance(numeric_log_level, int):
        print(
            f"Warning: Invalid log level '{effective_log_level_str}' from config. Defaulting to INFO.")
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
    log_formatter = logging.Formatter(
        f"%(asctime)s - v{project_version} - %(name)s [{effective_log_level_str}] %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    )

    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file_path, when="midnight", interval=1, backupCount=7, encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(log_formatter)
    root_logger.addHandler(stream_handler)
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

    logger.info(f"Logging to directory: {log_dir}")
    logger.info(f"Python version: {sys.version.splitlines()[0]}")
    logger.info(f"OS: {os.name}, Platform: {sys.platform}")
    if getattr(sys, 'frozen', False):
        logger.info("Running as a PyInstaller bundled application.")


def record_bot_startup_time_in_state():
    if user_manager.record_bot_startup_time():
        logger.info("Bot startup time and version recorded in bot_state.json.")
    else:
        logger.error("Failed to record bot startup time in bot_state.json.")


def check_pc_control_dependencies(config_file_path_in_data: str):

    try:
        if os.path.exists(config_file_path_in_data):

            temp_config_module = None
            try:
                spec = importlib.util.spec_from_file_location(
                    "temp_dep_check_config", config_file_path_in_data)
                if spec and spec.loader:
                    temp_config_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(temp_config_module)
            except Exception as e_load_dep:
                logger.warning(
                    f"Could not load config for PC dependency check: {e_load_dep}")

            if temp_config_module and getattr(temp_config_module, "PC_CONTROL_ENABLED", False):
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
                        f"WARNING: {warning_msg} This feature will not work correctly.")
    except Exception as e:
        logger.warning(
            f"Could not pre-check PC control dependencies: {e}", exc_info=False)


def load_and_validate_config(target_config_file_path: str):

    if not os.path.exists(target_config_file_path):

        if not ensure_config_file_is_present(target_config_file_path):
            print(
                f"CRITICAL: Config file could not be created at {target_config_file_path} from template. Exiting.")
            logger.critical(
                f"Config file could not be created at {target_config_file_path} from template. Exiting.")
            sys.exit(1)
        else:
            logger.info(
                f"Initial config.py created from template at {target_config_file_path}.")

    template_path = get_config_template_path()
    if not regenerate_config_from_template(template_path, target_config_file_path):
        logger.warning(
            f"Failed to regenerate config from template. Proceeding with existing {target_config_file_path} if possible.")

    initial_values_for_ui = {}
    try_initial_load_for_ui = True
    if os.path.exists(target_config_file_path):
        try:

            temp_config_for_ui_load = _load_config_module_from_path(
                target_config_file_path)

            if isinstance(temp_config_for_ui_load, dict) and not temp_config_for_ui_load:
                raise ValueError(
                    "Failed to load module for UI prefill, using definition defaults.")

            for key_ in ALL_USER_CONFIG_KEYS:
                field_def = CONFIG_FIELD_DEFINITIONS.get(key_, {})
                default_val_from_def = field_def.get(
                    "default", "")
                if field_def.get("type") in ["checkbutton_in_frame_title", "checkbutton"]:
                    default_val_from_def = bool(default_val_from_def)
                elif field_def.get("type") == "combobox" and key_ == "LOG_LEVEL":
                    default_val_from_def = field_def.get("default", "INFO")
                elif key_ in ["ABDM_PORT", "ADD_MEDIA_MAX_SEARCH_RESULTS", "ADD_MEDIA_ITEMS_PER_PAGE"]:
                    default_val_from_def = int(field_def.get("default", 0))

                current_val = getattr(
                    temp_config_for_ui_load, key_, default_val_from_def)

                if field_def.get("type") in ["checkbutton_in_frame_title", "checkbutton"]:
                    initial_values_for_ui[key_] = bool(current_val)
                elif field_def.get("type") == "combobox" and key_ == "LOG_LEVEL":
                    initial_values_for_ui[key_] = str(current_val).upper() if str(
                        current_val).upper() in LOG_LEVEL_OPTIONS else default_val_from_def
                else:
                    initial_values_for_ui[key_] = str(
                        current_val) if current_val is not None else ""
        except Exception as e:
            logger.warning(
                f"Could not fully parse config for UI prefill ({target_config_file_path}): {e}. UI will use definition defaults.")
            try_initial_load_for_ui = False
    else:
        logger.error(
            f"Target config file {target_config_file_path} still missing after checks. Using definition defaults for UI.")
        try_initial_load_for_ui = False

    if not try_initial_load_for_ui:
        for key_ in ALL_USER_CONFIG_KEYS:
            field_def = CONFIG_FIELD_DEFINITIONS.get(key_, {})
            default_val = field_def.get("default", "")
            if field_def.get("type") in ["checkbutton_in_frame_title", "checkbutton"]:
                default_val = bool(default_val)
            elif field_def.get("type") == "combobox" and key_ == "LOG_LEVEL":
                default_val = field_def.get("default", "INFO")
            elif key_ in ["ABDM_PORT", "ADD_MEDIA_MAX_SEARCH_RESULTS", "ADD_MEDIA_ITEMS_PER_PAGE"]:
                default_val = int(field_def.get("default", 0))

            initial_values_for_ui[key_] = str(default_val) if not isinstance(
                default_val, bool) else default_val

    if not config_exists_and_is_complete(target_config_file_path):
        print(
            f"INFO: Config at '{target_config_file_path}' is missing essential values or is invalid after regeneration. Launching Config UI.")
        logger.info(
            f"Config at '{target_config_file_path}' is missing essential values or is invalid after regeneration. Launching Config UI.")

        ui_result = run_config_ui(
            target_config_file_path, initial_values_for_ui)

        if not ui_result.get("saved"):
            print("INFO: Config UI was cancelled. Exiting.")
            logger.info("Config UI was cancelled. Exiting.")
            sys.exit(0)

        print("INFO: Configuration saved via UI. Please restart the application to apply all changes.")
        logger.info(
            "Configuration saved via UI. Restarting application is recommended to apply all changes correctly.")
        sys.exit(0)

    try:
        current_config_module = _load_config_module_from_path(
            target_config_file_path)
        if isinstance(current_config_module, dict) and not current_config_module:
            raise ImportError(
                "Failed to load configuration module for final validation.")

        if not validate_config_values(current_config_module, target_config_file_path):
            logger.critical(
                f"Config file {target_config_file_path} is invalid. "
                "Please fix errors (e.g., using the /settings GUI if bot runs partially, or by editing data/config.py) "
                "or delete data/config.py to re-run the Config UI on next start. Exiting.")
            sys.exit(1)

        initialize_services_with_config(current_config_module)
        return current_config_module
    except Exception as e:
        logger.critical(
            f"CRITICAL error loading or validating final config from {target_config_file_path}: {e}", exc_info=True)
        sys.exit(1)


def perform_initial_setup():
    app_config_holder.PROJECT_VERSION = load_project_version_from_file_utils()
    project_version = app_config_holder.PROJECT_VERSION
    current_data_path = determine_initial_data_storage_path()

    config_file_path = get_config_file_path()

    loaded_config_module = load_and_validate_config(config_file_path)

    log_level_str_from_cfg = getattr(loaded_config_module, "LOG_LEVEL", "INFO")
    setup_logging(current_data_path, project_version, log_level_str_from_cfg)

    logger.info(
        f"Using config file: {config_file_path} (contents recently regenerated from template if applicable)")

    try:
        user_manager.ensure_initial_bot_state()
    except Exception as e_state_init:
        logger.critical(
            f"Failed to initialize or ensure bot state (bot_state.json): {e_state_init}", exc_info=True)
        sys.exit("Critical error: Bot state initialization failed.")

    record_bot_startup_time_in_state()

    try:
        _ = load_requests_data()
        logger.info(f"Checked/Initialized requests data file.")
    except Exception as e_req_init:
        logger.error(
            f"Failed to initialize requests data file: {e_req_init}", exc_info=True)

    try:  # New block for tickets.json
        _ = load_tickets_data()
        logger.info(f"Checked/Initialized tickets data file.")
    except Exception as e_ticket_init:
        logger.error(
            f"Failed to initialize tickets data file: {e_ticket_init}", exc_info=True)

    check_pc_control_dependencies(config_file_path)

    telegram_bot_token = app_config_holder.get_telegram_bot_token()
    primary_admin_chat_id_check = app_config_holder.get_chat_id_str()

    if not telegram_bot_token:
        logger.critical(
            "TELEGRAM_BOT_TOKEN is missing or empty. Bot cannot start.")
        sys.exit("Fatal Error: Telegram Bot Token not configured.")
    if not primary_admin_chat_id_check:
        logger.critical(
            "Primary Admin CHAT_ID is missing or empty. Bot cannot start.")
        sys.exit("Fatal Error: Primary Admin Chat ID not configured.")

    logger.info("Initial setup completed successfully.")
    return telegram_bot_token, current_data_path, project_version
