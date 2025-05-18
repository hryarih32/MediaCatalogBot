import logging
import os
from telegram import Update
from telegram.ext import ContextTypes

from src.app import app_script_handler as script_handler
from src.bot.bot_initialization import (
    show_or_edit_main_menu,
    send_or_edit_universal_status_message,
)
import src.app.app_config_holder as app_config_holder
from src.handlers.radarr.menu_handler_radarr_add_search import handle_radarr_search_initiation
from src.handlers.sonarr.menu_handler_sonarr_add_search import handle_sonarr_search_initiation
from src.app.app_lifecycle import trigger_config_ui_from_bot
from src.config.config_definitions import CallbackData, SearchType


from src.handlers.menu_handler_launchers import display_launchers_menu
from src.services.radarr.bot_radarr_add import get_movie_results_file_path_local as get_radarr_search_file_path
from src.services.sonarr.bot_sonarr_add import get_show_results_file_path_local as get_sonarr_search_file_path


from src.handlers.radarr.menu_handler_radarr_controls import display_radarr_controls_menu
from src.handlers.sonarr.menu_handler_sonarr_controls import display_sonarr_controls_menu
from src.handlers.plex.menu_handler_plex_controls import display_plex_controls_menu

from src.handlers.pc_control.menu_handler_pc_root import display_pc_control_categories_menu


from src.bot.bot_text_utils import escape_md_v2, escape_md_v1


