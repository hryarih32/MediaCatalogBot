import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

import src.app.app_config_holder as app_config_holder
from src.bot.bot_callback_data import CallbackData
from src.bot.bot_initialization import send_or_edit_universal_status_message
from src.bot.bot_message_persistence import load_menu_message_id

from src.services.plex.bot_plex_library import get_plex_libraries, trigger_library_scan, trigger_metadata_refresh
from src.services.plex.bot_plex_now_playing import get_now_playing_structured, stop_plex_stream

from src.handlers.plex.menu_handler_plex_controls import display_plex_controls_menu
from src.handlers.plex.menu_handler_plex_library_server_tools import display_plex_library_server_tools_menu

from src.bot.bot_text_utils import escape_md_v2, escape_md_v1

logger = logging.getLogger(__name__)

PLEX_SCAN_LIBRARY_LIST_TEXT_RAW = "🔄 Plex Libraries - Scan:"
PLEX_REFRESH_LIBRARY_LIST_TEXT_RAW = "♻️ Plex Libraries - Refresh Metadata:"
PLEX_NOW_PLAYING_TEXT_RAW = "📺 Plex - Now Playing:"
MAX_BUTTON_TEXT_LEN = 60


def _truncate_button_text_plex_lib(base_text: str, item_count: int, action_prefix: str) -> str:
    item_count_str = str(item_count)
    core_info = f"{base_text} ({item_count_str} items)"
    if len(action_prefix + core_info) <= MAX_BUTTON_TEXT_LEN:
        return action_prefix + core_info
    suffix_len = len(f" ({item_count_str} items)") + 3
    prefix_len = len(action_prefix)
    available_for_base = MAX_BUTTON_TEXT_LEN - prefix_len - suffix_len
    if available_for_base < 5:
        short_base = f"{action_prefix}{base_text}"
        return short_base[:MAX_BUTTON_TEXT_LEN-3] + "..." if len(short_base) > MAX_BUTTON_TEXT_LEN else short_base
    else:
        truncated_base = base_text[:available_for_base] + "..."
        return f"{action_prefix}{truncated_base} ({item_count_str} items)"


