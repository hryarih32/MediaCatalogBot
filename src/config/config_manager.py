import os
import sys
import logging
import importlib.util
import shutil


from src.app.app_file_utils import get_config_template_path, get_project_version
from .config_definitions import (
    ALL_USER_CONFIG_KEYS,
    CONFIG_FIELD_DEFINITIONS
)

logger = logging.getLogger(__name__)


def _load_config_module_from_path(path_to_config_in_data):
    module_name = "config"
    normalized_path = os.path.normpath(path_to_config_in_data)

    if module_name in sys.modules and \
       hasattr(sys.modules[module_name], '__file__') and \
       sys.modules[module_name].__file__ is not None and \
       os.path.normpath(sys.modules[module_name].__file__) != normalized_path:
        logger.debug(
            f"Module '{module_name}' already loaded from a different path. Forcing reload from: {normalized_path}")
        del sys.modules[module_name]
    elif module_name in sys.modules and not hasattr(sys.modules[module_name], '__file__'):
        logger.debug(
            f"Module '{module_name}' in sys.modules without a file. Forcing reload from: {normalized_path}")
        del sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, normalized_path)
    if spec is None:
        raise ImportError(
            f"Could not load spec for module at {normalized_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def config_exists_and_is_complete(cfg_file_path_in_data):
    normalized_cfg_path = os.path.normpath(cfg_file_path_in_data)
    if not os.path.exists(normalized_cfg_path):
        return False
    try:
        config_module = _load_config_module_from_path(normalized_cfg_path)
        for key in ["TELEGRAM_BOT_TOKEN", "CHAT_ID"]:
            if not hasattr(config_module, key) or not getattr(config_module, key, "").strip():
                logger.debug(
                    f"Config check: Missing or empty core key '{key}' in {normalized_cfg_path}")
                return False
        chat_id_val = str(getattr(config_module, "CHAT_ID", ""))
        if not (chat_id_val and chat_id_val.lstrip('-').isdigit()):
            logger.debug(
                f"Config check: Invalid CHAT_ID format '{chat_id_val}' in {normalized_cfg_path}")
            return False
        if getattr(config_module, "PLEX_ENABLED", False):
            for key in ["PLEX_URL", "PLEX_TOKEN"]:
                if not hasattr(config_module, key) or not getattr(config_module, key, "").strip():
                    logger.debug(
                        f"Config check: Plex enabled, missing '{key}' in {normalized_cfg_path}")
                    return False
        if getattr(config_module, "RADARR_ENABLED", False):
            for key in ["RADARR_API_URL", "RADARR_API_KEY"]:
                if not hasattr(config_module, key) or not getattr(config_module, key, "").strip():
                    logger.debug(
                        f"Config check: Radarr enabled, missing '{key}' in {normalized_cfg_path}")
                    return False
        if getattr(config_module, "SONARR_ENABLED", False):
            for key in ["SONARR_API_URL", "SONARR_API_KEY"]:
                if not hasattr(config_module, key) or not getattr(config_module, key, "").strip():
                    logger.debug(
                        f"Config check: Sonarr enabled, missing '{key}' in {normalized_cfg_path}")
                    return False
        if getattr(config_module, "ABDM_ENABLED", False):
            if not hasattr(config_module, "ABDM_PORT") or not str(getattr(config_module, "ABDM_PORT", "")).strip().isdigit():
                logger.debug(
                    f"Config check: ABDM enabled, missing or invalid ABDM_PORT in {normalized_cfg_path}")
                return False
        for i in range(1, 4):
            if getattr(config_module, f"SCRIPT_{i}_ENABLED", False):
                for key_suffix in ["NAME", "PATH"]:
                    key = f"SCRIPT_{i}_{key_suffix}"
                    if not hasattr(config_module, key) or not getattr(config_module, key, "").strip():
                        logger.debug(
                            f"Config check: Script {i} enabled, missing '{key}' in {normalized_cfg_path}")
                        return False
        launcher_prefixes = ["PLEX", "SONARR",
                             "RADARR", "PROWLARR", "TORRENT", "ABDM"]
        for prefix in launcher_prefixes:
            if getattr(config_module, f"{prefix}_LAUNCHER_ENABLED", False):
                if not hasattr(config_module, f"{prefix}_LAUNCHER_PATH") or not getattr(config_module, f"{prefix}_LAUNCHER_PATH", "").strip():
                    logger.debug(
                        f"Config check: {prefix} Launcher enabled, missing PATH in {normalized_cfg_path}.")
                    return False
                if not hasattr(config_module, f"{prefix}_LAUNCHER_NAME") or not getattr(config_module, f"{prefix}_LAUNCHER_NAME", "").strip():
                    logger.debug(
                        f"Config check: {prefix} Launcher enabled, missing NAME in {normalized_cfg_path}.")
                    return False
        return True
    except Exception as e:
        logger.warning(
            f"Exception during config_exists_and_is_complete check for {normalized_cfg_path}: {e}", exc_info=False)
        return False


def ensure_config_file_is_present(target_cfg_file_path_in_data):
    normalized_target_path = os.path.normpath(target_cfg_file_path_in_data)
    if os.path.exists(normalized_target_path):
        return True

    logger.info(
        f"Config file not found at '{normalized_target_path}'. Attempting to copy from template.")

    template_path_to_try = get_config_template_path()

    if os.path.exists(template_path_to_try):
        try:

            os.makedirs(os.path.dirname(normalized_target_path), exist_ok=True)
            shutil.copy2(template_path_to_try, normalized_target_path)
            logger.info(
                f"Successfully copied config template to '{normalized_target_path}'.")
            return True
        except Exception as e:
            logger.error(
                f"Failed to copy template from '{template_path_to_try}' to '{normalized_target_path}': {e}", exc_info=True)
    else:
        logger.error(
            f"Config template '{template_path_to_try}' not found. Cannot create initial config at {normalized_target_path}.")
    return False


def validate_config_values(cfg_module, cfg_file_path_validated):
    is_valid = True
    project_version = get_project_version()

    def log_error(message):
        nonlocal is_valid
        logger.error(
            f"Config Validation Error in {cfg_file_path_validated}: {message}")
        is_valid = False

    for key in ALL_USER_CONFIG_KEYS:
        if not hasattr(cfg_module, key):
            is_conditionally_required = False
            field_def = CONFIG_FIELD_DEFINITIONS.get(key, {})
            dependency_key = field_def.get(
                "depends_on") or field_def.get("required_if_enabled")
            if dependency_key and getattr(cfg_module, dependency_key, False):
                is_conditionally_required = True
            if field_def.get("required") or is_conditionally_required:
                log_error(
                    f"Missing configuration key '{key}' which is required (possibly conditionally).")

    if not (hasattr(cfg_module, "TELEGRAM_BOT_TOKEN") and getattr(cfg_module, "TELEGRAM_BOT_TOKEN", "").strip()):
        log_error("TELEGRAM_BOT_TOKEN is missing or empty.")
    if not (hasattr(cfg_module, "CHAT_ID") and str(getattr(cfg_module, "CHAT_ID", "")).lstrip('-').isdigit()):
        log_error(
            f"CHAT_ID ('{getattr(cfg_module, 'CHAT_ID', '')}') is missing or invalid (must be numerical).")

    if getattr(cfg_module, "PLEX_ENABLED", False):
        if not getattr(cfg_module, "PLEX_URL", "").strip():
            log_error("PLEX_URL is required because Plex is enabled.")
        if not getattr(cfg_module, "PLEX_TOKEN", "").strip():
            log_error("PLEX_TOKEN is required because Plex is enabled.")
    if getattr(cfg_module, "RADARR_ENABLED", False):
        if not getattr(cfg_module, "RADARR_API_URL", "").strip():
            log_error("RADARR_API_URL is required because Radarr is enabled.")
        if not getattr(cfg_module, "RADARR_API_KEY", "").strip():
            log_error("RADARR_API_KEY is required because Radarr is enabled.")
    if getattr(cfg_module, "SONARR_ENABLED", False):
        if not getattr(cfg_module, "SONARR_API_URL", "").strip():
            log_error("SONARR_API_URL is required because Sonarr is enabled.")
        if not getattr(cfg_module, "SONARR_API_KEY", "").strip():
            log_error("SONARR_API_KEY is required because Sonarr is enabled.")
    if getattr(cfg_module, "ABDM_ENABLED", False):
        if not (hasattr(cfg_module, "ABDM_PORT") and str(getattr(cfg_module, "ABDM_PORT", "")).strip().isdigit()):
            log_error(
                "ABDM_PORT is required and must be a number because AB Download Manager is enabled.")

    for i in range(1, 4):
        if getattr(cfg_module, f"SCRIPT_{i}_ENABLED", False):
            if not getattr(cfg_module, f"SCRIPT_{i}_NAME", "").strip():
                log_error(
                    f"SCRIPT_{i}_NAME is required because Script {i} is enabled.")
            script_path = getattr(cfg_module, f"SCRIPT_{i}_PATH", "").strip()
            if not script_path:
                log_error(
                    f"SCRIPT_{i}_PATH is required because Script {i} is enabled.")
            elif not os.path.exists(script_path) and not getattr(sys, 'frozen', False):
                logger.warning(
                    f"SCRIPT_{i}_PATH ('{script_path}') does not exist (Script {i} is enabled). This might be an issue.")
    launcher_prefixes_val = ["PLEX", "SONARR",
                             "RADARR", "PROWLARR", "TORRENT", "ABDM"]
    for prefix_val in launcher_prefixes_val:
        if getattr(cfg_module, f"{prefix_val}_LAUNCHER_ENABLED", False):
            if not getattr(cfg_module, f"{prefix_val}_LAUNCHER_NAME", "").strip():
                log_error(
                    f"{prefix_val}_LAUNCHER_NAME is required because {prefix_val} Launcher is enabled.")
            launcher_path_val = getattr(
                cfg_module, f"{prefix_val}_LAUNCHER_PATH", "").strip()
            if not launcher_path_val:
                log_error(
                    f"{prefix_val}_LAUNCHER_PATH is required because {prefix_val} Launcher is enabled.")
            elif not os.path.exists(launcher_path_val) and not getattr(sys, 'frozen', False):
                logger.warning(
                    f"{prefix_val}_LAUNCHER_PATH ('{launcher_path_val}') does not exist. This might be an issue.")

    if is_valid:
        logger.info(
            f"Version {project_version} - Configuration validated successfully from {cfg_file_path_validated}.")
    else:
        logger.error(
            f"Version {project_version} - Configuration validation FAILED for {cfg_file_path_validated}.")
    return is_valid
