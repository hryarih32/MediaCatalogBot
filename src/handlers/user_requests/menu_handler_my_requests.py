
import logging
import math
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

import src.app.app_config_holder as app_config_holder
from src.bot.bot_callback_data import CallbackData
from src.bot.bot_initialization import send_or_edit_universal_status_message, show_or_edit_main_menu
from src.bot.bot_message_persistence import load_menu_message_id
from src.app.app_file_utils import load_requests_data
from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)

MY_REQUESTS_MENU_TITLE_TEMPLATE_RAW = "📋 My Media Requests (Page {current_page}/{total_pages})"
MY_REQUEST_DETAIL_TITLE_RAW = "ℹ️ My Request Details"
ITEMS_PER_PAGE_MY_REQUESTS = 5


def format_request_timestamp(timestamp: float | None) -> str:
    if not timestamp:
        return "N/A"
    try:
        return time.strftime('%Y-%m-%d %H:%M', time.localtime(timestamp))
    except Exception:
        return "Invalid Date"


async def display_my_requests_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_role = app_config_holder.get_user_role(str(chat_id))

    if query:
        await query.answer()
        if query.data.startswith(CallbackData.MY_REQUESTS_PAGE_PREFIX.value):
            try:
                page = int(query.data.replace(
                    CallbackData.MY_REQUESTS_PAGE_PREFIX.value, ""))
            except ValueError:
                logger.warning(
                    f"Invalid page number in 'My Requests' pagination: {query.data}")
                page = 1
        elif query.data == CallbackData.CMD_MY_REQUESTS_MENU.value:
            page = 1

    if user_role not in [app_config_holder.ROLE_ADMIN, app_config_holder.ROLE_STANDARD_USER]:
        logger.warning(
            f"Unauthorized access attempt to 'My Requests' by chat_id {chat_id} (Role: {user_role})")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access to 'My Requests' is restricted.", parse_mode=None)
        return

    all_requests = load_requests_data()
    user_requests = [
        req for req in all_requests if req.get("user_id") == user_id]
    user_requests.sort(key=lambda r: r.get(
        "request_timestamp", 0), reverse=True)

    total_items = len(user_requests)
    items_per_page_config = app_config_holder.get_add_media_items_per_page()
    items_per_page_to_use = items_per_page_config if items_per_page_config > 0 else ITEMS_PER_PAGE_MY_REQUESTS

    total_pages = math.ceil(
        total_items / items_per_page_to_use) if total_items > 0 else 1
    current_page = max(1, min(page, total_pages))

    start_index = (current_page - 1) * items_per_page_to_use
    end_index = start_index + items_per_page_to_use
    page_items = user_requests[start_index:end_index]

    keyboard = []

    menu_body_parts_for_menu_message = []

    title_template_for_escape = MY_REQUESTS_MENU_TITLE_TEMPLATE_RAW.replace(
        "(", "\\(").replace(")", "\\)")
    menu_title_display = escape_md_v2(title_template_for_escape.format(
        current_page=current_page, total_pages=total_pages))

    status_message_parts = [
        f"Displaying your media requests page {current_page} of {total_pages}."]

    if not page_items:
        if total_items == 0:
            status_message_parts = ["You have no submitted media requests."]
            menu_body_parts_for_menu_message.append(
                escape_md_v2("\n_You have not made any requests yet._"))
        else:
            status_message_parts = [
                f"No requests found on page {current_page}."]
            menu_body_parts_for_menu_message.append(
                escape_md_v2("\n_No requests to display on this page._"))
    else:
        for req_idx, req in enumerate(page_items):
            media_title = req.get("media_title", "Unknown Title")
            media_year_raw = req.get("media_year", "N/A")
            media_year = str(
                media_year_raw) if media_year_raw is not None else "N/A"
            media_type_symbol = "🎬" if req.get(
                "media_type") == "movie" else "🎞️"
            req_status_raw = req.get("status", "Unknown")
            req_status = req_status_raw.capitalize() if isinstance(
                req_status_raw, str) else "Unknown"

            display_title = media_title
            if len(media_title) > 25:
                display_title = media_title[:22] + "..."

            button_text = f"{media_type_symbol} {display_title} ({media_year}) - Status: {req_status}"
            if len(button_text) > 55:
                button_text = button_text[:52] + \
                    "..."

            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"{CallbackData.MY_REQUEST_DETAIL_PREFIX.value}{req.get('request_id')}"
            )])

    final_menu_display_text = menu_title_display
    if menu_body_parts_for_menu_message:
        final_menu_display_text += "\n" + \
            "".join(menu_body_parts_for_menu_message)

    pagination_row = []
    if current_page > 1:
        pagination_row.append(InlineKeyboardButton(
            "◀️ Prev", callback_data=f"{CallbackData.MY_REQUESTS_PAGE_PREFIX.value}{current_page-1}"))
    if current_page < total_pages:
        pagination_row.append(InlineKeyboardButton(
            "Next ▶️", callback_data=f"{CallbackData.MY_REQUESTS_PAGE_PREFIX.value}{current_page+1}"))
    if pagination_row:
        keyboard.append(pagination_row)

    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu",
                    callback_data=CallbackData.CMD_HOME_BACK.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await send_or_edit_universal_status_message(context.bot, chat_id, "\n".join(status_message_parts), parse_mode=None)

    menu_message_id = load_menu_message_id(str(chat_id))
    if menu_message_id:
        try:
            current_content_key = f"menu_message_content_{chat_id}_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (final_menu_display_text,
                                 reply_markup.to_json())

            if old_content_tuple != new_content_tuple:
                await context.bot.edit_message_text(
                    chat_id=chat_id, message_id=menu_message_id,
                    text=final_menu_display_text, reply_markup=reply_markup,
                    parse_mode="MarkdownV2"
                )
                context.bot_data[current_content_key] = new_content_tuple
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                logger.error(
                    f"Error displaying 'My Requests' list (edit): {e}.", exc_info=True)
                await show_or_edit_main_menu(str(chat_id), context)
            else:
                logger.debug(
                    f"'My Requests' list for chat {chat_id} not modified by API.")
        except Exception as e:
            logger.error(
                f"Unexpected error displaying 'My Requests' list: {e}.", exc_info=True)
            await show_or_edit_main_menu(str(chat_id), context)
    else:
        logger.error(
            f"Cannot find menu_message_id for 'My Requests' for chat {chat_id}.")
        await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)


