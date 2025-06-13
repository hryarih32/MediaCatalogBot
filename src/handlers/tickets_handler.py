import logging
import math
import time
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.error import BadRequest

import src.app.app_config_holder as app_config_holder
import src.app.user_manager as user_manager
from src.bot.bot_callback_data import CallbackData
from src.bot.bot_initialization import send_or_edit_universal_status_message, show_or_edit_main_menu
from src.app.app_file_utils import load_tickets_data, save_tickets_data
from src.bot.bot_message_persistence import load_menu_message_id  # Added import
from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)

USER_TICKETS_MENU_TITLE_MD2 = "🎫 My Open Tickets"
ADMIN_TICKETS_MENU_TITLE_MD2 = "🎫 All Open Tickets"  # For later admin view
AWAITING_NEW_TICKET_TEXT = 0  # Define as a simple integer for a single state

ITEMS_PER_PAGE_TICKETS = 5


def get_user_open_tickets(user_chat_id_str: str, all_tickets_store: dict) -> list:
    user_tickets = []
    for ticket_id, ticket_data in all_tickets_store.items():
        if ticket_data.get("user_chat_id") == user_chat_id_str and \
           not ticket_data.get("status", "").startswith("closed"):
            user_tickets.append(ticket_data)
    user_tickets.sort(key=lambda t: t.get("last_updated_at", 0), reverse=True)
    return user_tickets


def get_all_open_tickets_for_admin(all_tickets_store: dict) -> list:
    open_tickets = []
    for ticket_id, ticket_data in all_tickets_store.items():
        if not ticket_data.get("status", "").startswith("closed"):
            open_tickets.append(ticket_data)
    # Prioritize tickets needing admin attention (new or user replied)
    open_tickets.sort(key=lambda t: (t.get("status") not in [
                      "open_by_user", "user_replied"], t.get("last_updated_at", 0)), reverse=False)
    return open_tickets


async def display_tickets_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1) -> None:
    query = update.callback_query
    chat_id_str = str(update.effective_chat.id)
    user_role = app_config_holder.get_user_role(chat_id_str)

    if query:
        await query.answer()
        # Allow any admin for pagination
        if query.data.startswith(CallbackData.CMD_ADMIN_TICKETS_PAGE_PREFIX.value) and app_config_holder.get_user_role(chat_id_str) == app_config_holder.ROLE_ADMIN:
            try:  # Ensure page number is valid
                page = int(query.data.replace(
                    CallbackData.CMD_ADMIN_TICKETS_PAGE_PREFIX.value, ""))
            except ValueError:
                page = 1
        # Add similar pagination for user if CMD_USER_TICKETS_PAGE_PREFIX is introduced

    # support_tickets_store = context.application.bot_data.get('support_tickets', {}) # Old
    support_tickets_store = load_tickets_data()

    open_tickets = []
    menu_title = ""
    # Check if user has admin role
    is_admin_role_view = user_role == app_config_holder.ROLE_ADMIN

    if is_admin_role_view:
        open_tickets = get_all_open_tickets_for_admin(support_tickets_store)
        menu_title = ADMIN_TICKETS_MENU_TITLE_MD2
    elif user_role == app_config_holder.ROLE_STANDARD_USER or user_role == app_config_holder.ROLE_ADMIN:  # Non-primary admins see their own
        open_tickets = get_user_open_tickets(
            chat_id_str, support_tickets_store)
        menu_title = USER_TICKETS_MENU_TITLE_MD2
    else:
        await send_or_edit_universal_status_message(context.bot, int(chat_id_str), "⚠️ Access to tickets is restricted.", parse_mode=None)
        return

    keyboard = []
    menu_body_parts = ["\n"]

    total_items = len(open_tickets)
    total_pages = math.ceil(
        total_items / ITEMS_PER_PAGE_TICKETS) if total_items > 0 else 1
    current_page = max(1, min(page, total_pages))

    start_index = (current_page - 1) * ITEMS_PER_PAGE_TICKETS
    end_index = start_index + ITEMS_PER_PAGE_TICKETS
    page_items = open_tickets[start_index:end_index]

    if not page_items:
        menu_body_parts.append(escape_md_v2("_No open tickets to display._\n" if total_items ==
                               0 else f"_No open tickets on page {current_page}\\._\n"))
    else:
        for ticket in page_items:
            ticket_id = ticket.get("ticket_id")
            user_disp_name = escape_md_v2(
                ticket.get("user_username", "Unknown User"))
            subject_preview = ticket.get("messages")[0].get("text", "Ticket")[
                :25] + "..." if ticket.get("messages") else "Ticket"

            status_disp = ticket.get(
                "status", "unknown").replace("_", " ").title()
            status_emoji = "❗" if ticket.get(
                "status") in ["open_by_user", "user_replied"] and is_admin_role_view else "🎫"

            button_text_parts = [f"{status_emoji} #{ticket_id[:6]}"]
            # Show user if admin is viewing and it's not their own ticket
            if is_admin_role_view and ticket.get("user_chat_id") != chat_id_str:
                button_text_parts.append(f"Fr: {user_disp_name[:15]}")
            button_text_parts.append(f"{subject_preview[:20]}")
            button_text_parts.append(f"({status_disp})")
            # Join with space, skip empty
            button_text = " ".join(part for part in button_text_parts if part)

            callback_action = CallbackData.CMD_ADMIN_VIEW_TICKET_PREFIX if is_admin_role_view else CallbackData.CMD_USER_VIEW_TICKET_PREFIX
            keyboard.append([InlineKeyboardButton(
                button_text, callback_data=f"{callback_action.value}{ticket_id}")])

    pagination_row = []
    # Placeholder for user pagination
    # Use correct prefix for admin
    # Use correct prefix for admin
    # Use correct prefix for admin
    page_cb_prefix = CallbackData.CMD_ADMIN_TICKETS_PAGE_PREFIX if is_admin_role_view else "user_tickets_page_"
    if current_page > 1:
        pagination_row.append(InlineKeyboardButton(
            "◀️ Prev", callback_data=f"{page_cb_prefix.value}{current_page-1}"))
    if current_page < total_pages:
        pagination_row.append(InlineKeyboardButton(
            "Next ▶️", callback_data=f"{page_cb_prefix.value}{current_page+1}"))
    if pagination_row:
        keyboard.append(pagination_row)

    # Only non-admins (users) can create new tickets from this menu
    if not is_admin_role_view:
        keyboard.append([InlineKeyboardButton("✉️ New Ticket to Admin",
                        callback_data=CallbackData.CMD_USER_NEW_TICKET_INIT.value)])
    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu",
                    callback_data=CallbackData.CMD_HOME_BACK.value)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    final_menu_text = menu_title + "".join(menu_body_parts)

    menu_message_id = load_menu_message_id(chat_id_str)
    if menu_message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=int(chat_id_str), message_id=menu_message_id,
                text=final_menu_text, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )
            context.application.bot_data[f"menu_message_content_{chat_id_str}_{menu_message_id}"] = (
                final_menu_text, reply_markup.to_json())
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                logger.error(
                    f"Error displaying tickets menu (edit): {e}", exc_info=True)
                await show_or_edit_main_menu(chat_id_str, context.application, force_send_new=True)
        except Exception as e:
            logger.error(
                f"Unexpected error displaying tickets menu: {e}", exc_info=True)
            await show_or_edit_main_menu(chat_id_str, context.application, force_send_new=True)
    else:
        # Send new if no menu_id
        await show_or_edit_main_menu(chat_id_str, context.application, force_send_new=True)

    await send_or_edit_universal_status_message(context.bot, int(chat_id_str), "Tickets menu displayed.", parse_mode=None)


