
import logging
import urllib.parse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

import src.app.app_config_holder as app_config_holder

from src.bot.bot_callback_data import CallbackData
from src.bot.bot_initialization import send_or_edit_universal_status_message, load_menu_message_id, show_or_edit_main_menu
from src.app import launcher_manager
from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)

LAUNCHERS_MENU_TITLE_RAW = "🚀 Launchers"
SUBGROUP_MENU_TITLE_TEMPLATE_RAW = "📂 Subgroup: {subgroup_name}"
ITEMS_PER_ROW_LAUNCHERS = 3


async def handle_subgroup_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles a subgroup button press, stores selection, and re-displays the launchers menu."""
    query = update.callback_query
    await query.answer()

    subgroup_name_encoded = query.data.replace(
        CallbackData.CMD_LAUNCHER_SUBGROUP_PREFIX.value, "")
    subgroup_name = urllib.parse.unquote_plus(
        subgroup_name_encoded)

    context.user_data['launcher_selected_subgroup'] = subgroup_name
    logger.debug(
        f"Subgroup '{subgroup_name}' selected by user {update.effective_chat.id}")

    await display_launchers_menu(update, context)


async def handle_dynamic_launcher_execution(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles a dynamic launcher button press."""
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    launcher_id = query.data.replace(
        CallbackData.CMD_LAUNCH_DYNAMIC_PREFIX.value, "")

    launcher_details = launcher_manager.get_launcher_details(launcher_id)
    launcher_name_disp = launcher_details.get(
        "name", "Selected Launcher") if launcher_details else "Unknown Launcher"

    await send_or_edit_universal_status_message(
        context.bot, chat_id,
        escape_md_v2(f"⏳ Attempting to run {launcher_name_disp}\\.\\.\\."),
        parse_mode="MarkdownV2"
    )

    status_msg_raw = launcher_manager.run_dynamic_launcher(launcher_id)

    await send_or_edit_universal_status_message(
        context.bot, chat_id,
        escape_md_v2(status_msg_raw),
        parse_mode="MarkdownV2"
    )

    await display_launchers_menu(update, context)


