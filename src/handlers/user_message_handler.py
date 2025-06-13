import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import src.app.app_config_holder as app_config_holder
import uuid  # For unique reply IDs
import time  # For timestamp
from src.bot.bot_callback_data import CallbackData
from src.bot.bot_initialization import send_or_edit_universal_status_message, show_or_edit_main_menu
from src.bot.bot_message_persistence import load_menu_message_id
from src.app.app_file_utils import load_tickets_data, save_tickets_data
from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)

VIEW_ADMIN_MESSAGE_MENU_TITLE_RAW = "✉️ Message from Administrator"  # Will be deprecated
VIEW_TICKET_MENU_TITLE_RAW = "🎫 Ticket Details"

# States for different conversations within this handler
# For replying to an old admin message (will be deprecated)
AWAITING_USER_REPLY_TEXT = 0
AWAITING_TICKET_REPLY_TEXT = 1  # For replying to a ticket message


async def handle_view_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # This function is part of the old direct messaging system and will be deprecated.
    query = update.callback_query
    chat_id_str = str(update.effective_chat.id)
    await query.answer()
    message_uuid = query.data.replace(
        CallbackData.CMD_USER_VIEW_ADMIN_MESSAGE_PREFIX.value, "")
    unread_messages_store = context.application.bot_data.get(
        'unread_admin_messages', {})
    message_data = unread_messages_store.get(chat_id_str)
    if not message_data or message_data.get("id") != message_uuid:
        await send_or_edit_universal_status_message(context.bot, int(chat_id_str), "⚠️ Message not found or already read.", parse_mode=None)
        await show_or_edit_main_menu(chat_id_str, context.application)
        return
    full_message_text_for_user = f"✉️ *Message from Administrator:*\n\n{escape_md_v2(message_data['text'])}"
    await send_or_edit_universal_status_message(
        context.bot, int(chat_id_str), full_message_text_for_user, parse_mode="MarkdownV2")
    keyboard = [[
        InlineKeyboardButton(
            "💬 Reply", callback_data=f"{CallbackData.CMD_USER_REPLY_TO_ADMIN_INIT_PREFIX.value}{message_uuid}"),
        InlineKeyboardButton(
            "✅ Mark as Read", callback_data=f"{CallbackData.CMD_USER_MARK_ADMIN_MESSAGE_READ_PREFIX.value}{message_uuid}")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_message_id = load_menu_message_id(chat_id_str)
    menu_title_text = escape_md_v2(VIEW_ADMIN_MESSAGE_MENU_TITLE_RAW)
    if menu_message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=int(chat_id_str), message_id=menu_message_id, text=menu_title_text,
                reply_markup=reply_markup, parse_mode="MarkdownV2")
            context.application.bot_data[f"menu_message_content_{chat_id_str}_{menu_message_id}"] = (
                menu_title_text, reply_markup.to_json())
        except Exception as e:
            logger.error(
                f"Error updating main menu for viewing admin message: {e}", exc_info=True)
            await show_or_edit_main_menu(chat_id_str, context.application, force_send_new=True)
    else:
        logger.error(
            f"Cannot find menu_message_id for user {chat_id_str} when viewing admin message.")
        await show_or_edit_main_menu(chat_id_str, context.application, force_send_new=True)


async def handle_mark_admin_message_read(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id_str = str(update.effective_chat.id)
    await query.answer()
    message_uuid_to_mark = query.data.replace(
        CallbackData.CMD_USER_MARK_ADMIN_MESSAGE_READ_PREFIX.value, "")
    unread_messages_store = context.application.bot_data.get(
        'unread_admin_messages', {})
    user_message_data = unread_messages_store.get(chat_id_str)
    message_marked = False
    if user_message_data and user_message_data.get("id") == message_uuid_to_mark:
        del unread_messages_store[chat_id_str]
        if not unread_messages_store:
            context.application.bot_data.pop('unread_admin_messages', None)
        logger.info(
            f"Admin message ID {message_uuid_to_mark} marked as read by user {chat_id_str}.")
        message_marked = True
    if message_marked:
        await send_or_edit_universal_status_message(
            context.bot, int(chat_id_str), "✅ Message from administrator marked as read.", parse_mode=None)
    else:
        await send_or_edit_universal_status_message(
            context.bot, int(chat_id_str), "⚠️ Could not mark message as read (already read or error).", parse_mode=None)
    await show_or_edit_main_menu(chat_id_str, context.application)


async def handle_reply_to_admin_init(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    chat_id_str = str(update.effective_chat.id)
    await query.answer()
    message_uuid_to_reply_to = query.data.replace(
        CallbackData.CMD_USER_REPLY_TO_ADMIN_INIT_PREFIX.value, "")
    unread_messages_store = context.application.bot_data.get(
        'unread_admin_messages', {})
    original_message_data = unread_messages_store.get(chat_id_str)
    if not original_message_data or original_message_data.get("id") != message_uuid_to_reply_to:
        await send_or_edit_universal_status_message(context.bot, int(chat_id_str), "⚠️ Message to reply to not found or already read.", parse_mode=None)
        return ConversationHandler.END
    context.user_data['replying_to_admin_msg_uuid'] = message_uuid_to_reply_to
    context.user_data['replying_to_admin_msg_text_snippet'] = original_message_data['text'][:100]
    prompt_text = "📝 Type your reply to the administrator's message below\\. Send /cancel\\_reply to abort\\."
    await send_or_edit_universal_status_message(context.bot, int(chat_id_str), prompt_text, parse_mode="MarkdownV2", force_send_new=True)
    return AWAITING_USER_REPLY_TEXT


async def handle_user_reply_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_chat_id_str = str(update.effective_chat.id)
    user_reply_text = update.message.text
    original_msg_snippet = context.user_data.get(
        'replying_to_admin_msg_text_snippet', "an earlier message")
    try:
        await update.message.delete()
    except Exception as e_del:
        logger.warning(f"Could not delete user's reply input message: {e_del}")
    primary_admin_chat_id_str = app_config_holder.get_chat_id_str()
    if not primary_admin_chat_id_str:
        logger.error(
            "Primary admin CHAT_ID not configured. Cannot forward user reply.")
        await send_or_edit_universal_status_message(context.bot, int(user_chat_id_str), "⚠️ Could not send reply: Admin not configured.", parse_mode=None)
        return ConversationHandler.END
    user_display_name = update.effective_user.username or update.effective_user.first_name or f"User_{user_chat_id_str}"
    try:
        reply_uuid = str(uuid.uuid4())
        unread_user_replies_store = context.application.bot_data.setdefault(
            'unread_user_replies', {})
        admin_replies_list = unread_user_replies_store.setdefault(
            primary_admin_chat_id_str, [])
        admin_replies_list.append({
            "reply_text": user_reply_text,
            "original_admin_msg_snippet": original_msg_snippet,
            "replying_user_id": user_chat_id_str,
            "replying_user_display_name": user_display_name,
            "id": reply_uuid,
            "timestamp": time.time()
        })
        logger.info(
            f"Stored unread user reply (ID: {reply_uuid}) from {user_chat_id_str} for admin {primary_admin_chat_id_str} (via old system)")

        async def refresh_admin_ui_job(job_context: ContextTypes.DEFAULT_TYPE):
            admin_id_to_refresh = job_context.job.data.get('chat_id')
            replying_user_name_esc = job_context.job.data.get(
                'replying_user_name_esc', 'a user')
            ticket_short_id_esc = job_context.job.data.get(
                'ticket_short_id_esc', 'a_ticket')  # Ensure this is retrieved
            if admin_id_to_refresh:
                await show_or_edit_main_menu(str(admin_id_to_refresh), job_context.application)
                await send_or_edit_universal_status_message(
                    job_context.bot, int(admin_id_to_refresh),
                    f"📬 New reply from {replying_user_name_esc} in Ticket \\#{ticket_short_id_esc}\\. Check /tickets or main menu\\.",
                    parse_mode="MarkdownV2")
        context.application.job_queue.run_once(refresh_admin_ui_job, 0.5, data={'chat_id': primary_admin_chat_id_str, 'replying_user_name_esc': escape_md_v2(
            user_display_name), 'ticket_short_id_esc': 'N/A_old_sys'}, name=f"refresh_admin_ui_new_reply_old_sys_{reply_uuid}")
        await send_or_edit_universal_status_message(context.bot, int(user_chat_id_str), "✅ Your reply has been queued for the administrator.", parse_mode=None)
    except Exception as e:
        logger.error(
            f"Failed to process user reply (old system): {e}", exc_info=True)
        await send_or_edit_universal_status_message(context.bot, int(user_chat_id_str), "⚠️ Failed to send your reply. Please try again later.", parse_mode=None)
    context.user_data.pop('replying_to_admin_msg_uuid', None)
    context.user_data.pop('replying_to_admin_msg_text_snippet', None)
    return ConversationHandler.END


async def handle_user_view_ticket_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id_str = str(update.effective_chat.id)
    user_id_str = str(update.effective_user.id)
    await query.answer()
    ticket_id_to_view = query.data.replace(
        CallbackData.CMD_USER_VIEW_TICKET_PREFIX.value, "")
    support_tickets_store = load_tickets_data()
    ticket_data = support_tickets_store.get(ticket_id_to_view)
    if not ticket_data or ticket_data.get("user_chat_id") != chat_id_str:
        await send_or_edit_universal_status_message(context.bot, int(chat_id_str), "⚠️ Ticket not found or access denied.", parse_mode=None)
        await show_or_edit_main_menu(chat_id_str, context.application)
        return
    if ticket_data.get("status") == "open_by_admin" and not ticket_data.get("user_viewed_initial_admin_msg"):
        ticket_data["user_viewed_initial_admin_msg"] = True
        ticket_data["last_updated_at"] = time.time()
        save_tickets_data(support_tickets_store)
        logger.info(
            f"User {user_id_str} viewed initial admin message for ticket {ticket_id_to_view}")
    thread_display_parts = [
        f"💬 *Ticket \\#{escape_md_v2(ticket_id_to_view[:8])}*"]
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
    full_thread_text_for_user = "\n".join(thread_display_parts)
    if len(full_thread_text_for_user) > 4096:
        full_thread_text_for_user = full_thread_text_for_user[:4090] + "\n\\.\\.\\."
    await send_or_edit_universal_status_message(
        context.bot, int(chat_id_str), full_thread_text_for_user, parse_mode="MarkdownV2", force_send_new=True)
    keyboard = [
        [InlineKeyboardButton(
            "💬 Reply to Ticket", callback_data=f"{CallbackData.CMD_USER_REPLY_TO_TICKET_INIT_PREFIX.value}{ticket_id_to_view}")],
        [InlineKeyboardButton(
            "🏁 Close My Ticket", callback_data=f"{CallbackData.CMD_USER_CLOSE_TICKET_PREFIX.value}{ticket_id_to_view}")],
        [InlineKeyboardButton("🔙 Back to Main Menu",
                              callback_data=CallbackData.CMD_HOME_BACK.value)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_message_id = load_menu_message_id(chat_id_str)
    menu_title_text = escape_md_v2(
        f"{VIEW_TICKET_MENU_TITLE_RAW} (#{ticket_id_to_view[:8]})")
    if menu_message_id:
        current_content_key = f"menu_message_content_{chat_id_str}_{menu_message_id}"
        old_content_tuple_json = context.application.bot_data.get(
            current_content_key)
        new_content_tuple_json = (menu_title_text, reply_markup.to_json())

        try:
            if old_content_tuple_json != new_content_tuple_json:
                await context.bot.edit_message_text(
                    chat_id=int(chat_id_str), message_id=menu_message_id, text=menu_title_text,
                    reply_markup=reply_markup, parse_mode="MarkdownV2")
                context.application.bot_data[current_content_key] = new_content_tuple_json
            # else: logger.debug("User view ticket details: Menu content not modified, edit skipped.")
        except Exception as e:
            logger.error(
                f"Error updating main menu for viewing ticket: {e}", exc_info=True)
            await send_or_edit_universal_status_message(context.bot, int(chat_id_str), "⚠️ Error displaying ticket actions. Ticket content shown above. Use 'Back' to return to your ticket list or main menu.", parse_mode=None, force_send_new=False)
    else:
        logger.error(
            f"Cannot find menu_message_id for user {chat_id_str} when viewing ticket.")
        await send_or_edit_universal_status_message(context.bot, int(chat_id_str), "⚠️ Error displaying ticket actions (menu ID missing). Ticket content shown above. Use 'Back' to return to main menu.", parse_mode=None, force_send_new=False)


async def handle_user_reply_to_ticket_init(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    chat_id_str = str(update.effective_chat.id)
    await query.answer()
    ticket_id_to_reply_to = query.data.replace(
        CallbackData.CMD_USER_REPLY_TO_TICKET_INIT_PREFIX.value, "")
    support_tickets_store = load_tickets_data()
    ticket_data = support_tickets_store.get(ticket_id_to_reply_to)
    if not ticket_data or ticket_data.get("user_chat_id") != chat_id_str or ticket_data.get("status", "").startswith("closed"):
        await send_or_edit_universal_status_message(context.bot, int(chat_id_str), "⚠️ Cannot reply: Ticket not found, not yours, or already closed.", parse_mode=None)
        return ConversationHandler.END
    context.user_data['replying_to_ticket_id'] = ticket_id_to_reply_to
    prompt_text = f"📝 Type your reply for Ticket \\#{escape_md_v2(ticket_id_to_reply_to[:8])}\\. Send /cancel\\_ticket\\_reply to abort\\."
    await send_or_edit_universal_status_message(context.bot, int(chat_id_str), prompt_text, parse_mode="MarkdownV2", force_send_new=True)
    return AWAITING_TICKET_REPLY_TEXT


async def handle_user_ticket_reply_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_chat_id_str = str(update.effective_chat.id)
    user_reply_text = update.message.text
    user_username = update.effective_user.username or update.effective_user.first_name or f"User_{user_chat_id_str}"
    ticket_id = context.user_data.pop('replying_to_ticket_id', None)
    try:
        await update.message.delete()
    except Exception as e_del:
        logger.warning(f"Could not delete user's ticket reply input: {e_del}")
    if not ticket_id:
        await send_or_edit_universal_status_message(context.bot, int(user_chat_id_str), "⚠️ Error: Ticket ID for reply not found. Please try again.", parse_mode=None)
        return ConversationHandler.END
    support_tickets_store = load_tickets_data()
    ticket_data = support_tickets_store.get(ticket_id)
    if not ticket_data or ticket_data.get("user_chat_id") != user_chat_id_str or ticket_data.get("status", "").startswith("closed"):
        await send_or_edit_universal_status_message(context.bot, int(user_chat_id_str), "⚠️ Cannot send reply: Ticket not found, not yours, or already closed.", parse_mode=None)
        return ConversationHandler.END
    ticket_data.setdefault("messages", []).append({
        "sender_id": user_chat_id_str, "sender_username": user_username,
        "sender_type": "user", "text": user_reply_text, "timestamp": time.time()
    })
    ticket_data["status"] = "user_replied"
    ticket_data["last_updated_at"] = time.time()
    save_tickets_data(support_tickets_store)
    await send_or_edit_universal_status_message(context.bot, int(user_chat_id_str), f"✅ Your reply to Ticket \\#{escape_md_v2(ticket_id[:8])} has been sent\\.", parse_mode="MarkdownV2")
    primary_admin_chat_id_str = app_config_holder.get_chat_id_str()
    if primary_admin_chat_id_str:
        async def refresh_admin_ui_job(job_context: ContextTypes.DEFAULT_TYPE):
            admin_id = job_context.job.data.get('chat_id')
            replying_user_name_esc = job_context.job.data.get(
                'replying_user_name_esc', 'a user')
            ticket_short_id_esc = job_context.job.data.get(
                'ticket_short_id_esc', 'a_ticket')  # Definition
            if admin_id:
                await show_or_edit_main_menu(str(admin_id), job_context.application)
                await send_or_edit_universal_status_message(
                    job_context.bot, int(admin_id),
                    # Usage
                    f"📬 New reply from {replying_user_name_esc} in Ticket \\#{ticket_short_id_esc}\\. Check /tickets or main menu\\.",
                    parse_mode="MarkdownV2")
        context.application.job_queue.run_once(refresh_admin_ui_job, 0.5, data={'chat_id': primary_admin_chat_id_str, 'replying_user_name_esc': escape_md_v2(
            user_username), 'ticket_short_id_esc': escape_md_v2(ticket_id[:8])}, name=f"refresh_admin_ui_ticket_reply_{ticket_id}")

    class DummyMessageForCallback:
        def __init__(self, original_chat, original_message_id=None):
            self.chat = original_chat
            self.message_id = original_message_id or 0

    class DummyCallbackQuery:
        def __init__(self, data_val, original_update_obj: Update):
            self.id = "dummy_cq_id_" + str(uuid.uuid4())
            self.data = data_val
            self.from_user = original_update_obj.effective_user
            self.message = DummyMessageForCallback(
                original_update_obj.effective_chat)

        async def answer(self): pass
    dummy_cq = DummyCallbackQuery(
        f"{CallbackData.CMD_USER_VIEW_TICKET_PREFIX.value}{ticket_id}", update)
    dummy_update = Update(update_id=update.update_id, callback_query=dummy_cq)
    await handle_user_view_ticket_details(dummy_update, context)
    return ConversationHandler.END


async def cancel_user_reply_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await send_or_edit_universal_status_message(context.bot, update.effective_chat.id, "Reply cancelled.", parse_mode=None)
    context.user_data.pop('replying_to_admin_msg_uuid', None)
    context.user_data.pop('replying_to_admin_msg_text_snippet', None)
    context.user_data.pop('replying_to_ticket_id', None)
    from src.handlers.tickets_handler import display_tickets_menu
    try:
        await display_tickets_menu(update, context)
    except Exception as e:
        logger.error(f"Error trying to display tickets menu after cancel: {e}")
        await show_or_edit_main_menu(str(update.effective_chat.id), context.application)
    return ConversationHandler.END


async def handle_user_close_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id_str = str(update.effective_chat.id)
    await query.answer()
    ticket_id_to_close = query.data.replace(
        CallbackData.CMD_USER_CLOSE_TICKET_PREFIX.value, "")
    support_tickets_store = load_tickets_data()
    ticket_data = support_tickets_store.get(ticket_id_to_close)
    if not ticket_data or ticket_data.get("user_chat_id") != chat_id_str:
        await send_or_edit_universal_status_message(context.bot, int(chat_id_str), "⚠️ Ticket not found or you cannot close it.", parse_mode=None)
        return
    ticket_data["status"] = "closed_by_user"
    ticket_data["last_updated_at"] = time.time()
    save_tickets_data(support_tickets_store)
    logger.info(f"User {chat_id_str} closed ticket {ticket_id_to_close}")
    await send_or_edit_universal_status_message(context.bot, int(chat_id_str), f"✅ Ticket \\#{escape_md_v2(ticket_id_to_close[:8])} has been closed\\.", parse_mode="MarkdownV2")
    primary_admin_chat_id_str = app_config_holder.get_chat_id_str()
    if primary_admin_chat_id_str:
        user_username = update.effective_user.username or update.effective_user.first_name or f"User_{chat_id_str}"
        admin_notification_text = f"ℹ️ User {escape_md_v2(user_username)} has closed their ticket \\#{escape_md_v2(ticket_id_to_close[:8])}\\."
        try:
            # Refresh admin's menu first
            await show_or_edit_main_menu(primary_admin_chat_id_str, context.application)
            # Then send USM notification
            await send_or_edit_universal_status_message(
                context.bot, int(primary_admin_chat_id_str), admin_notification_text, parse_mode="MarkdownV2"
            )
        except Exception as e_notify_admin_close:
            logger.error(
                f"Failed to notify admin about user closing ticket {ticket_id_to_close}: {e_notify_admin_close}")
    await show_or_edit_main_menu(chat_id_str, context.application)