async def handle_user_new_ticket_init(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    chat_id_str = str(update.effective_chat.id)
    await query.answer()

    prompt_text = "📝 Please type your message for the new ticket to the administrator\\. Send /cancel\\_new\\_ticket to abort\\."
    await send_or_edit_universal_status_message(context.bot, int(chat_id_str), prompt_text, parse_mode="MarkdownV2")
    return AWAITING_NEW_TICKET_TEXT


async def handle_user_new_ticket_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_chat_id_str = str(update.effective_chat.id)
    user_message_text = update.message.text
    user_username = update.effective_user.username or update.effective_user.first_name or f"User_{user_chat_id_str}"

    try:
        await update.message.delete()  # Delete user's input message
    except Exception as e_del:
        logger.warning(
            f"Could not delete user's new ticket input message: {e_del}")

    ticket_id = str(uuid.uuid4())
    support_tickets_store = load_tickets_data()  # New
    primary_admin_chat_id_str = app_config_holder.get_chat_id_str()

    new_ticket = {
        "ticket_id": ticket_id,
        "user_chat_id": user_chat_id_str,
        "user_username": user_username,
        # All tickets go to primary admin for now
        "admin_chat_id": primary_admin_chat_id_str,
        "status": "open_by_user",
        "created_at": time.time(),
        "last_updated_at": time.time(),
        "messages": [{
            "sender_id": user_chat_id_str, "sender_username": user_username,
            "sender_type": "user", "text": user_message_text, "timestamp": time.time()
        }]
    }
    support_tickets_store[ticket_id] = new_ticket
    save_tickets_data(support_tickets_store)  # New
    logger.info(
        f"User {user_chat_id_str} created new ticket (ID: {ticket_id})")

    await send_or_edit_universal_status_message(context.bot, int(user_chat_id_str), "✅ Your new ticket has been submitted.", parse_mode=None)

    # Notify Admin
    if primary_admin_chat_id_str:
        async def refresh_admin_ui_job(job_context: ContextTypes.DEFAULT_TYPE):
            admin_id = job_context.job.data.get('chat_id')
            replying_user_name_esc = job_context.job.data.get(
                'replying_user_name_esc', 'a user')
            if admin_id:
                await show_or_edit_main_menu(str(admin_id), job_context.application)
                await send_or_edit_universal_status_message(
                    job_context.bot, int(admin_id),
                    f"📬 New ticket received from {replying_user_name_esc}\\. Check /tickets or main menu\\.",
                    parse_mode="MarkdownV2"
                )
        context.application.job_queue.run_once(refresh_admin_ui_job, 0.5, data={
                                               'chat_id': primary_admin_chat_id_str, 'replying_user_name_esc': escape_md_v2(user_username)}, name=f"refresh_admin_ui_new_ticket_{ticket_id}")

    # Show the updated ticket list to the user
    await display_tickets_menu(update, context)
    return ConversationHandler.END


async def cancel_new_ticket_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await send_or_edit_universal_status_message(context.bot, update.effective_chat.id, "Ticket creation cancelled.", parse_mode=None, force_send_new=True)
    await display_tickets_menu(update, context)  # Go back to ticket list
    return ConversationHandler.END
