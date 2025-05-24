import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

import src.app.app_config_holder as app_config_holder
from src.bot.bot_message_persistence import load_menu_message_id
from src.bot.bot_initialization import send_or_edit_universal_status_message
from src.bot.bot_callback_data import CallbackData

from src.handlers.plex.menu_handler_plex_controls import display_plex_controls_menu
from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)

PLEX_LIBRARY_SERVER_TOOLS_MENU_TEXT_RAW = "🛠️ Plex Library & Server Tools"


async def display_plex_library_server_tools_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, called_internally=False) -> None:
    query = update.callback_query
    if query and (query.data == CallbackData.CMD_PLEX_LIBRARY_SERVER_TOOLS.value or called_internally):

        try:
            await query.answer()
        except BadRequest as e_ans:
            if "query is too old" not in str(e_ans).lower() and "callback query is not found" not in str(e_ans).lower():
                logger.debug(
                    f"Query answer failed in display_plex_library_server_tools_menu (might be already answered): {e_ans}")

    chat_id = update.effective_chat.id

    admin_chat_id_str = app_config_holder.get_chat_id_str()

    if not admin_chat_id_str or str(chat_id) != admin_chat_id_str:
        logger.warning(
            f"Plex library/server tools attempt by non-primary admin {chat_id}.")
        return

    if not app_config_holder.is_plex_enabled():
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Plex features are disabled.", parse_mode=None)
        if admin_chat_id_str:

            await display_plex_controls_menu(update, context)
        return

    keyboard = [
        [InlineKeyboardButton(
            "🔄 Scan Libraries", callback_data=CallbackData.CMD_PLEX_SCAN_LIBRARIES_SELECT.value)],
        [InlineKeyboardButton("♻️ Refresh Library Metadata",
                              callback_data=CallbackData.CMD_PLEX_REFRESH_LIBRARY_METADATA_SELECT.value)],

        [InlineKeyboardButton("🔧 Server Maintenance & Info",
                              callback_data=CallbackData.CMD_PLEX_SERVER_TOOLS_SUB_MENU.value)],
        [InlineKeyboardButton("🔙 Back to Plex Controls",
                              callback_data=CallbackData.CMD_PLEX_CONTROLS.value)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_message_id = load_menu_message_id()
    if not menu_message_id and context.bot_data:
        menu_message_id = context.bot_data.get("main_menu_message_id")

    escaped_menu_title_for_display = escape_md_v2(
        PLEX_LIBRARY_SERVER_TOOLS_MENU_TEXT_RAW)

    if menu_message_id:
        try:
            current_content_key = f"menu_message_content_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (
                escaped_menu_title_for_display, reply_markup.to_json())

            if old_content_tuple != new_content_tuple or \
               (query and query.data == CallbackData.CMD_PLEX_LIBRARY_SERVER_TOOLS.value) or \
               called_internally:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=menu_message_id,
                    text=escaped_menu_title_for_display,
                    reply_markup=reply_markup,
                    parse_mode="MarkdownV2"
                )
                context.bot_data[current_content_key] = new_content_tuple

            if query and query.data == CallbackData.CMD_PLEX_LIBRARY_SERVER_TOOLS.value:
                await send_or_edit_universal_status_message(context.bot, chat_id, "Select a Plex library or server tool.", parse_mode=None)

        except BadRequest as e:
            if "message is not modified" in str(e).lower():
                logger.debug(
                    f"Plex Library & Server Tools menu already displayed. Message ID: {menu_message_id}")
                if query and query.data == CallbackData.CMD_PLEX_LIBRARY_SERVER_TOOLS.value:
                    await send_or_edit_universal_status_message(context.bot, chat_id, "Select a Plex library or server tool.", parse_mode=None)
            else:
                logger.error(
                    f"Error displaying Plex Library & Server Tools menu: {e}", exc_info=True)
                if admin_chat_id_str:
                    await display_plex_controls_menu(update, context)
        except Exception as e:
            logger.error(
                f"Error displaying Plex Library & Server Tools menu: {e}", exc_info=True)
            if admin_chat_id_str:
                await display_plex_controls_menu(update, context)
    else:
        logger.error(
            "Could not find main_menu_message_id for Plex Library & Server Tools menu.")
        if admin_chat_id_str:
            await display_plex_controls_menu(update, context)
