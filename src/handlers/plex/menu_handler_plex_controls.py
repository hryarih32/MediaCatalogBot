
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

PLEX_CONTROLS_MENU_TEXT_RAW = "🌐 Plex Controls"


async def display_plex_controls_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_role = app_config_holder.get_user_role(str(chat_id))

    if query:
        await query.answer()

    if user_role != app_config_holder.ROLE_ADMIN:
        logger.warning(
            f"Unauthorized attempt to access Plex controls menu from chat_id {chat_id} (Role: {user_role})")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied. Plex Controls are for administrators.", parse_mode=None)

        return

    if not app_config_holder.is_plex_enabled():
        logger.info(
            f"Plex controls menu request by {chat_id}, but Plex feature is disabled.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Plex API features are disabled in the bot's settings.", parse_mode=None)

        return

    keyboard = [
        [InlineKeyboardButton(
            "📺 View Now Playing", callback_data=CallbackData.CMD_PLEX_VIEW_NOW_PLAYING.value)],
        [InlineKeyboardButton(
            "🆕 View Recently Added", callback_data=CallbackData.CMD_PLEX_VIEW_RECENTLY_ADDED.value)],
        [InlineKeyboardButton(
            "🔍 Search Plex Content", callback_data=CallbackData.CMD_PLEX_INITIATE_SEARCH.value)],
        [InlineKeyboardButton("🛠️ Library & Server Tools",
                              callback_data=CallbackData.CMD_PLEX_LIBRARY_SERVER_TOOLS.value)],
        [InlineKeyboardButton("🔙 Back to Main Menu",
                              callback_data=CallbackData.CMD_HOME_BACK.value)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_message_id = load_menu_message_id(str(chat_id))
    if not menu_message_id and context.bot_data:
        menu_message_id = context.bot_data.get(
            f"main_menu_message_id_{chat_id}")

    escaped_menu_title_for_display = escape_md_v2(PLEX_CONTROLS_MENU_TEXT_RAW)

    if menu_message_id:
        try:
            current_content_key = f"menu_message_content_{chat_id}_{menu_message_id}"
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
            await send_or_edit_universal_status_message(context.bot, chat_id, "Select a Plex control option.", parse_mode=None)
        except BadRequest as e:
            if "message is not modified" in str(e).lower():
                logger.debug(
                    f"Plex Controls menu already displayed for message {menu_message_id}. Edit skipped.")

                await send_or_edit_universal_status_message(context.bot, chat_id, "Select a Plex control option.", parse_mode=None)
            else:
                logger.error(
                    f"BadRequest displaying Plex Controls menu: {e}", exc_info=True)
                await show_or_edit_main_menu(str(chat_id), context)
        except Exception as e:
            logger.error(
                f"Error displaying Plex Controls menu: {e}", exc_info=True)
            await show_or_edit_main_menu(str(chat_id), context)
    else:
        logger.error(
            "Could not find main_menu_message_id for Plex Controls menu.")

        await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)