async def plex_now_playing_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, from_stop_action=False) -> None:
    if not from_stop_action:
        query = update.callback_query
        if query:
            await query.answer()

    chat_id = update.effective_chat.id

    admin_chat_id_str = app_config_holder.get_chat_id_str()
    if not admin_chat_id_str or str(chat_id) != admin_chat_id_str:
        logger.warning(
            f"Plex now playing attempt by non-primary admin {chat_id}.")
        return

    if not app_config_holder.is_plex_enabled():
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Plex features are disabled.", parse_mode=None)
        return

    now_playing_data = get_now_playing_structured()

    if "error" in now_playing_data:
        await send_or_edit_universal_status_message(context.bot, chat_id, now_playing_data["error"], parse_mode="MarkdownV2")
        await display_plex_controls_menu(update, context)
        return
    else:
        await send_or_edit_universal_status_message(context.bot, chat_id, now_playing_data["summary_text"], parse_mode="MarkdownV2")

    keyboard = []
    if now_playing_data.get("playing"):
        for item in now_playing_data["playing"]:
            session_id = item.get('session_id_for_stop')
            player_id = item.get('player_identifier_for_stop')
            cb_parts = []
            if player_id:
                cb_parts.append(f"player_{player_id}")
            if session_id:
                cb_parts.append(f"session_{session_id}")
            stop_identifier_for_cb = "|".join(cb_parts)
            if stop_identifier_for_cb:
                button_text_raw = f"Stop: {item['user_title']} - {item['media_title']}"
                button_text = button_text_raw[:MAX_BUTTON_TEXT_LEN-3] + "..." if len(
                    button_text_raw) > MAX_BUTTON_TEXT_LEN else button_text_raw
                keyboard.append([InlineKeyboardButton(
                    button_text, callback_data=f"{CallbackData.CMD_PLEX_STOP_STREAM_PREFIX.value}{stop_identifier_for_cb}")])

    keyboard.append([InlineKeyboardButton("🔄 Refresh Now Playing",
                    callback_data=CallbackData.CMD_PLEX_VIEW_NOW_PLAYING.value)])
    keyboard.append([InlineKeyboardButton("🔙 Back to Plex Controls",
                    callback_data=CallbackData.CMD_PLEX_CONTROLS.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)

    menu_message_id = load_menu_message_id(str(chat_id))
    if menu_message_id:
        try:
            escaped_menu_title = escape_md_v2(PLEX_NOW_PLAYING_TEXT_RAW)
            current_content_key = f"menu_message_content_{chat_id}_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (escaped_menu_title, reply_markup.to_json())
            if old_content_tuple != new_content_tuple:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=menu_message_id, text=escaped_menu_title, reply_markup=reply_markup, parse_mode="MarkdownV2")
                context.bot_data[current_content_key] = new_content_tuple
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                logger.error(
                    f"Error editing message for Plex Now Playing: {e}", exc_info=True)
        except Exception as e:
            logger.error(
                f"Error editing message for Plex Now Playing: {e}", exc_info=True)
    else:
        logger.error(
            "Cannot find menu_message_id for plex_now_playing_callback")


async def plex_stop_stream_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer(text="Processing stop command...")
    chat_id = update.effective_chat.id

    admin_chat_id_str = app_config_holder.get_chat_id_str()
    if not admin_chat_id_str or str(chat_id) != admin_chat_id_str:
        logger.warning(
            f"Plex stop stream attempt by non-primary admin {chat_id}.")

        await query.answer("Access Denied.", show_alert=True)
        return

    full_identifier_payload = query.data.replace(
        CallbackData.CMD_PLEX_STOP_STREAM_PREFIX.value, "")
    session_id_to_stop, player_id_to_stop = None, None
    parts = full_identifier_payload.split('|')
    for part in parts:
        if part.startswith("player_"):
            player_id_to_stop = part.replace("player_", "")
        elif part.startswith("session_"):
            session_id_to_stop = part.replace("session_", "")

        elif not ("player_" in part or "session_" in part) and part:
            session_id_to_stop = part

    if not app_config_holder.is_plex_enabled():
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Plex features are disabled.", parse_mode=None)
        return
    if not session_id_to_stop and not player_id_to_stop:
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2("⚠️ Could not identify stream to stop \\(no valid ID\\)\\."), parse_mode="MarkdownV2")
        await plex_now_playing_callback(update, context, from_stop_action=True)
        return

    target_info_log_raw = []
    if player_id_to_stop:
        target_info_log_raw.append(f"PlayerID='{player_id_to_stop}'")
    if session_id_to_stop:
        target_info_log_raw.append(f"SessionID='{session_id_to_stop}'")
    log_msg_ids_raw = ", ".join(target_info_log_raw)
    await send_or_edit_universal_status_message(context.bot, chat_id, f"⏳ Attempting to stop stream \\({escape_md_v2(log_msg_ids_raw)}\\)\\.\\.\\.", parse_mode="MarkdownV2")

    stop_result_v2_escaped = stop_plex_stream(
        session_id_to_stop=session_id_to_stop, player_identifier_to_stop=player_id_to_stop)
    logger.info(
        f"Plex stop_plex_stream result for {log_msg_ids_raw}: {stop_result_v2_escaped}")

    await plex_now_playing_callback(update, context, from_stop_action=True)

    alert_text_raw = stop_result_v2_escaped.replace('\\*', '*').replace(
        '\\(', '(').replace('\\)', ')').replace('\\.', '.').replace('\\!', '!').replace('\\-', '-')
    alert_text_raw = alert_text_raw.replace('⚠️', '').replace('✅', '').strip()
    if not alert_text_raw:
        alert_text_raw = "Plex: Unknown status for stop command."

    show_alert_flag = "✅" not in stop_result_v2_escaped
    alert_text_display = alert_text_raw[:190] + \
        "..." if len(alert_text_raw) > 190 else alert_text_raw
    await context.bot.answer_callback_query(query.id, text=alert_text_display, show_alert=show_alert_flag)


