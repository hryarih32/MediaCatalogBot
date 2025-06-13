import logging
import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import datetime
from telegram.error import BadRequest
import time
import uuid

import src.app.app_config_holder as app_config_holder
import src.app.user_manager as user_manager
from src.bot.bot_callback_data import CallbackData
from src.bot.bot_initialization import send_or_edit_universal_status_message, show_or_edit_main_menu
from src.bot.bot_message_persistence import load_menu_message_id
from src.app.app_file_utils import load_tickets_data, save_tickets_data  # New import
from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)

MANAGE_USERS_TITLE_MD2_TEMPLATE = "👑 Manage Users & Requests"
EDIT_USER_TITLE_MD2_TEMPLATE = "✏️ Edit User: {username} \\({chat_id}\\)"
ITEMS_PER_PAGE_USERS = 5

ASK_NEW_USER_CHAT_ID, ASK_NEW_USER_ROLE, AWAITING_ADMIN_MESSAGE_TEXT = range(3)


async def display_manage_users_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1) -> None:
    query = update.callback_query
    admin_chat_id = update.effective_chat.id

    if not app_config_holder.is_primary_admin(str(admin_chat_id)):
        logger.warning(
            f"Non-primary admin {admin_chat_id} attempted to access user management.")
        if query:
            await query.answer("Access Denied.", show_alert=True)
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, "⚠️ This section is for the Primary Administrator only.", parse_mode=None)
        return

    if query:
        await query.answer()
        if query.data.startswith(CallbackData.CMD_ADMIN_USER_PAGE_PREFIX.value):
            try:
                page = int(query.data.replace(
                    CallbackData.CMD_ADMIN_USER_PAGE_PREFIX.value, ""))
            except ValueError:
                page = 1
        elif query.data == CallbackData.CMD_ADMIN_MANAGE_USERS_MENU.value:
            page = 1

    context.user_data.pop('admin_access_requests_current_page', None)

    all_users_dict = user_manager.get_all_users_from_state()
    primary_admin_id_str = app_config_holder.get_chat_id_str()

    displayable_users_list = []
    for uid, udata in all_users_dict.items():
        if uid != primary_admin_id_str:
            displayable_users_list.append({'chat_id': uid, **udata})

    try:
        displayable_users_list.sort(
            key=lambda u: int(str(u['chat_id']).lstrip('-')))
    except ValueError:
        displayable_users_list.sort(key=lambda u: str(u['chat_id']))

    total_items = len(displayable_users_list)
    total_pages = math.ceil(
        total_items / ITEMS_PER_PAGE_USERS) if total_items > 0 else 1
    current_page = max(1, min(page, total_pages))
    context.user_data['admin_users_current_page'] = current_page

    start_index = (current_page - 1) * ITEMS_PER_PAGE_USERS
    end_index = start_index + ITEMS_PER_PAGE_USERS
    page_items = displayable_users_list[start_index:end_index]

    pending_requests_dict = user_manager.get_pending_access_requests()
    pending_requests_list_sorted = sorted(
        pending_requests_dict.items(),
        key=lambda item: item[1].get("timestamp", "")
    )

    keyboard = []
    menu_title_display = escape_md_v2(MANAGE_USERS_TITLE_MD2_TEMPLATE)
    menu_body_parts = ["\n"]

    if pending_requests_list_sorted:
        menu_body_parts.append(escape_md_v2(
            "\n--- 🔑 Pending Access Requests ---\n"))
        for req_chat_id_str, req_data in pending_requests_list_sorted:
            username_raw = req_data.get("username", f"User_{req_chat_id_str}")
            timestamp_raw = req_data.get("timestamp")
            req_date_display = "Unknown time"
            if timestamp_raw:
                try:
                    dt_obj = datetime.datetime.fromisoformat(
                        timestamp_raw.replace("Z", "+00:00"))
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
        menu_body_parts.append(escape_md_v2("\n--- 👥 Existing Users ---\n"))
    else:
        menu_body_parts.append(escape_md_v2(
            "\n_No pending access requests at this time._\n"))
        menu_body_parts.append(escape_md_v2("\n--- 👥 Existing Users ---\n"))

    if not page_items:
        if total_items == 0:
            menu_body_parts.append(escape_md_v2(
                "\n_No other users found besides the primary admin._"))
        else:

            menu_body_parts.append(escape_md_v2(
                f"\n_No existing users to display on page {current_page}._"))
    else:
        for user_data in page_items:
            uid_str = str(user_data.get('chat_id', 'N/A'))
            uname = user_data.get('username', f'User_{uid_str}')
            urole = user_data.get('role', 'UNKNOWN')
            display_text = f"{escape_md_v2(uname)} \\({escape_md_v2(uid_str)}\\) \\- Role: {escape_md_v2(urole)}"
            menu_body_parts.append(f"👤 {display_text}\n")
            keyboard.append([InlineKeyboardButton(
                f"✏️ Edit: {uname[:25]}", callback_data=f"{CallbackData.CMD_ADMIN_USER_SELECT_FOR_EDIT_PREFIX.value}{uid_str}")])

    pagination_row = []
    if current_page > 1:
        pagination_row.append(InlineKeyboardButton(
            "◀️ Prev", callback_data=f"{CallbackData.CMD_ADMIN_USER_PAGE_PREFIX.value}{current_page-1}"))
    if current_page < total_pages:
        pagination_row.append(InlineKeyboardButton(
            "Next ▶️", callback_data=f"{CallbackData.CMD_ADMIN_USER_PAGE_PREFIX.value}{current_page+1}"))
    if pagination_row:

        if page_items or total_items > 0:
            menu_body_parts.append(escape_md_v2(
                f"\n_Showing existing users page {current_page} of {total_pages}_"))
            keyboard.append(pagination_row)

    final_menu_text = menu_title_display + "".join(menu_body_parts)
    keyboard.append([InlineKeyboardButton(
        "➕ Add New User", callback_data=CallbackData.CMD_ADMIN_USER_ADD_INIT.value)])
    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu",
                    callback_data=CallbackData.CMD_HOME_BACK.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await send_or_edit_universal_status_message(context.bot, admin_chat_id, f"Displaying users & requests. Users page {current_page} of {total_pages}.", parse_mode=None)

    menu_message_id = load_menu_message_id(str(admin_chat_id))
    if menu_message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=admin_chat_id, message_id=menu_message_id,
                text=final_menu_text, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )
            context.bot_data[f"menu_message_content_{admin_chat_id}_{menu_message_id}"] = (
                final_menu_text, reply_markup.to_json())
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                logger.error(
                    f"Error displaying manage users menu (edit): {e}", exc_info=True)
        except Exception as e:
            logger.error(
                f"Unexpected error displaying manage users menu: {e}", exc_info=True)
    else:
        await show_or_edit_main_menu(str(admin_chat_id), context, force_send_new=True)


