
import logging

import src.app.user_manager as user_manager

logger = logging.getLogger(__name__)

MESSAGE_TYPE_MENU = "main_menu_id"
MESSAGE_TYPE_UNIVERSAL_STATUS = "universal_status_id"


def load_menu_message_id(chat_id_str: str) -> int | None:
    """Loads the persisted main menu message ID for a given chat from bot_state.json."""
    if not chat_id_str:
        logger.error("load_menu_message_id: chat_id_str is empty.")
        return None

    message_ids = user_manager.get_message_ids_for_chat(str(chat_id_str))
    msg_id = message_ids.get(MESSAGE_TYPE_MENU)
    if msg_id:
        logger.debug(
            f"Loaded menu_message_id {msg_id} for chat_id {chat_id_str} from bot_state.")
        return int(msg_id)
    logger.debug(
        f"No persisted menu_message_id found for chat_id {chat_id_str} in bot_state.")
    return None


def save_menu_message_id(message_id: int, chat_id_str: str):
    """Saves the main menu message ID for a given chat to bot_state.json."""
    if not chat_id_str:
        logger.error("save_menu_message_id: chat_id_str is empty.")
        return
    if not isinstance(message_id, int):
        logger.error(
            f"save_menu_message_id: message_id '{message_id}' is not an integer for chat_id {chat_id_str}.")
        return

    if user_manager.save_message_id_for_chat(str(chat_id_str), MESSAGE_TYPE_MENU, message_id):
        logger.info(
            f"Saved menu_message_id {message_id} for chat_id {chat_id_str} to bot_state.")
    else:
        logger.error(
            f"Failed to save menu_message_id for chat_id {chat_id_str} to bot_state.")


def delete_menu_id_file(chat_id_str: str):
    """Clears the persisted main menu message ID for a given chat from bot_state.json."""
    if not chat_id_str:
        logger.error(
            "delete_menu_id_file (clear_menu_id_in_state): chat_id_str is empty.")
        return

    if user_manager.clear_message_id_for_chat(str(chat_id_str), MESSAGE_TYPE_MENU):
        logger.info(
            f"Cleared persisted menu_message_id for chat_id {chat_id_str} from bot_state.")
    else:
        logger.debug(
            f"No menu_message_id to clear for chat_id {chat_id_str} in bot_state or error during clearing.")


def load_universal_status_message_id(chat_id_str: str) -> int | None:
    """Loads the persisted universal status message ID for a given chat from bot_state.json."""
    if not chat_id_str:
        logger.error("load_universal_status_message_id: chat_id_str is empty.")
        return None

    message_ids = user_manager.get_message_ids_for_chat(str(chat_id_str))
    msg_id = message_ids.get(MESSAGE_TYPE_UNIVERSAL_STATUS)
    if msg_id:
        logger.debug(
            f"Loaded universal_status_id {msg_id} for chat_id {chat_id_str} from bot_state.")
        return int(msg_id)
    logger.debug(
        f"No persisted universal_status_id found for chat_id {chat_id_str} in bot_state.")
    return None


def save_universal_status_message_id(message_id: int, chat_id_str: str):
    """Saves the universal status message ID for a given chat to bot_state.json."""
    if not chat_id_str:
        logger.error("save_universal_status_message_id: chat_id_str is empty.")
        return
    if not isinstance(message_id, int):
        logger.error(
            f"save_universal_status_message_id: message_id '{message_id}' is not an integer for chat_id {chat_id_str}.")
        return

    if user_manager.save_message_id_for_chat(str(chat_id_str), MESSAGE_TYPE_UNIVERSAL_STATUS, message_id):
        logger.info(
            f"Saved universal_status_id {message_id} for chat_id {chat_id_str} to bot_state.")
    else:
        logger.error(
            f"Failed to save universal_status_id for chat_id {chat_id_str} to bot_state.")


def delete_universal_status_message_id_file(chat_id_str: str):
    """Clears the persisted universal status message ID for a given chat from bot_state.json."""
    if not chat_id_str:
        logger.error(
            "delete_universal_status_message_id_file (clear_universal_status_id_in_state): chat_id_str is empty.")
        return

    if user_manager.clear_message_id_for_chat(str(chat_id_str), MESSAGE_TYPE_UNIVERSAL_STATUS):
        logger.info(
            f"Cleared persisted universal_status_id for chat_id {chat_id_str} from bot_state.")
    else:
        logger.debug(
            f"No universal_status_id to clear for chat_id {chat_id_str} in bot_state or error during clearing.")


def load_message_id_from_file(filename_key: str) -> int | None:
    logger.warning(
        f"DEPRECATED: load_message_id_from_file called for '{filename_key}'. "
        "Message IDs are now managed in bot_state.json via user_manager. Use chat_id specific functions."
    )
    return None


def save_message_id_to_file(message_id: int, filename_key: str):
    logger.warning(
        f"DEPRECATED: save_message_id_to_file called for '{filename_key}'. "
        "Message IDs are now managed in bot_state.json via user_manager. Use chat_id specific functions."
    )
    return


def delete_message_id_file(filename_key: str):
    logger.warning(
        f"DEPRECATED: delete_message_id_file (singular) called for '{filename_key}'. "
        "Message IDs are now managed in bot_state.json. Use chat_id specific functions like delete_menu_id_file."
    )
    return