async def plex_scan_libraries_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    admin_chat_id_str = app_config_holder.get_chat_id_str()
    if not admin_chat_id_str or str(chat_id) != admin_chat_id_str:
        logger.warning(
            f"Plex scan select attempt by non-primary admin {chat_id}.")
        return

    if not app_config_holder.is_plex_enabled():
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Plex features are disabled.", parse_mode=None)
        await display_plex_library_server_tools_menu(update, context, called_internally=True)
        return

    libraries = get_plex_libraries()
    if not libraries:
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ No Plex libraries found or error fetching them.", parse_mode=None)
        await display_plex_library_server_tools_menu(update, context, called_internally=True)
        return

    keyboard = [[InlineKeyboardButton(
        "➡️ Scan All Libraries ⬅️", callback_data=f"{CallbackData.CMD_PLEX_SCAN_LIBRARY_PREFIX.value}all")]]
    for lib in libraries:
        base_button_text = f"{lib['title']} ({lib['type']})"
        button_text = _truncate_button_text_plex_lib(
            base_button_text, lib.get('item_count', 0), "Scan: ")
        keyboard.append([InlineKeyboardButton(
            button_text, callback_data=f"{CallbackData.CMD_PLEX_SCAN_LIBRARY_PREFIX.value}{lib['key']}")])

    keyboard.append([InlineKeyboardButton("🔙 Back to Library & Server Tools",
                    callback_data=CallbackData.CMD_PLEX_LIBRARY_SERVER_TOOLS.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_message_id = load_menu_message_id(str(chat_id))
    escaped_menu_title = escape_md_v2(PLEX_SCAN_LIBRARY_LIST_TEXT_RAW)

    if menu_message_id:
        try:
            current_content_key = f"menu_message_content_{chat_id}_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (escaped_menu_title, reply_markup.to_json())
            if old_content_tuple != new_content_tuple:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=menu_message_id, text=escaped_menu_title, reply_markup=reply_markup, parse_mode="MarkdownV2")
                context.bot_data[current_content_key] = new_content_tuple
            await send_or_edit_universal_status_message(context.bot, chat_id, "Select a library to scan, or scan all.", parse_mode=None)
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                logger.error(
                    f"Error editing message for Plex scan list: {e}", exc_info=True)

            await display_plex_library_server_tools_menu(update, context, called_internally=True)
        except Exception as e:
            logger.error(
                f"Error editing message for Plex scan list: {e}", exc_info=True)

            await display_plex_library_server_tools_menu(update, context, called_internally=True)
    else:
        logger.error(
            "Cannot find menu_message_id for plex_scan_libraries_select_callback")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Critical error displaying libraries for scan.", parse_mode=None)


async def plex_scan_library_execute_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    admin_chat_id_str = app_config_holder.get_chat_id_str()
    if not admin_chat_id_str or str(chat_id) != admin_chat_id_str:
        logger.warning(
            f"Plex scan execute attempt by non-primary admin {chat_id}.")
        return

    data_parts = query.data.split(
        CallbackData.CMD_PLEX_SCAN_LIBRARY_PREFIX.value)
    if len(data_parts) < 2:
        logger.error(f"Invalid callback data for scan: {query.data}")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Error processing scan request.", parse_mode=None)
        return
    library_key_or_all = data_parts[1]
    if not app_config_holder.is_plex_enabled():
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Plex features are disabled.", parse_mode=None)
        return
    scan_target_msg_raw = "all libraries" if library_key_or_all == "all" else f"library key {library_key_or_all}"
    await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(f"⏳ Initiating Plex scan for {scan_target_msg_raw}\\.\\.\\."), parse_mode="MarkdownV2")
    scan_result_text_raw = trigger_library_scan(
        library_key_or_all if library_key_or_all != "all" else None)
    await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(scan_result_text_raw), parse_mode="MarkdownV2")

    await display_plex_library_server_tools_menu(update, context, called_internally=True)