async def display_edit_user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    admin_chat_id = update.effective_chat.id

    if not app_config_holder.is_primary_admin(str(admin_chat_id)):
        await query.answer("Access Denied.", show_alert=True)
        return

    user_to_edit_id_str = query.data.replace(
        CallbackData.CMD_ADMIN_USER_SELECT_FOR_EDIT_PREFIX.value, "")
    await query.answer()

    all_users = user_manager.get_all_users_from_state()
    user_data_to_edit = all_users.get(user_to_edit_id_str)

    if not user_data_to_edit or user_to_edit_id_str == app_config_holder.get_chat_id_str():
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, "⚠️ User not found or cannot edit primary admin.", parse_mode=None)
        await display_manage_users_menu(update, context, page=context.user_data.get('admin_users_current_page', 1))
        return

    context.user_data['editing_user_id'] = user_to_edit_id_str

    username_to_edit = user_data_to_edit.get(
        'username', f"User_{user_to_edit_id_str}")
    current_role = user_data_to_edit.get(
        'role', app_config_holder.ROLE_UNKNOWN)

    menu_text = EDIT_USER_TITLE_MD2_TEMPLATE.format(
        username=escape_md_v2(username_to_edit),
        chat_id=escape_md_v2(user_to_edit_id_str)
    )
    menu_text += f"\n\nCurrent Role: *{escape_md_v2(current_role)}*"

    keyboard = []
    if current_role != app_config_holder.ROLE_ADMIN:
        keyboard.append([InlineKeyboardButton(
            "👑 Set Role: Admin", callback_data=f"{CallbackData.CMD_ADMIN_USER_CHANGE_ROLE_PREFIX.value}{user_to_edit_id_str}_{app_config_holder.ROLE_ADMIN}")])
    if current_role != app_config_holder.ROLE_STANDARD_USER:
        keyboard.append([InlineKeyboardButton("👤 Set Role: Standard User",
                        callback_data=f"{CallbackData.CMD_ADMIN_USER_CHANGE_ROLE_PREFIX.value}{user_to_edit_id_str}_{app_config_holder.ROLE_STANDARD_USER}")])
    keyboard.append([InlineKeyboardButton("💬 Create Ticket for User",  # Changed button text
                    callback_data=f"{CallbackData.CMD_ADMIN_CREATE_TICKET_FOR_USER_INIT_PREFIX.value}{user_to_edit_id_str}")])

    keyboard.append([InlineKeyboardButton(
        "🗑️ Remove User", callback_data=f"{CallbackData.CMD_ADMIN_USER_REMOVE_PREFIX.value}{user_to_edit_id_str}")])
    keyboard.append([InlineKeyboardButton("🔙 Back to User List",
                    callback_data=CallbackData.CMD_ADMIN_MANAGE_USERS_MENU.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)

    menu_message_id = load_menu_message_id(str(admin_chat_id))
    if menu_message_id:
        await context.bot.edit_message_text(
            chat_id=admin_chat_id, message_id=menu_message_id,
            text=menu_text, reply_markup=reply_markup, parse_mode="MarkdownV2"
        )
        context.bot_data[f"menu_message_content_{admin_chat_id}_{menu_message_id}"] = (
            menu_text, reply_markup.to_json())
    await send_or_edit_universal_status_message(context.bot, admin_chat_id, f"Editing user: {username_to_edit}.", parse_mode=None)


async def handle_change_user_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    admin_chat_id = update.effective_chat.id

    if not app_config_holder.is_primary_admin(str(admin_chat_id)):
        await query.answer("Access Denied.", show_alert=True)
        return

    payload = query.data.replace(
        CallbackData.CMD_ADMIN_USER_CHANGE_ROLE_PREFIX.value, "")
    parts = payload.split("_", 1)
    if len(parts) != 2:
        await query.answer("Error processing role change.", show_alert=True)
        return

    user_to_change_id_str, new_role = parts[0], parts[1]
    await query.answer(f"Changing role to {new_role}...")

    if user_to_change_id_str == app_config_holder.get_chat_id_str():
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, "⚠️ Cannot change the role of the Primary Administrator.", parse_mode=None)
        await display_manage_users_menu(update, context, page=context.user_data.get('admin_users_current_page', 1))
        return

    current_full_state = user_manager._load_bot_state(force_reload=True)
    users_in_state = current_full_state.get("users", {})
    user_to_modify = users_in_state.get(user_to_change_id_str)

    if user_to_modify:
        old_role = user_to_modify.get("role")
        user_to_modify["role"] = new_role
        current_full_state["users"] = users_in_state
        if user_manager._save_bot_state(current_full_state):
            username_changed = user_to_modify.get(
                'username', user_to_change_id_str)
            await send_or_edit_universal_status_message(context.bot, admin_chat_id, escape_md_v2(f"✅ Role for {username_changed} changed to {new_role}."), parse_mode="MarkdownV2")
            try:

                await show_or_edit_main_menu(user_to_change_id_str, context, force_send_new=True)

                user_notification_text = f"ℹ️ Your role has been updated to: {new_role} by the administrator."
                await send_or_edit_universal_status_message(
                    context.bot, int(
                        user_to_change_id_str), user_notification_text,
                    parse_mode=None, force_send_new=True)
            except Exception as e_notify:
                logger.warning(
                    f"Could not notify user {user_to_change_id_str} about role change: {e_notify}", exc_info=False)
        else:
            await send_or_edit_universal_status_message(context.bot, admin_chat_id, "⚠️ Failed to save role change.", parse_mode=None)
    else:
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, "⚠️ User not found to change role.", parse_mode=None)

    await display_edit_user_menu(update, context)


