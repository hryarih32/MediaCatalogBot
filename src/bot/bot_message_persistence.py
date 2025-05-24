import logging
import os

from src.app.app_file_utils import get_data_storage_path

logger = logging.getLogger(__name__)

MENU_ID_FILE_PREFIX = "msg_id_menu_"

UNIVERSAL_MESSAGE_ID_FILE_PREFIX = "msg_id_universal_status_"


def get_user_specific_data_file_path(base_prefix: str, chat_id_str: str) -> str:
    """Generates a user-specific filename."""
    if not chat_id_str:
        logger.error(
            "Chat ID is empty, cannot generate user-specific file path.")

        return os.path.join(get_data_storage_path(), f"{base_prefix}unknown_user.txt")

    safe_chat_id_suffix = chat_id_str.replace(
        '-', 'neg')

    filename = f"{base_prefix}{safe_chat_id_suffix}.txt"
    data_storage_path = get_data_storage_path()
    return os.path.join(data_storage_path, filename)


def _load_id_from_file_generic(filename_key_for_log: str, filepath: str) -> int | None:
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                content = f.read().strip()
                if content.isdigit():
                    logger.debug(
                        f"Loaded ID {content} from {filepath} (key: {filename_key_for_log})")
                    return int(content)
                else:
                    logger.warning(
                        f"Content of {filepath} ('{content}') (key: {filename_key_for_log}) is not a valid ID. Deleting file.")
                    try:
                        os.remove(filepath)
                    except OSError as e_del:
                        logger.error(
                            f"Could not delete corrupt file {filepath}: {e_del}")
        except Exception as e:
            logger.warning(
                f"Could not read or parse ID from {filepath} (key: {filename_key_for_log}): {e}", exc_info=False)
    return None


def _save_id_to_file_generic(message_id: int, filename_key_for_log: str, filepath: str):
    try:
        with open(filepath, 'w') as f:
            f.write(str(message_id))
        logger.info(
            f"Saved ID {message_id} to {filepath} (key: {filename_key_for_log})")
    except Exception as e:
        logger.error(
            f"Could not write ID {message_id} to {filepath} (key: {filename_key_for_log}): {e}", exc_info=True)


def _delete_file_generic(filename_key_for_log: str, filepath: str):
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            logger.info(
                f"Deleted file {filepath} (key: {filename_key_for_log})")
        except OSError as e:
            logger.error(
                f"Could not delete file {filepath} (key: {filename_key_for_log}): {e}", exc_info=True)


def load_menu_message_id(chat_id_str: str) -> int | None:
    filepath = get_user_specific_data_file_path(
        MENU_ID_FILE_PREFIX, chat_id_str)
    return _load_id_from_file_generic(f"{MENU_ID_FILE_PREFIX}{chat_id_str}", filepath)


def save_menu_message_id(message_id: int, chat_id_str: str):
    filepath = get_user_specific_data_file_path(
        MENU_ID_FILE_PREFIX, chat_id_str)
    _save_id_to_file_generic(
        message_id, f"{MENU_ID_FILE_PREFIX}{chat_id_str}", filepath)


def delete_menu_id_file(chat_id_str: str):
    filepath = get_user_specific_data_file_path(
        MENU_ID_FILE_PREFIX, chat_id_str)
    _delete_file_generic(
        f"{MENU_ID_FILE_PREFIX}{chat_id_str}", filepath)


def load_universal_status_message_id(chat_id_str: str) -> int | None:
    filepath = get_user_specific_data_file_path(
        UNIVERSAL_MESSAGE_ID_FILE_PREFIX, chat_id_str)
    return _load_id_from_file_generic(f"{UNIVERSAL_MESSAGE_ID_FILE_PREFIX}{chat_id_str}", filepath)


def save_universal_status_message_id(message_id: int, chat_id_str: str):
    filepath = get_user_specific_data_file_path(
        UNIVERSAL_MESSAGE_ID_FILE_PREFIX, chat_id_str)
    _save_id_to_file_generic(message_id, f"{UNIVERSAL_MESSAGE_ID_FILE_PREFIX}{chat_id_str}",
                             filepath)


def delete_universal_status_message_id_file(chat_id_str: str):
    filepath = get_user_specific_data_file_path(
        UNIVERSAL_MESSAGE_ID_FILE_PREFIX, chat_id_str)
    _delete_file_generic(f"{UNIVERSAL_MESSAGE_ID_FILE_PREFIX}{chat_id_str}",
                         filepath)


def load_message_id_from_file(filename_key: str) -> int | None:
    logger.warning(
        f"Deprecated load_message_id_from_file called for {filename_key}. Use user-specific load functions.")

    return None


def save_message_id_to_file(message_id: int, filename_key: str):
    logger.warning(
        f"Deprecated save_message_id_to_file called for {filename_key}. Use user-specific save functions.")

    return


def delete_message_id_file(filename_key: str):
    logger.warning(
        f"Deprecated delete_message_id_file (singular) called for {filename_key}. Use specific delete functions with chat_id.")

    return
