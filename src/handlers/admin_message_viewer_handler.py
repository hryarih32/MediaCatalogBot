import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import time  # Added for timestamp formatting
from telegram.ext import ContextTypes, ConversationHandler
import uuid

import src.app.app_config_holder as app_config_holder
from src.bot.bot_callback_data import CallbackData
from src.bot.bot_initialization import send_or_edit_universal_status_message, show_or_edit_main_menu
from src.bot.bot_message_persistence import load_menu_message_id
from src.app.app_file_utils import load_tickets_data, save_tickets_data  # New import
from src.handlers.tickets_handler import display_tickets_menu  # Added import
from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)

ADMIN_VIEW_TICKET_MENU_TITLE_RAW = "🎫 Ticket Details"
# Define as a simple integer for a single state
AWAITING_ADMIN_TICKET_REPLY_TEXT = 0


# Renamed
async def handle_admin_view_ticket_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    admin_chat_id_str = str(update.effective_chat.id)

    admin_user_role = app_config_holder.get_user_role(
        admin_chat_id_str)  # Get the role
    if admin_user_role != app_config_holder.ROLE_ADMIN:  # Check for general admin role
        await query.answer("Access Denied. This action is for administrators.", show_alert=True)
        return
    await query.answer()

    ticket_id_to_view = query.data.replace(
        CallbackData.CMD_ADMIN_VIEW_TICKET_PREFIX.value, "")  # Updated CB

    support_tickets_store = load_tickets_data()  # New
    ticket_data = support_tickets_store.get(ticket_id_to_view)

    if not ticket_data:
        await send_or_edit_universal_status_message(context.bot, int(admin_chat_id_str), "⚠️ Ticket not found or already handled. Returning to ticket list.", parse_mode=None, force_send_new=True)
        await show_or_edit_main_menu(admin_chat_id_str, context.application)
        return  # Important to return here

    # Display the full thread
    thread_display_parts = [
        f"🎫 *Ticket \\#{escape_md_v2(ticket_id_to_view[:8])}*"]
    thread_display_parts.append(
        f"User: {escape_md_v2(ticket_data.get('user_username', 'N/A'))} \\(ID: {escape_md_v2(ticket_data.get('user_chat_id', 'N/A'))}\\)")
    thread_display_parts.append(
        f"Status: {escape_md_v2(ticket_data.get('status', 'N/A').replace('_', ' ').title())}\n")

    for msg in ticket_data.get("messages", []):
        sender_disp = escape_md_v2(msg.get("sender_username", "Unknown"))
        msg_time = time.strftime(
            '%Y-%m-%d %H:%M', time.localtime(msg.get("timestamp", 0))).replace('-', '\\-')
        msg_text_disp = escape_md_v2(
            msg.get("text", "_empty message_").replace('-', '\\-'))
        thread_display_parts.append(
            f"_{escape_md_v2(msg_time)}_ *{sender_disp}*:\n{msg_text_disp}\n{'\\-'*20}")

    full_thread_text_for_admin = "\n".join(thread_display_parts)
    if len(full_thread_text_for_admin) > 4096:  # Telegram message limit
        full_thread_text_for_admin = full_thread_text_for_admin[:4090] + "\n\\.\\.\\."

    await send_or_edit_universal_status_message(
        context.bot, int(admin_chat_id_str),
        full_thread_text_for_admin,
        parse_mode="MarkdownV2", force_send_new=True  # Force new for clarity
    )

    # Mark ticket as admin_viewed if it was user_replied or open_by_user
    if ticket_data.get("status") in ["user_replied", "open_by_user"]:
        ticket_data["status"] = "admin_viewed"  # Or a more specific status
        ticket_data["last_updated_at"] = time.time()
        save_tickets_data(support_tickets_store)  # New
        logger.info(
            f"Admin {admin_chat_id_str} viewed ticket {ticket_id_to_view}. Status updated.")
    keyboard = []

    keyboard.append([InlineKeyboardButton("💬 Reply to User",
                     callback_data=f"{CallbackData.CMD_ADMIN_REPLY_TO_TICKET_INIT_PREFIX.value}{ticket_id_to_view}")])
    keyboard.append([InlineKeyboardButton("🏁 Close Ticket (Notify User)",
                     # Corrected CB
                                          callback_data=f"{CallbackData.CMD_ADMIN_CLOSE_TICKET_PREFIX.value}{ticket_id_to_view}")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Ticket List",
                     callback_data=CallbackData.CMD_TICKETS_MENU.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)

    menu_message_id = load_menu_message_id(admin_chat_id_str)
    menu_title_text = escape_md_v2(
        f"{ADMIN_VIEW_TICKET_MENU_TITLE_RAW} (#{ticket_id_to_view[:8]})")

    if menu_message_id:
        try:
            current_content_key = f"menu_message_content_{admin_chat_id_str}_{menu_message_id}"
            old_content_tuple_json = context.application.bot_data.get(
                current_content_key)
            new_content_tuple_json = (menu_title_text, reply_markup.to_json())

            if old_content_tuple_json != new_content_tuple_json:
                await context.bot.edit_message_text(
                    chat_id=int(admin_chat_id_str), message_id=menu_message_id,
                    text=menu_title_text, reply_markup=reply_markup, parse_mode="MarkdownV2"
                )
                context.application.bot_data[current_content_key] = new_content_tuple_json
            # else: logger.debug(f"Admin view ticket details: Menu content for {admin_chat_id_str} not modified, edit skipped.")
        except Exception as e:
            logger.error(
                f"Error updating admin's main menu for viewing ticket: {e}", exc_info=True)
            # Fallback to ticket list if menu edit fails
            # USM should have the ticket content.
            # await send_or_edit_universal_status_message(context.bot, int(admin_chat_id_str), "⚠️ Error displaying ticket actions. Ticket content shown above. Returning to ticket list.", parse_mode=None, force_send_new=False) # This might overwrite the ticket content in USM
            await display_tickets_menu(update, context)  # Fallback
    else:
        logger.error(
            f"Cannot find menu_message_id for admin {admin_chat_id_str} when viewing ticket details.")
        # USM should have the ticket content.
        await send_or_edit_universal_status_message(context.bot, int(admin_chat_id_str), "⚠️ Error displaying ticket actions (menu ID missing). Ticket content shown above. Returning to ticket list.", parse_mode=None, force_send_new=False)
        await display_tickets_menu(update, context)  # Fallback


async def handle_admin_mark_user_reply_read(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    admin_chat_id_str = str(update.effective_chat.id)
    admin_user_role = app_config_holder.get_user_role(admin_chat_id_str)
    # Allow any admin to mark as read, not just primary
    if admin_user_role != app_config_holder.ROLE_ADMIN:
        await query.answer("Access Denied.", show_alert=True)
        return
    await query.answer()

    reply_uuid_to_mark = query.data.replace(
        CallbackData.CMD_ADMIN_MARK_USER_REPLY_READ_PREFIX.value, "")

    # This handler is for the old direct message system, which is being deprecated.
    unread_replies_store = context.application.bot_data.get(
        'unread_user_replies', {})
    admin_replies_list = unread_replies_store.get(admin_chat_id_str, [])

    initial_len = len(admin_replies_list)
    admin_replies_list[:] = [
        reply for reply in admin_replies_list if reply.get("id") != reply_uuid_to_mark]

    if not admin_replies_list:  # If list becomes empty
        unread_replies_store.pop(admin_chat_id_str, None)
        if not unread_replies_store:  # If no admins have unread replies
            context.application.bot_data.pop('unread_user_replies', None)

    if len(admin_replies_list) < initial_len:
        await send_or_edit_universal_status_message(context.bot, int(admin_chat_id_str), "✅ Ticket marked as handled (for now).", parse_mode=None)
        logger.info(
            f"User reply ID {reply_uuid_to_mark} marked as read by admin {admin_chat_id_str}.")
    # else: # No need for an error if it wasn't found, it might have been processed.
    #     await send_or_edit_universal_status_message(context.bot, int(admin_chat_id_str), "⚠️ Could not mark ticket as handled (already handled or error).", parse_mode=None)

    # Go back to admin's main menu or ticket list
    await show_or_edit_main_menu(admin_chat_id_str, context.application)


async def handle_admin_close_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ADDED THIS LINE
    logger.info(
        f"handle_admin_close_ticket CALLED. Update data: {update.callback_query.data if update.callback_query else 'No callback_query'}")
    query = update.callback_query
    admin_chat_id_str = str(update.effective_chat.id)

    # Answer the query as early as possible to prevent client-side timeout
    if query:
        await query.answer()
        logger.info(
            f"Admin close ticket: Query answered for {admin_chat_id_str}, data: {query.data}")
    else:
        logger.error(
            "handle_admin_close_ticket called without a query object.")
        return

    admin_user_role = app_config_holder.get_user_role(admin_chat_id_str)
    if admin_user_role != app_config_holder.ROLE_ADMIN:
        logger.warning(
            f"Admin close ticket: Access denied for {admin_chat_id_str}, role {admin_user_role}")
        await send_or_edit_universal_status_message(context.bot, int(admin_chat_id_str), "Access Denied. This action is for administrators.", parse_mode=None)
        return

    ticket_id_to_close = query.data.replace(
        CallbackData.CMD_ADMIN_CLOSE_TICKET_PREFIX.value, "")

    support_tickets_store = load_tickets_data()  # New
    ticket_data = support_tickets_store.get(ticket_id_to_close)
    admin_username = update.effective_user.username or update.effective_user.first_name or f"Admin_{admin_chat_id_str}"

    if not ticket_data:
        await send_or_edit_universal_status_message(context.bot, int(admin_chat_id_str), "⚠️ Ticket not found to close.", parse_mode=None)
        await display_tickets_menu(update, context)
        return

    if ticket_data.get("status", "").startswith("closed"):
        await send_or_edit_universal_status_message(context.bot, int(admin_chat_id_str), f"Ticket #{escape_md_v2(ticket_id_to_close[:8])} is already closed.", parse_mode="MarkdownV2")
        await display_tickets_menu(update, context)
        return

    ticket_data["status"] = "closed_by_admin"
    ticket_data["last_updated_at"] = time.time()
    # Optionally add a closing message from admin
    ticket_data.setdefault("messages", []).append({
        "sender_id": admin_chat_id_str, "sender_username": admin_username,
        "sender_type": "admin", "text": f"Ticket closed by administrator.",
        "timestamp": time.time()
    })
    save_tickets_data(support_tickets_store)  # New
    replying_user_id_to_notify = ticket_data.get("user_chat_id")

    logger.info(
        f"Admin {admin_chat_id_str} closed ticket {ticket_id_to_close}.")
    await send_or_edit_universal_status_message(context.bot, int(admin_chat_id_str), f"✅ Ticket \\#{escape_md_v2(ticket_id_to_close[:8])} closed\\.", parse_mode="MarkdownV2")

    if replying_user_id_to_notify:
        try:
            # Refresh user's menu first
            await show_or_edit_main_menu(str(replying_user_id_to_notify), context.application)
            # Then send USM notification
            await send_or_edit_universal_status_message(
                context.bot, int(replying_user_id_to_notify),
                f"ℹ️ Administrator has closed your ticket \\#{escape_md_v2(ticket_id_to_close[:8])}\\.",
                parse_mode="MarkdownV2"
            )
        except Exception as e_notify_user:
            logger.error(
                f"Failed to notify user {replying_user_id_to_notify} about ticket close: {e_notify_user}")

    await display_tickets_menu(update, context)


async def handle_admin_reply_to_ticket_init(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    admin_chat_id_str = str(update.effective_chat.id)
    admin_user_role = app_config_holder.get_user_role(admin_chat_id_str)

    if admin_user_role != app_config_holder.ROLE_ADMIN:
        await query.answer("Access Denied.", show_alert=True)
        return ConversationHandler.END
    await query.answer()  # Answer the callback query

    ticket_id_to_reply_to = query.data.replace(
        CallbackData.CMD_ADMIN_REPLY_TO_TICKET_INIT_PREFIX.value, "")

    # support_tickets_store = context.application.bot_data.get('support_tickets', {}) # Old
    support_tickets_store = load_tickets_data()  # New
    ticket_data = support_tickets_store.get(ticket_id_to_reply_to)

    if not ticket_data or ticket_data.get("status", "").startswith("closed"):
        await send_or_edit_universal_status_message(context.bot, int(admin_chat_id_str), "⚠️ Cannot reply: Ticket not found or already closed.", parse_mode=None)
        return ConversationHandler.END

    context.user_data['admin_replying_to_ticket_id'] = ticket_id_to_reply_to
    context.user_data['admin_replying_to_user_chat_id'] = ticket_data.get(
        "user_chat_id")
    context.user_data['admin_replying_to_user_username'] = ticket_data.get(
        "user_username")

    prompt_text = f"📝 Type your reply for Ticket \\#{escape_md_v2(ticket_id_to_reply_to[:8])} \\(to user: {escape_md_v2(ticket_data.get('user_username', 'N/A'))}\\)\\. Send /cancel\\_admin\\_ticket\\_reply to abort\\."
    await send_or_edit_universal_status_message(context.bot, int(admin_chat_id_str), prompt_text, parse_mode="MarkdownV2", force_send_new=True)
    return AWAITING_ADMIN_TICKET_REPLY_TEXT


async def handle_admin_ticket_reply_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_chat_id_str = str(update.effective_chat.id)
    admin_reply_text = update.message.text
    admin_username = update.effective_user.username or update.effective_user.first_name or f"Admin_{admin_chat_id_str}"

    ticket_id = context.user_data.pop('admin_replying_to_ticket_id', None)
    target_user_chat_id = context.user_data.pop(
        'admin_replying_to_user_chat_id', None)
    target_user_username = context.user_data.pop(
        'admin_replying_to_user_username', 'User')

    try:
        await update.message.delete()
    except Exception as e_del:
        logger.warning(f"Could not delete admin's ticket reply input: {e_del}")

    if not ticket_id or not target_user_chat_id:
        await send_or_edit_universal_status_message(context.bot, int(admin_chat_id_str), "⚠️ Error: Ticket/User ID for reply not found. Please try again.", parse_mode=None)
        return ConversationHandler.END

    support_tickets_store = load_tickets_data()  # New
    ticket_data = support_tickets_store.get(ticket_id)

    if not ticket_data or ticket_data.get("status", "").startswith("closed"):
        await send_or_edit_universal_status_message(context.bot, int(admin_chat_id_str), "⚠️ Cannot send reply: Ticket not found or already closed.", parse_mode=None)
        return ConversationHandler.END

    ticket_data.setdefault("messages", []).append({
        "sender_id": admin_chat_id_str, "sender_username": admin_username,
        "sender_type": "admin", "text": admin_reply_text, "timestamp": time.time()
    })
    ticket_data["status"] = "admin_replied"
    ticket_data["last_updated_at"] = time.time()
    # Save the ticket with the new message
    save_tickets_data(support_tickets_store)

    await send_or_edit_universal_status_message(context.bot, int(admin_chat_id_str), f"✅ Your reply to Ticket \\#{escape_md_v2(ticket_id[:8])} has been sent to {escape_md_v2(target_user_username)}\\.", parse_mode="MarkdownV2")

    # Notify User
    async def refresh_user_ui_job(job_context: ContextTypes.DEFAULT_TYPE):
        # Similar to new ticket notification for user
        # ... (implementation for user UI refresh) ...
        user_id_to_refresh = job_context.job.data.get('chat_id')
        ticket_short_id_esc = job_context.job.data.get(
            'ticket_short_id_esc', 'a ticket')
        if user_id_to_refresh:
            # Refresh user's main menu
            await show_or_edit_main_menu(str(user_id_to_refresh), job_context.application)
            await send_or_edit_universal_status_message(
                job_context.bot, int(user_id_to_refresh),  # Corrected Markdown
                f"📬 New reply from administrator in Ticket \\#{ticket_short_id_esc}\\. Check /tickets or main menu\\.",
                parse_mode="MarkdownV2"
            )
    context.application.job_queue.run_once(refresh_user_ui_job, 0.5, data={
                                           'chat_id': target_user_chat_id, 'ticket_short_id_esc': escape_md_v2(ticket_id[:8])}, name=f"refresh_user_ui_admin_reply_{ticket_id}")

    # After sending reply, show the admin the updated ticket view
    # Create a dummy CallbackQuery to re-enter the view ticket details flow
    class DummyMessageForCallback:
        def __init__(self, original_chat, original_message_id=None):
            self.chat = original_chat
            # Not strictly needed if details view edits a persisted menu_id
            self.message_id = original_message_id or 0

    class DummyCallbackQuery:
        def __init__(self, data_val, original_update_obj: Update):
            # CallbackQuery ID must be a string
            self.id = "dummy_cq_id_" + str(uuid.uuid4())
            self.data = data_val
            self.from_user = original_update_obj.effective_user  # User who "pressed" the button
            self.message = DummyMessageForCallback(
                original_update_obj.effective_chat)  # Message the button was on

        # CallbackQuery must have an answer method
        async def answer(self): pass

    dummy_cq = DummyCallbackQuery(
        # Pass the original update object
        f"{CallbackData.CMD_ADMIN_VIEW_TICKET_PREFIX.value}{ticket_id}", update)
    dummy_update = Update(update_id=update.update_id,
                          callback_query=dummy_cq)
    # No setattr needed for effective_user and effective_chat
    await handle_admin_view_ticket_details(dummy_update, context)
    return ConversationHandler.END


async def cancel_admin_ticket_reply_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await send_or_edit_universal_status_message(context.bot, update.effective_chat.id, "Admin ticket reply cancelled.", parse_mode=None)
    context.user_data.pop('admin_replying_to_ticket_id', None)
    context.user_data.pop('admin_replying_to_user_chat_id', None)
    context.user_data.pop('admin_replying_to_user_username', None)

    await display_tickets_menu(update, context)
    return ConversationHandler.END
