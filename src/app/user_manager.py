
import logging
import os
import datetime
from telegram import User
from .app_file_utils import get_bot_state_file_path, load_json_data, save_json_data
import src.app.app_config_holder as app_config_holder

logger = logging.getLogger(__name__)

DEFAULT_BOT_STATE = {
    "users": {},
    "message_persistence": {},
    "bot_info": {
        "last_startup_time": None,
        "version_at_last_run": None,
        "static_launchers_migrated": False
    },
    "dynamic_launchers": [],
    "access_requests_pending": {}
}

_bot_state_cache = None

PLACEHOLDER_USERNAME_PREFIXES = ["User_", "PrimaryAdmin_"]
OTHER_PLACEHOLDERS = ["N/A", "Unknown User", "Unknown (to be fetched)"]


def _is_username_placeholder(username: str | None, chat_id_str: str | None = None) -> bool:

    if not username:
        return True
    if username in OTHER_PLACEHOLDERS:
        return True
    for prefix in PLACEHOLDER_USERNAME_PREFIXES:
        if username.startswith(prefix):
            if chat_id_str and username == f"{prefix}{chat_id_str}":
                return True
            elif not chat_id_str and username.startswith(prefix):
                return True
    return False


def _load_bot_state(force_reload: bool = False) -> dict:

    global _bot_state_cache
    if not force_reload and _bot_state_cache is not None:
        return _bot_state_cache.copy()

    bot_state_path = get_bot_state_file_path()
    loaded_state = load_json_data(bot_state_path)

    if loaded_state is None:
        logger.warning(
            f"{bot_state_path} (and its backup) not found or invalid. Initializing with default structure.")
        _bot_state_cache = DEFAULT_BOT_STATE.copy()
        if not os.path.exists(bot_state_path) or (loaded_state is None and os.path.exists(bot_state_path)):
            _save_bot_state(_bot_state_cache)
    else:
        _bot_state_cache = loaded_state

    updated_during_load = False
    for key, default_value in DEFAULT_BOT_STATE.items():
        if key not in _bot_state_cache:
            logger.info(
                f"Key '{key}' missing in bot_state.json, initializing with default.")
            _bot_state_cache[key] = default_value.copy() if isinstance(
                default_value, (dict, list)) else default_value
            updated_during_load = True

        if key == "bot_info" and isinstance(_bot_state_cache.get(key), dict):
            bot_info_state = _bot_state_cache[key]
            default_bot_info = DEFAULT_BOT_STATE["bot_info"]
            for sub_key, sub_default_value in default_bot_info.items():
                if sub_key not in bot_info_state:
                    logger.info(
                        f"Sub-key '{sub_key}' missing in bot_state.json['bot_info'], initializing.")
                    bot_info_state[sub_key] = sub_default_value
                    updated_during_load = True

        elif key == "access_requests_pending" and not isinstance(_bot_state_cache.get(key), dict):
            logger.warning(
                f"Key '{key}' in bot_state.json is not a dict. Resetting to default.")
            _bot_state_cache[key] = default_value.copy()
            updated_during_load = True

    if updated_during_load:
        _save_bot_state(_bot_state_cache)

    return _bot_state_cache.copy()


def _save_bot_state(state_data: dict) -> bool:

    global _bot_state_cache
    bot_state_path = get_bot_state_file_path()
    data_to_save = state_data.copy()
    if save_json_data(bot_state_path, data_to_save):
        _bot_state_cache = data_to_save
        logger.debug(
            f"Bot state successfully saved to {bot_state_path} and cache updated.")
        return True
    else:
        logger.error(
            f"Failed to save bot state to {bot_state_path}. Cache not updated.")
        return False


def get_all_users_from_state() -> dict:

    state = _load_bot_state(force_reload=True)
    return state.get("users", {}).copy()


def get_role_for_chat_id(chat_id_str: str) -> str:

    if not chat_id_str:
        return app_config_holder.ROLE_UNKNOWN
    if app_config_holder.is_primary_admin(chat_id_str):
        return app_config_holder.ROLE_ADMIN
    state = _load_bot_state()
    users = state.get("users", {})
    user_info = users.get(str(chat_id_str))
    if user_info and "role" in user_info:
        role = user_info["role"]
        if role in [app_config_holder.ROLE_ADMIN, app_config_holder.ROLE_STANDARD_USER]:
            return role
        else:
            logger.warning(
                f"User {chat_id_str} has an unknown role '{role}'. Defaulting to UNKNOWN.")
            return app_config_holder.ROLE_UNKNOWN
    logger.debug(
        f"User {chat_id_str} not found in bot_state.json and is not primary admin. Assigning ROLE_UNKNOWN.")
    return app_config_holder.ROLE_UNKNOWN


def ensure_initial_bot_state():

    logger.info("Ensuring initial bot state and primary admin configuration...")
    _load_bot_state(force_reload=True)
    ensure_primary_admin_in_state()


