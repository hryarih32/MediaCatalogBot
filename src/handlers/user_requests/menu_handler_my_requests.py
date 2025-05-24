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
ITEMS_PER_PAGE_MY_REQUESTS = 5


def format_request_timestamp(timestamp: float) -> str:
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

    user_role = app_config_holder.get_user_role(str(chat_id))
    if user_role not in [app_config_holder.ROLE_ADMIN, app_config_holder.ROLE_STANDARD_USER] and \
       not (user_role == app_config_holder.ROLE_ADMIN and app_config_holder.get_user_role(str(chat_id)) == app_config_holder.ROLE_STANDARD_USER):
        is_admin_checking_own = user_role == app_config_holder.ROLE_ADMIN and \
            app_config_holder.get_user_role(
                str(chat_id)) == app_config_holder.ROLE_STANDARD_USER
        if not is_admin_checking_own:
            await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access to 'My Requests' is restricted.", parse_mode=None)
            return

    all_requests = load_requests_data()
    user_requests = [
        req for req in all_requests if req.get("user_id") == user_id]
    user_requests.sort(key=lambda r: r.get(
        "request_timestamp", 0), reverse=True)

    total_items = len(user_requests)
    total_pages = math.ceil(
        total_items / ITEMS_PER_PAGE_MY_REQUESTS) if total_items > 0 else 1
    current_page = max(1, min(page, total_pages))

    start_index = (current_page - 1) * ITEMS_PER_PAGE_MY_REQUESTS
    end_index = start_index + ITEMS_PER_PAGE_MY_REQUESTS
    page_items = user_requests[start_index:end_index]

    keyboard = []

    title_template_for_escape = MY_REQUESTS_MENU_TITLE_TEMPLATE_RAW.replace(
        "(", "\\(").replace(")", "\\)")
    menu_title_display = escape_md_v2(title_template_for_escape.format(
        current_page=current_page, total_pages=total_pages))

    status_message_parts = [
        f"Displaying your media requests page {current_page} of {total_pages}."]

    menu_body_parts = ["\n"]

    if not page_items:
        if total_items == 0:
            status_message_parts = ["You have no submitted media requests."]
            menu_body_parts.append(escape_md_v2(
                "\n_You have not made any requests yet._"))
        else:
            status_message_parts = [
                f"No requests found on page {current_page}."]
            menu_body_parts.append(escape_md_v2(
                "\n_No requests to display on this page._"))
    else:
        for req in page_items:
            media_title = req.get("media_title", "Unknown Title")
            media_year_raw = req.get("media_year", "N/A")
            media_year = str(
                media_year_raw) if media_year_raw is not None else "N/A"
            media_type_symbol = "🎬" if req.get(
                "media_type") == "movie" else "🎞️"
            req_status_raw = req.get("status", "Unknown")
            req_status = req_status_raw.capitalize() if isinstance(
                req_status_raw, str) else "Unknown"
            req_date = format_request_timestamp(req.get("request_timestamp"))

            display_title = media_title
            if len(media_title) > 35:
                display_title = media_title[:32] + "..."

            escaped_display_title = escape_md_v2(display_title)
            escaped_media_year = escape_md_v2(media_year)
            escaped_req_status = escape_md_v2(req_status)
            escaped_req_date = escape_md_v2(req_date)

            line1 = f"{media_type_symbol} *{escaped_display_title}* \\({escaped_media_year}\\)\n"
            line2 = f"  Status: {escaped_req_status}  \\(Req: {escaped_req_date}\\)\n\n"
            menu_body_parts.append(line1)
            menu_body_parts.append(line2)

    final_menu_display_text = menu_title_display + "".join(menu_body_parts)

    if len(final_menu_display_text) > 4096:
        final_menu_display_text = final_menu_display_text[:4090] + escape_md_v2(
            "...")

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
                    chat_id=chat_id,
                    message_id=menu_message_id,
                    text=final_menu_display_text,
                    reply_markup=reply_markup,
                    parse_mode="MarkdownV2"
                )
                context.bot_data[current_content_key] = new_content_tuple
            else:
                logger.debug(
                    f"'My Requests' menu for chat {chat_id} (msg {menu_message_id}) not modified.")
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                logger.error(
                    f"Error displaying 'My Requests' menu (edit): {e}. Text was: '{final_menu_display_text}'", exc_info=True)
                await show_or_edit_main_menu(str(chat_id), context)
            else:
                logger.debug(
                    f"'My Requests' menu for chat {chat_id} (msg {menu_message_id}) reported as 'not modified' by API.")
        except Exception as e:
            logger.error(
                f"Unexpected error displaying 'My Requests' menu: {e}. Text was: '{final_menu_display_text}'", exc_info=True)
            await show_or_edit_main_menu(str(chat_id), context)
    else:
        logger.error(
            f"Cannot find menu_message_id for 'My Requests' for chat {chat_id}.")
        await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)
