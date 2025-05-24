import logging
import os
import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


import src.app.app_config_holder as app_config_holder
from src.app.app_file_utils import get_startup_time_file_path
from src.config.config_definitions import CallbackData
from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)


def build_main_menu_content(version: str):
    plex_status_emoji = "🔘"
    if app_config_holder.is_plex_enabled():
        plex_status_emoji = "✅" if app_config_holder.get_plex_url(
        ) and app_config_holder.get_plex_token() else "⚠️"

    radarr_status_emoji = "🔘"
    if app_config_holder.is_radarr_enabled():
        radarr_status_emoji = "✅" if app_config_holder.get_radarr_base_api_url(
        ) and app_config_holder.get_radarr_api_key() else "⚠️"

    sonarr_status_emoji = "🔘"
    if app_config_holder.is_sonarr_enabled():
        sonarr_status_emoji = "✅" if app_config_holder.get_sonarr_base_api_url(
        ) and app_config_holder.get_sonarr_api_key() else "⚠️"

    abdm_status_emoji = "🔘"
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
        logger.warning(f"Startup time file not found: {startup_time_file}")
        formatted_startup_time = "Not available"

    escaped_version = escape_md_v2(version)
    escaped_startup_time = escape_md_v2(formatted_startup_time)

    dynamic_menu_text = (
        f"Media Catalog Telegram Bot \\(v{escaped_version}\\)\n"
        f"\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\n"
        f"Plex: {plex_status_emoji} \\| ABDM: {abdm_status_emoji}\n"
        f"Sonarr: {sonarr_status_emoji} \\| Radarr: {radarr_status_emoji}\n"
        f"Up Since: {escaped_startup_time}"
    )

    keyboard = []

    if app_config_holder.is_radarr_enabled():
        keyboard.append([InlineKeyboardButton("➕ Add Movie",
                        callback_data=CallbackData.CMD_ADD_MOVIE_INIT.value)])

    if app_config_holder.is_sonarr_enabled():
        keyboard.append([InlineKeyboardButton("➕ Add TV Show",
                        callback_data=CallbackData.CMD_ADD_SHOW_INIT.value)])

    if app_config_holder.is_abdm_enabled():
        keyboard.append([InlineKeyboardButton("📥 Add Download",
                                              callback_data=CallbackData.CMD_ADD_DOWNLOAD_INIT.value)])

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

    keyboard.append([InlineKeyboardButton("⚙️ Bot Settings",
                    callback_data=CallbackData.CMD_SETTINGS.value)])

    if not keyboard:
        keyboard.append([InlineKeyboardButton("⚙️ Bot Settings",
                        callback_data=CallbackData.CMD_SETTINGS.value)])
        dynamic_menu_text += "\n\n" + \
            escape_md_v2(
                "No features seem to be enabled. Please check settings.")

    reply_markup = InlineKeyboardMarkup(keyboard)
    return dynamic_menu_text, reply_markup
