
import logging
from telegram import Update
from telegram.ext import ContextTypes

import src.app.app_config_holder as app_config_holder
from src.bot.bot_initialization import send_or_edit_universal_status_message, show_or_edit_main_menu
from src.bot.bot_callback_data import CallbackData
from src.services.sonarr.bot_sonarr_manage import (
    rescan_all_series,
    refresh_all_series,
    rename_all_series_files,
    trigger_missing_episode_search,
    trigger_episode_search,
    remove_queue_item as sonarr_remove_queue_item
)

from .menu_handler_library_management_sonarr import (
    display_sonarr_queue_menu,
    display_sonarr_wanted_episodes_menu
)
from .menu_handler_sonarr_tools import display_sonarr_library_maintenance_menu
from src.handlers.shared.menu_handler_library_management_actions_shared import display_queue_item_action_menu
from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)


async def handle_sonarr_library_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_role = app_config_holder.get_user_role(str(chat_id))

    await query.answer()

    if user_role != app_config_holder.ROLE_ADMIN:
        logger.warning(
            f"Sonarr library action attempt by non-admin {chat_id} (Role: {user_role}).")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied. Sonarr library actions are for administrators.", parse_mode=None)
        return

    if not app_config_holder.is_sonarr_enabled():
        logger.info(
            f"Sonarr library action by {chat_id}, but Sonarr feature is disabled.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Sonarr API features are disabled.", parse_mode=None)
        await show_or_edit_main_menu(str(chat_id), context)
        return

    callback_data_str = query.data
    result_message_raw = "An unknown error occurred with Sonarr action."
    current_page_sonarr_queue = context.user_data.get(
        'sonarr_queue_current_page', 1)
    current_page_sonarr_wanted = context.user_data.get(
        'sonarr_wanted_current_page', 1)

    action_message_raw = None

    if callback_data_str == CallbackData.CMD_SONARR_SCAN_FILES.value:
        action_message_raw = "⏳ Initiating Sonarr disk rescan for all series..."
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(action_message_raw), parse_mode="MarkdownV2")
        result_message_raw = rescan_all_series()
        await display_sonarr_library_maintenance_menu(update, context)
    elif callback_data_str == CallbackData.CMD_SONARR_UPDATE_METADATA.value:
        action_message_raw = "⏳ Initiating Sonarr metadata refresh for all series..."
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(action_message_raw), parse_mode="MarkdownV2")
        result_message_raw = refresh_all_series()
        await display_sonarr_library_maintenance_menu(update, context)
    elif callback_data_str == CallbackData.CMD_SONARR_RENAME_FILES.value:
        action_message_raw = "⏳ Initiating Sonarr series/episode file renaming..."
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(action_message_raw), parse_mode="MarkdownV2")
        result_message_raw = rename_all_series_files()
        await display_sonarr_library_maintenance_menu(update, context)
    elif callback_data_str == CallbackData.CMD_SONARR_SEARCH_WANTED_ALL_NOW.value:
        action_message_raw = "⏳ Initiating Sonarr search for all wanted/missing episodes..."
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(action_message_raw), parse_mode="MarkdownV2")
        result_message_raw = trigger_missing_episode_search()

        await display_sonarr_wanted_episodes_menu(update, context, page=current_page_sonarr_wanted)
    elif callback_data_str.startswith(CallbackData.CMD_SONARR_WANTED_SEARCH_EPISODE_PREFIX.value):
        episode_id_to_search = callback_data_str.replace(
            CallbackData.CMD_SONARR_WANTED_SEARCH_EPISODE_PREFIX.value, "")
        if episode_id_to_search.isdigit():
            action_message_raw = f"⏳ Initiating Sonarr search for episode ID {episode_id_to_search}..."
            await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(action_message_raw), parse_mode="MarkdownV2")
            result_message_raw = trigger_episode_search(
                episode_ids=[int(episode_id_to_search)])
        else:
            result_message_raw = "⚠️ Invalid episode ID for search."

        await display_sonarr_wanted_episodes_menu(update, context, page=current_page_sonarr_wanted)
    elif callback_data_str.startswith(CallbackData.CMD_SONARR_QUEUE_ITEM_ACTIONS_MENU_PREFIX.value):
        payload = callback_data_str.replace(
            CallbackData.CMD_SONARR_QUEUE_ITEM_ACTIONS_MENU_PREFIX.value, "")
        parts = payload.split("_", 1)
        queue_item_id = parts[0]

        media_search_id = parts[1] if len(parts) > 1 else "0"

        item_title_from_button = "Selected Sonarr Item"
        if query.message and query.message.reply_markup:
            for row in query.message.reply_markup.inline_keyboard:
                for button in row:
                    if button.callback_data == callback_data_str:
                        item_title_from_button = button.text
                        break
                if item_title_from_button != "Selected Sonarr Item":
                    break

        context.user_data['current_queue_action_item'] = {
            'service_name': 'Sonarr', 'item_id': queue_item_id,
            'search_id': media_search_id, 'item_title': item_title_from_button
        }
        await display_queue_item_action_menu(update, context, "Sonarr", queue_item_id, item_title_from_button, media_search_id)
        return
    elif callback_data_str.startswith(CallbackData.CMD_SONARR_QUEUE_ITEM_REMOVE_NO_BLOCKLIST_PREFIX.value):
        action_item_data = context.user_data.get(
            'current_queue_action_item', {})
        queue_item_id = action_item_data.get('item_id', callback_data_str.replace(
            CallbackData.CMD_SONARR_QUEUE_ITEM_REMOVE_NO_BLOCKLIST_PREFIX.value, ""))

        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(f"⏳ Removing item {queue_item_id} (no blocklist)..."), parse_mode="MarkdownV2")
        result_message_raw = sonarr_remove_queue_item(
            queue_item_id, blocklist=False)
        if context.user_data.get('current_queue_action_item'):
            del context.user_data['current_queue_action_item']
        await display_sonarr_queue_menu(update, context, page=current_page_sonarr_queue)
    elif callback_data_str.startswith(CallbackData.CMD_SONARR_QUEUE_ITEM_BLOCKLIST_ONLY_PREFIX.value):
        action_item_data = context.user_data.get(
            'current_queue_action_item', {})
        queue_item_id = action_item_data.get('item_id', callback_data_str.replace(
            CallbackData.CMD_SONARR_QUEUE_ITEM_BLOCKLIST_ONLY_PREFIX.value, ""))

        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(f"⏳ Blocklisting item {queue_item_id} (no search)..."), parse_mode="MarkdownV2")
        result_message_raw = sonarr_remove_queue_item(
            queue_item_id, blocklist=True)

        if context.user_data.get('current_queue_action_item'):
            del context.user_data['current_queue_action_item']
        await display_sonarr_queue_menu(update, context, page=current_page_sonarr_queue)
    elif callback_data_str.startswith(CallbackData.CMD_SONARR_QUEUE_ITEM_BLOCKLIST_SEARCH_PREFIX.value):
        action_item_data = context.user_data.get(
            'current_queue_action_item', {})
        queue_item_id = action_item_data.get('item_id', callback_data_str.replace(
            CallbackData.CMD_SONARR_QUEUE_ITEM_BLOCKLIST_SEARCH_PREFIX.value, ""))
        media_search_id = action_item_data.get('search_id', "0")

        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(f"⏳ Blocklisting item {queue_item_id} and searching again..."), parse_mode="MarkdownV2")
        result_message_raw = sonarr_remove_queue_item(
            queue_item_id, blocklist=True)

        if "✅" in result_message_raw and media_search_id != "0":
            try:
                sonarr_episode_id_for_search = int(media_search_id)
                search_msg_raw = trigger_episode_search(
                    episode_ids=[sonarr_episode_id_for_search])
                result_message_raw += f"\n{search_msg_raw}"
            except ValueError:
                result_message_raw += "\n⚠️ Could not trigger search: Invalid Episode ID for search."
        elif media_search_id == "0":
            result_message_raw += "\n⚠️ Could not trigger search: Episode ID not available."

        if context.user_data.get('current_queue_action_item'):
            del context.user_data['current_queue_action_item']
        await display_sonarr_queue_menu(update, context, page=current_page_sonarr_queue)
    elif callback_data_str == CallbackData.CMD_SONARR_QUEUE_BACK_TO_LIST.value:
        if context.user_data.get('current_queue_action_item'):
            del context.user_data['current_queue_action_item']
        await display_sonarr_queue_menu(update, context, page=current_page_sonarr_queue)
        return
    else:
        logger.warning(f"Unhandled Sonarr library action: {callback_data_str}")
        result_message_raw = "⚠️ Unrecognized Sonarr library management action."
        await show_or_edit_main_menu(str(chat_id), context)

    if action_message_raw is not None or \
       callback_data_str.startswith(CallbackData.CMD_SONARR_QUEUE_ITEM_REMOVE_NO_BLOCKLIST_PREFIX.value) or \
       callback_data_str.startswith(CallbackData.CMD_SONARR_QUEUE_ITEM_BLOCKLIST_ONLY_PREFIX.value) or \
       callback_data_str.startswith(CallbackData.CMD_SONARR_QUEUE_ITEM_BLOCKLIST_SEARCH_PREFIX.value) or \
       result_message_raw == "⚠️ Unrecognized Sonarr library management action.":
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(result_message_raw), parse_mode="MarkdownV2")