async def handle_back_to_subgroups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the 'Back to Subgroups' button press."""
    query = update.callback_query
    await query.answer()
    context.user_data.pop('launcher_selected_subgroup',
                          None)
    logger.debug(
        f"User {update.effective_chat.id} navigating back to subgroup list.")

    await display_launchers_menu(update, context)


async def display_launchers_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id

    if not app_config_holder.is_primary_admin(str(chat_id)):
        logger.warning(
            f"Unauthorized attempt to access launchers menu by non-primary admin {chat_id}")
        if query:
            await query.answer("Access Denied.", show_alert=True)
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied. This feature is for the Primary Administrator only.", parse_mode=None)

        return

    if query and query.data == CallbackData.CMD_LAUNCHERS_MENU.value:
        await query.answer()

        context.user_data.pop('launcher_selected_subgroup', None)

    keyboard_rows = []
    menu_title_text = LAUNCHERS_MENU_TITLE_RAW

    selected_subgroup = context.user_data.get('launcher_selected_subgroup')
    all_dynamic_launchers = launcher_manager.get_all_dynamic_launchers(
        force_refresh=True)

    current_row = []

    if selected_subgroup:
        menu_title_text = SUBGROUP_MENU_TITLE_TEMPLATE_RAW.format(
            subgroup_name=escape_md_v2(selected_subgroup))
        launchers_to_display = launcher_manager.get_launchers_by_subgroup(
            selected_subgroup)
        launchers_to_display.sort(key=lambda x: x.get(
            "name", "").lower())

        for launcher in launchers_to_display:
            btn_text = launcher.get("name", "Unnamed Launcher")
            if len(btn_text) > 25:
                btn_text = btn_text[:22] + "..."
            current_row.append(InlineKeyboardButton(
                f"▶️ {btn_text}",
                callback_data=f"{CallbackData.CMD_LAUNCH_DYNAMIC_PREFIX.value}{launcher.get('id')}"
            ))
            if len(current_row) == ITEMS_PER_ROW_LAUNCHERS:
                keyboard_rows.append(current_row)
                current_row = []
        if current_row:
            keyboard_rows.append(current_row)

        if not launchers_to_display:
            keyboard_rows.append([InlineKeyboardButton(
                "ℹ️ No launchers in this subgroup.", callback_data="cb_no_op")])

        keyboard_rows.append([InlineKeyboardButton(
            "🔙 Back to Subgroups", callback_data=CallbackData.CMD_LAUNCHERS_BACK_TO_SUBGROUPS.value)])

    else:
        all_subgroups = launcher_manager.get_all_subgroups()
        ungrouped_launchers = launcher_manager.get_launchers_by_subgroup(None)
        ungrouped_launchers.sort(key=lambda x: x.get("name", "").lower())

        if all_subgroups:
            for subgroup in all_subgroups:
                btn_text = subgroup
                if len(btn_text) > 25:
                    btn_text = btn_text[:22] + "..."
                subgroup_encoded = urllib.parse.quote_plus(subgroup)
                current_row.append(InlineKeyboardButton(
                    f"📂 {btn_text}",
                    callback_data=f"{CallbackData.CMD_LAUNCHER_SUBGROUP_PREFIX.value}{subgroup_encoded}"
                ))
                if len(current_row) == ITEMS_PER_ROW_LAUNCHERS:
                    keyboard_rows.append(current_row)
                    current_row = []
            if current_row:
                keyboard_rows.append(current_row)
                current_row = []

        if ungrouped_launchers:
            if all_subgroups:

                if current_row:
                    keyboard_rows.append(current_row)
                    current_row = []

            for launcher in ungrouped_launchers:
                btn_text = launcher.get("name", "Unnamed Launcher")
                if len(btn_text) > 25:
                    btn_text = btn_text[:22] + "..."
                current_row.append(InlineKeyboardButton(
                    f"▶️ {btn_text}",
                    callback_data=f"{CallbackData.CMD_LAUNCH_DYNAMIC_PREFIX.value}{launcher.get('id')}"
                ))
                if len(current_row) == ITEMS_PER_ROW_LAUNCHERS:
                    keyboard_rows.append(current_row)
                    current_row = []
            if current_row:
                keyboard_rows.append(current_row)

        if not all_subgroups and not ungrouped_launchers:
            keyboard_rows.append([InlineKeyboardButton(
                "ℹ️ No launchers configured.", callback_data="cb_no_op")])

    keyboard_rows.append([InlineKeyboardButton(
        "🔙 Back to Main Menu", callback_data=CallbackData.CMD_HOME_BACK.value)])
    reply_markup = InlineKeyboardMarkup(keyboard_rows)

    menu_message_id = load_menu_message_id(str(chat_id))
    if not menu_message_id and context.bot_data:
        menu_message_id = context.bot_data.get(
            f"main_menu_message_id_{chat_id}")

    escaped_menu_title_for_display = escape_md_v2(
        menu_title_text.replace("*", "\\*"))

    if menu_message_id:
        try:
            current_content_key = f"menu_message_content_{chat_id}_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (
                escaped_menu_title_for_display, reply_markup.to_json())

            if old_content_tuple != new_content_tuple or \
               (query and query.data == CallbackData.CMD_LAUNCHERS_MENU.value):
                await context.bot.edit_message_text(
                    chat_id=chat_id, message_id=menu_message_id,
                    text=escaped_menu_title_for_display, reply_markup=reply_markup,
                    parse_mode="MarkdownV2"
                )
                context.bot_data[current_content_key] = new_content_tuple

            status_msg_to_send = "Select a launcher or subgroup."
            if selected_subgroup:
                status_msg_to_send = f"Displaying launchers in subgroup '{selected_subgroup}'."
            elif not all_dynamic_launchers:
                status_msg_to_send = "No launchers configured. Add them via /settings."

            if query and (query.data == CallbackData.CMD_LAUNCHERS_MENU.value or
                          query.data.startswith(CallbackData.CMD_LAUNCHER_SUBGROUP_PREFIX.value) or
                          query.data == CallbackData.CMD_LAUNCHERS_BACK_TO_SUBGROUPS.value):
                await send_or_edit_universal_status_message(context.bot, chat_id, status_msg_to_send, parse_mode=None)

        except BadRequest as e:
            if "message is not modified" in str(e).lower():
                logger.debug("Launchers menu not modified.")
            else:
                logger.error(
                    f"BadRequest displaying launchers menu: {e}", exc_info=True)
                await show_or_edit_main_menu(str(chat_id), context)
        except Exception as e:
            logger.error(
                f"Error displaying launchers menu: {e}", exc_info=True)
            await show_or_edit_main_menu(str(chat_id), context)
    else:
        logger.error("Could not find main_menu_message_id for Launchers menu.")
        await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)
