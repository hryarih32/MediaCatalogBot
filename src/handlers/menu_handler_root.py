
import logging
import os
from telegram import Update
from telegram.ext import ContextTypes

from src.handlers.abdm.menu_handler_abdm_download import handle_abdm_download_initiation

import src.app.launcher_manager as launcher_manager
from src.bot.bot_initialization import (
    show_or_edit_main_menu,
    send_or_edit_universal_status_message,
)
import src.app.app_config_holder as app_config_holder
import src.app.user_manager as user_manager
from src.handlers.radarr.menu_handler_radarr_add_search import handle_radarr_search_initiation
from src.handlers.sonarr.menu_handler_sonarr_add_search import handle_sonarr_search_initiation
from src.app.app_lifecycle import trigger_config_ui_from_bot
from src.config.config_definitions import SearchType
from src.bot.bot_callback_data import CallbackData

from src.handlers.menu_handler_launchers import display_launchers_menu
from src.services.radarr.bot_radarr_add import get_movie_results_file_path_local as get_radarr_search_file_path
from src.services.sonarr.bot_sonarr_add import get_show_results_file_path_local as get_sonarr_search_file_path

from src.handlers.radarr.menu_handler_radarr_controls import display_radarr_controls_menu
from src.handlers.sonarr.menu_handler_sonarr_controls import display_sonarr_controls_menu
from src.handlers.plex.menu_handler_plex_controls import display_plex_controls_menu
from src.handlers.plex.menu_handler_plex_search_init_results import plex_search_initiate_callback

from src.handlers.pc_control.menu_handler_pc_root import display_pc_control_categories_menu

from src.handlers.user_requests.menu_handler_my_requests import display_my_requests_menu
from src.handlers.admin_requests.menu_handler_admin_requests import display_admin_pending_requests_menu

from src.bot.bot_text_utils import escape_md_v2, escape_md_v1

