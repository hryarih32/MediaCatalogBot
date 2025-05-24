import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

import src.app.app_config_holder as app_config_holder
from src.bot.bot_message_persistence import load_menu_message_id
from src.bot.bot_initialization import send_or_edit_universal_status_message, show_or_edit_main_menu
from src.bot.bot_callback_data import CallbackData
from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)

RADARR_CONTROLS_MENU_TEXT_RAW = "🎬 Radarr Controls"


async def display_radarr_controls_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()

    chat_id = update.effective_chat.id

    admin_chat_id_str = app_config_holder.get_chat_id_str()

    if not admin_chat_id_str or str(chat_id) != admin_chat_id_str:
        logger.warning(
            f"Unauthorized attempt to access Radarr controls menu from chat_id {chat_id}")
        return

    if not app_config_holder.is_radarr_enabled():
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Radarr API features are disabled.", parse_mode=None)
        await show_or_edit_main_menu(admin_chat_id_str, context)
        return

    keyboard = [
        [InlineKeyboardButton(
            "📥 View Download Queue", callback_data=CallbackData.CMD_RADARR_VIEW_QUEUE.value)],
        [InlineKeyboardButton(
            "🛠️ Library Maintenance", callback_data=CallbackData.CMD_RADARR_LIBRARY_MAINTENANCE.value)],
        [InlineKeyboardButton("🔙 Back to Main Menu",
                              callback_data=CallbackData.CMD_HOME_BACK.value)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_message_id = load_menu_message_id()
    if not menu_message_id and context.bot_data:
        menu_message_id = context.bot_data.get("main_menu_message_id")

    escaped_menu_title_for_display = escape_md_v2(
        RADARR_CONTROLS_MENU_TEXT_RAW)

    if menu_message_id:
        try:
            current_content_key = f"menu_message_content_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (
                escaped_menu_title_for_display, reply_markup.to_json())

            if old_content_tuple != new_content_tuple:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=menu_message_id,
                    text=escaped_menu_title_for_display,
                    reply_markup=reply_markup,
                    parse_mode="MarkdownV2"
                )
                context.bot_data[current_content_key] = new_content_tuple
            await send_or_edit_universal_status_message(context.bot, chat_id, "Select a Radarr control option.", parse_mode=None)
        except BadRequest as e:
            if "message is not modified" in str(e).lower():
                logger.debug(
                    f"Radarr Controls menu already displayed for message {menu_message_id}. Edit skipped.")
            else:
                logger.error(
                    f"Error displaying Radarr Controls menu: {e}", exc_info=True)
            if admin_chat_id_str:
                await show_or_edit_main_menu(admin_chat_id_str, context)
        except Exception as e:
            logger.error(
                f"Error displaying Radarr Controls menu: {e}", exc_info=True)
            if admin_chat_id_str:
                await show_or_edit_main_menu(admin_chat_id_str, context)
    else:
        logger.error(
            "Could not find main_menu_message_id for Radarr Controls menu.")
        if admin_chat_id_str:
            await show_or_edit_main_menu(admin_chat_id_str, context, force_send_new=True)
