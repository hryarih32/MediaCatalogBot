import logging
import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

import src.app.app_config_holder as app_config_holder
from src.bot.bot_message_persistence import load_menu_message_id
from src.bot.bot_initialization import send_or_edit_universal_status_message
from src.bot.bot_callback_data import CallbackData
from src.services.radarr.bot_radarr_manage import get_radarr_queue

from src.handlers.radarr.menu_handler_radarr_controls import display_radarr_controls_menu
from src.bot.bot_text_utils import escape_md_v2, escape_md_v1

logger = logging.getLogger(__name__)

RADARR_QUEUE_MENU_TEXT_TEMPLATE_RAW = "📥 Radarr - Download Queue (Page {current_page}/{total_pages})"

DEFAULT_PAGE_SIZE = 5


async def display_radarr_queue_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1) -> None:
    query = update.callback_query
    if query:
        await query.answer()
    chat_id = update.effective_chat.id

    admin_chat_id_str = app_config_holder.get_chat_id_str()
    if not admin_chat_id_str or str(chat_id) != admin_chat_id_str:
        logger.warning(f"Radarr queue attempt by non-primary admin {chat_id}.")
        return

    is_refresh_call = query and query.data == CallbackData.CMD_RADARR_QUEUE_REFRESH.value

    queue_data = get_radarr_queue(page=page, page_size=DEFAULT_PAGE_SIZE)
    keyboard = []
    menu_title_text_raw = "📥 Radarr - Download Queue"

    if queue_data and 'records' in queue_data:
        items = queue_data['records']
        total_records = queue_data.get('totalRecords', 0)
        current_page = queue_data.get('page', page)
        page_size_from_api = queue_data.get('pageSize', DEFAULT_PAGE_SIZE)
        total_pages = math.ceil(
            total_records / page_size_from_api) if total_records > 0 else 1
        if total_pages == 0 and total_records > 0:
            total_pages = 1

        menu_title_text_raw = RADARR_QUEUE_MENU_TEXT_TEMPLATE_RAW.format(
            current_page=current_page, total_pages=total_pages)
        context.user_data['radarr_queue_current_page'] = current_page

        status_msg_raw = f"Displaying page {current_page} of {total_pages} for Radarr queue."
        if is_refresh_call:
            status_msg_raw = f"🔄 Radarr queue refreshed. {status_msg_raw}"
        if not items and total_records == 0:
            status_msg_raw = "✅ Radarr download queue is empty."
        elif not items and current_page > 1:
            status_msg_raw = "ℹ️ No more items on this page of Radarr queue."

        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(status_msg_raw), parse_mode="MarkdownV2")

        for item in items:
            if not isinstance(item, dict):
                logger.warning(
                    f"Skipping non-dict item in Radarr queue: {item}")
                continue
            movie_info = item.get('movie', {})
            title_raw = movie_info.get(
                'title', item.get('title', 'Unknown Movie'))
            status_raw = item.get('status', 'N/A')
            progress_value = 0.0
            if 'sizeleft' in item and 'size' in item and item.get('size', 0) > 0:
                progress_value = (
                    (item['size'] - item['sizeleft']) / item['size']) * 100.0
            elif 'progress' in item:
                progress_value = item.get('progress', 0.0)
            progress_percent_raw = f"{progress_value:.1f}%"
            timeleft_raw = item.get('timeleft', 'N/A')
            item_id_for_actions = str(item.get('id'))
            movie_id_for_search = str(

                movie_info.get('id', item.get('movieId', '0')))

            display_text = f"{title_raw} ({status_raw} - {progress_percent_raw} - {timeleft_raw})"
            if len(display_text) > 50:
                display_text = display_text[:47] + "..."
            callback_payload = f"{item_id_for_actions}_{movie_id_for_search}"
            keyboard.append([InlineKeyboardButton(
                f"➡️ {display_text}", callback_data=f"{CallbackData.CMD_RADARR_QUEUE_ITEM_ACTIONS_MENU_PREFIX.value}{callback_payload}")])

        pagination_row = []
        if current_page > 1:
            pagination_row.append(InlineKeyboardButton(
                "◀️ Prev", callback_data=f"{CallbackData.CMD_RADARR_QUEUE_PAGE_PREFIX.value}{current_page-1}"))
        if current_page < total_pages:
            pagination_row.append(InlineKeyboardButton(
                "Next ▶️", callback_data=f"{CallbackData.CMD_RADARR_QUEUE_PAGE_PREFIX.value}{current_page+1}"))
        if pagination_row:
            keyboard.append(pagination_row)
    else:
        error_msg_raw = queue_data.get(
            "error", "⚠️ Could not fetch Radarr queue.")
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(error_msg_raw), parse_mode="MarkdownV2")

        await display_radarr_controls_menu(update, context)
        return

    keyboard.append([InlineKeyboardButton(
        "🔄 Refresh Queue", callback_data=CallbackData.CMD_RADARR_QUEUE_REFRESH.value)])

    keyboard.append([InlineKeyboardButton("🔙 Back to Radarr Controls",
                    callback_data=CallbackData.CMD_RADARR_CONTROLS.value)])
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
                    f"Error displaying Radarr Queue menu (edit): {e}", exc_info=True)
        except Exception as e:
            logger.error(
                f"Error displaying Radarr Queue menu (edit): {e}", exc_info=True)
    else:
        logger.error("Cannot find menu_message_id for Radarr Queue menu.")