logger = logging.getLogger(__name__)


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not update.effective_user or not update.effective_chat:
        logger.warning(
            "main_menu_callback invoked without query or effective_user/chat.")
        if query:
            await query.answer("Error processing request.")
        return

    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id

    user_manager.update_username_if_placeholder(
        str(chat_id), update.effective_user)

    user_role = app_config_holder.get_user_role(str(chat_id))
    is_general_admin = (user_role == app_config_holder.ROLE_ADMIN)
    is_primary_admin = app_config_holder.is_primary_admin(str(chat_id))
    is_standard_user = (user_role == app_config_holder.ROLE_STANDARD_USER)

    context.user_data.pop("pending_search_type", None)
    context.user_data.pop("search_prompt_message_id", None)
    context.user_data.pop('radarr_add_flow', None)
    context.user_data.pop('sonarr_add_flow', None)
    context.chat_data.pop('pc_pending_power_action', None)
    context.chat_data.pop('pc_pending_power_time', None)
    context.user_data.pop('pending_plex_search', None)
    context.user_data.pop('pending_download_url', None)

    context.user_data.pop('launcher_selected_subgroup', None)
    plex_keys_to_clear = [
        'plex_search_current_show_rating_key', 'plex_search_current_show_title',
        'plex_search_current_season_number', 'plex_search_current_season_title',
        'plex_search_current_episode_page', 'plex_current_item_details_context',
        'plex_refresh_target_rating_key', 'plex_refresh_target_type',
        'plex_recently_added_current_library_key', 'plex_recently_added_all_items',
        'plex_return_to_menu_id'
    ]
    for key in plex_keys_to_clear:
        context.user_data.pop(key, None)

    primary_admin_only_actions = [
        CallbackData.CMD_ADD_DOWNLOAD_INIT.value,
        CallbackData.CMD_SETTINGS.value,

        CallbackData.CMD_LAUNCHERS_MENU.value,
    ]

    admin_only_actions = [
        CallbackData.CMD_RADARR_CONTROLS.value,
        CallbackData.CMD_SONARR_CONTROLS.value,
        CallbackData.CMD_PLEX_CONTROLS.value,
        CallbackData.CMD_PC_CONTROL_ROOT.value,
        CallbackData.CMD_ADMIN_REQUESTS_MENU.value,

    ]

    standard_user_plus_actions = [
        CallbackData.CMD_ADD_MOVIE_INIT.value,
        CallbackData.CMD_ADD_SHOW_INIT.value,
        CallbackData.CMD_MY_REQUESTS_MENU.value,

        CallbackData.CMD_PLEX_INITIATE_SEARCH.value,

        CallbackData.CMD_HOME_BACK.value,

        CallbackData.RADARR_CANCEL.value,

        CallbackData.SONARR_CANCEL.value,

        CallbackData.CMD_PLEX_MENU_BACK.value
    ]

    if data in primary_admin_only_actions and not is_primary_admin:
        logger.warning(
            f"Callback '{data}' by non-primary admin {chat_id} (Role: {user_role}). Denying.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ This action is exclusively for the primary bot administrator.", parse_mode=None)
        return
    elif data in admin_only_actions and not is_general_admin:
        logger.warning(
            f"Callback '{data}' by non-admin user {chat_id} (Role: {user_role}). Denying.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied. This action is for administrators.", parse_mode=None)
        return

    if data == CallbackData.CMD_RADARR_CONTROLS.value:
        await display_radarr_controls_menu(update, context)
    elif data == CallbackData.CMD_SONARR_CONTROLS.value:
        await display_sonarr_controls_menu(update, context)
    elif data == CallbackData.CMD_PLEX_CONTROLS.value:
        await display_plex_controls_menu(update, context)
    elif data == CallbackData.CMD_PC_CONTROL_ROOT.value:
        if app_config_holder.is_pc_control_enabled():
            await display_pc_control_categories_menu(update, context)
        else:
            await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ PC Controls are currently disabled.", parse_mode=None)
            await show_or_edit_main_menu(str(chat_id), context)

    elif data == CallbackData.CMD_ADD_MOVIE_INIT.value:
        if not app_config_holder.is_radarr_enabled():
            await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Radarr API features are disabled.", parse_mode=None)
            await show_or_edit_main_menu(str(chat_id), context)
            return
        context.user_data["pending_search_type"] = SearchType.MOVIE.value
        prompt_action_text = "add" if is_general_admin else "request"
        prompt_msg_id = await send_or_edit_universal_status_message(context.bot, chat_id, f"🎬 Enter the movie name to {prompt_action_text}:", parse_mode=None)
        if prompt_msg_id:
            context.user_data["search_prompt_message_id"] = prompt_msg_id
        else:
            await show_or_edit_main_menu(str(chat_id), context)

    elif data == CallbackData.CMD_ADD_SHOW_INIT.value:
        if not app_config_holder.is_sonarr_enabled():
            await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Sonarr API features are disabled.", parse_mode=None)
            await show_or_edit_main_menu(str(chat_id), context)
            return
        context.user_data["pending_search_type"] = SearchType.TV.value
        prompt_action_text = "add" if is_general_admin else "request"

        prompt_msg_id = await send_or_edit_universal_status_message(context.bot, chat_id, f"🎞️ Enter the TV show name to {prompt_action_text}:", parse_mode=None)
        if prompt_msg_id:
            context.user_data["search_prompt_message_id"] = prompt_msg_id
        else:
            await show_or_edit_main_menu(str(chat_id), context)

    elif data == CallbackData.CMD_PLEX_INITIATE_SEARCH.value:

        await plex_search_initiate_callback(update, context)

    elif data == CallbackData.CMD_ADD_DOWNLOAD_INIT.value:
        if not app_config_holder.is_abdm_enabled():
            await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ AB Download Manager integration is disabled.", parse_mode=None)
            await show_or_edit_main_menu(str(chat_id), context)
            return
        context.user_data["pending_download_url"] = True
        prompt_msg_id = await send_or_edit_universal_status_message(context.bot, chat_id, "🔗 Enter the URL for the download:", parse_mode=None)
        if prompt_msg_id:
            context.user_data["search_prompt_message_id"] = prompt_msg_id
        else:
            await show_or_edit_main_menu(str(chat_id), context)

    elif data == CallbackData.CMD_SETTINGS.value:
        logger.info(
            f"Settings command triggered by callback from primary admin {chat_id}")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚙️ Opening settings panel...", parse_mode=None)
        await trigger_config_ui_from_bot(context.application)

    elif data == CallbackData.CMD_LAUNCHERS_MENU.value:
        await display_launchers_menu(update, context)

    elif data == CallbackData.CMD_MY_REQUESTS_MENU.value:
        await display_my_requests_menu(update, context)
    elif data == CallbackData.CMD_ADMIN_REQUESTS_MENU.value:
        await display_admin_pending_requests_menu(update, context, page=1)

    elif data == CallbackData.CMD_HOME_BACK.value:
        logger.info(f"Back to home action from chat ID {chat_id}")
        await show_or_edit_main_menu(str(chat_id), context, force_send_new=False)
        await send_or_edit_universal_status_message(context.bot, chat_id, "⬅️ Returned to main menu.", parse_mode=None, force_send_new=False)

    elif data == CallbackData.RADARR_CANCEL.value or data == CallbackData.SONARR_CANCEL.value:

        results_file_to_clean = get_radarr_search_file_path(
        ) if data == CallbackData.RADARR_CANCEL.value else get_sonarr_search_file_path()
        if os.path.exists(results_file_to_clean):
            try:
                os.remove(results_file_to_clean)
                logger.info(
                    f"Cleaned search results on cancel: {results_file_to_clean}")
            except OSError as e:
                logger.warning(f"Could not remove results on cancel: {e}")
        await show_or_edit_main_menu(str(chat_id), context, force_send_new=False)
        await send_or_edit_universal_status_message(context.bot, chat_id, "✅ Add/Request process cancelled.", parse_mode=None, force_send_new=False)

    elif data == CallbackData.CMD_PLEX_MENU_BACK.value:
        await display_plex_controls_menu(update, context)

    else:
        logger.warning(
            f"Unhandled callback data in main_menu_callback: {data} from chat ID {chat_id}. Reshowing main menu.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "🤔 Unrecognized command. Displaying main menu.", parse_mode=None)
        await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)