async def display_my_request_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays detailed information for a specific user request."""
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_role = app_config_holder.get_user_role(str(chat_id))

    await query.answer()

    if user_role not in [app_config_holder.ROLE_ADMIN, app_config_holder.ROLE_STANDARD_USER]:
        logger.warning(
            f"Unauthorized access attempt to 'My Request Detail' by chat_id {chat_id} (Role: {user_role})")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied.", parse_mode=None)
        return

    request_id_to_view = query.data.replace(
        CallbackData.MY_REQUEST_DETAIL_PREFIX.value, "")
    all_requests = load_requests_data()
    target_request = next((req for req in all_requests if req.get(
        "request_id") == request_id_to_view and req.get("user_id") == user_id), None)

    if not target_request:
        logger.warning(
            f"User {user_id} tried to view details for non-existent or unauthorized request ID {request_id_to_view}.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Request not found or access denied.", parse_mode=None)

        await display_my_requests_menu(update, context, page=context.user_data.get('my_requests_current_page', 1))
        return

    media_title = escape_md_v2(target_request.get("media_title", "N/A"))
    media_year = escape_md_v2(str(target_request.get("media_year", "N/A")))
    media_type_raw = target_request.get("media_type", "N/A")
    media_type = escape_md_v2(media_type_raw.capitalize(
    ) if isinstance(media_type_raw, str) else "N/A")
    media_id_key = "TMDB ID" if media_type_raw == "movie" else "TVDB ID"
    media_id_val = escape_md_v2(str(target_request.get(
        "media_tmdb_id") if media_type_raw == "movie" else target_request.get("media_tvdb_id", "N/A")))

    req_date = escape_md_v2(format_request_timestamp(
        target_request.get("request_timestamp")))
    status_raw = target_request.get("status", "Unknown")
    status = escape_md_v2(status_raw.capitalize()
                          if isinstance(status_raw, str) else "Unknown")
    status_date = escape_md_v2(format_request_timestamp(
        target_request.get("status_timestamp")))
    admin_notes_raw = target_request.get(
        "admin_notes")
    admin_notes = escape_md_v2(
        admin_notes_raw) if admin_notes_raw else "_No notes from admin\\._"

    detail_text_parts = [
        f"*{MY_REQUEST_DETAIL_TITLE_RAW}*\n",
        f"🎬 *Title:* {media_title} \\({media_year}\\)",
        f"🎞️ *Type:* {media_type}",
        f"🆔 *{media_id_key}:* {media_id_val}",
        f" L *Requested:* {req_date}",
        f" L *Status:* {status} \\(as of {status_date}\\)",
        f"📝 *Admin Notes:* {admin_notes}"
    ]

    final_detail_text = "\n".join(detail_text_parts)
    if len(final_detail_text) > 4096:
        final_detail_text = final_detail_text[:4090] + escape_md_v2("...")

    await send_or_edit_universal_status_message(context.bot, chat_id, final_detail_text, parse_mode="MarkdownV2")

    keyboard = [[InlineKeyboardButton(
        f"🔙 Back to My Requests (Page {context.user_data.get('my_requests_current_page', 1)})",
        callback_data=f"{CallbackData.MY_REQUESTS_PAGE_PREFIX.value}{context.user_data.get('my_requests_current_page', 1)}"
    )]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    menu_message_id = load_menu_message_id(str(chat_id))
    if menu_message_id:
        try:

            menu_title_for_detail_view = escape_md_v2(
                f"Request: {target_request.get('media_title', 'Details')[:30]}")

            current_content_key = f"menu_message_content_{chat_id}_{menu_message_id}"

            new_content_tuple = (menu_title_for_detail_view,
                                 reply_markup.to_json())

            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=menu_message_id,
                text=menu_title_for_detail_view,
                reply_markup=reply_markup,
                parse_mode="MarkdownV2"
            )
            context.bot_data[current_content_key] = new_content_tuple
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                logger.error(
                    f"Error displaying 'My Request Detail' menu (edit): {e}.", exc_info=True)
        except Exception as e:
            logger.error(
                f"Unexpected error displaying 'My Request Detail' menu: {e}.", exc_info=True)
    else:
        logger.error(
            f"Cannot find menu_message_id for 'My Request Detail' for chat {chat_id}.")

        await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)