async def handle_remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    admin_chat_id = update.effective_chat.id

    if not app_config_holder.is_primary_admin(str(admin_chat_id)):
        await query.answer("Access Denied.", show_alert=True)
        return

    user_to_remove_id_str = query.data.replace(
        CallbackData.CMD_ADMIN_USER_REMOVE_PREFIX.value, "")
    await query.answer(f"Removing user {user_to_remove_id_str}...")

    if user_to_remove_id_str == app_config_holder.get_chat_id_str():
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, "⚠️ Cannot remove the Primary Administrator.", parse_mode=None)
        await display_manage_users_menu(update, context, page=context.user_data.get('admin_users_current_page', 1))
        return

    current_full_state = user_manager._load_bot_state(force_reload=True)
    users_in_state = current_full_state.get("users", {})
    user_removed_data = users_in_state.pop(user_to_remove_id_str, None)

    if user_removed_data:
        current_full_state["users"] = users_in_state
        if user_manager._save_bot_state(current_full_state):
            username_removed = user_removed_data.get(
                'username', user_to_remove_id_str)
            await send_or_edit_universal_status_message(context.bot, admin_chat_id, escape_md_v2(f"✅ User {username_removed} removed."), parse_mode="MarkdownV2")
            try:

                await show_or_edit_main_menu(user_to_remove_id_str, context, force_send_new=True)

                user_notification_text = "ℹ️ Your access to this bot has been revoked by the administrator."
                await send_or_edit_universal_status_message(
                    context.bot, int(
                        user_to_remove_id_str), user_notification_text,
                    parse_mode=None, force_send_new=True)
            except Exception as e_notify_removed:
                logger.warning(
                    f"Could not notify user {user_to_remove_id_str} about removal: {e_notify_removed}", exc_info=False)
        else:
            await send_or_edit_universal_status_message(context.bot, admin_chat_id, "⚠️ Failed to save user removal.", parse_mode=None)
    else:
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, "⚠️ User not found for removal.", parse_mode=None)

    context.user_data.pop('editing_user_id', None)
    await display_manage_users_menu(update, context, page=context.user_data.get('admin_users_current_page', 1))


