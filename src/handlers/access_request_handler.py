
import logging
from telegram import Update
from telegram.ext import ContextTypes
import src.app.app_config_holder as app_config_holder
import src.app.user_manager as user_manager
from src.bot.bot_initialization import send_or_edit_universal_status_message, show_or_edit_main_menu, refresh_main_menus_for_all_admins
from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)


async def handle_request_access_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the action when an unknown user clicks the 'Request Access' button.
    Logs the request, notifies admins, and informs the user.
    """
    query = update.callback_query
    from src.bot.bot_initialization import send_or_edit_universal_status_message, show_or_edit_main_menu
    if not query or not update.effective_user or not update.effective_chat:
        logger.warning(
            "handle_request_access_button invoked without query or effective_user/chat.")
        if query:
            await query.answer("Error processing request.", show_alert=True)
        return

    await query.answer()

    chat_id = update.effective_chat.id

    user_id_str = str(chat_id)

    telegram_user = update.effective_user
    display_username = telegram_user.username
    if not display_username and telegram_user.first_name:
        display_username = telegram_user.first_name
    elif not display_username:
        display_username = f"User_{user_id_str}"

    current_user_role = app_config_holder.get_user_role(user_id_str)
    if current_user_role != app_config_holder.ROLE_UNKNOWN:
        logger.info(
            f"User {user_id_str} (Role: {current_user_role}) clicked 'Request Access' but is not ROLE_UNKNOWN. Showing their main menu.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "Your access status has already been determined.", parse_mode=None)

        await show_or_edit_main_menu(user_id_str, context)
        return

    if user_manager.add_pending_access_request(user_id_str, display_username):
        logger.info(
            f"Access request submitted for user_id: {user_id_str}, username: {display_username}")
        await send_or_edit_universal_status_message(
            context.bot, chat_id,
            "✅ Your access request has been submitted. An administrator will review it shortly.",
            parse_mode=None
        )
        await refresh_main_menus_for_all_admins(context)

    else:

        logger.warning(
            f"Failed to add pending access request for {user_id_str} - they might already be pending or an existing user.")

        existing_role = app_config_holder.get_user_role(
            user_id_str)
        if existing_role != app_config_holder.ROLE_UNKNOWN:
            await send_or_edit_universal_status_message(context.bot, chat_id, "It seems you already have access. Your menu is being updated.", parse_mode=None)
            await show_or_edit_main_menu(user_id_str, context)

        else:
            await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Your access request is already pending review or could not be processed at this time.", parse_mode=None)
