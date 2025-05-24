import logging
import os
import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import src.app.app_config_holder as app_config_holder
from src.app.app_file_utils import get_startup_time_file_path, load_requests_data
from src.bot.bot_callback_data import CallbackData
from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)


def get_pending_request_count() -> int:
    """Counts the number of requests with 'pending' status."""
    all_requests = load_requests_data()
    pending_count = sum(
        1 for req in all_requests if req.get("status") == "pending")
    return pending_count


def build_main_menu_content(version: str, user_role: str, chat_id_str: str):
    is_primary_admin = app_config_holder.is_primary_admin(chat_id_str)
    is_general_admin = user_role == app_config_holder.ROLE_ADMIN
    is_standard_user = user_role == app_config_holder.ROLE_STANDARD_USER

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
    startup_time_file = get_startup_time_file_path()
    if os.path.exists(startup_time_file):
        try:
            with open(startup_time_file, "r") as f:
                iso_timestamp = f.read().strip()
                startup_time_obj = datetime.datetime.fromisoformat(
                    iso_timestamp)
                formatted_startup_time = startup_time_obj.strftime(
                    "%Y-%m-%d %H:%M")
        except Exception as e:
            logger.warning(
                f"Could not read or parse startup time from {startup_time_file}: {e}")
            formatted_startup_time = "Error reading time"
    else:
        formatted_startup_time = "Not available"

    escaped_version = escape_md_v2(version)
    escaped_startup_time = escape_md_v2(formatted_startup_time)

    separator_line = "—" * 30

    header_parts = [f"🎬 Media Bot \\(v{escaped_version}\\)"]

    if is_general_admin or is_primary_admin:
        header_parts.append(escape_md_v2(separator_line))
        header_parts.append(
            f"Plex: {plex_status_emoji} Sonarr: {sonarr_status_emoji} Radarr: {radarr_status_emoji} ABDM: {abdm_status_emoji}"
        )
        header_parts.append(f"Up Since: {escaped_startup_time}")
    else:
        header_parts.append(escape_md_v2(separator_line))
        header_parts.append("Welcome\\! Select an option below\\.")

    dynamic_menu_text = "\n".join(header_parts)

    keyboard = []

    actual_add_movie_text = "➕ Add Movie (Admin)" if is_general_admin else "➕ Request Movie"
    actual_add_show_text = "➕ Add TV Show (Admin)" if is_general_admin else "➕ Request TV Show"

    if app_config_holder.is_radarr_enabled():
        if is_general_admin:
            keyboard.append([InlineKeyboardButton(actual_add_movie_text,
                                                  callback_data=CallbackData.CMD_ADD_MOVIE_INIT.value)])
        elif is_standard_user:
            keyboard.append([InlineKeyboardButton(actual_add_movie_text,
                                                  callback_data=CallbackData.CMD_ADD_MOVIE_INIT.value)])

    if app_config_holder.is_sonarr_enabled():
        if is_general_admin:
            keyboard.append([InlineKeyboardButton(actual_add_show_text,
                            callback_data=CallbackData.CMD_ADD_SHOW_INIT.value)])
        elif is_standard_user:
            keyboard.append([InlineKeyboardButton(actual_add_show_text,
                            callback_data=CallbackData.CMD_ADD_SHOW_INIT.value)])

    if is_primary_admin and app_config_holder.is_abdm_enabled():
        keyboard.append([InlineKeyboardButton("📥 Add Download (ABDM)",
                                              callback_data=CallbackData.CMD_ADD_DOWNLOAD_INIT.value)])

    if is_standard_user and not is_general_admin:
        keyboard.append([InlineKeyboardButton("📋 My Requests",
                                              callback_data=CallbackData.CMD_MY_REQUESTS_MENU.value)])

    if is_general_admin:
        pending_count = get_pending_request_count()
        admin_requests_button_text = f"📮 Admin Requests ({pending_count}❗️)" if pending_count > 0 else "📮 Admin Requests"
        keyboard.append([InlineKeyboardButton(admin_requests_button_text,
                                              callback_data=CallbackData.CMD_ADMIN_REQUESTS_MENU.value)])

    if is_general_admin:
        if app_config_holder.is_radarr_enabled():
            keyboard.append([InlineKeyboardButton("🎬 Radarr Controls",
                            callback_data=CallbackData.CMD_RADARR_CONTROLS.value)])
        if app_config_holder.is_sonarr_enabled():
            keyboard.append([InlineKeyboardButton("🎞️ Sonarr Controls",
                            callback_data=CallbackData.CMD_SONARR_CONTROLS.value)])
        if app_config_holder.is_plex_enabled():
            keyboard.append([InlineKeyboardButton("🌐 Plex Controls",
                            callback_data=CallbackData.CMD_PLEX_CONTROLS.value)])

        any_launcher_enabled = False
        launcher_prefixes = ["PLEX", "SONARR",
                             "RADARR", "PROWLARR", "TORRENT", "ABDM"]
        for prefix in launcher_prefixes:
            if app_config_holder.is_service_launcher_enabled(prefix):
                any_launcher_enabled = True
                break
        if not any_launcher_enabled:
            for i in range(1, 4):
                if app_config_holder.is_script_enabled(i):
                    any_launcher_enabled = True
                    break
        if any_launcher_enabled:
            keyboard.append([InlineKeyboardButton("🚀 Launchers & Scripts",
                            callback_data=CallbackData.CMD_LAUNCHERS_MENU.value)])

        if app_config_holder.is_pc_control_enabled():
            keyboard.append([InlineKeyboardButton("🖥️ PC Control",
                                                  callback_data=CallbackData.CMD_PC_CONTROL_ROOT.value)])

    if is_primary_admin:
        keyboard.append([InlineKeyboardButton("⚙️ Bot Settings",
                        callback_data=CallbackData.CMD_SETTINGS.value)])

    if not keyboard:
        if is_primary_admin:
            keyboard.append([InlineKeyboardButton("⚙️ Bot Settings",
                                                  callback_data=CallbackData.CMD_SETTINGS.value)])
        no_features_text_parts = ["\n" + escape_md_v2(separator_line)]
        no_features_text_parts.append(
            escape_md_v2("No features available for your role." if not is_primary_admin else
                         "No features enabled. Please check settings.")
        )
        dynamic_menu_text += "\n".join(no_features_text_parts)

    elif not is_primary_admin and not is_standard_user and not is_general_admin:
        dynamic_menu_text += "\n" + escape_md_v2(separator_line) + "\n" + escape_md_v2(
            "No options available for your current access level.")

    reply_markup = InlineKeyboardMarkup(keyboard)
    return dynamic_menu_text, reply_markup