async def handle_add_user_init(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    admin_chat_id = update.effective_chat.id

    if not app_config_holder.is_primary_admin(str(admin_chat_id)):
        await query.answer("Access Denied.", show_alert=True)
        return ConversationHandler.END
    await query.answer()

    await send_or_edit_universal_status_message(context.bot, admin_chat_id, "💬 Please send the Telegram Chat ID of the new user (must be a number). Send /cancel to abort.", parse_mode=None)
    context.user_data['admin_adding_user_flow'] = 'ask_chat_id'
    return ASK_NEW_USER_CHAT_ID


async def handle_add_user_chat_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_chat_id = update.effective_chat.id
    if not app_config_holder.is_primary_admin(str(admin_chat_id)):
        return ConversationHandler.END

    if not update.message or not update.message.text:
        return ASK_NEW_USER_CHAT_ID

    try:
        await update.message.delete()
    except Exception as e:
        logger.warning(f"Could not delete user's chat ID input message: {e}")

    new_user_chat_id_str = update.message.text.strip()
    if not new_user_chat_id_str.lstrip('-').isdigit():
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, "⚠️ Invalid Chat ID. It must be a number. Please try again or /cancel.", parse_mode=None)
        return ASK_NEW_USER_CHAT_ID

    if new_user_chat_id_str == app_config_holder.get_chat_id_str():
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, "⚠️ Cannot add the Primary Administrator. Try a different Chat ID or /cancel.", parse_mode=None)
        return ASK_NEW_USER_CHAT_ID

    all_users = user_manager.get_all_users_from_state()
    if new_user_chat_id_str in all_users:
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, f"⚠️ User with Chat ID {escape_md_v2(new_user_chat_id_str)} already exists. Try a different Chat ID or /cancel.", parse_mode="MarkdownV2")
        return ASK_NEW_USER_CHAT_ID

    context.user_data['admin_new_user_chat_id'] = new_user_chat_id_str
    context.user_data['admin_adding_user_flow'] = 'ask_role'

    keyboard = [
        [InlineKeyboardButton(
            "👑 Assign Role: Admin", callback_data=f"assign_role_{app_config_holder.ROLE_ADMIN}")],
        [InlineKeyboardButton("👤 Assign Role: Standard User",
                              callback_data=f"assign_role_{app_config_holder.ROLE_STANDARD_USER}")],
        [InlineKeyboardButton("❌ Cancel Add User",
                              callback_data="cancel_add_user")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await send_or_edit_universal_status_message(context.bot, admin_chat_id, f"➕ Adding user with Chat ID: {escape_md_v2(new_user_chat_id_str)}\\. Select a role:", reply_markup=reply_markup, parse_mode="MarkdownV2")
    return ASK_NEW_USER_ROLE


async def handle_add_user_role_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    admin_chat_id = update.effective_chat.id
    if not app_config_holder.is_primary_admin(str(admin_chat_id)):
        await query.answer("Access Denied.", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    action = query.data

    if action == "cancel_add_user":
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, "User addition cancelled.", parse_mode=None)
        context.user_data.pop('admin_adding_user_flow', None)
        context.user_data.pop('admin_new_user_chat_id', None)
        await display_manage_users_menu(update, context, page=context.user_data.get('admin_users_current_page', 1))
        return ConversationHandler.END

    new_user_chat_id = context.user_data.get('admin_new_user_chat_id')
    if not new_user_chat_id:
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, "⚠️ Error: User Chat ID not found in session. Please start over.", parse_mode=None)
        await display_manage_users_menu(update, context, page=context.user_data.get('admin_users_current_page', 1))
        return ConversationHandler.END

    selected_role = ""
    if action == f"assign_role_{app_config_holder.ROLE_ADMIN}":
        selected_role = app_config_holder.ROLE_ADMIN
    elif action == f"assign_role_{app_config_holder.ROLE_STANDARD_USER}":
        selected_role = app_config_holder.ROLE_STANDARD_USER
    else:
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, "⚠️ Invalid role selection.", parse_mode=None)
        return ASK_NEW_USER_ROLE

    current_full_state = user_manager._load_bot_state(force_reload=True)
    users_in_state = current_full_state.get("users", {})
    users_in_state[new_user_chat_id] = {
        "username": f"User_{new_user_chat_id}", "role": selected_role}
    current_full_state["users"] = users_in_state

    if user_manager._save_bot_state(current_full_state):
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, escape_md_v2(f"✅ User {new_user_chat_id} added with role {selected_role}."), parse_mode="MarkdownV2")
        try:
            await show_or_edit_main_menu(new_user_chat_id, context, force_send_new=True)

            user_notification_text = f"ℹ️ You have been granted access to this bot with the role: {selected_role}."
            await send_or_edit_universal_status_message(
                context.bot, int(new_user_chat_id), user_notification_text,
                parse_mode=None, force_send_new=True)
        except Exception as e_notify_new:
            logger.warning(
                f"Could not notify newly added user {new_user_chat_id}: {e_notify_new}", exc_info=False)
    else:
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, "⚠️ Failed to save new user.", parse_mode=None)

    context.user_data.pop('admin_adding_user_flow', None)
    context.user_data.pop('admin_new_user_chat_id', None)

    await display_manage_users_menu(update, context, page=1)
    return ConversationHandler.END


