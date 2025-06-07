import logging
import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import datetime
from telegram.error import BadRequest

import src.app.app_config_holder as app_config_holder
import src.app.user_manager as user_manager
from src.bot.bot_callback_data import CallbackData
from src.bot.bot_initialization import send_or_edit_universal_status_message, show_or_edit_main_menu
from src.bot.bot_message_persistence import load_menu_message_id
from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)

MANAGE_USERS_TITLE_MD2_TEMPLATE = "👑 Manage Users & Requests"  # Unified Title
EDIT_USER_TITLE_MD2_TEMPLATE = "✏️ Edit User: {username} \\({chat_id}\\)"
ITEMS_PER_PAGE_USERS = 5

# Conversation states for adding a user
ASK_NEW_USER_CHAT_ID, ASK_NEW_USER_ROLE = range(2)


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
            page = 1  # Reset to page 1 if coming from main menu or back button

    # Clear old pagination if any
    context.user_data.pop('admin_access_requests_current_page', None)

    all_users_dict = user_manager.get_all_users_from_state()  # Existing users
    primary_admin_id_str = app_config_holder.get_chat_id_str()

    # Filter out the primary admin and sort by chat_id (numerically if possible)
    displayable_users_list = []
    for uid, udata in all_users_dict.items():
        if uid != primary_admin_id_str:
            displayable_users_list.append({'chat_id': uid, **udata})

    try:
        displayable_users_list.sort(
            key=lambda u: int(str(u['chat_id']).lstrip('-')))
    except ValueError:
        displayable_users_list.sort(key=lambda u: str(u['chat_id']))

    # --- Pagination for Existing Users ---
    # This part remains for the "Existing Users" section

    total_items = len(displayable_users_list)
    total_pages = math.ceil(
        total_items / ITEMS_PER_PAGE_USERS) if total_items > 0 else 1
    current_page = max(1, min(page, total_pages))
    context.user_data['admin_users_current_page'] = current_page

    start_index = (current_page - 1) * ITEMS_PER_PAGE_USERS
    end_index = start_index + ITEMS_PER_PAGE_USERS
    page_items = displayable_users_list[start_index:end_index]

    # --- Fetch Pending Access Requests ---
    pending_requests_dict = user_manager.get_pending_access_requests()
    pending_requests_list_sorted = sorted(
        pending_requests_dict.items(),
        key=lambda item: item[1].get("timestamp", "")
    )

    keyboard = []
    menu_title_display = escape_md_v2(MANAGE_USERS_TITLE_MD2_TEMPLATE)
    menu_body_parts = ["\n"]

    # --- Display Pending Access Requests ---
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

    # --- Display Existing Users (Paginated) ---
    if not page_items:  # This checks if the *current page* of existing users is empty
        if total_items == 0:
            menu_body_parts.append(escape_md_v2(
                "\n_No other users found besides the primary admin._"))
        else:
            # This case means there are users, but not on *this* page (e.g., if page > total_pages)
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

    # Pagination controls for existing users
    pagination_row = []
    if current_page > 1:
        pagination_row.append(InlineKeyboardButton(
            "◀️ Prev", callback_data=f"{CallbackData.CMD_ADMIN_USER_PAGE_PREFIX.value}{current_page-1}"))
    if current_page < total_pages:
        pagination_row.append(InlineKeyboardButton(
            "Next ▶️", callback_data=f"{CallbackData.CMD_ADMIN_USER_PAGE_PREFIX.value}{current_page+1}"))
    if pagination_row:
        # Insert pagination before Add User and Back buttons if there are users to paginate
        # Add pagination if there are items on this page OR if there are total items (even if current page is empty but valid)
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

    # Ensure only primary admin can edit
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

    # Store for actions
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
                # First, refresh the menu (it will be new)
                await show_or_edit_main_menu(user_to_change_id_str, context, force_send_new=True)
                # Then, send the universal status message (it will also be new and appear after the menu)
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

    # Re-display edit menu for the same user
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
                # Will show restricted menu
                await show_or_edit_main_menu(user_to_remove_id_str, context, force_send_new=True)
                # Then, send the universal status message
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

    context.user_data.pop('editing_user_id', None)  # Clear editing context
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
        return ConversationHandler.END  # Should not happen if conv started by admin

    if not update.message or not update.message.text:
        return ASK_NEW_USER_CHAT_ID  # Stay in state if no text

    # Delete user's message (chat ID input)
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
        return ASK_NEW_USER_ROLE  # Stay in role selection

    # Add user
    current_full_state = user_manager._load_bot_state(force_reload=True)
    users_in_state = current_full_state.get("users", {})
    users_in_state[new_user_chat_id] = {
        "username": f"User_{new_user_chat_id}", "role": selected_role}
    current_full_state["users"] = users_in_state

    if user_manager._save_bot_state(current_full_state):
        await send_or_edit_universal_status_message(context.bot, admin_chat_id, escape_md_v2(f"✅ User {new_user_chat_id} added with role {selected_role}."), parse_mode="MarkdownV2")
        try:
            await show_or_edit_main_menu(new_user_chat_id, context, force_send_new=True)
            # Then, send the universal status message
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
    # Go to first page after adding
    await display_manage_users_menu(update, context, page=1)
    return ConversationHandler.END


async def cancel_add_user_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_chat_id = update.effective_chat.id
    if update.message:  # If /cancel command
        try:
            await update.message.delete()
        except Exception:
            pass

    await send_or_edit_universal_status_message(context.bot, admin_chat_id, "User addition cancelled.", parse_mode=None)
    context.user_data.pop('admin_adding_user_flow', None)
    context.user_data.pop('admin_new_user_chat_id', None)

    # Create a dummy query to pass to display_manage_users_menu
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
