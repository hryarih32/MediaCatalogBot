
import logging
import math
import time
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.error import BadRequest

import src.app.app_config_holder as app_config_holder
from src.bot.bot_callback_data import CallbackData
from src.bot.bot_initialization import send_or_edit_universal_status_message, show_or_edit_main_menu
from src.bot.bot_message_persistence import load_menu_message_id
from src.app.app_file_utils import load_requests_data, save_requests_data
from src.bot.bot_text_utils import escape_md_v2, escape_md_v1
from src.handlers.user_requests.menu_handler_my_requests import format_request_timestamp

from src.handlers.radarr.menu_handler_radarr_add_flow import radarr_movie_selection_callback as admin_radarr_add_flow_initiator
from src.handlers.sonarr.menu_handler_sonarr_add_flow import sonarr_show_selection_callback as admin_sonarr_add_flow_initiator
from src.services.radarr.bot_radarr_core import _radarr_request as radarr_api_get
from src.services.sonarr.bot_sonarr_core import _sonarr_request as sonarr_api_get

logger = logging.getLogger(__name__)

ADMIN_PENDING_REQUESTS_TITLE_TEMPLATE = "📬 Pending User Requests (Page {current_page}/{total_pages})"
ADMIN_HISTORY_REQUESTS_TITLE_TEMPLATE = "📜 Request History (Page {current_page}/{total_pages})"
ITEMS_PER_PAGE_ADMIN_REQUESTS = 5

ASK_REJECTION_REASON, HANDLE_REJECTION_REASON = range(2)