logger = logging.getLogger(__name__)


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id
    admin_chat_id_str = app_config_holder.get_chat_id_str()

    if not admin_chat_id_str:
        logger.error("Admin CHAT_ID not configured in main_menu_callback.")
        if query.message:
            await send_or_edit_universal_status_message(context.bot, chat_id, "🚨 Critical error: Bot admin chat ID missing.", parse_mode=None)
        return
    admin_chat_id_int = int(admin_chat_id_str)
    if chat_id != admin_chat_id_int:
        logger.warning(
            f"Callback received from non-admin chat ID {chat_id}. Ignoring.")
        if query.message:
            await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied.", parse_mode=None)
        return

    context.user_data.pop("pending_search_type", None)
    context.user_data.pop("search_prompt_message_id", None)
    context.user_data.pop('radarr_add_flow', None)
    context.user_data.pop('sonarr_add_flow', None)
    context.chat_data.pop('pc_pending_power_action', None)
    context.chat_data.pop('pc_pending_power_time', None)
    context.user_data.pop('pending_plex_search', None)
    plex_keys_to_clear = ['plex_search_current_show_rating_key', 'plex_search_current_show_title', 'plex_search_current_season_number', 'plex_search_current_season_title', 'plex_search_current_episode_page',
                          'plex_current_item_details_context', 'plex_refresh_target_rating_key', 'plex_refresh_target_type', 'plex_recently_added_current_library_key', 'plex_recently_added_all_items', 'plex_return_to_menu_id']
    for key in plex_keys_to_clear:
        context.user_data.pop(key, None)

    if data == CallbackData.CMD_RADARR_CONTROLS.value:
        await display_radarr_controls_menu(update, context)
        return
    elif data == CallbackData.CMD_SONARR_CONTROLS.value:
        await display_sonarr_controls_menu(update, context)
        return
    elif data == CallbackData.CMD_PLEX_CONTROLS.value:
        await display_plex_controls_menu(update, context)
        return
    elif data == CallbackData.CMD_PC_CONTROL_ROOT.value:
        if app_config_holder.is_pc_control_enabled():
            await display_pc_control_categories_menu(update, context)
        else:
            await send_or_edit_universal_status_message(context.bot, admin_chat_id_int, "ℹ️ PC Controls are currently disabled.", parse_mode=None)
            await show_or_edit_main_menu(admin_chat_id_str, context, force_send_new=True)
        return
    elif data == CallbackData.CMD_ADD_MOVIE_INIT.value:
        if not app_config_holder.is_radarr_enabled():
            await send_or_edit_universal_status_message(context.bot, admin_chat_id_int, "ℹ️ Radarr API features are disabled.", parse_mode=None)
            await show_or_edit_main_menu(admin_chat_id_str, context, force_send_new=True)
            return
        context.user_data["pending_search_type"] = SearchType.MOVIE.value
        prompt_msg_id = await send_or_edit_universal_status_message(context.bot, admin_chat_id_int, "🎬 Enter the movie name to add:", parse_mode=None)
        if prompt_msg_id:
            context.user_data["search_prompt_message_id"] = prompt_msg_id
        else:
            await send_or_edit_universal_status_message(context.bot, admin_chat_id_int, "⚠️ Error displaying add prompt.", parse_mode=None)
            await show_or_edit_main_menu(admin_chat_id_str, context, force_send_new=True)
        return
    elif data == CallbackData.CMD_ADD_SHOW_INIT.value:
        if not app_config_holder.is_sonarr_enabled():
            await send_or_edit_universal_status_message(context.bot, admin_chat_id_int, "ℹ️ Sonarr API features are disabled.", parse_mode=None)
            await show_or_edit_main_menu(admin_chat_id_str, context, force_send_new=True)
            return
        context.user_data["pending_search_type"] = SearchType.TV.value
        prompt_msg_id = await send_or_edit_universal_status_message(context.bot, admin_chat_id_int, "🎞️ Enter the TV show name to add:", parse_mode=None)
        if prompt_msg_id:
            context.user_data["search_prompt_message_id"] = prompt_msg_id
        else:
            await send_or_edit_universal_status_message(context.bot, admin_chat_id_int, "⚠️ Error displaying add prompt.", parse_mode=None)
            await show_or_edit_main_menu(admin_chat_id_str, context, force_send_new=True)
        return
    elif data == CallbackData.CMD_LAUNCHERS_MENU.value:
        await display_launchers_menu(update, context)
        return
    elif data == CallbackData.CMD_SETTINGS.value:
        logger.info(
            f"Settings command triggered by callback from chat ID {chat_id}")
        await send_or_edit_universal_status_message(context.bot, admin_chat_id_int, "⚙️ Opening settings panel...", parse_mode=None)
        await trigger_config_ui_from_bot(context.application)
        return
    elif data == CallbackData.CMD_HOME_BACK.value:
        logger.info(f"Back to home action from chat ID {chat_id}")
        await show_or_edit_main_menu(admin_chat_id_str, context, force_send_new=False)
        await send_or_edit_universal_status_message(context.bot, admin_chat_id_int, "⬅️ Returned to main menu.", parse_mode=None, force_send_new=False)
        return
    elif data == CallbackData.RADARR_CANCEL.value or data == CallbackData.SONARR_CANCEL.value:
        logger.info(
            f"Add process cancellation for {data} by chat ID {chat_id}")
        if data == CallbackData.RADARR_CANCEL.value:
            radarr_res_file = get_radarr_search_file_path()
            if os.path.exists(radarr_res_file):
                try:
                    os.remove(radarr_res_file)
                    logger.info(
                        f"Cleaned Radarr search results on cancel: {radarr_res_file}")
                except OSError as e:
                    logger.warning(
                        f"Could not remove Radarr results on cancel: {e}")
        elif data == CallbackData.SONARR_CANCEL.value:
            sonarr_res_file = get_sonarr_search_file_path()
            if os.path.exists(sonarr_res_file):
                try:
                    os.remove(sonarr_res_file)
                    logger.info(
                        f"Cleaned Sonarr search results on cancel: {sonarr_res_file}")
                except OSError as e:
                    logger.warning(
                        f"Could not remove Sonarr results on cancel: {e}")
        await show_or_edit_main_menu(admin_chat_id_str, context, force_send_new=False)
        await send_or_edit_universal_status_message(context.bot, admin_chat_id_int, "✅ Add process cancelled. Returned to main menu.", parse_mode=None, force_send_new=False)
        return

    script_identifier_to_run = None
    if data == CallbackData.CMD_SCRIPT_1.value:
        script_identifier_to_run = "SCRIPT_1"
    elif data == CallbackData.CMD_SCRIPT_2.value:
        script_identifier_to_run = "SCRIPT_2"
    elif data == CallbackData.CMD_SCRIPT_3.value:
        script_identifier_to_run = "SCRIPT_3"
    elif data == CallbackData.CMD_LAUNCH_PLEX.value:
        script_identifier_to_run = "PLEX"
    elif data == CallbackData.CMD_LAUNCH_SONARR.value:
        script_identifier_to_run = "SONARR"
    elif data == CallbackData.CMD_LAUNCH_RADARR.value:
        script_identifier_to_run = "RADARR"
    elif data == CallbackData.CMD_LAUNCH_PROWLARR.value:
        script_identifier_to_run = "PROWLARR"
    elif data == CallbackData.CMD_LAUNCH_TORRENT.value:
        script_identifier_to_run = "TORRENT"

    if script_identifier_to_run:
        display_name_raw = ""
        s_num = 0
        if script_identifier_to_run.startswith("SCRIPT_"):
            try:
                s_num = int(script_identifier_to_run.split("_")[1])
            except (IndexError, ValueError):
                pass
            display_name_raw = app_config_holder.get_script_name(
                s_num) or f"Script {s_num}"
        elif script_identifier_to_run in script_handler.SERVICE_LAUNCHER_IDENTIFIERS:
            display_name_raw = app_config_holder.get_service_launcher_name(
                script_identifier_to_run) or f"Launch {script_identifier_to_run.capitalize()}"
        else:
            display_name_raw = f"'{script_identifier_to_run}'"
        await send_or_edit_universal_status_message(context.bot, admin_chat_id_int, escape_md_v2(f"⏳ Attempting to run {display_name_raw}\\.\\.\\."), parse_mode="MarkdownV2")
        status_msg_raw = await script_handler.run_script_by_identifier(script_identifier_to_run)
        await send_or_edit_universal_status_message(context.bot, admin_chat_id_int, escape_md_v2(status_msg_raw), parse_mode="MarkdownV2")
        await display_launchers_menu(update, context)
        return

    logger.warning(
        f"Unhandled callback data in main_menu_callback: {data}. Reshowing main menu.")
    await send_or_edit_universal_status_message(context.bot, admin_chat_id_int, "🤔 Unrecognized command. Displaying main menu.", parse_mode=None)
    await show_or_edit_main_menu(admin_chat_id_str, context, force_send_new=True)


