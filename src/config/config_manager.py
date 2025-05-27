
import os
import sys
import logging
import importlib.util
import shutil
import re
import json

from src.app.app_file_utils import get_config_template_path, get_project_version
from .config_definitions import (
    ALL_USER_CONFIG_KEYS,
    CONFIG_FIELD_DEFINITIONS,
    LOG_LEVEL_OPTIONS
)

logger = logging.getLogger(__name__)


def _load_config_module_from_path(path_to_config_in_data):
    module_name = "config"
    normalized_path = os.path.normpath(path_to_config_in_data)

    if module_name in sys.modules:
        loaded_module = sys.modules[module_name]
        loaded_path = getattr(loaded_module, '__file__', None)
        if loaded_path is None or os.path.normpath(loaded_path) != normalized_path:
            logger.debug(
                f"Module '{module_name}' found in sys.modules from a different path ('{loaded_path}') "
                f"or without a file. Forcing reload from: {normalized_path}"
            )
            del sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, normalized_path)
    if spec is None:

        logger.error(
            f"Could not load spec for module at {normalized_path}. File might be empty or malformed.")
        raise ImportError(
            f"Could not load spec for module at {normalized_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except SyntaxError as e:
        logger.error(f"Syntax error in config file {normalized_path}: {e}")

        return {}
    except Exception as e:
        logger.error(
            f"Error executing module from {normalized_path}: {e}", exc_info=True)
        return {}

    return module


def regenerate_config_from_template(template_path: str, target_config_path: str):
    """
    Regenerates the target_config_path based on the template_path.
    Preserves existing values from target_config_path for keys defined in ALL_USER_CONFIG_KEYS.
    Adds new keys from the template (if also in ALL_USER_CONFIG_KEYS) with their defaults.
    Removes keys from target_config_path that are not in the template or ALL_USER_CONFIG_KEYS.
    Preserves comments and blank lines from the template.
    """
    logger.info(
        f"Regenerating config file '{target_config_path}' using template '{template_path}'.")

    existing_values = {}
    if os.path.exists(target_config_path):
        try:
            existing_config_module = _load_config_module_from_path(
                target_config_path)

            if isinstance(existing_config_module, dict):
                logger.warning(
                    f"Existing config at {target_config_path} was unreadable or empty. Proceeding with template defaults.")
            else:
                for key in ALL_USER_CONFIG_KEYS:
                    if hasattr(existing_config_module, key):
                        existing_values[key] = getattr(
                            existing_config_module, key)
                logger.info(
                    f"Loaded {len(existing_values)} existing values from {target_config_path}.")
        except Exception as e:
            logger.warning(
                f"Could not load existing config from {target_config_path} due to: {e}. Will use defaults from template for all values.")
            existing_values = {}

    if not os.path.exists(template_path):
        logger.error(
            f"Config template not found at {template_path}. Cannot regenerate config.")

        return False

    new_config_lines = []
    try:
        with open(template_path, 'r', encoding='utf-8') as tf:
            for line_num, line_content in enumerate(tf):
                stripped_line = line_content.strip()

                if not stripped_line or stripped_line.startswith('#'):
                    new_config_lines.append(line_content.rstrip('\r\n'))
                    continue

                match = re.match(
                    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)", stripped_line)
                if match:
                    key_from_template = match.group(1)
                    default_value_str_from_template = match.group(2)

                    if key_from_template in ALL_USER_CONFIG_KEYS:
                        definition = CONFIG_FIELD_DEFINITIONS.get(
                            key_from_template, {})

                        user_value = existing_values.get(key_from_template)

                        final_value_to_write = None

                        if user_value is not None:

                            if definition.get("type") in ["checkbutton_in_frame_title", "checkbutton"]:
                                final_value_to_write = bool(user_value)

                            elif key_from_template in ["ABDM_PORT", "ADD_MEDIA_MAX_SEARCH_RESULTS", "ADD_MEDIA_ITEMS_PER_PAGE"]:

                                try:
                                    final_value_to_write = int(user_value)
                                except (ValueError, TypeError):
                                    logger.warning(
                                        f"Invalid integer value '{user_value}' for '{key_from_template}' from existing config. Using template default.")

                                    try:

                                        final_value_to_write = int(
                                            eval(default_value_str_from_template))
                                    except:
                                        final_value_to_write = definition.get(
                                            "default", 0)
                            elif definition.get("type") == "combobox" and key_from_template == "LOG_LEVEL":
                                final_value_to_write = str(user_value).upper() if str(
                                    user_value).upper() in LOG_LEVEL_OPTIONS else definition.get("default", "INFO")
                            else:
                                final_value_to_write = str(user_value)
                        else:

                            if definition.get("type") in ["checkbutton_in_frame_title", "checkbutton"]:
                                final_value_to_write = default_value_str_from_template.lower() == 'true'

                            elif key_from_template in ["ABDM_PORT", "ADD_MEDIA_MAX_SEARCH_RESULTS", "ADD_MEDIA_ITEMS_PER_PAGE"]:
                                try:
                                    final_value_to_write = int(
                                        eval(default_value_str_from_template))
                                except:
                                    final_value_to_write = int(definition.get(
                                        "default", 0))
                            elif definition.get("type") == "combobox" and key_from_template == "LOG_LEVEL":

                                final_value_to_write = eval(default_value_str_from_template).upper() \
                                    if eval(default_value_str_from_template).upper() in LOG_LEVEL_OPTIONS \
                                    else definition.get("default", "INFO")
                            else:
                                final_value_to_write = eval(
                                    default_value_str_from_template)

                        field_type_from_def = definition.get("type")
                        is_known_int_key = key_from_template in [
                            "ABDM_PORT", "ADD_MEDIA_MAX_SEARCH_RESULTS", "ADD_MEDIA_ITEMS_PER_PAGE"]

                        if field_type_from_def in ["checkbutton_in_frame_title", "checkbutton"]:
                            new_config_lines.append(
                                f'{key_from_template} = {bool(final_value_to_write)}')
                        elif is_known_int_key:

                            try:
                                val_to_write_as_int = int(final_value_to_write)
                                new_config_lines.append(
                                    f'{key_from_template} = {val_to_write_as_int}')

                            except (ValueError, TypeError):
                                logger.error(
                                    f"CRITICAL: Could not ensure integer for {key_from_template}. Writing as string. Value: {final_value_to_write}")

                                new_config_lines.append(
                                    f'{key_from_template} = {json.dumps(str(final_value_to_write))}')
                        elif field_type_from_def == "file_path" or key_from_template.endswith("_PATH"):
                            path_val_str_content = str(
                                final_value_to_write).replace('\\', '\\\\')
                            new_config_lines.append(
                                f'{key_from_template} = r{json.dumps(path_val_str_content)}')

                        else:
                            new_config_lines.append(
                                f'{key_from_template} = {json.dumps(str(final_value_to_write))}')
                    else:
                        logger.info(
                            f"Obsolete key '{key_from_template}' found in template. It will not be written to the new config.py.")
                else:
                    new_config_lines.append(line_content.rstrip('\r\n'))

        temp_target_config_path = target_config_path + ".tmp"
        with open(temp_target_config_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_config_lines))
            f.write('\n')

        os.replace(temp_target_config_path, target_config_path)
        logger.info(
            f"Successfully regenerated config file at {target_config_path}.")
        return True

    except Exception as e:
        logger.error(
            f"Failed to regenerate config file '{target_config_path}': {e}", exc_info=True)
        if 'temp_target_config_path' in locals() and os.path.exists(temp_target_config_path):
            try:
                os.remove(temp_target_config_path)
            except OSError:
                pass
        return False