async def display_admin_pending_requests_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_role = app_config_holder.get_user_role(str(chat_id))

    if query:
        await query.answer()
        if query.data.startswith(CallbackData.ADMIN_REQUESTS_PENDING_PAGE_PREFIX.value):
            try:
                page = int(query.data.replace(
                    CallbackData.ADMIN_REQUESTS_PENDING_PAGE_PREFIX.value, ""))
            except ValueError:
                logger.warning(
                    f"Invalid page number in admin pending requests pagination: {query.data}")
                page = 1
        elif query.data == CallbackData.CMD_ADMIN_REQUESTS_MENU.value:
            page = 1

    if user_role != app_config_holder.ROLE_ADMIN:
        logger.warning(
            f"Unauthorized access attempt to admin pending requests by chat_id {chat_id} (Role: {user_role})")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied. This section is for administrators.", parse_mode=None)
        return

    all_requests = load_requests_data()
    pending_requests = [
        req for req in all_requests if req.get("status") == "pending"]
    pending_requests.sort(key=lambda r: r.get(
        "request_timestamp", 0), reverse=False)

    total_items = len(pending_requests)
    total_pages = math.ceil(
        total_items / ITEMS_PER_PAGE_ADMIN_REQUESTS) if total_items > 0 else 1
    current_page = max(1, min(page, total_pages))

    start_index = (current_page - 1) * ITEMS_PER_PAGE_ADMIN_REQUESTS
    end_index = start_index + ITEMS_PER_PAGE_ADMIN_REQUESTS
    page_items = pending_requests[start_index:end_index]

    keyboard = []

    title_template_for_escape = ADMIN_PENDING_REQUESTS_TITLE_TEMPLATE.replace(
        "(", "\\(").replace(")", "\\)")
    menu_title_display = escape_md_v2(title_template_for_escape.format(
        current_page=current_page, total_pages=total_pages))

    status_message_parts = [
        f"Displaying pending user requests page {current_page} of {total_pages}."]
    menu_body_parts = ["\n"]

    if not page_items:
        if total_items == 0:
            status_message_parts = ["✅ No pending user requests."]
            menu_body_parts.append(escape_md_v2(
                "\n_There are currently no pending requests._"))
        else:
            status_message_parts = [
                f"No pending requests found on page {current_page}."]
            menu_body_parts.append(escape_md_v2(
                "\n_No requests to display on this page._"))
    else:
        for req in page_items:
            media_title_raw = req.get("media_title", "Unknown Title")
            media_year_raw = req.get("media_year", "N/A")
            username_raw = req.get("username", "Unknown User")

            media_title = str(
                media_title_raw) if media_title_raw is not None else "Unknown Title"
            media_year = str(
                media_year_raw) if media_year_raw is not None else "N/A"
            username = str(
                username_raw) if username_raw is not None else "Unknown User"

            media_type_symbol = "🎬" if req.get(
                "media_type") == "movie" else "🎞️"
            req_date = format_request_timestamp(req.get("request_timestamp"))

            display_title = media_title
            if len(media_title) > 25:
                display_title = media_title[:22] + "..."

            escaped_display_title = escape_md_v2(display_title)
            escaped_media_year = escape_md_v2(media_year)
            escaped_username = escape_md_v2(username)
            escaped_req_date = escape_md_v2(req_date)

            line1 = f"{media_type_symbol} *{escaped_display_title}* \\({escaped_media_year}\\)\n"
            line2 = f"  User: {escaped_username} \\(Req: {escaped_req_date}\\)\n\n"
            menu_body_parts.append(line1)
            menu_body_parts.append(line2)

            keyboard.append([InlineKeyboardButton(f"👁️ View: {display_title}",
                            callback_data=f"{CallbackData.CMD_ADMIN_VIEW_REQUEST_PREFIX.value}{req.get('request_id')}")])

    final_menu_display_text = menu_title_display + "".join(menu_body_parts)
    if len(final_menu_display_text) > 4096:
        final_menu_display_text = final_menu_display_text[:4090] + escape_md_v2(
            "...")

    pagination_row = []
    if current_page > 1:
        pagination_row.append(InlineKeyboardButton(
            "◀️ Prev", callback_data=f"{CallbackData.ADMIN_REQUESTS_PENDING_PAGE_PREFIX.value}{current_page-1}"))
    if current_page < total_pages:
        pagination_row.append(InlineKeyboardButton(
            "Next ▶️", callback_data=f"{CallbackData.ADMIN_REQUESTS_PENDING_PAGE_PREFIX.value}{current_page+1}"))
    if pagination_row:
        keyboard.append(pagination_row)

    keyboard.append([InlineKeyboardButton(
        "📜 View History", callback_data=CallbackData.CMD_ADMIN_REQUEST_HISTORY_MENU.value)])
    keyboard.append([InlineKeyboardButton(
        "🔄 Refresh List", callback_data=CallbackData.CMD_ADMIN_REQUESTS_MENU.value)])
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
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                logger.error(
                    f"Error displaying admin pending requests menu (edit): {e}. Text was: '{final_menu_display_text}'", exc_info=True)
        except Exception as e:
            logger.error(
                f"Unexpected error displaying admin pending requests: {e}. Text was: '{final_menu_display_text}'", exc_info=True)
    else:
        logger.error(
            f"Cannot find menu_message_id for admin pending requests for chat {chat_id}.")
        await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)