async def handle_pending_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    admin_chat_id_str = app_config_holder.get_chat_id_str()
    chat_id = update.message.chat_id
    if not admin_chat_id_str or str(chat_id) != admin_chat_id_str:
        logger.warning(
            f"Text input for add from non-admin {chat_id}. Ignoring.")
        return
    admin_chat_id_int = int(admin_chat_id_str)
    query_text_raw = update.message.text.strip()
    user_query_message_id = update.message.message_id
    search_prompt_message_id = context.user_data.pop(
        "search_prompt_message_id", None)
    try:
        if search_prompt_message_id:
            await context.bot.delete_message(chat_id=chat_id, message_id=search_prompt_message_id)
        await context.bot.delete_message(chat_id=chat_id, message_id=user_query_message_id)
    except Exception as e:
        logger.warning(f"Could not delete user's query or prompt message: {e}")

    if "pending_search_type" in context.user_data:
        search_type_value = context.user_data.pop("pending_search_type")
        search_type = SearchType(search_type_value)
        search_service_name_raw = "Radarr API" if search_type == SearchType.MOVIE else "Sonarr API"
        if search_type == SearchType.MOVIE and app_config_holder.is_radarr_enabled():
            await handle_radarr_search_initiation(update, context, query_text_raw, admin_chat_id_int)
        elif search_type == SearchType.TV and app_config_holder.is_sonarr_enabled():
            await handle_sonarr_search_initiation(update, context, query_text_raw, admin_chat_id_int)
        else:
            await send_or_edit_universal_status_message(context.bot, admin_chat_id_int, escape_md_v2(f"⚠️ Cannot search: {search_service_name_raw} features are disabled."), parse_mode="MarkdownV2")
            await show_or_edit_main_menu(admin_chat_id_str, context, force_send_new=True)
        return
    elif context.user_data.pop('pending_plex_search', None):

        from src.services.plex.bot_plex_search import search_plex_media
        from src.handlers.plex.menu_handler_plex_search_init_results import display_plex_search_results
        logger.info(f"Plex search initiated with query: '{query_text_raw}'")
        await send_or_edit_universal_status_message(context.bot, admin_chat_id_int, escape_md_v2(f"⏳ Searching Plex for: \"{query_text_raw}\"\\.\\.\\."), parse_mode="MarkdownV2")
        search_results_data = search_plex_media(query_text_raw)
        await display_plex_search_results(update, context, search_results_data)
        return
    logger.debug(
        f"Received unprompted text message from admin: '{query_text_raw}'. No action taken.")
