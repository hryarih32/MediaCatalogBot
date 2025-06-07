
import logging
import os
import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import src.app.app_config_holder as app_config_holder

from src.app.app_file_utils import load_requests_data

import src.app.user_manager as user_manager
from src.bot.bot_callback_data import CallbackData
from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)


def get_pending_request_count() -> int:
    """Counts the number of media requests with 'pending' status."""
    all_requests = load_requests_data()
    pending_count = sum(
        1 for req in all_requests if req.get("status") == "pending")
    return pending_count


def get_pending_access_request_count() -> int:
    """Counts the number of pending user access requests."""

    pending_access_requests = user_manager.get_pending_access_requests()
    return len(pending_access_requests)


def build_main_menu_content(version: str, user_role: str, chat_id_str: str):
    is_primary_admin = app_config_holder.is_primary_admin(chat_id_str)
    is_general_admin = (user_role == app_config_holder.ROLE_ADMIN)
    is_standard_user = (user_role == app_config_holder.ROLE_STANDARD_USER)
    is_unknown_user = (user_role == app_config_holder.ROLE_UNKNOWN)

    plex_status_emoji = "⚙️" if app_config_holder.is_plex_enabled() else "🔘"
    if app_config_holder.is_plex_enabled():
        plex_status_emoji = "✅" if app_config_holder.get_plex_url(
        ) and app_config_holder.get_plex_token() else "⚠️"
    radarr_status_emoji = "⚙️" if app_config_holder.is_radarr_enabled() else "🔘"
    if app_config_holder.is_radarr_enabled():
        radarr_status_emoji = "✅" if app_config_holder.get_radarr_base_api_url(
        ) and app_config_holder.get_radarr_api_key() else "⚠️"
    sonarr_status_emoji = "⚙️" if app_config_holder.is_sonarr_enabled() else "🔘"
    if app_config_holder.is_sonarr_enabled():
        sonarr_status_emoji = "✅" if app_config_holder.get_sonarr_base_api_url(
        ) and app_config_holder.get_sonarr_api_key() else "⚠️"
    abdm_status_emoji = "⚙️" if app_config_holder.is_abdm_enabled() else "🔘"
    if app_config_holder.is_abdm_enabled():
        abdm_port_val = app_config_holder.get_abdm_port()
        abdm_status_emoji = "✅" if abdm_port_val is not None else "⚠️"

    formatted_startup_time = "Unknown"
    iso_startup_timestamp = user_manager.get_last_startup_time_str()
    if iso_startup_timestamp:
        try:
            utc_startup_time_obj = datetime.datetime.fromisoformat(
                iso_startup_timestamp)
            local_startup_time_obj = utc_startup_time_obj.astimezone()
            formatted_startup_time = local_startup_time_obj.strftime(
                "%Y-%m-%d %H:%M")
        except ValueError:
            logger.warning(
                f"Could not parse startup timestamp '{iso_startup_timestamp}' from bot_state. Using 'Invalid Format'.")
            formatted_startup_time = "Invalid Format"
        except Exception as e_time:
            logger.error(
                f"Error converting startup timestamp '{iso_startup_timestamp}': {e_time}", exc_info=True)
            formatted_startup_time = "Error Converting Time"
    else:
        logger.info("Last startup time not yet recorded in bot_state.json.")
        formatted_startup_time = "Not yet recorded"

    escaped_version = escape_md_v2(version)
    escaped_startup_time = escape_md_v2(formatted_startup_time)
    separator_line = "—" * 17

    header_parts = [f"🎬 Media Catalog Bot \\(v{escaped_version}\\)"]
    if is_general_admin:
        header_parts.append(escape_md_v2(separator_line))
        header_parts.append(
            f"Plex: {plex_status_emoji} Sonarr: {sonarr_status_emoji} Radarr: {radarr_status_emoji} ABDM: {abdm_status_emoji}"
        )
        header_parts.append(f"Up Since: {escaped_startup_time}")
    elif is_standard_user:
        header_parts.append(escape_md_v2(separator_line))
        header_parts.append("Welcome\\! Select an option below\\.")
    elif is_unknown_user:
        header_parts.append(escape_md_v2(separator_line))

        header_parts.append("Access to this bot is restricted\\.")
    else:
        header_parts.append(escape_md_v2(separator_line))
        header_parts.append("Your access level is currently undefined\\.")

    dynamic_menu_text = "\n".join(header_parts)
    keyboard = []

    if is_standard_user:
        standard_user_media_buttons = []
        if app_config_holder.is_radarr_enabled():
            standard_user_media_buttons.append(InlineKeyboardButton("➕ Request Movie",
                                                                    callback_data=CallbackData.CMD_ADD_MOVIE_INIT.value))
        if app_config_holder.is_sonarr_enabled():
            standard_user_media_buttons.append(InlineKeyboardButton("➕ Request TV Show",
                                                                    callback_data=CallbackData.CMD_ADD_SHOW_INIT.value))
        if standard_user_media_buttons:
            keyboard.append(standard_user_media_buttons)

        if app_config_holder.is_plex_enabled():
            keyboard.append([InlineKeyboardButton("🔍 Search Plex",
                                                  callback_data=CallbackData.CMD_PLEX_INITIATE_SEARCH.value)])
        keyboard.append([InlineKeyboardButton("📋 My Requests",
                                              callback_data=CallbackData.CMD_MY_REQUESTS_MENU.value)])

    elif is_general_admin:
        admin_add_media_buttons = []
        if app_config_holder.is_radarr_enabled():
            admin_add_media_buttons.append(
                InlineKeyboardButton("➕ Add Movie",
                                     callback_data=CallbackData.CMD_ADD_MOVIE_INIT.value)
            )
        if app_config_holder.is_sonarr_enabled():
            admin_add_media_buttons.append(InlineKeyboardButton("➕ Add TV Show",
                                                                callback_data=CallbackData.CMD_ADD_SHOW_INIT.value))
        if admin_add_media_buttons:
            keyboard.append(admin_add_media_buttons)

        if is_primary_admin and app_config_holder.is_abdm_enabled():
            keyboard.append([InlineKeyboardButton("📥 Add Download (ABDM)",
                                                  callback_data=CallbackData.CMD_ADD_DOWNLOAD_INIT.value)])

        pending_media_req_count = get_pending_request_count()
        admin_media_req_button_text = f"📮 Media Requests ({pending_media_req_count}❗️)" if pending_media_req_count > 0 else "📮 Media Requests"
        keyboard.append([InlineKeyboardButton(admin_media_req_button_text,
                                              callback_data=CallbackData.CMD_ADMIN_REQUESTS_MENU.value)])

        radarr_sonarr_controls_row = []
        if app_config_holder.is_radarr_enabled():
            radarr_sonarr_controls_row.append(InlineKeyboardButton("🎬 Radarr Controls",
                                                                   callback_data=CallbackData.CMD_RADARR_CONTROLS.value))
        if app_config_holder.is_sonarr_enabled():
            radarr_sonarr_controls_row.append(InlineKeyboardButton("🎞️ Sonarr Controls",
                                                                   callback_data=CallbackData.CMD_SONARR_CONTROLS.value))
        if radarr_sonarr_controls_row:
            keyboard.append(radarr_sonarr_controls_row)

        plex_pc_controls_row = []
        if app_config_holder.is_plex_enabled():

            plex_pc_controls_row.append(InlineKeyboardButton("🌐 Plex Controls",
                                                             callback_data=CallbackData.CMD_PLEX_CONTROLS.value))
        if app_config_holder.is_pc_control_enabled():
            plex_pc_controls_row.append(InlineKeyboardButton("🖥️ PC Control",
                                                             callback_data=CallbackData.CMD_PC_CONTROL_ROOT.value))
        if plex_pc_controls_row:

            if len(plex_pc_controls_row) > 3:
                keyboard.append(plex_pc_controls_row[:2])
                keyboard.append(plex_pc_controls_row[2:])
            else:
                keyboard.append(plex_pc_controls_row)

        if is_primary_admin:
            keyboard.append([InlineKeyboardButton("🚀 Launchers Menu",
                                                  callback_data=CallbackData.CMD_LAUNCHERS_MENU.value)])
            pending_access_req_count = get_pending_access_request_count()
            manage_users_button_text = f"👑 Manage Users & Requests ({pending_access_req_count}❗️)" if pending_access_req_count > 0 else "👑 Manage Users & Requests"
            keyboard.append([InlineKeyboardButton(manage_users_button_text,
                                                  callback_data=CallbackData.CMD_ADMIN_MANAGE_USERS_MENU.value)])

    elif is_unknown_user:
        keyboard.append([InlineKeyboardButton("🚪 Request Access",
                                              callback_data=CallbackData.CMD_REQUEST_ACCESS.value)])

    if is_primary_admin:
        keyboard.append([InlineKeyboardButton("⚙️ Bot Settings",
                        callback_data=CallbackData.CMD_SETTINGS.value)])

    if not keyboard:
        if is_primary_admin:
            keyboard.append([InlineKeyboardButton(
                "⚙️ Bot Settings", callback_data=CallbackData.CMD_SETTINGS.value)])

        no_features_text_parts = ["\n" + escape_md_v2(separator_line)]
        if is_unknown_user:
            no_features_text_parts.append(escape_md_v2(
                "Use the button above to request access."))
        elif not is_primary_admin and not is_standard_user and not is_general_admin:
            no_features_text_parts.append(escape_md_v2(
                "No options currently available for your access level."))
        else:
            no_features_text_parts.append(
                escape_md_v2("No features currently available for your role." if not is_primary_admin else
                             "No features currently enabled. Please check settings via the /settings command.")
            )

        if not (is_unknown_user and len(keyboard) == 1 and keyboard[0][0].callback_data == CallbackData.CMD_REQUEST_ACCESS.value):
            dynamic_menu_text += "\n" + "\n".join(no_features_text_parts)

    reply_markup = InlineKeyboardMarkup(keyboard)
    return dynamic_menu_text, reply_markup