def ensure_primary_admin_in_state():

    primary_admin_id_str = app_config_holder.get_chat_id_str()
    if not primary_admin_id_str:
        logger.critical(
            "Primary Admin CHAT_ID not configured! Cannot ensure admin state in bot_state.json.")
        return
    current_bot_state = _load_bot_state(force_reload=True)
    users_in_state = current_bot_state.get("users", {})
    needs_save = False
    primary_admin_info = users_in_state.get(primary_admin_id_str)
    desired_username = f"PrimaryAdmin_{primary_admin_id_str}"
    if not primary_admin_info:
        users_in_state[primary_admin_id_str] = {
            "username": desired_username, "role": app_config_holder.ROLE_ADMIN}
        needs_save = True
    else:
        if primary_admin_info.get("role") != app_config_holder.ROLE_ADMIN:
            primary_admin_info["role"] = app_config_holder.ROLE_ADMIN
            needs_save = True
        if not primary_admin_info.get("username"):
            primary_admin_info["username"] = desired_username
            needs_save = True
    if needs_save:
        current_bot_state["users"] = users_in_state
        _save_bot_state(current_bot_state)


def save_users_from_gui(users_data_from_gui: dict):

    primary_admin_id_str = app_config_holder.get_chat_id_str()
    if primary_admin_id_str:
        desired_pa_username = f"PrimaryAdmin_{primary_admin_id_str}"
        if primary_admin_id_str not in users_data_from_gui:
            users_data_from_gui[primary_admin_id_str] = {
                "username": desired_pa_username, "role": app_config_holder.ROLE_ADMIN}
        elif users_data_from_gui[primary_admin_id_str].get("role") != app_config_holder.ROLE_ADMIN:
            users_data_from_gui[primary_admin_id_str]["role"] = app_config_holder.ROLE_ADMIN
        if not users_data_from_gui[primary_admin_id_str].get("username"):
            users_data_from_gui[primary_admin_id_str]["username"] = desired_pa_username
    current_full_state = _load_bot_state(force_reload=True)
    current_full_state["users"] = users_data_from_gui
    return _save_bot_state(current_full_state)


def get_message_ids_for_chat(chat_id_str: str) -> dict:

    state = _load_bot_state()
    return state.get("message_persistence", {}).get(str(chat_id_str), {}).copy()


def save_message_id_for_chat(chat_id_str: str, message_type: str, message_id: int) -> bool:

    if not chat_id_str or not message_type:
        return False
    current_full_state = _load_bot_state(force_reload=True)
    if "message_persistence" not in current_full_state:
        current_full_state["message_persistence"] = {}
    if str(chat_id_str) not in current_full_state["message_persistence"]:
        current_full_state["message_persistence"][str(chat_id_str)] = {}
    current_full_state["message_persistence"][str(
        chat_id_str)][message_type] = message_id
    return _save_bot_state(current_full_state)


def clear_message_id_for_chat(chat_id_str: str, message_type: str) -> bool:

    if not chat_id_str or not message_type:
        return False
    current_full_state = _load_bot_state(force_reload=True)
    if "message_persistence" in current_full_state and \
       str(chat_id_str) in current_full_state["message_persistence"] and \
       message_type in current_full_state["message_persistence"][str(chat_id_str)]:
        del current_full_state["message_persistence"][str(
            chat_id_str)][message_type]
        if not current_full_state["message_persistence"][str(chat_id_str)]:
            del current_full_state["message_persistence"][str(chat_id_str)]
        if not current_full_state["message_persistence"]:
            current_full_state.pop("message_persistence", None)
        return _save_bot_state(current_full_state)
    return False


def record_bot_startup_time() -> bool:

    current_full_state = _load_bot_state(force_reload=True)
    if "bot_info" not in current_full_state or not isinstance(current_full_state.get("bot_info"), dict):
        current_full_state["bot_info"] = DEFAULT_BOT_STATE["bot_info"].copy()
    current_full_state["bot_info"]["last_startup_time"] = datetime.datetime.now(
        datetime.timezone.utc).isoformat()
    current_full_state["bot_info"]["version_at_last_run"] = app_config_holder.get_project_version()
    logger.info(
        f"Recording startup time: {current_full_state['bot_info']['last_startup_time']} and version: {current_full_state['bot_info']['version_at_last_run']}")
    return _save_bot_state(current_full_state)


def get_last_startup_time_str() -> str | None:

    state = _load_bot_state()
    return state.get("bot_info", {}).get("last_startup_time")


def update_username_if_placeholder(chat_id_str: str, effective_user: User) -> bool:

    if not chat_id_str or not effective_user:
        return False
    state = _load_bot_state(force_reload=True)
    users = state.get("users", {})
    user_info = users.get(str(chat_id_str))
    if not user_info:
        logger.debug(
            f"User {chat_id_str} not found in state for username update.")
        return False
    current_username = user_info.get("username")
    needs_update = False
    if _is_username_placeholder(current_username, chat_id_str):
        new_name_to_set = effective_user.username or effective_user.first_name
        if new_name_to_set and new_name_to_set != current_username:
            user_info["username"] = new_name_to_set
            needs_update = True
            logger.info(
                f"Updating username for {chat_id_str} from '{current_username}' to '{new_name_to_set}'.")
        elif not new_name_to_set and current_username:
            logger.debug(
                f"User {chat_id_str} has placeholder '{current_username}', but no new name from Telegram.")
    if needs_update:
        state["users"] = users
        return _save_bot_state(state)
    return False