async def plex_refresh_library_metadata_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    admin_chat_id_str = app_config_holder.get_chat_id_str()
    if not admin_chat_id_str or str(chat_id) != admin_chat_id_str:
        logger.warning(
            f"Plex refresh select attempt by non-primary admin {chat_id}.")
        return

    if not app_config_holder.is_plex_enabled():
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Plex features are disabled.", parse_mode=None)
        await display_plex_library_server_tools_menu(update, context, called_internally=True)
        return

    libraries = get_plex_libraries()
    if not libraries:
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ No Plex libraries found or error fetching them.", parse_mode=None)
        await display_plex_library_server_tools_menu(update, context, called_internally=True)
        return

    keyboard = [[InlineKeyboardButton(
        "➡️ Refresh All Libraries ⬅️", callback_data=f"{CallbackData.CMD_PLEX_REFRESH_LIBRARY_METADATA_PREFIX.value}all")]]
    for lib in libraries:
        if lib['type'] in ['movie', 'show', 'artist']:
            base_button_text = f"{lib['title']} ({lib['type']})"
            button_text = _truncate_button_text_plex_lib(
                base_button_text, lib.get('item_count', 0), "Refresh: ")
            keyboard.append([InlineKeyboardButton(
                button_text, callback_data=f"{CallbackData.CMD_PLEX_REFRESH_LIBRARY_METADATA_PREFIX.value}{lib['key']}")])

    keyboard.append([InlineKeyboardButton("🔙 Back to Library & Server Tools",
                    callback_data=CallbackData.CMD_PLEX_LIBRARY_SERVER_TOOLS.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_message_id = load_menu_message_id(str(chat_id))
    escaped_menu_title = escape_md_v2(PLEX_REFRESH_LIBRARY_LIST_TEXT_RAW)

    if menu_message_id:
        try:
            current_content_key = f"menu_message_content_{chat_id}_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (escaped_menu_title, reply_markup.to_json())
            if old_content_tuple != new_content_tuple:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=menu_message_id, text=escaped_menu_title, reply_markup=reply_markup, parse_mode="MarkdownV2")
                context.bot_data[current_content_key] = new_content_tuple
            await send_or_edit_universal_status_message(context.bot, chat_id, "Select a library to refresh metadata, or refresh all.", parse_mode=None)
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                logger.error(
                    f"Error editing message for Plex refresh list: {e}", exc_info=True)

            await display_plex_library_server_tools_menu(update, context, called_internally=True)
        except Exception as e:
            logger.error(
                f"Error editing message for Plex refresh list: {e}", exc_info=True)

            await display_plex_library_server_tools_menu(update, context, called_internally=True)
    else:
        logger.error(
            "Cannot find menu_message_id for plex_refresh_library_metadata_select_callback")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Critical error displaying libraries for refresh.", parse_mode=None)


async def plex_refresh_library_metadata_execute_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    admin_chat_id_str = app_config_holder.get_chat_id_str()
    if not admin_chat_id_str or str(chat_id) != admin_chat_id_str:
        logger.warning(
            f"Plex refresh execute attempt by non-primary admin {chat_id}.")
        return

    data_parts = query.data.split(
        CallbackData.CMD_PLEX_REFRESH_LIBRARY_METADATA_PREFIX.value)
    if len(data_parts) < 2:
        logger.error(f"Invalid callback data for refresh: {query.data}")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Error processing refresh request.", parse_mode=None)
        return
    library_key_or_all = data_parts[1]
    if not app_config_holder.is_plex_enabled():
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Plex features are disabled.", parse_mode=None)
        return
    refresh_target_msg_raw = "all eligible libraries" if library_key_or_all == "all" else f"library key {library_key_or_all}"
    await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(f"⏳ Initiating Plex metadata refresh for {refresh_target_msg_raw}\\.\\.\\."), parse_mode="MarkdownV2")
    refresh_result_text_raw = trigger_metadata_refresh(
        library_key_or_all if library_key_or_all != "all" else None)
    await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(refresh_result_text_raw), parse_mode="MarkdownV2")

    await display_plex_library_server_tools_menu(update, context, called_internally=True)
