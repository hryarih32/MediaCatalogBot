
import logging
import math
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest
import datetime

import src.app.app_config_holder as app_config_holder
import src.app.user_manager as user_manager
from src.bot.bot_callback_data import CallbackData
from src.bot.bot_initialization import send_or_edit_universal_status_message, show_or_edit_main_menu
from src.bot.bot_message_persistence import load_menu_message_id
from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)

PENDING_ACCESS_REQUESTS_TITLE_TEMPLATE_RAW = "🔑 Pending User Access Requests (Page {current_page}/{total_pages})"
ITEMS_PER_PAGE_ACCESS_REQUESTS = 5
ASSIGN_ROLE_MENU_TEXT_RAW_MD2_TEMPLATE = "👤 Assign Role for User: {username} \\({chat_id}\\)"


async def display_pending_access_requests_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1) -> None:
    query = update.callback_query
    admin_chat_id = update.effective_chat.id

    if query:
        await query.answer()

        if query.data.startswith(CallbackData.ACCESS_REQUEST_ADMIN_PAGE_PREFIX.value):
            try:
                page = int(query.data.replace(
                    CallbackData.ACCESS_REQUEST_ADMIN_PAGE_PREFIX.value, ""))
            except ValueError:
                logger.warning(
                    f"Invalid page number in access request pagination: {query.data}")
                page = 1
        elif query.data == CallbackData.CMD_ADMIN_VIEW_ACCESS_REQUESTS.value:
            page = 1

    admin_user_role = app_config_holder.get_user_role(str(admin_chat_id))
    if admin_user_role != app_config_holder.ROLE_ADMIN:
        logger.warning(
            f"Unauthorized access attempt to admin view access requests by chat_id {admin_chat_id} (Role: {admin_user_role})")
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, "⚠️ Access Denied. This section is for administrators.", parse_mode=None)
        return

    pending_requests_dict = user_manager.get_pending_access_requests()

    pending_requests_list = sorted(
        pending_requests_dict.items(),

        key=lambda item: item[1].get("timestamp", "")
    )

    total_items = len(pending_requests_list)
    items_per_page_to_use = ITEMS_PER_PAGE_ACCESS_REQUESTS
    total_pages = math.ceil(
        total_items / items_per_page_to_use) if total_items > 0 else 1
    current_page = max(1, min(page, total_pages))
    context.user_data['admin_access_requests_current_page'] = current_page

    start_index = (current_page - 1) * items_per_page_to_use
    end_index = start_index + items_per_page_to_use
    page_items = pending_requests_list[start_index:end_index]

    keyboard = []
    title_template_for_escape = PENDING_ACCESS_REQUESTS_TITLE_TEMPLATE_RAW.replace(
        "(", "\\(").replace(")", "\\)")
    menu_title_display = escape_md_v2(title_template_for_escape.format(
        current_page=current_page, total_pages=total_pages))

    status_message_parts = [
        f"Displaying pending access requests page {current_page} of {total_pages}."]
    menu_body_parts = ["\n"]

    if not page_items:
        if total_items == 0:
            status_message_parts = ["✅ No pending user access requests."]
            menu_body_parts.append(escape_md_v2(
                "\n_There are currently no pending access requests._"))
        else:
            status_message_parts = [
                f"No access requests found on page {current_page}."]
            menu_body_parts.append(escape_md_v2(
                "\n_No requests to display on this page._"))
    else:
        for req_chat_id_str, req_data in page_items:
            username_raw = req_data.get("username", f"User_{req_chat_id_str}")
            timestamp_raw = req_data.get("timestamp")

            req_date_display = "Unknown time"
            if timestamp_raw:
                try:
                    dt_obj = datetime.datetime.fromisoformat(timestamp_raw.replace(
                        "Z", "+00:00"))
                    req_date_display = dt_obj.astimezone().strftime('%Y-%m-%d %H:%M')
                except ValueError:
                    req_date_display = timestamp_raw

            display_info = f"{escape_md_v2(username_raw)} \\(ID: {escape_md_v2(req_chat_id_str)}\\)\n  Requested: {escape_md_v2(req_date_display)}"
            menu_body_parts.append(display_info + "\n")
            keyboard.append([
                InlineKeyboardButton(
                    f"✅ Approve: {username_raw[:20]}", callback_data=f"{CallbackData.ACCESS_REQUEST_APPROVE_PREFIX.value}{req_chat_id_str}"),
                InlineKeyboardButton(
                    f"❌ Deny: {username_raw[:20]}", callback_data=f"{CallbackData.ACCESS_REQUEST_DENY_PREFIX.value}{req_chat_id_str}")
            ])

    final_menu_display_text = menu_title_display + "".join(menu_body_parts)
    if len(final_menu_display_text) > 4096:
        final_menu_display_text = final_menu_display_text[:4090] + escape_md_v2(
            "...")

    pagination_row = []
    if current_page > 1:
        pagination_row.append(InlineKeyboardButton(

            "◀️ Prev", callback_data=f"{CallbackData.ACCESS_REQUEST_ADMIN_PAGE_PREFIX.value}{current_page-1}"))
    if current_page < total_pages:
        pagination_row.append(InlineKeyboardButton(
            "Next ▶️", callback_data=f"{CallbackData.ACCESS_REQUEST_ADMIN_PAGE_PREFIX.value}{current_page+1}"))
    if pagination_row:
        keyboard.append(pagination_row)

    keyboard.append([InlineKeyboardButton(
        "🔄 Refresh List", callback_data=CallbackData.CMD_ADMIN_VIEW_ACCESS_REQUESTS.value)])
    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu",
                    callback_data=CallbackData.CMD_HOME_BACK.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await send_or_edit_universal_status_message(context.bot, admin_chat_id, "\n".join(status_message_parts), parse_mode=None)

    menu_message_id = load_menu_message_id(str(admin_chat_id))
    if menu_message_id:
        try:
            current_content_key = f"menu_message_content_{admin_chat_id}_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (final_menu_display_text,
                                 reply_markup.to_json())
            if old_content_tuple != new_content_tuple:
                await context.bot.edit_message_text(
                    chat_id=admin_chat_id, message_id=menu_message_id,
                    text=final_menu_display_text, reply_markup=reply_markup, parse_mode="MarkdownV2"
                )
                context.bot_data[current_content_key] = new_content_tuple
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                logger.error(
                    f"Error displaying pending access requests (edit): {e}", exc_info=True)
        except Exception as e:
            logger.error(
                f"Unexpected error displaying pending access requests: {e}", exc_info=True)
    else:
        logger.error(
            f"Cannot find menu_message_id for pending access requests for admin {admin_chat_id}.")
        await show_or_edit_main_menu(str(admin_chat_id), context, force_send_new=True)


