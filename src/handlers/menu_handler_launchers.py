import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

import src.app.app_config_holder as app_config_holder
from src.bot.bot_callback_data import CallbackData
from src.bot.bot_initialization import send_or_edit_universal_status_message, load_menu_message_id, show_or_edit_main_menu

from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)

LAUNCHERS_LIST_MENU_TEXT_RAW = "🚀 Launchers & Scripts"


async def display_launchers_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:

        if query.data == CallbackData.CMD_LAUNCHERS_MENU.value:
            await query.answer()

    chat_id = update.effective_chat.id
    admin_chat_id_str = app_config_holder.get_chat_id_str()

    if not admin_chat_id_str or str(chat_id) != admin_chat_id_str:
        logger.warning(
            f"Unauthorized attempt to access launchers menu from chat_id {chat_id}")
        return

    keyboard = []
    launcher_buttons_added = 0

    ordered_launchers_map = {
        "PLEX": CallbackData.CMD_LAUNCH_PLEX,
        "SONARR": CallbackData.CMD_LAUNCH_SONARR,
        "RADARR": CallbackData.CMD_LAUNCH_RADARR,
        "PROWLARR": CallbackData.CMD_LAUNCH_PROWLARR,
        "TORRENT": CallbackData.CMD_LAUNCH_TORRENT,
        "ABDM": CallbackData.CMD_LAUNCH_ABDM,
    }

    for service_prefix, cb_data in ordered_launchers_map.items():
        if app_config_holder.is_service_launcher_enabled(service_prefix):
            launcher_name = app_config_holder.get_service_launcher_name(
                service_prefix) or f"Launch {service_prefix.capitalize()}"

            if service_prefix == "ABDM":
                launcher_name = app_config_holder.get_abdm_launcher_name() or "Launch AB Download Manager"

            keyboard.append([InlineKeyboardButton(
                f"▶️ {launcher_name}", callback_data=cb_data.value)])
            launcher_buttons_added += 1

    for i in range(1, 4):
        if app_config_holder.is_script_enabled(i):
            script_name = app_config_holder.get_script_name(i) or f"Script {i}"
            callback_val_str = f"CMD_SCRIPT_{i}"
            if hasattr(CallbackData, callback_val_str):
                callback_val = getattr(CallbackData, callback_val_str).value
                keyboard.append([InlineKeyboardButton(
                    f"⚙️ {script_name}", callback_data=callback_val)])
                launcher_buttons_added += 1
            else:
                logger.error(
                    f"CallbackData missing for script in launchers menu: {callback_val_str}")

    status_msg_after_build = "Select an application or script to launch."
    if launcher_buttons_added == 0:
        status_msg_after_build = "ℹ️ No application launchers or custom scripts are enabled."

        keyboard.append([InlineKeyboardButton(
            "🔙 Back to Main Menu", callback_data=CallbackData.CMD_HOME_BACK.value)])
        reply_markup = InlineKeyboardMarkup(keyboard)
        menu_message_id = load_menu_message_id()

        escaped_menu_title = escape_md_v2(LAUNCHERS_LIST_MENU_TEXT_RAW)

        if menu_message_id:
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=menu_message_id,
                text=escaped_menu_title, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )
        await send_or_edit_universal_status_message(context.bot, chat_id, status_msg_after_build, parse_mode=None)

        if query and query.data == CallbackData.CMD_LAUNCHERS_MENU.value and launcher_buttons_added == 0:
            await show_or_edit_main_menu(admin_chat_id_str, context)
        return

    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu",
                    callback_data=CallbackData.CMD_HOME_BACK.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)

    menu_message_id = load_menu_message_id()
    if not menu_message_id and context.bot_data:
        menu_message_id = context.bot_data.get("main_menu_message_id")

    escaped_menu_title_for_display = escape_md_v2(LAUNCHERS_LIST_MENU_TEXT_RAW)

    if menu_message_id:
        try:
            current_content_key = f"menu_message_content_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (
                escaped_menu_title_for_display, reply_markup.to_json())

            if old_content_tuple != new_content_tuple or \
               (query and query.data == CallbackData.CMD_LAUNCHERS_MENU.value):
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=menu_message_id,
                    text=escaped_menu_title_for_display,
                    reply_markup=reply_markup,
                    parse_mode="MarkdownV2"
                )
                context.bot_data[current_content_key] = new_content_tuple
                logger.info(
                    f"Launchers list menu displayed/refreshed by editing message {menu_message_id}")
            else:
                logger.debug(
                    f"Launchers list menu content for message {menu_message_id} is already up to date. Edit skipped.")

            if query and query.data == CallbackData.CMD_LAUNCHERS_MENU.value:
                await send_or_edit_universal_status_message(context.bot, chat_id, status_msg_after_build, parse_mode=None)

        except BadRequest as e:
            if "message is not modified" in str(e).lower():
                logger.debug(
                    f"Launchers list menu content for message {menu_message_id} was not modified (caught by API). Edit skipped.")
                if query and query.data == CallbackData.CMD_LAUNCHERS_MENU.value:
                    await send_or_edit_universal_status_message(context.bot, chat_id, status_msg_after_build, parse_mode=None)
            else:
                logger.error(
                    f"Error editing message for Launchers list menu: {e}", exc_info=True)
                if admin_chat_id_str:
                    await show_or_edit_main_menu(admin_chat_id_str, context)
        except Exception as e:
            logger.error(
                f"Unexpected error editing message for Launchers list menu: {e}", exc_info=True)
            if admin_chat_id_str:
                await show_or_edit_main_menu(admin_chat_id_str, context)
    else:
        logger.error(
            "Could not find main_menu_message_id for Launchers list menu.")

        if admin_chat_id_str:
            await show_or_edit_main_menu(admin_chat_id_str, context, force_send_new=True)
