import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

import src.app.app_config_holder as app_config_holder
from src.bot.bot_message_persistence import load_menu_message_id
from src.bot.bot_initialization import send_or_edit_universal_status_message
from src.bot.bot_callback_data import CallbackData

from src.handlers.radarr.menu_handler_radarr_controls import display_radarr_controls_menu
from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)

RADARR_LIBRARY_MAINTENANCE_MENU_TEXT_RAW = "🎬 Radarr - Library Maintenance"


async def display_radarr_library_maintenance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()
    chat_id = update.effective_chat.id

    admin_chat_id_str = app_config_holder.get_chat_id_str()

    if not admin_chat_id_str or str(chat_id) != admin_chat_id_str:
        logger.warning(
            f"Radarr library maint attempt by non-primary admin {chat_id}.")
        return

    if not app_config_holder.is_radarr_enabled():
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Radarr API features are disabled.", parse_mode=None)

        await display_radarr_controls_menu(update, context)
        return

    keyboard = [
        [InlineKeyboardButton("🔄 Scan Files (Disk Sync)",
                              callback_data=CallbackData.CMD_RADARR_SCAN_FILES.value)],
        [InlineKeyboardButton(
            "♻️ Update All Metadata", callback_data=CallbackData.CMD_RADARR_UPDATE_METADATA.value)],
        [InlineKeyboardButton("✍️ Rename All Movie Files",
                              callback_data=CallbackData.CMD_RADARR_RENAME_FILES.value)],

        [InlineKeyboardButton("🔙 Back to Radarr Controls",
                              callback_data=CallbackData.CMD_RADARR_CONTROLS.value)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_message_id = load_menu_message_id(str(chat_id))
    if not menu_message_id and context.bot_data:
        menu_message_id = context.bot_data.get(
            f"main_menu_message_id_{chat_id}")

    escaped_menu_title_for_display = escape_md_v2(
        RADARR_LIBRARY_MAINTENANCE_MENU_TEXT_RAW)

    if menu_message_id:
        try:
            current_content_key = f"menu_message_content_{chat_id}_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (
                escaped_menu_title_for_display, reply_markup.to_json())

            if old_content_tuple != new_content_tuple:
                await context.bot.edit_message_text(
                    chat_id=chat_id, message_id=menu_message_id,
                    text=escaped_menu_title_for_display, reply_markup=reply_markup, parse_mode="MarkdownV2"
                )
                context.bot_data[current_content_key] = new_content_tuple
            await send_or_edit_universal_status_message(context.bot, chat_id, "Select a Radarr library maintenance action.", parse_mode=None)
        except BadRequest as e:
            if "message is not modified" in str(e).lower():
                logger.debug(
                    f"Radarr Library Maintenance menu already displayed for message {menu_message_id}. Edit skipped.")
            else:
                logger.error(
                    f"Error displaying Radarr Library Maintenance menu: {e}", exc_info=True)
            await display_radarr_controls_menu(update, context)
        except Exception as e:
            logger.error(
                f"Error displaying Radarr Library Maintenance menu: {e}", exc_info=True)
            await display_radarr_controls_menu(update, context)
    else:
        logger.error(
            "Cannot find menu_message_id for Radarr Library Maintenance menu.")
        await display_radarr_controls_menu(update, context)