async def display_admin_request_details_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_role = app_config_holder.get_user_role(str(chat_id))

    if user_role != app_config_holder.ROLE_ADMIN:
        logger.warning(
            f"Unauthorized access attempt to admin request details by chat_id {chat_id} (Role: {user_role})")
        await query.answer("Access Denied.", show_alert=True)
        return

    request_id = query.data.replace(
        CallbackData.CMD_ADMIN_VIEW_REQUEST_PREFIX.value, "")
    await query.answer()

    all_requests = load_requests_data()
    target_request_idx, target_request = -1, None
    for idx, req in enumerate(all_requests):
        if req.get("request_id") == request_id:
            target_request = req
            target_request_idx = idx
            break

    if not target_request:
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Request not found (it might have been processed or deleted).", parse_mode=None)
        await display_admin_pending_requests_menu(update, context)
        return

    context.user_data['admin_current_request_to_process'] = target_request
    context.user_data['admin_current_request_idx_to_process'] = target_request_idx

    media_title_raw = target_request.get("media_title", "N/A")
    media_year_raw = target_request.get("media_year", "N/A")
    media_type_raw = target_request.get("media_type", "N/A")
    media_id_key_raw = "TMDB ID" if target_request.get(
        "media_type") == "movie" else "TVDB ID"
    media_id_val_raw = target_request.get("media_tmdb_id") if target_request.get(
        "media_type") == "movie" else target_request.get("media_tvdb_id", "N/A")
    requested_by_raw = f"{target_request.get('username', 'N/A')} (ID: {target_request.get('user_id')})"
    request_date_raw = format_request_timestamp(
        target_request.get("request_timestamp"))
    current_status_raw = target_request.get("status", "N/A")
    status_date_raw = format_request_timestamp(
        target_request.get("status_timestamp"))
    admin_notes_raw = target_request.get("admin_notes", "_No notes yet_")

    escaped_media_title = escape_md_v2(str(media_title_raw))
    escaped_media_year = escape_md_v2(str(media_year_raw))
    escaped_media_type = escape_md_v2(str(media_type_raw).capitalize())
    escaped_media_id_key = escape_md_v2(str(media_id_key_raw))
    escaped_media_id_val = escape_md_v2(str(media_id_val_raw))
    escaped_requested_by = escape_md_v2(str(requested_by_raw))
    escaped_request_date = escape_md_v2(str(request_date_raw))
    escaped_current_status = escape_md_v2(str(current_status_raw).capitalize())
    escaped_status_date = escape_md_v2(str(status_date_raw))
    escaped_admin_notes = escape_md_v2(str(admin_notes_raw))

    line1 = f"🔔 *Request Details: {escaped_media_title} \\({escaped_media_year}\\)*"
    line2 = f"Type: {escaped_media_type}"
    line3 = f"{escaped_media_id_key}: {escaped_media_id_val}"
    line4 = f"Requested by: {escaped_requested_by}"
    line5 = f"Status: *{escaped_current_status}* \\(since {escaped_status_date}\\)"
    line6 = f"Admin Notes: {escaped_admin_notes}"

    details_text_parts = [line1, line2, line3, line4, line5, line6]

    keyboard = []
    if current_status_raw == "pending":
        keyboard.append([
            InlineKeyboardButton(
                "✅ Approve", callback_data=f"{CallbackData.CMD_ADMIN_APPROVE_REQUEST_PREFIX.value}{request_id}"),
            InlineKeyboardButton(
                "❌ Reject", callback_data=f"{CallbackData.CMD_ADMIN_REJECT_REQUEST_PREFIX.value}{request_id}")
        ])

    keyboard.append([InlineKeyboardButton("🔙 Back to Pending Requests",
                    callback_data=CallbackData.CMD_ADMIN_REQUESTS_MENU.value)])
    keyboard.append([InlineKeyboardButton(
        "📜 View History", callback_data=CallbackData.CMD_ADMIN_REQUEST_HISTORY_MENU.value)])
    keyboard.append([InlineKeyboardButton("🏠 Back to Main Menu",
                    callback_data=CallbackData.CMD_HOME_BACK.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)

    final_text = "\n".join(details_text_parts)
    if len(final_text) > 4096:
        final_text = final_text[:4090] + escape_md_v2("...")

    menu_message_id = load_menu_message_id(str(chat_id))
    if menu_message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=menu_message_id,
                text=final_text,
                reply_markup=reply_markup,
                parse_mode="MarkdownV2"
            )
            context.bot_data[f"menu_message_content_{chat_id}_{menu_message_id}"] = (
                final_text, reply_markup.to_json())
        except BadRequest as e_bad:
            logger.error(
                f"BadRequest editing admin request details view: {e_bad}. Text was: '{final_text}'", exc_info=True)
            await send_or_edit_universal_status_message(context.bot, chat_id, final_text, parse_mode="MarkdownV2", reply_markup=reply_markup, force_send_new=True)
        except Exception as e:
            logger.error(
                f"Error editing admin request details view: {e}. Text was: '{final_text}'", exc_info=True)
            await send_or_edit_universal_status_message(context.bot, chat_id, final_text, parse_mode="MarkdownV2", reply_markup=reply_markup, force_send_new=True)
    else:
        logger.error(
            f"Cannot find menu_message_id for admin request details view for chat {chat_id}.")
        await send_or_edit_universal_status_message(context.bot, chat_id, final_text, parse_mode="MarkdownV2", reply_markup=reply_markup, force_send_new=True)


async def admin_approve_request_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    admin_chat_id = update.effective_chat.id
    user_role = app_config_holder.get_user_role(str(admin_chat_id))

    if user_role != app_config_holder.ROLE_ADMIN:
        logger.warning(
            f"Unauthorized attempt to approve request by chat_id {admin_chat_id} (Role: {user_role})")
        await query.answer("Access Denied.", show_alert=True)
        return

    request_id = query.data.replace(
        CallbackData.CMD_ADMIN_APPROVE_REQUEST_PREFIX.value, "")
    await query.answer("Processing approval...")

    target_request = context.user_data.get('admin_current_request_to_process')

    if not target_request or target_request.get("request_id") != request_id:
        all_requests_list = load_requests_data()

        for idx, req in enumerate(all_requests_list):
            if req.get("request_id") == request_id:
                target_request = req

                context.user_data['admin_current_request_to_process'] = target_request

                break

    if not target_request:
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, "⚠️ Error: Could not find the request to approve. It might have been processed already.", parse_mode=None)

        await display_admin_pending_requests_menu(update, context)
        return

    if target_request.get("status") != "pending":
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, f"⚠️ Request for '{escape_md_v2(str(target_request.get('media_title')))}' is already '{escape_md_v2(str(target_request.get('status')))}'\\. No action taken\\.", parse_mode="MarkdownV2")

        await display_admin_request_details_view(update, context)
        return

    media_type = target_request.get("media_type")
    media_id = target_request.get(
        "media_tmdb_id") if media_type == "movie" else target_request.get("media_tvdb_id")
    media_title_raw = target_request.get("media_title")
    requesting_user_id = target_request.get("user_id")
    requesting_username_raw = target_request.get("username")

    media_title = str(
        media_title_raw) if media_title_raw is not None else "Unknown Title"
    requesting_username = str(
        requesting_username_raw) if requesting_username_raw is not None else "Unknown User"

    approval_status_text = f"⏳ Approving request for '{escape_md_v2(media_title)}' and attempting to add to {'Radarr' if media_type == 'movie' else 'Sonarr'}\\.\\.\\."
    await send_or_edit_universal_status_message(context.bot, admin_chat_id, approval_status_text, parse_mode="MarkdownV2")

    full_media_object_for_add_flow = None
    if media_type == "movie":
        try:
            lookup_response = radarr_api_get(
                'get', f'/movie/lookup/tmdb?tmdbId={media_id}')
            if isinstance(lookup_response, list) and lookup_response:
                full_media_object_for_add_flow = lookup_response[0]
            elif isinstance(lookup_response, dict):
                full_media_object_for_add_flow = lookup_response
        except Exception as e:
            logger.error(
                f"Failed to re-fetch Radarr movie details for approved request {request_id}: {e}")
    elif media_type == "tv":
        try:

            lookup_response = sonarr_api_get(
                'get', f'/series/lookup', params={'term': f'tvdb:{media_id}'})
            if isinstance(lookup_response, list) and lookup_response:
                full_media_object_for_add_flow = lookup_response[0]
            elif isinstance(lookup_response, dict):
                full_media_object_for_add_flow = lookup_response
        except Exception as e:
            logger.error(
                f"Failed to re-fetch Sonarr show details for approved request {request_id}: {e}")

    if not full_media_object_for_add_flow:
        status_update_text = f"⚠️ Could not re\\-fetch details for '{escape_md_v2(media_title)}' to add it automatically\\. Please add manually\\. Request marked as approved\\."
        all_reqs = load_requests_data()
        updated = False
        for i in range(len(all_reqs)):
            if all_reqs[i].get("request_id") == request_id:

                all_reqs[i]["status"] = "approved"
                all_reqs[i]["status_timestamp"] = time.time()
                all_reqs[i]["admin_notes"] = "Approved (manual add required due to detail fetch error)."
                updated = True
                break
        if updated:
            save_requests_data(all_reqs)

        await send_or_edit_universal_status_message(context.bot, admin_chat_id, status_update_text, parse_mode="MarkdownV2")

        await display_admin_pending_requests_menu(update, context)
        return

    flow_data_key = 'radarr_add_flow' if media_type == "movie" else 'sonarr_add_flow'

    context.user_data.pop(flow_data_key, None)

    context.user_data[flow_data_key] = {
        'movie_tmdb_id' if media_type == "movie" else 'show_tvdb_id': media_id,
        'movie_title' if media_type == "movie" else 'show_title': media_title,
        'movie_year' if media_type == "movie" else 'show_year': target_request.get('media_year'),
        'radarr_movie_object_from_lookup' if media_type == "movie" else 'sonarr_show_object_from_lookup': full_media_object_for_add_flow,

        'current_step': 'initial_choice_radarr' if media_type == "movie" else 'initial_choice_sonarr',
        'chat_id': admin_chat_id,
        'user_id': admin_chat_id,

        'username': update.effective_user.username or str(admin_chat_id),

        'main_menu_message_id': query.message.message_id,
        'approved_request_id': request_id,
        'approved_request_original_user_id': requesting_user_id,
        'approved_request_original_username': requesting_username,

        'initiator_action_data': f"{CallbackData.RADARR_SELECT_PREFIX.value}{media_id}" if media_type == "movie" else f"{CallbackData.SONARR_SELECT_PREFIX.value}{media_id}"
    }

    all_reqs = load_requests_data()
    updated_processing = False
    for i in range(len(all_reqs)):
        if all_reqs[i].get("request_id") == request_id:
            all_reqs[i]["status"] = "processing_approval"
            all_reqs[i]["status_timestamp"] = time.time()
            all_reqs[i]["admin_notes"] = f"Approved by admin {update.effective_user.username or admin_chat_id}. Awaiting addition."
            updated_processing = True
            break
    if updated_processing:
        save_requests_data(all_reqs)

    status_msg_proceed = f"Request for '{escape_md_v2(media_title)}' approved\\. Proceeding to add options\\.\\.\\."
    await send_or_edit_universal_status_message(context.bot, admin_chat_id, status_msg_proceed, parse_mode="MarkdownV2")

    if media_type == "movie":
        await admin_radarr_add_flow_initiator(update, context)
    elif media_type == "tv":
        await admin_sonarr_add_flow_initiator(update, context)


