import logging
import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

import src.app.app_config_holder as app_config_holder
from src.bot.bot_message_persistence import load_menu_message_id
from src.bot.bot_initialization import send_or_edit_universal_status_message
from src.bot.bot_callback_data import CallbackData
from src.services.sonarr.bot_sonarr_manage import get_wanted_missing_episodes, get_sonarr_queue
from src.services.sonarr.bot_sonarr_core import get_all_series_ids_and_titles_cached

from src.handlers.sonarr.menu_handler_sonarr_controls import display_sonarr_controls_menu
from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)

SONARR_WANTED_EPISODES_MENU_TEXT_TEMPLATE_RAW = "🎯 Sonarr - Wanted Episodes (Page {current_page}/{total_pages})"
SONARR_QUEUE_MENU_TEXT_TEMPLATE_RAW = "📥 Sonarr - Download Queue (Page {current_page}/{total_pages})"

DEFAULT_PAGE_SIZE = 5


async def display_sonarr_wanted_episodes_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1) -> None:
    query = update.callback_query
    if query:
        await query.answer()
    chat_id = update.effective_chat.id

    admin_chat_id_str = app_config_holder.get_chat_id_str()
    if not admin_chat_id_str or str(chat_id) != admin_chat_id_str:
        logger.warning(
            f"Sonarr wanted episodes attempt by non-primary admin {chat_id}.")
        return

    is_refresh_call = query and query.data == CallbackData.CMD_SONARR_WANTED_REFRESH.value
    if page == 1 or is_refresh_call:
        logger.debug(
            "Refreshing Sonarr series title cache for wanted episodes list.")
        get_all_series_ids_and_titles_cached(force_refresh=True)

    wanted_data = get_wanted_missing_episodes(
        page=page, page_size=DEFAULT_PAGE_SIZE)
    keyboard = []
    menu_title_text_raw = "🎯 Sonarr - Wanted Episodes"

    if wanted_data and 'records' in wanted_data:
        episodes = wanted_data['records']
        total_records = wanted_data.get('totalRecords', 0)
        current_page = wanted_data.get('page', page)
        page_size_from_api = wanted_data.get('pageSize', DEFAULT_PAGE_SIZE)
        total_pages = math.ceil(
            total_records / page_size_from_api) if total_records > 0 else 1
        if total_pages == 0 and total_records > 0:
            total_pages = 1

        menu_title_text_raw = SONARR_WANTED_EPISODES_MENU_TEXT_TEMPLATE_RAW.format(
            current_page=current_page, total_pages=total_pages)
        context.user_data['sonarr_wanted_current_page'] = current_page

        status_message_text_raw = f"Displaying page {current_page} of {total_pages} for wanted episodes."
        if is_refresh_call:
            status_message_text_raw = f"🔄 Wanted list refreshed. {status_message_text_raw}"
        if not episodes and total_records == 0:
            status_message_text_raw = "✅ No wanted episodes found in Sonarr."
        elif not episodes and current_page > 1:
            status_message_text_raw = "ℹ️ No more wanted episodes on this page."
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(status_message_text_raw), parse_mode="MarkdownV2")

        for ep_item in episodes:
            if not isinstance(ep_item, dict):
                logger.warning(
                    f"Skipping non-dict item in Sonarr wanted episodes: {ep_item}")
                continue

            series_title_raw = ep_item.get('seriesTitle', 'Unknown Series')
            ep_title_raw = ep_item.get(
                'title', f"Ep {ep_item.get('episodeNumber', '?')}")
            button_text = f"{series_title_raw} - S{ep_item.get('seasonNumber'):02d}E{ep_item.get('episodeNumber'):02d} - {ep_title_raw}"
            if len(button_text) > 60:
                button_text = button_text[:57] + "..."
            keyboard.append([InlineKeyboardButton(
                button_text, callback_data=f"{CallbackData.CMD_SONARR_WANTED_SEARCH_EPISODE_PREFIX.value}{ep_item.get('id')}")])

        pagination_row = []
        if current_page > 1:
            pagination_row.append(InlineKeyboardButton(
                "◀️ Prev", callback_data=f"{CallbackData.CMD_SONARR_WANTED_PAGE_PREFIX.value}{current_page-1}"))
        if current_page < total_pages:
            pagination_row.append(InlineKeyboardButton(
                "Next ▶️", callback_data=f"{CallbackData.CMD_SONARR_WANTED_PAGE_PREFIX.value}{current_page+1}"))
        if pagination_row:
            keyboard.append(pagination_row)
    else:
        error_msg_raw = wanted_data.get(
            "error", "⚠️ Could not fetch wanted episodes.")
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(error_msg_raw), parse_mode="MarkdownV2")
        await display_sonarr_controls_menu(update, context)
        return

    keyboard.append([InlineKeyboardButton("🔍 Search All Wanted Now",
                    callback_data=CallbackData.CMD_SONARR_SEARCH_WANTED_ALL_NOW.value)])
    keyboard.append([InlineKeyboardButton(
        "🔄 Refresh List", callback_data=CallbackData.CMD_SONARR_WANTED_REFRESH.value)])

    keyboard.append([InlineKeyboardButton("🔙 Back to Sonarr Controls",
                    callback_data=CallbackData.CMD_SONARR_CONTROLS.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)

    menu_message_id = load_menu_message_id()
    if not menu_message_id and context.bot_data:
        menu_message_id = context.bot_data.get("main_menu_message_id")

    escaped_menu_title_display = escape_md_v2(
        menu_title_text_raw.replace("(", "\\(").replace(")", "\\)"))

    if menu_message_id:
        try:
            current_content_key = f"menu_message_content_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (escaped_menu_title_display,
                                 reply_markup.to_json())
            if old_content_tuple != new_content_tuple:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=menu_message_id, text=escaped_menu_title_display, reply_markup=reply_markup, parse_mode="MarkdownV2")
                context.bot_data[current_content_key] = new_content_tuple
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                logger.error(
                    f"Error displaying Sonarr Wanted Episodes menu (edit): {e}", exc_info=True)
        except Exception as e:
            logger.error(
                f"Error displaying Sonarr Wanted Episodes menu (edit): {e}", exc_info=True)
    else:
        logger.error(
            "Cannot find menu_message_id for Sonarr Wanted Episodes menu.")


