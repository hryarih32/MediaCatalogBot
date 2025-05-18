import logging
from telegram import Update
from telegram.ext import ContextTypes

import src.app.app_config_holder as app_config_holder
from src.bot.bot_initialization import send_or_edit_universal_status_message, show_or_edit_main_menu
from src.config.config_definitions import CallbackData
from src.services.radarr.bot_radarr_manage import (
    rescan_all_movies,
    refresh_all_movies,
    rename_all_movie_files,
    remove_queue_item as radarr_remove_queue_item,
    trigger_movie_search_for_id as radarr_trigger_movie_search
)


from .menu_handler_library_management_radarr import display_radarr_queue_menu

from .menu_handler_radarr_tools import display_radarr_library_maintenance_menu
from src.handlers.shared.menu_handler_library_management_actions_shared import display_queue_item_action_menu
from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)


async def handle_radarr_library_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    callback_data_str = query.data
    result_message_raw = "An unknown error occurred with Radarr action."
    current_page_radarr = context.user_data.get('radarr_queue_current_page', 1)

    if callback_data_str == CallbackData.CMD_RADARR_SCAN_FILES.value:
        action_message_raw = "⏳ Initiating Radarr disk rescan for all movies..."
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(action_message_raw), parse_mode="MarkdownV2")
        result_message_raw = rescan_all_movies()

        await display_radarr_library_maintenance_menu(update, context)
    elif callback_data_str == CallbackData.CMD_RADARR_UPDATE_METADATA.value:
        action_message_raw = "⏳ Initiating Radarr metadata refresh for all movies..."
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(action_message_raw), parse_mode="MarkdownV2")
        result_message_raw = refresh_all_movies()

        await display_radarr_library_maintenance_menu(update, context)
    elif callback_data_str == CallbackData.CMD_RADARR_RENAME_FILES.value:
        action_message_raw = "⏳ Initiating Radarr movie file renaming..."
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(action_message_raw), parse_mode="MarkdownV2")
        result_message_raw = rename_all_movie_files()

        await display_radarr_library_maintenance_menu(update, context)
    elif callback_data_str.startswith(CallbackData.CMD_RADARR_QUEUE_ITEM_ACTIONS_MENU_PREFIX.value):
        payload = callback_data_str.replace(
            CallbackData.CMD_RADARR_QUEUE_ITEM_ACTIONS_MENU_PREFIX.value, "")
        parts = payload.split("_", 1)
        queue_item_id = parts[0]
        media_search_id = parts[1] if len(parts) > 1 else "0"
        item_title_from_button = "Selected Radarr Item"
        if query.message and query.message.reply_markup:
            for row in query.message.reply_markup.inline_keyboard:
                for button in row:
                    if button.callback_data == callback_data_str:
                        item_title_from_button = button.text
                        break
                if item_title_from_button != "Selected Radarr Item":
                    break
        context.user_data['current_queue_action_item'] = {
            'service_name': 'Radarr', 'item_id': queue_item_id, 'search_id': media_search_id, 'item_title': item_title_from_button}
        await display_queue_item_action_menu(update, context, "Radarr", queue_item_id, item_title_from_button, media_search_id)
        return
    elif callback_data_str.startswith(CallbackData.CMD_RADARR_QUEUE_ITEM_REMOVE_NO_BLOCKLIST_PREFIX.value):
        action_item_data = context.user_data.get(
            'current_queue_action_item', {})
        queue_item_id = action_item_data.get('item_id', callback_data_str.replace(
            CallbackData.CMD_RADARR_QUEUE_ITEM_REMOVE_NO_BLOCKLIST_PREFIX.value, ""))
        result_message_raw = radarr_remove_queue_item(
            queue_item_id, blocklist=False)
        if context.user_data.get('current_queue_action_item'):
            del context.user_data['current_queue_action_item']
        await display_radarr_queue_menu(update, context, page=current_page_radarr)
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(result_message_raw), parse_mode="MarkdownV2")
        return
    elif callback_data_str.startswith(CallbackData.CMD_RADARR_QUEUE_ITEM_BLOCKLIST_SEARCH_PREFIX.value):
        action_item_data = context.user_data.get(
            'current_queue_action_item', {})
        queue_item_id = action_item_data.get('item_id', callback_data_str.replace(
            CallbackData.CMD_RADARR_QUEUE_ITEM_BLOCKLIST_SEARCH_PREFIX.value, ""))
        media_search_id = action_item_data.get('search_id', "0")
        result_message_raw = radarr_remove_queue_item(
            queue_item_id, blocklist=True)
        if "✅" in result_message_raw and media_search_id != "0":
            try:
                search_msg_raw = radarr_trigger_movie_search(
                    int(media_search_id))
                result_message_raw += f"\n{search_msg_raw}"
            except ValueError:
                result_message_raw += "\n⚠️ Could not trigger search: Invalid Movie ID for search."
        elif media_search_id == "0":
            result_message_raw += "\n⚠️ Could not trigger search: Movie ID not available."
        if context.user_data.get('current_queue_action_item'):
            del context.user_data['current_queue_action_item']
        await display_radarr_queue_menu(update, context, page=current_page_radarr)
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(result_message_raw), parse_mode="MarkdownV2")
        return
    elif callback_data_str == CallbackData.CMD_RADARR_QUEUE_BACK_TO_LIST.value:
        if context.user_data.get('current_queue_action_item'):
            del context.user_data['current_queue_action_item']

        await display_radarr_queue_menu(update, context, page=current_page_radarr)
        return
    else:
        logger.warning(f"Unhandled Radarr library action: {callback_data_str}")
        result_message_raw = "⚠️ Unrecognized Radarr library management action."
        admin_chat_id_str = app_config_holder.get_chat_id_str()
        if admin_chat_id_str:
            await show_or_edit_main_menu(admin_chat_id_str, context)

    if callback_data_str in [CallbackData.CMD_RADARR_SCAN_FILES.value, CallbackData.CMD_RADARR_UPDATE_METADATA.value, CallbackData.CMD_RADARR_RENAME_FILES.value]:
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(result_message_raw), parse_mode="MarkdownV2")
    elif result_message_raw == "⚠️ Unrecognized Radarr library management action.":
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(result_message_raw), parse_mode="MarkdownV2")