async def cancel_add_user_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_chat_id = update.effective_chat.id
    if update.message:
        try:
            await update.message.delete()
        except Exception:
            pass

    await send_or_edit_universal_status_message(context.bot, admin_chat_id, "User addition cancelled.", parse_mode=None)
    context.user_data.pop('admin_adding_user_flow', None)
    context.user_data.pop('admin_new_user_chat_id', None)

    class DummyQuery:
        def __init__(self, data_val, message_obj, from_user_obj):
            self.data = data_val
            self.message = message_obj
            self.from_user = from_user_obj

        async def answer(self): pass

    menu_msg_id = load_menu_message_id(str(admin_chat_id))
    if menu_msg_id:
        dummy_msg = type('DummyMessage', (), {
                         'chat_id': admin_chat_id, 'message_id': menu_msg_id, 'chat': update.effective_chat})()
        dummy_q = DummyQuery(
            CallbackData.CMD_ADMIN_MANAGE_USERS_MENU.value, dummy_msg, update.effective_user)
        dummy_update = Update(update_id=update.update_id,
                              callback_query=dummy_q)
        setattr(dummy_update, 'effective_user', update.effective_user)
        setattr(dummy_update, 'effective_chat', update.effective_chat)
        await display_manage_users_menu(dummy_update, context, page=context.user_data.get('admin_users_current_page', 1))
    else:
        await show_or_edit_main_menu(str(admin_chat_id), context)
    return ConversationHandler.END