async def handle_approve_access_request_initiate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    admin_chat_id = update.effective_chat.id

    admin_user_role = app_config_holder.get_user_role(str(admin_chat_id))
    if admin_user_role != app_config_holder.ROLE_ADMIN:
        await query.answer("Access Denied.", show_alert=True)
        return

    requester_chat_id_str = query.data.replace(
        CallbackData.ACCESS_REQUEST_APPROVE_PREFIX.value, "")
    await query.answer()

    pending_requests = user_manager.get_pending_access_requests()
    requester_data = pending_requests.get(requester_chat_id_str)

    if not requester_data:
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, "⚠️ User not found in pending requests list (might have been processed).", parse_mode=None)
        await display_pending_access_requests_menu(update, context, page=context.user_data.get('admin_access_requests_current_page', 1))
        return

    requester_username = requester_data.get(
        "username", f"User_{requester_chat_id_str}")
    context.user_data['approving_access_for_user'] = {
        "chat_id": requester_chat_id_str, "username": requester_username}

    keyboard = [
        [InlineKeyboardButton(f"Assign as {app_config_holder.ROLE_STANDARD_USER}",
                              callback_data=f"{CallbackData.ACCESS_REQUEST_ASSIGN_ROLE_PREFIX.value}{requester_chat_id_str}_{app_config_holder.ROLE_STANDARD_USER}")],
        [InlineKeyboardButton(f"Assign as {app_config_holder.ROLE_ADMIN}",
                              callback_data=f"{CallbackData.ACCESS_REQUEST_ASSIGN_ROLE_PREFIX.value}{requester_chat_id_str}_{app_config_holder.ROLE_ADMIN}")],

        [InlineKeyboardButton(
            "🔙 Cancel Approval", callback_data=CallbackData.CMD_ADMIN_VIEW_ACCESS_REQUESTS.value)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    escaped_req_username = escape_md_v2(requester_username)
    escaped_req_chat_id_str = escape_md_v2(requester_chat_id_str)
    menu_text = ASSIGN_ROLE_MENU_TEXT_RAW_MD2_TEMPLATE.format(
        username=escaped_req_username,
        chat_id=escaped_req_chat_id_str
    )

    status_text_md2 = f"Preparing to approve access for {escaped_req_username} \\({escaped_req_chat_id_str}\\)\\."
    await send_or_edit_universal_status_message(context.bot, admin_chat_id, status_text_md2, parse_mode="MarkdownV2")

    menu_message_id = load_menu_message_id(str(admin_chat_id))
    if menu_message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=admin_chat_id, message_id=menu_message_id,
                text=menu_text, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )
            context.bot_data[f"menu_message_content_{admin_chat_id}_{menu_message_id}"] = (
                menu_text, reply_markup.to_json())
        except Exception as e:
            logger.error(
                f"Error displaying role assignment menu: {e}", exc_info=True)
    else:
        logger.error("Cannot find menu_message_id for role assignment.")


async def handle_approve_access_request_assign_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    admin_chat_id = update.effective_chat.id

    admin_user_role = app_config_holder.get_user_role(str(admin_chat_id))
    if admin_user_role != app_config_holder.ROLE_ADMIN:
        await query.answer("Access Denied.", show_alert=True)
        return

    payload = query.data.replace(
        CallbackData.ACCESS_REQUEST_ASSIGN_ROLE_PREFIX.value, "")
    parts = payload.split("_", 1)
    if len(parts) != 2:
        logger.error(f"Invalid payload for role assignment: {query.data}")
        await query.answer("Error processing role assignment.", show_alert=True)
        return

    requester_chat_id_str, assigned_role = parts[0], parts[1]
    await query.answer(f"Assigning role {assigned_role}...")

    approving_user_context = context.user_data.get('approving_access_for_user')
    if not approving_user_context or approving_user_context.get("chat_id") != requester_chat_id_str:

        pending_reqs = user_manager.get_pending_access_requests()
        requester_data = pending_reqs.get(requester_chat_id_str)
        requester_username = requester_data.get(
            "username", f"User_{requester_chat_id_str}") if requester_data else f"User_{requester_chat_id_str}"
    else:
        requester_username = approving_user_context.get("username")

    if user_manager.add_approved_user(requester_chat_id_str, requester_username, assigned_role):

        success_msg_admin = f"✅ Access for {escape_md_v2(requester_username)} \\({escape_md_v2(requester_chat_id_str)}\\) approved as {escape_md_v2(assigned_role)}\\."
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, success_msg_admin, parse_mode="MarkdownV2")

        await show_or_edit_main_menu(requester_chat_id_str, context, force_send_new=True)

    else:
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, f"⚠️ Failed to approve access for {escape_md_v2(requester_username)}. See logs.", parse_mode="MarkdownV2")

    context.user_data.pop('approving_access_for_user', None)
    await display_pending_access_requests_menu(update, context, page=context.user_data.get('admin_access_requests_current_page', 1))


async def handle_deny_access_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    admin_chat_id = update.effective_chat.id

    admin_user_role = app_config_holder.get_user_role(str(admin_chat_id))
    if admin_user_role != app_config_holder.ROLE_ADMIN:
        await query.answer("Access Denied.", show_alert=True)
        return

    requester_chat_id_str = query.data.replace(
        CallbackData.ACCESS_REQUEST_DENY_PREFIX.value, "")
    await query.answer("Processing denial...")

    pending_requests = user_manager.get_pending_access_requests()
    requester_data = pending_requests.get(requester_chat_id_str)
    requester_username = requester_data.get(
        "username", f"User_{requester_chat_id_str}") if requester_data else f"User_{requester_chat_id_str}"

    if user_manager.remove_pending_access_request(requester_chat_id_str):
        success_msg_admin = f"🚫 Access for {escape_md_v2(requester_username)} ({escape_md_v2(requester_chat_id_str)}) has been denied."
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, success_msg_admin, parse_mode="MarkdownV2")

    else:
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, f"⚠️ User {escape_md_v2(requester_username)} not found in pending list or error removing. They may have been processed already.", parse_mode="MarkdownV2")

    await display_pending_access_requests_menu(update, context, page=context.user_data.get('admin_access_requests_current_page', 1))
