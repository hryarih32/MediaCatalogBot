
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

PC_CONTROL_CATEGORIES_MENU_TEXT_RAW = "🖥️ PC Control Categories"


async def display_pc_control_categories_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_role = app_config_holder.get_user_role(str(chat_id))
    is_primary_admin_check = app_config_holder.is_primary_admin(str(chat_id))

    if query:
        await query.answer()

    if not is_primary_admin_check:
        logger.warning(
            f"Unauthorized attempt to access PC control categories from chat_id {chat_id} (Role: {user_role}, IsPrimary: {is_primary_admin_check})")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied. PC Controls are for administrators.", parse_mode=None)
        return

    if not app_config_holder.is_pc_control_enabled():
        logger.info(
            f"PC control categories menu request by {chat_id}, but feature is disabled.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ PC Control features are currently disabled in the bot's settings.", parse_mode=None)

        return

    keyboard = []
    buttons_added = 0

    media_control_available = True
    try:
        import pyautogui
    except ImportError:
        media_control_available = False
        logger.warning(
            "PyAutoGUI not found, PC Media controls will be limited or disabled for display.")

    if media_control_available:
        keyboard.append([InlineKeyboardButton(
            "🎧 Media & Sound", callback_data=CallbackData.CMD_PC_SHOW_MEDIA_SOUND_MENU.value)])
        buttons_added += 1

    keyboard.append([InlineKeyboardButton(
        "🔌 System Power", callback_data=CallbackData.CMD_PC_SHOW_SYSTEM_POWER_MENU.value)])
    buttons_added += 1

    if buttons_added == 0:
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ No PC control options seem available despite feature being enabled. Check logs/dependencies.", parse_mode=None)
        await show_or_edit_main_menu(str(chat_id), context)
        return

    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu",
                    callback_data=CallbackData.CMD_HOME_BACK.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)

    menu_message_id = load_menu_message_id(str(chat_id))
    if not menu_message_id and context.bot_data:
        menu_message_id = context.bot_data.get(
            f"main_menu_message_id_{chat_id}")

    escaped_menu_title_for_display = escape_md_v2(
        PC_CONTROL_CATEGORIES_MENU_TEXT_RAW)

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

            await send_or_edit_universal_status_message(context.bot, chat_id, "Select a PC control category.", parse_mode=None)

        except BadRequest as e:
            if "message is not modified" in str(e).lower():
                logger.debug(
                    f"PC Control Categories menu content was not modified (BadRequest): {menu_message_id}")
            else:
                logger.error(
                    f"BadRequest editing message for PC Control Categories menu: {e}", exc_info=True)

                await show_or_edit_main_menu(str(chat_id), context)
        except Exception as e:
            logger.error(
                f"Error editing message for PC Control Categories menu: {e}", exc_info=True)

            await show_or_edit_main_menu(str(chat_id), context)
    else:
        logger.error(
            "Could not find main_menu_message_id for PC Control Categories menu.")
        await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)
