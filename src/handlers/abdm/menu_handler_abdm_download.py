import logging
from telegram import Update, constants
from telegram.ext import ContextTypes
import src.app.app_config_holder as app_config_holder
from src.bot.bot_initialization import send_or_edit_universal_status_message, show_or_edit_main_menu
from src.services.abdm.bot_abdm_core import add_download_to_abdm
from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)


async def handle_abdm_download_initiation(update: Update, context: ContextTypes.DEFAULT_TYPE, download_url: str, chat_id: int):
    """
    Handles the initiation of a download request to AB Download Manager.
    This function is called after the user provides the URL.
    """
    await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)

    await send_or_edit_universal_status_message(
        context.bot,
        chat_id,
        f"⏳ Sending download request for: `{escape_md_v2(download_url[:60] + '...' if len(download_url) > 60 else download_url)}` to AB Download Manager...",
        parse_mode="MarkdownV2"
    )

    abdm_response = add_download_to_abdm(
        url=download_url,
        filename=None,
        destination_path=None,
        silent_add=True,
        silent_start=True
    )

    await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(abdm_response), parse_mode="MarkdownV2")

    admin_chat_id_str = app_config_holder.get_chat_id_str()
    if admin_chat_id_str and context.bot_data:
        await show_or_edit_main_menu(admin_chat_id_str, context, force_send_new=False)
