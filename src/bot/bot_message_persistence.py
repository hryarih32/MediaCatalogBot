import logging
import os

from src.app.app_file_utils import get_data_storage_path

logger = logging.getLogger(__name__)

MENU_ID_FILE_NAME = "msg_id_menu.txt"
UNIVERSAL_MESSAGE_ID_FILE_NAME = "msg_id_universal_status.txt"


def get_app_data_file_path(filename: str) -> str:

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

                    if filename_key_for_log == MENU_ID_FILE_NAME:
                        delete_menu_id_file()
                    elif filename_key_for_log == UNIVERSAL_MESSAGE_ID_FILE_NAME:
                        delete_universal_status_message_id_file()
        except Exception as e:
            logger.warning(
                f"Could not read or parse ID from {filepath} (key: {filename_key_for_log}): {e}", exc_info=True)
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


def load_menu_message_id() -> int | None:
    return _load_id_from_file_generic(MENU_ID_FILE_NAME, get_app_data_file_path(MENU_ID_FILE_NAME))


def save_menu_message_id(message_id: int):
    _save_id_to_file_generic(
        message_id, MENU_ID_FILE_NAME, get_app_data_file_path(MENU_ID_FILE_NAME))


def delete_menu_id_file():
    _delete_file_generic(
        MENU_ID_FILE_NAME, get_app_data_file_path(MENU_ID_FILE_NAME))


def load_universal_status_message_id() -> int | None:
    return _load_id_from_file_generic(UNIVERSAL_MESSAGE_ID_FILE_NAME, get_app_data_file_path(UNIVERSAL_MESSAGE_ID_FILE_NAME))


def save_universal_status_message_id(message_id: int):
    _save_id_to_file_generic(message_id, UNIVERSAL_MESSAGE_ID_FILE_NAME,
                             get_app_data_file_path(UNIVERSAL_MESSAGE_ID_FILE_NAME))


def delete_universal_status_message_id_file():
    _delete_file_generic(UNIVERSAL_MESSAGE_ID_FILE_NAME,
                         get_app_data_file_path(UNIVERSAL_MESSAGE_ID_FILE_NAME))


def load_message_id_from_file(filename_key: str) -> int | None:
    logger.warning(
        f"Deprecated load_message_id_from_file called for {filename_key}. Use specific load functions.")
    if filename_key == MENU_ID_FILE_NAME:
        return load_menu_message_id()
    if filename_key == UNIVERSAL_MESSAGE_ID_FILE_NAME:
        return load_universal_status_message_id()
    return _load_id_from_file_generic(filename_key, get_app_data_file_path(filename_key))


def save_message_id_to_file(message_id: int, filename_key: str):
    logger.warning(
        f"Deprecated save_message_id_to_file called for {filename_key}. Use specific save functions.")
    if filename_key == MENU_ID_FILE_NAME:
        save_menu_message_id(message_id)
        return
    if filename_key == UNIVERSAL_MESSAGE_ID_FILE_NAME:
        save_universal_status_message_id(message_id)
        return
    _save_id_to_file_generic(message_id, filename_key,
                             get_app_data_file_path(filename_key))


def delete_message_id_file(filename_key: str):
    logger.warning(
        f"Deprecated delete_message_id_file called for {filename_key}. Use specific delete functions.")
    if filename_key == MENU_ID_FILE_NAME:
        delete_menu_id_file()
        return
    if filename_key == UNIVERSAL_MESSAGE_ID_FILE_NAME:
        delete_universal_status_message_id_file()
        return
    _delete_file_generic(filename_key, get_app_data_file_path(filename_key))