def config_exists_and_is_complete(cfg_file_path_in_data):
    normalized_cfg_path = os.path.normpath(cfg_file_path_in_data)
    if not os.path.exists(normalized_cfg_path):
        return False
    try:
        config_module = _load_config_module_from_path(normalized_cfg_path)
        if isinstance(config_module, dict):
            logger.warning(
                f"config.py at {normalized_cfg_path} could not be loaded as a module for completeness check.")
            return False

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
                        f"Config check: Plex enabled but missing '{key}'.")
                    return False
        if getattr(config_module, "RADARR_ENABLED", False):
            for key in ["RADARR_API_URL", "RADARR_API_KEY"]:
                if not hasattr(config_module, key) or not getattr(config_module, key, "").strip():
                    logger.debug(
                        f"Config check: Radarr enabled but missing '{key}'.")
                    return False
        if getattr(config_module, "SONARR_ENABLED", False):
            for key in ["SONARR_API_URL", "SONARR_API_KEY"]:
                if not hasattr(config_module, key) or not getattr(config_module, key, "").strip():
                    logger.debug(
                        f"Config check: Sonarr enabled but missing '{key}'.")
                    return False
        if getattr(config_module, "ABDM_ENABLED", False):
            abdm_port_val = getattr(config_module, "ABDM_PORT", None)
            valid_port = False
            if abdm_port_val is not None:
                try:
                    if int(abdm_port_val) > 0:
                        valid_port = True
                except (ValueError, TypeError):
                    pass
            if not valid_port:
                logger.debug(
                    f"Config check: ABDM enabled but ABDM_PORT ('{abdm_port_val}') is not a positive integer. Type: {type(abdm_port_val)}")
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
                f"Successfully copied config template to '{normalized_target_path}'. Regeneration will follow.")
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
            definition = CONFIG_FIELD_DEFINITIONS.get(key, {})
            if definition.get("required"):
                log_error(
                    f"Missing required configuration key '{key}'. Regeneration might have failed or template is incomplete.")
            else:
                logger.debug(
                    f"Key '{key}' not found directly, but regeneration should handle defaults.")

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
        abdm_port_val = getattr(cfg_module, "ABDM_PORT", None)
        valid_port_for_validation = False
        if abdm_port_val is not None:
            try:
                if int(abdm_port_val) > 0:
                    valid_port_for_validation = True
            except (ValueError, TypeError):
                pass
        if not valid_port_for_validation:
            log_error(
                f"ABDM_PORT ('{abdm_port_val}') is required (as a positive integer) because AB Download Manager is enabled.")

    if is_valid:
        logger.info(
            f"Version {project_version} - Configuration validated successfully from {cfg_file_path_validated}.")
    else:
        logger.error(
            f"Version {project_version} - Configuration validation FAILED for {cfg_file_path_validated}.")
    return is_valid