async def admin_reject_request_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    admin_chat_id = update.effective_chat.id
    user_role = app_config_holder.get_user_role(str(admin_chat_id))

    if user_role != app_config_holder.ROLE_ADMIN:
        logger.warning(
            f"Unauthorized attempt to reject request by chat_id {admin_chat_id} (Role: {user_role})")
        await query.answer("Access Denied.", show_alert=True)
        return ConversationHandler.END

    request_id = query.data.replace(
        CallbackData.CMD_ADMIN_REJECT_REQUEST_PREFIX.value, "")
    await query.answer()

    target_request = context.user_data.get('admin_current_request_to_process')
    if not target_request or target_request.get("request_id") != request_id:
        all_requests_list = load_requests_data()
        target_request = next(
            (req for req in all_requests_list if req.get("request_id") == request_id), None)
        if target_request:
            context.user_data['admin_current_request_to_process'] = target_request

    if not target_request:
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, "⚠️ Error: Could not find the request to reject.", parse_mode=None)
        return ConversationHandler.END

    if target_request.get("status") != "pending":
        await send_or_edit_universal_status_message(
            context.bot, admin_chat_id,
            f"⚠️ Request for '{escape_md_v2(str(target_request.get('media_title')))}' is already '{escape_md_v2(str(target_request.get('status')))}'\\. No action taken\\.",
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

    context.user_data['rejecting_request_id'] = request_id
    context.user_data['rejecting_request_title'] = target_request.get(
        "media_title")
    context.user_data['rejecting_request_user_id'] = target_request.get(
        "user_id")

    rejection_prompt_text = f"⚠️ Enter reason for rejecting '{escape_md_v2(str(target_request.get('media_title')))}' \\(or send /skip\\):"
    await send_or_edit_universal_status_message(context.bot, admin_chat_id, rejection_prompt_text, parse_mode="MarkdownV2")
    return ASK_REJECTION_REASON


async def handle_rejection_reason_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_chat_id = update.effective_chat.id

    user_role = app_config_holder.get_user_role(str(admin_chat_id))
    if user_role != app_config_holder.ROLE_ADMIN:
        logger.warning(
            f"Unauthorized attempt to provide rejection reason by chat_id {admin_chat_id} (Role: {user_role})")

        return ConversationHandler.END

    if update.message and update.message.message_id:
        try:
            await context.bot.delete_message(chat_id=admin_chat_id, message_id=update.message.message_id)
            logger.info(
                f"Deleted admin's rejection reason message {update.message.message_id}")
        except Exception as e_del_reason:
            logger.warning(
                f"Could not delete admin's rejection reason message: {e_del_reason}")

    reason_text = update.message.text if update.message and update.message.text else "/skip"
    if update.message and update.message.text and update.message.text.lower() == "/skip":
        reason_text = "/skip"

    request_id = context.user_data.get('rejecting_request_id')
    media_title_raw = context.user_data.get(
        'rejecting_request_title', "this request")
    media_title = str(
        media_title_raw) if media_title_raw is not None else "this request"

    if not request_id:
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, "⚠️ Error: No request selected for rejection.", parse_mode=None)
        return ConversationHandler.END

    all_requests = load_requests_data()
    req_found_and_updated = False
    for i in range(len(all_requests)):
        if all_requests[i].get("request_id") == request_id and all_requests[i].get("status") == "pending":
            all_requests[i]["status"] = "rejected"
            all_requests[i]["status_timestamp"] = time.time()
            all_requests[i]["admin_notes"] = reason_text if reason_text != "/skip" else "Rejected by admin."
            req_found_and_updated = True
            break

    if req_found_and_updated:
        save_requests_data(all_requests)
        rejection_feedback_raw = f"✅ Request for '{media_title}' rejected."
        if reason_text != "/skip":
            rejection_feedback_raw += f" Reason: {reason_text}"
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, escape_md_v2(rejection_feedback_raw), parse_mode="MarkdownV2")
        logger.info(
            f"Request ID {request_id} ('{media_title}') rejected by admin {admin_chat_id}. Reason: {reason_text}")
    else:
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, "⚠️ Request was not found or already processed.", parse_mode=None)

    context.user_data.pop('rejecting_request_id', None)
    context.user_data.pop('rejecting_request_title', None)
    context.user_data.pop('rejecting_request_user_id', None)

    original_menu_msg_id = load_menu_message_id(str(admin_chat_id))
    effective_user_obj = update.effective_user
    effective_chat_obj = update.effective_chat

    class DummyQuery:
        def __init__(self, data_val, message_obj, from_user_obj):
            self.data = data_val
            self.message = message_obj
            self.from_user = from_user_obj

        async def answer(self): pass

    if original_menu_msg_id and effective_user_obj and effective_chat_obj:
        dummy_message_obj = type('DummyMessage', (), {
                                 'chat_id': admin_chat_id, 'message_id': original_menu_msg_id, 'chat': effective_chat_obj})()

        from_user_for_dummy = update.message.from_user if update.message else effective_user_obj

        dummy_query_obj = DummyQuery(
            CallbackData.CMD_ADMIN_REQUESTS_MENU.value, dummy_message_obj, from_user_for_dummy)

        current_update_id_val = update.update_id if hasattr(
            update, 'update_id') else 0

        dummy_update_obj = Update(
            update_id=current_update_id_val, callback_query=dummy_query_obj)

        dummy_update_obj.effective_user = from_user_for_dummy
        dummy_update_obj.effective_chat = effective_chat_obj

        await display_admin_pending_requests_menu(dummy_update_obj, context, page=1)
    else:
        logger.warning(
            "Could not construct dummy update to refresh admin pending menu after rejection.")
        await show_or_edit_main_menu(str(admin_chat_id), context)

    return ConversationHandler.END