# --- Conversation for Sending Message to User ---
# Renamed
async def handle_create_ticket_for_user_init(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    admin_chat_id = update.effective_chat.id

    if not app_config_holder.is_primary_admin(str(admin_chat_id)):
        await query.answer("Access Denied.", show_alert=True)
        return ConversationHandler.END

    target_user_id_str = query.data.replace(
        CallbackData.CMD_ADMIN_CREATE_TICKET_FOR_USER_INIT_PREFIX.value, "")  # Updated CB
    await query.answer()

    all_users = user_manager.get_all_users_from_state()
    target_user_data = all_users.get(target_user_id_str)

    if not target_user_data:
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, "⚠️ User not found.", parse_mode=None)
        return ConversationHandler.END

    target_username = target_user_data.get(
        'username', f"User_{target_user_id_str}")

    context.user_data['admin_creating_ticket_for_user_id'] = target_user_id_str
    context.user_data['admin_creating_ticket_for_username'] = target_username

    prompt_text = f"📝 Enter the initial message for the new ticket to {escape_md_v2(target_username)} \\({escape_md_v2(target_user_id_str)}\\)\\. Send /cancel\\_ticket to abort\\."
    prompt_msg = await send_or_edit_universal_status_message(context.bot, admin_chat_id, prompt_text, parse_mode="MarkdownV2")
    if prompt_msg:
        context.user_data['admin_creating_ticket_prompt_msg_id'] = prompt_msg

    return AWAITING_ADMIN_MESSAGE_TEXT