async def display_sonarr_queue_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1) -> None:
    query = update.callback_query
    if query:
        await query.answer()
    chat_id = update.effective_chat.id

    admin_chat_id_str = app_config_holder.get_chat_id_str()
    if not admin_chat_id_str or str(chat_id) != admin_chat_id_str:
        logger.warning(f"Sonarr queue attempt by non-primary admin {chat_id}.")
        return

    is_refresh_call = query and query.data == CallbackData.CMD_SONARR_QUEUE_REFRESH.value

    queue_data = get_sonarr_queue(page=page, page_size=DEFAULT_PAGE_SIZE)
    keyboard = []
    menu_title_text_raw = "📥 Sonarr - Download Queue"

    if queue_data and 'records' in queue_data:
        items = queue_data['records']
        total_records = queue_data.get('totalRecords', 0)
        current_page = queue_data.get('page', page)
        page_size_from_api = queue_data.get('pageSize', DEFAULT_PAGE_SIZE)
        total_pages = math.ceil(
            total_records / page_size_from_api) if total_records > 0 else 1
        if total_pages == 0 and total_records > 0:
            total_pages = 1

        menu_title_text_raw = SONARR_QUEUE_MENU_TEXT_TEMPLATE_RAW.format(
            current_page=current_page, total_pages=total_pages)
        context.user_data['sonarr_queue_current_page'] = current_page

        status_msg_raw = f"Displaying page {current_page} of {total_pages} for Sonarr queue."
        if is_refresh_call:
            status_msg_raw = f"🔄 Sonarr queue refreshed. {status_msg_raw}"
        if not items and total_records == 0:
            status_msg_raw = "✅ Sonarr download queue is empty."
        elif not items and current_page > 1:
            status_msg_raw = "ℹ️ No more items on this page of Sonarr queue."
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(status_msg_raw), parse_mode="MarkdownV2")

        for item in items:
            if not isinstance(item, dict):
                logger.warning(
                    f"Skipping non-dict item in Sonarr queue: {item}")
                continue

            series_title_raw = item.get('seriesTitle', 'Unknown Series')
            ep_info = item.get('episode', {})
            status_raw = item.get('status', 'N/A')
            season_num_raw = ep_info.get(

                'seasonNumber', item.get('seasonNumber', ''))
            ep_num_raw = ep_info.get(
                'episodeNumber', item.get('episodeNumber', ''))
            progress_value = item.get(

                'progress', item.get('totalProgress', 0.0))
            progress_percent_raw = f"{progress_value:.1f}%"
            item_id_for_actions = str(item.get('id'))
            episode_id_for_search = str(ep_info.get(
                'id', '0'))

            button_display_title = f"{series_title_raw} - S{season_num_raw:02d}E{ep_num_raw:02d}" if season_num_raw != '' and ep_num_raw != '' else series_title_raw
            if len(button_display_title) > 30:
                button_display_title = button_display_title[:27] + "..."

            display_text = f"{button_display_title} ({status_raw} - {progress_percent_raw})"
            if len(display_text) > 50:
                display_text = display_text[:47] + "..."
            callback_payload = f"{item_id_for_actions}_{episode_id_for_search}"
            keyboard.append([InlineKeyboardButton(
                f"➡️ {display_text}", callback_data=f"{CallbackData.CMD_SONARR_QUEUE_ITEM_ACTIONS_MENU_PREFIX.value}{callback_payload}")])

        pagination_row = []
        if current_page > 1:
            pagination_row.append(InlineKeyboardButton(
                "◀️ Prev", callback_data=f"{CallbackData.CMD_SONARR_QUEUE_PAGE_PREFIX.value}{current_page-1}"))
        if current_page < total_pages:
            pagination_row.append(InlineKeyboardButton(
                "Next ▶️", callback_data=f"{CallbackData.CMD_SONARR_QUEUE_PAGE_PREFIX.value}{current_page+1}"))
        if pagination_row:
            keyboard.append(pagination_row)
    else:
        error_msg_raw = queue_data.get(
            "error", "⚠️ Could not fetch Sonarr queue.")
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(error_msg_raw), parse_mode="MarkdownV2")
        await display_sonarr_controls_menu(update, context)
        return

    keyboard.append([InlineKeyboardButton(
        "🔄 Refresh Queue", callback_data=CallbackData.CMD_SONARR_QUEUE_REFRESH.value)])

    keyboard.append([InlineKeyboardButton("🔙 Back to Sonarr Controls",
                    callback_data=CallbackData.CMD_SONARR_CONTROLS.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)

    menu_message_id = load_menu_message_id()
    if not menu_message_id and context.bot_data:
        menu_message_id = context.bot_data.get("main_menu_message_id")

    escaped_menu_title_display = escape_md_v2(
        menu_title_text_raw.replace("(", "\\(").replace(")", "\\)"))

    if menu_message_id:
        try:
            current_content_key = f"menu_message_content_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (escaped_menu_title_display,
                                 reply_markup.to_json())
            if old_content_tuple != new_content_tuple:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=menu_message_id, text=escaped_menu_title_display, reply_markup=reply_markup, parse_mode="MarkdownV2")
                context.bot_data[current_content_key] = new_content_tuple
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                logger.error(
                    f"Error displaying Sonarr Queue menu (edit): {e}", exc_info=True)
        except Exception as e:
            logger.error(
                f"Error displaying Sonarr Queue menu (edit): {e}", exc_info=True)
    else:
        logger.error("Cannot find menu_message_id for Sonarr Queue menu.")