async def cancel_rejection_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_chat_id = update.effective_chat.id

    user_role = app_config_holder.get_user_role(str(admin_chat_id))
    if user_role != app_config_holder.ROLE_ADMIN:
        logger.warning(
            f"Unauthorized attempt to cancel rejection by chat_id {admin_chat_id} (Role: {user_role})")
        return ConversationHandler.END

    await send_or_edit_universal_status_message(context.bot, admin_chat_id, "Rejection process cancelled.", parse_mode=None)
    context.user_data.pop('rejecting_request_id', None)
    context.user_data.pop('rejecting_request_title', None)
    context.user_data.pop('rejecting_request_user_id', None)

    original_menu_msg_id = load_menu_message_id(str(admin_chat_id))
    effective_user_obj = update.effective_user
    effective_chat_obj = update.effective_chat

    class DummyQuery:
        def __init__(self, data_val, message_obj, from_user_obj):
            self.data = data_val
            self.message = message_obj
            self.from_user = from_user_obj

        async def answer(self): pass

    if original_menu_msg_id and effective_user_obj and effective_chat_obj:
        dummy_message_obj = type('DummyMessage', (), {
                                 'chat_id': admin_chat_id, 'message_id': original_menu_msg_id, 'chat': effective_chat_obj})()
        from_user_for_dummy = update.message.from_user if update.message else effective_user_obj

        dummy_query_obj = DummyQuery(
            CallbackData.CMD_ADMIN_REQUESTS_MENU.value, dummy_message_obj, from_user_for_dummy)

        current_update_id_val = update.update_id if hasattr(
            update, 'update_id') else 0
        dummy_update_obj = Update(
            update_id=current_update_id_val, callback_query=dummy_query_obj)
        dummy_update_obj.effective_user = from_user_for_dummy
        dummy_update_obj.effective_chat = effective_chat_obj

        await display_admin_pending_requests_menu(dummy_update_obj, context, page=1)
    else:
        logger.warning(
            "Could not construct dummy update to refresh admin pending menu after cancel rejection.")
        await show_or_edit_main_menu(str(admin_chat_id), context)
    return ConversationHandler.END