def get_dynamic_launchers() -> list:

    state = _load_bot_state()
    return state.get("dynamic_launchers", []).copy()


def save_dynamic_launchers(launchers_list: list) -> bool:

    if not isinstance(launchers_list, list):
        logger.error("Attempted to save non-list data as dynamic_launchers.")
        return False
    current_full_state = _load_bot_state(force_reload=True)
    current_full_state["dynamic_launchers"] = launchers_list
    return _save_bot_state(current_full_state)


def get_static_launchers_migrated_flag() -> bool:

    state = _load_bot_state()
    return state.get("bot_info", {}).get("static_launchers_migrated", False)


def set_static_launchers_migrated_flag(migrated: bool) -> bool:

    current_full_state = _load_bot_state(force_reload=True)
    if "bot_info" not in current_full_state or not isinstance(current_full_state.get("bot_info"), dict):
        current_full_state["bot_info"] = DEFAULT_BOT_STATE["bot_info"].copy()
    current_full_state["bot_info"]["static_launchers_migrated"] = migrated
    return _save_bot_state(current_full_state)


def add_pending_access_request(chat_id_str: str, username: str | None) -> bool:
    """Adds a user to the pending access request list."""
    if not chat_id_str:
        return False

    current_full_state = _load_bot_state(force_reload=True)

    if "access_requests_pending" not in current_full_state or not isinstance(current_full_state["access_requests_pending"], dict):
        current_full_state["access_requests_pending"] = {}

    users = current_full_state.get("users", {})
    if str(chat_id_str) in users:
        logger.info(
            f"User {chat_id_str} already exists in users list. Not adding to pending access.")
        return False
    if str(chat_id_str) in current_full_state["access_requests_pending"]:
        logger.info(
            f"User {chat_id_str} already has a pending access request.")

        current_full_state["access_requests_pending"][str(
            chat_id_str)]["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if username and current_full_state["access_requests_pending"][str(chat_id_str)].get("username") != username:
            current_full_state["access_requests_pending"][str(
                chat_id_str)]["username"] = username
        return _save_bot_state(current_full_state)

    current_full_state["access_requests_pending"][str(chat_id_str)] = {

        "username": username or f"User_{chat_id_str}",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    logger.info(
        f"User {chat_id_str} (Username: {username}) added to pending access requests.")
    return _save_bot_state(current_full_state)


def get_pending_access_requests() -> dict:
    """Retrieves the dictionary of pending access requests."""
    state = _load_bot_state(force_reload=True)
    return state.get("access_requests_pending", {}).copy()


def remove_pending_access_request(chat_id_str: str) -> bool:
    """Removes a user from the pending access request list (e.g., after approval or denial)."""
    if not chat_id_str:
        return False

    current_full_state = _load_bot_state(force_reload=True)
    if "access_requests_pending" in current_full_state and str(chat_id_str) in current_full_state["access_requests_pending"]:
        del current_full_state["access_requests_pending"][str(chat_id_str)]

        if not current_full_state["access_requests_pending"]:
            current_full_state.pop("access_requests_pending", None)
        logger.info(
            f"User {chat_id_str} removed from pending access requests.")
        return _save_bot_state(current_full_state)
    logger.info(
        f"User {chat_id_str} not found in pending access requests for removal.")
    return False


def add_approved_user(chat_id_str: str, username: str, role: str) -> bool:
    """Adds an approved user to the main users list and removes them from pending."""
    if not chat_id_str or not role or role not in [app_config_holder.ROLE_ADMIN, app_config_holder.ROLE_STANDARD_USER]:
        logger.error(
            f"Cannot add approved user {chat_id_str}: Invalid parameters (role: {role}).")
        return False

    primary_admin_id = app_config_holder.get_chat_id_str()
    if chat_id_str == primary_admin_id and role != app_config_holder.ROLE_ADMIN:
        logger.warning(
            f"Attempt to approve primary admin {chat_id_str} with role {role} blocked. Primary admin must be ADMIN.")
        role = app_config_holder.ROLE_ADMIN

    current_full_state = _load_bot_state(force_reload=True)
    users = current_full_state.get("users", {})

    users[str(chat_id_str)] = {

        "username": username or f"User_{chat_id_str}",
        "role": role
    }
    current_full_state["users"] = users
    logger.info(
        f"User {chat_id_str} (Username: {username}) added/updated in users list with role {role}.")

    if "access_requests_pending" in current_full_state and str(chat_id_str) in current_full_state["access_requests_pending"]:
        del current_full_state["access_requests_pending"][str(chat_id_str)]
        if not current_full_state["access_requests_pending"]:
            current_full_state.pop("access_requests_pending", None)
        logger.info(
            f"User {chat_id_str} also removed from pending access requests after approval.")

    return _save_bot_state(current_full_state)