# Renamed
async def handle_admin_initial_ticket_message_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_chat_id = update.effective_chat.id
    if not app_config_holder.is_primary_admin(str(admin_chat_id)) or not update.message:
        return ConversationHandler.END

    admin_message_text = update.message.text
    admin_input_msg_id = update.message.message_id

    target_user_id_str = context.user_data.get(
        'admin_creating_ticket_for_user_id')
    target_username = context.user_data.get(
        'admin_creating_ticket_for_username', 'the user')
    prompt_msg_id = context.user_data.pop(
        'admin_creating_ticket_prompt_msg_id', None)

    try:
        await context.bot.delete_message(chat_id=admin_chat_id, message_id=admin_input_msg_id)
        if prompt_msg_id:
            await context.bot.delete_message(chat_id=admin_chat_id, message_id=prompt_msg_id)
    except Exception as e_del:
        logger.warning(f"Could not delete admin message input/prompt: {e_del}")

    if not target_user_id_str:
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, "⚠️ Error: Target user ID not found. Ticket not created.", parse_mode=None)
        return ConversationHandler.END

    try:
        # Create and store the new ticket
        ticket_id = str(uuid.uuid4())
        # support_tickets_store = context.application.bot_data.setdefault('support_tickets', {}) # Old
        support_tickets_store = load_tickets_data()  # New

        new_ticket = {
            "ticket_id": ticket_id,
            "user_chat_id": target_user_id_str,
            "user_username": target_username,  # Username of the target user
            # ID of the admin creating the ticket
            "admin_chat_id": str(admin_chat_id),
            "status": "open_by_admin",  # Initial status
            "created_at": time.time(),
            "last_updated_at": time.time(),
            "messages": [
                {
                    "sender_id": str(admin_chat_id),
                    # Admin's username
                    "sender_username": update.effective_user.username or str(admin_chat_id),
                    "sender_type": "admin",
                    "text": admin_message_text,
                    "timestamp": time.time()
                }
            ]
        }
        support_tickets_store[ticket_id] = new_ticket
        save_tickets_data(support_tickets_store)  # New
        logger.info(
            f"Admin {admin_chat_id} created new ticket (ID: {ticket_id}) for user {target_user_id_str}")

        # Schedule a job to refresh the target user's UI
        async def refresh_user_ui_job(job_context: ContextTypes.DEFAULT_TYPE):
            user_id_to_refresh = job_context.job.data.get('chat_id')
            if user_id_to_refresh:
                logger.info(
                    f"Job: Refreshing UI for user {user_id_to_refresh} due to new ticket from admin.")
                await show_or_edit_main_menu(str(user_id_to_refresh), job_context.application)
                await send_or_edit_universal_status_message(
                    job_context.bot, int(user_id_to_refresh),
                    "📬 You have a new ticket from the administrator. Check your main menu or /tickets.",
                    parse_mode=None
                )
        context.application.job_queue.run_once(refresh_user_ui_job, 0.5, data={
                                               # Use short ID for job name
                                               'chat_id': target_user_id_str}, name=f"refresh_ui_new_ticket_{target_user_id_str}_{ticket_id[:8]}")

        success_message_text_raw = f"✅ Ticket #{ticket_id[:8]} created for {target_username}."
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, escape_md_v2(success_message_text_raw), parse_mode="MarkdownV2")

    except Exception as e:
        error_message_text_raw = f"⚠️ Failed to create ticket for {target_username}. Error: {str(e)}"
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, escape_md_v2(error_message_text_raw), parse_mode="MarkdownV2")
        logger.error(
            f"Failed to create ticket from admin {admin_chat_id} for user {target_user_id_str}: {e}", exc_info=True)

    context.user_data.pop('admin_creating_ticket_for_user_id', None)
    context.user_data.pop('admin_creating_ticket_for_username', None)
    return ConversationHandler.END


async def cancel_send_message_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_chat_id = update.effective_chat.id
    prompt_msg_id = context.user_data.pop(
        'admin_creating_ticket_prompt_msg_id', None)  # Updated key
    if prompt_msg_id:
        try:
            await context.bot.delete_message(chat_id=admin_chat_id, message_id=prompt_msg_id)
        except Exception:
            pass
    # Updated text
    await send_or_edit_universal_status_message(context.bot, admin_chat_id, "Ticket creation cancelled.", parse_mode=None)
    context.user_data.pop('admin_creating_ticket_for_user_id', None)
    context.user_data.pop('admin_creating_ticket_for_username', None)
    return ConversationHandler.END