async def handle_pending_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text or not update.effective_user or not update.effective_chat:
        logger.warning(
            "handle_pending_search invoked without necessary update components.")
        return

    chat_id = update.effective_chat.id
    user_manager.update_username_if_placeholder(
        str(chat_id), update.effective_user)
    user_role = app_config_holder.get_user_role(
        str(chat_id))

    query_text_raw = update.message.text.strip()
    user_query_message_id = update.message.message_id
    search_prompt_message_id = context.user_data.pop(
        "search_prompt_message_id", None)

    try:
        if search_prompt_message_id:
            await context.bot.delete_message(chat_id=chat_id, message_id=search_prompt_message_id)
        await context.bot.delete_message(chat_id=chat_id, message_id=user_query_message_id)
    except Exception as e:
        logger.warning(
            f"Could not delete user's query or prompt message for chat {chat_id}: {e}")

    if context.user_data.pop("pending_download_url", None):
        if not app_config_holder.is_primary_admin(str(chat_id)):
            logger.warning(
                f"ABDM download text input by non-primary admin {chat_id}. Denying.")
            await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ This feature is available only to the primary bot administrator.", parse_mode=None)
            return
        if app_config_holder.is_abdm_enabled():
            await handle_abdm_download_initiation(update, context, query_text_raw, chat_id)
        else:
            await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2("⚠️ Cannot add download: AB Download Manager integration is disabled."), parse_mode="MarkdownV2")
        return

    elif "pending_search_type" in context.user_data:
        search_type_value = context.user_data.pop("pending_search_type")
        search_type = SearchType(search_type_value)
        search_service_name_raw = "Radarr" if search_type == SearchType.MOVIE else "Sonarr"

        if search_type == SearchType.MOVIE and app_config_holder.is_radarr_enabled():
            await handle_radarr_search_initiation(update, context, query_text_raw, chat_id)
        elif search_type == SearchType.TV and app_config_holder.is_sonarr_enabled():
            await handle_sonarr_search_initiation(update, context, query_text_raw, chat_id)
        else:
            await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(f"⚠️ Cannot perform search: {search_service_name_raw} features are disabled."), parse_mode="MarkdownV2")
            await show_or_edit_main_menu(str(chat_id), context)
        return

    elif context.user_data.pop('pending_plex_search', None):
        if user_role not in [app_config_holder.ROLE_ADMIN, app_config_holder.ROLE_STANDARD_USER]:
            logger.warning(
                f"Plex search attempt by unauthorized role {user_role} for chat_id {chat_id}. Ignoring.")
            await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied. You do not have permission for Plex search.", parse_mode=None)
            return

        from src.services.plex.bot_plex_search import search_plex_media
        from src.handlers.plex.menu_handler_plex_search_init_results import display_plex_search_results

        if app_config_holder.is_plex_enabled():
            await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(f"⏳ Searching Plex for: \"{query_text_raw}\"\\.\\.\\."), parse_mode="MarkdownV2")
            search_results_data = search_plex_media(query_text_raw)

            await display_plex_search_results(update, context, search_results_data)
        else:
            await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Plex features are disabled.", parse_mode=None)
            await show_or_edit_main_menu(str(chat_id), context)
        return

    logger.debug(
        f"Received unprompted text message from user {chat_id}: '{query_text_raw}'. No specific pending action found.")