async def display_admin_history_requests_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_role = app_config_holder.get_user_role(str(chat_id))

    if query:
        await query.answer()
        if query.data.startswith(CallbackData.ADMIN_REQUESTS_HISTORY_PAGE_PREFIX.value):
            try:
                page = int(query.data.replace(
                    CallbackData.ADMIN_REQUESTS_HISTORY_PAGE_PREFIX.value, ""))
            except ValueError:
                page = 1
        elif query.data == CallbackData.CMD_ADMIN_REQUEST_HISTORY_MENU.value:
            page = 1

    if user_role != app_config_holder.ROLE_ADMIN:
        logger.warning(
            f"Unauthorized access attempt to admin request history by chat_id {chat_id} (Role: {user_role})")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied.", parse_mode=None)
        return

    all_requests = load_requests_data()
    processed_requests = [req for req in all_requests if req.get(

        "status") in ["approved", "rejected", "add_failed"]]
    processed_requests.sort(key=lambda r: r.get(
        "status_timestamp", 0), reverse=True)

    total_items = len(processed_requests)
    total_pages = math.ceil(
        total_items / ITEMS_PER_PAGE_ADMIN_REQUESTS) if total_items > 0 else 1
    current_page = max(1, min(page, total_pages))

    start_index = (current_page - 1) * ITEMS_PER_PAGE_ADMIN_REQUESTS
    end_index = start_index + ITEMS_PER_PAGE_ADMIN_REQUESTS
    page_items = processed_requests[start_index:end_index]

    keyboard = []
    title_template_for_escape = ADMIN_HISTORY_REQUESTS_TITLE_TEMPLATE.replace(
        "(", "\\(").replace(")", "\\)")
    menu_title_display = escape_md_v2(title_template_for_escape.format(
        current_page=current_page, total_pages=total_pages))

    status_message_parts = [
        f"Displaying request history page {current_page} of {total_pages}."]
    menu_body_parts = ["\n"]

    if not page_items:
        if total_items == 0:
            status_message_parts = ["No processed requests found in history."]
            menu_body_parts.append(escape_md_v2(
                "\n_Request history is empty._"))
        else:
            status_message_parts = [
                f"No requests found on page {current_page} of history."]
            menu_body_parts.append(escape_md_v2(
                "\n_No history to display on this page._"))
    else:
        for req in page_items:
            media_title_raw = req.get("media_title", "N/A")
            media_year_raw = req.get("media_year", "N/A")
            username_raw = req.get("username", "N/A")
            req_status_raw = req.get("status", "N/A")

            media_title = str(
                media_title_raw) if media_title_raw is not None else "N/A"
            media_year = str(
                media_year_raw) if media_year_raw is not None else "N/A"
            media_type_symbol = "🎬" if req.get(
                "media_type") == "movie" else "🎞️"
            req_status = req_status_raw.capitalize() if isinstance(
                req_status_raw, str) else "N/A"
            status_date = format_request_timestamp(req.get("status_timestamp"))
            username = str(username_raw) if username_raw is not None else "N/A"

            display_title = media_title
            if len(media_title) > 25:
                display_title = media_title[:22] + "..."

            escaped_title = escape_md_v2(display_title)
            escaped_year = escape_md_v2(media_year)
            escaped_status = escape_md_v2(req_status)
            escaped_user = escape_md_v2(username)
            escaped_status_date = escape_md_v2(status_date)

            line1 = f"{media_type_symbol} *{escaped_title}* \\({escaped_year}\\) by {escaped_user}\n"
            line2 = f"  Status: {escaped_status} on {escaped_status_date}\n\n"
            menu_body_parts.append(line1 + line2)

            keyboard.append([InlineKeyboardButton(f"{display_title} - {req_status}",
                            callback_data=f"{CallbackData.CMD_ADMIN_VIEW_REQUEST_PREFIX.value}{req.get('request_id')}")])

    final_menu_display_text = menu_title_display + "".join(menu_body_parts)
    if len(final_menu_display_text) > 4096:
        final_menu_display_text = final_menu_display_text[:4090] + escape_md_v2(
            "...")

    pagination_row = []
    if current_page > 1:
        pagination_row.append(InlineKeyboardButton(
            "◀️ Prev", callback_data=f"{CallbackData.ADMIN_REQUESTS_HISTORY_PAGE_PREFIX.value}{current_page-1}"))
    if current_page < total_pages:
        pagination_row.append(InlineKeyboardButton(
            "Next ▶️", callback_data=f"{CallbackData.ADMIN_REQUESTS_HISTORY_PAGE_PREFIX.value}{current_page+1}"))
    if pagination_row:
        keyboard.append(pagination_row)

    keyboard.append([InlineKeyboardButton("📬 Back to Pending",
                    callback_data=CallbackData.CMD_ADMIN_REQUESTS_MENU.value)])
    keyboard.append([InlineKeyboardButton("🏠 Back to Main Menu",
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
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                logger.error(
                    f"Error displaying admin request history menu (edit): {e}. Text: '{final_menu_display_text}'", exc_info=True)
        except Exception as e:
            logger.error(
                f"Unexpected error displaying admin request history: {e}. Text: '{final_menu_display_text}'", exc_info=True)
    else:
        logger.error(
            f"Cannot find menu_message_id for admin request history for chat {chat_id}.")
        await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)
