
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

import src.app.app_config_holder as app_config_holder
from src.bot.bot_message_persistence import load_menu_message_id
from src.bot.bot_initialization import send_or_edit_universal_status_message, show_or_edit_main_menu
from src.bot.bot_callback_data import CallbackData
from src.bot.bot_text_utils import escape_md_v2

from src.services.plex.bot_plex_core import (
    clean_plex_bundles,
    empty_plex_trash,
    optimize_plex_database,
    get_plex_server_info_formatted
)
from src.services.plex.bot_plex_library import get_plex_libraries, format_bytes_to_readable

from src.handlers.plex.menu_handler_plex_library_server_tools import display_plex_library_server_tools_menu

from src.handlers.plex.menu_handler_plex_main import _truncate_button_text_plex_lib

logger = logging.getLogger(__name__)

PLEX_SERVER_TOOLS_SUB_MENU_TEXT_RAW = "🔧 Plex - Server Maintenance & Info"
PLEX_EMPTY_TRASH_LIBRARY_LIST_TEXT_RAW = "🗑️ Plex Libraries - Empty Trash:"
PLEX_SERVER_INFO_DISPLAY_TEXT_RAW = "ℹ️ Plex Server Information"


async def display_plex_server_tools_sub_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, server_info_text: str | None = None) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_role = app_config_holder.get_user_role(str(chat_id))

    if query and (query.data == CallbackData.CMD_PLEX_SERVER_TOOLS_SUB_MENU.value or server_info_text or
                  query.data == CallbackData.CMD_PLEX_SERVER_INFO.value):
        try:
            await query.answer()
        except BadRequest as e_ans:
            if "query is too old" not in str(e_ans).lower() and "callback query is not found" not in str(e_ans).lower():
                logger.debug(
                    f"Query answer failed in display_plex_server_tools_sub_menu: {e_ans}")
    elif query:
        await query.answer()

    if user_role != app_config_holder.ROLE_ADMIN:
        logger.warning(
            f"Plex server tools sub menu attempt by non-admin {chat_id} (Role: {user_role}).")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied. Server tools are for administrators.", parse_mode=None)
        return

    if not app_config_holder.is_plex_enabled():
        logger.info(
            f"Plex server tools sub menu request by {chat_id}, but Plex feature is disabled.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Plex features are disabled.", parse_mode=None)

        await display_plex_library_server_tools_menu(update, context, called_internally=True)
        return

    keyboard = []
    menu_text_display = ""
    status_update_text = "Select a server maintenance task or view info."

    if server_info_text:

        menu_text_display = f"*{escape_md_v2(PLEX_SERVER_INFO_DISPLAY_TEXT_RAW)}*\n\n{server_info_text}"
        keyboard.append([InlineKeyboardButton("🔙 Back to Server Maintenance",
                        callback_data=CallbackData.CMD_PLEX_SERVER_TOOLS_SUB_MENU.value)])
        status_update_text = "Plex server information displayed."
    else:
        menu_text_display = escape_md_v2(PLEX_SERVER_TOOLS_SUB_MENU_TEXT_RAW)
        keyboard = [
            [InlineKeyboardButton(
                "🧹 Clean Bundles", callback_data=CallbackData.CMD_PLEX_CLEAN_BUNDLES.value)],
            [InlineKeyboardButton(
                "🗑️ Empty Trash...", callback_data=CallbackData.CMD_PLEX_EMPTY_TRASH_SELECT_LIBRARY.value)],
            [InlineKeyboardButton(
                "⚙️ Optimize Database", callback_data=CallbackData.CMD_PLEX_OPTIMIZE_DB.value)],
            [InlineKeyboardButton(
                "ℹ️ Server Info", callback_data=CallbackData.CMD_PLEX_SERVER_INFO.value)],
            [InlineKeyboardButton("🔙 Back to Library & Server Tools",
                                  callback_data=CallbackData.CMD_PLEX_LIBRARY_SERVER_TOOLS.value)]
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_message_id = load_menu_message_id(str(chat_id))
    if not menu_message_id and context.bot_data:
        menu_message_id = context.bot_data.get(
            f"main_menu_message_id_{chat_id}")

    if menu_message_id:
        try:
            current_content_key = f"menu_message_content_{chat_id}_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (menu_text_display, reply_markup.to_json())

            if old_content_tuple != new_content_tuple:
                await context.bot.edit_message_text(
                    chat_id=chat_id, message_id=menu_message_id,
                    text=menu_text_display,
                    reply_markup=reply_markup, parse_mode="MarkdownV2"
                )
                context.bot_data[current_content_key] = new_content_tuple

            await send_or_edit_universal_status_message(context.bot, chat_id, status_update_text, parse_mode=None)

        except BadRequest as e:
            if "message is not modified" in str(e).lower():
                logger.debug(
                    f"Plex Server Tools Sub-menu already displayed. Message ID: {menu_message_id}")
                await send_or_edit_universal_status_message(context.bot, chat_id, status_update_text, parse_mode=None)
            else:
                logger.error(
                    f"BadRequest displaying Plex Server Tools Sub-menu (edit): {e}. Text was: '{menu_text_display}'", exc_info=True)

                await display_plex_library_server_tools_menu(update, context, called_internally=True)
        except Exception as e:
            logger.error(
                f"Error displaying Plex Server Tools Sub-menu: {e}. Text was: '{menu_text_display}'", exc_info=True)

            await display_plex_library_server_tools_menu(update, context, called_internally=True)
    else:
        logger.error(
            "Cannot find menu_message_id for Plex Server Tools Sub-menu.")

        await display_plex_library_server_tools_menu(update, context, called_internally=True)


async def handle_plex_server_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_role = app_config_holder.get_user_role(str(chat_id))

    await query.answer()

    if user_role != app_config_holder.ROLE_ADMIN:
        logger.warning(
            f"Plex server action attempt by non-admin {chat_id} (Role: {user_role}).")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied. Server actions are for administrators.", parse_mode=None)
        return

    callback_data_str = query.data
    result_message_raw = "An unknown error occurred."
    action_status_message_raw = None

    if not app_config_holder.is_plex_enabled():
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Plex features are disabled.", parse_mode=None)
        return

    if callback_data_str == CallbackData.CMD_PLEX_CLEAN_BUNDLES.value:
        action_status_message_raw = "⏳ Initiating Plex 'Clean Bundles'..."
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(action_status_message_raw), parse_mode="MarkdownV2")
        result_message_raw = clean_plex_bundles()
    elif callback_data_str == CallbackData.CMD_PLEX_OPTIMIZE_DB.value:
        action_status_message_raw = "⏳ Initiating Plex 'Optimize Database'..."
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(action_status_message_raw), parse_mode="MarkdownV2")
        result_message_raw = optimize_plex_database()
    elif callback_data_str == CallbackData.CMD_PLEX_SERVER_INFO.value:
        action_status_message_raw = "⏳ Fetching Plex server & library info..."
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(action_status_message_raw), parse_mode="MarkdownV2")

        server_info_data = get_plex_server_info_formatted()

        info_parts_display = []

        if "error" in server_info_data:
            info_parts_display.append(escape_md_v2(server_info_data["error"]))
        else:
            for key, value_raw in server_info_data.items():
                key_v2 = escape_md_v2(key)
                value_v2 = escape_md_v2(str(value_raw))
                info_parts_display.append(f"  *{key_v2}:*\n    {value_v2}")

            all_libraries_detailed = get_plex_libraries(force_refresh=True)
            library_stats = {"movie": {"count": 0}, "show": {
                "count": 0}, "artist": {"count": 0}}
            if all_libraries_detailed:
                for lib_detail in all_libraries_detailed:
                    lib_type = lib_detail.get('type')
                    if lib_type in library_stats:
                        library_stats[lib_type]["count"] += lib_detail.get(
                            'item_count', 0)

                info_parts_display.append(
                    f"\n*{escape_md_v2('Plex Library Counts:')}*")
                if library_stats["movie"]["count"] > 0:
                    info_parts_display.append(
                        f"  *{escape_md_v2('Movies:')}* {escape_md_v2(str(library_stats['movie']['count']))} items")
                if library_stats["show"]["count"] > 0:
                    info_parts_display.append(
                        f"  *{escape_md_v2('TV Shows:')}* {escape_md_v2(str(library_stats['show']['count']))} {escape_md_v2('(Series)')}")
                if library_stats["artist"]["count"] > 0:
                    info_parts_display.append(
                        f"  *{escape_md_v2('Music:')}* {escape_md_v2(str(library_stats['artist']['count']))} {escape_md_v2('(Artists)')}")
            else:
                info_parts_display.append(
                    f"\n_{escape_md_v2('Could not fetch Plex library statistics.')}_")

            if app_config_holder.is_sonarr_enabled():
                from src.services.sonarr.bot_sonarr_manage import get_sonarr_library_stats
                sonarr_stats = get_sonarr_library_stats()
                info_parts_display.append(
                    f"\n*{escape_md_v2('Sonarr Managed:')}*")
                if not sonarr_stats.get("error"):
                    info_parts_display.extend([
                        f"  Series: {escape_md_v2(str(sonarr_stats['total_series']))}",
                        f"  Episode Files: {escape_md_v2(str(sonarr_stats['total_episodes']))}",
                        f"  Disk Usage: {escape_md_v2(format_bytes_to_readable(sonarr_stats['total_size_on_disk_bytes']))}"
                    ])
                else:
                    info_parts_display.append(
                        f"  {escape_md_v2(sonarr_stats.get('error'))}")

            if app_config_holder.is_radarr_enabled():
                from src.services.radarr.bot_radarr_manage import get_radarr_library_stats
                radarr_stats = get_radarr_library_stats()
                info_parts_display.append(
                    f"\n*{escape_md_v2('Radarr Managed:')}*")
                if not radarr_stats.get("error"):
                    info_parts_display.extend([
                        f"  Movies: {escape_md_v2(str(radarr_stats['total_movies']))}",
                        f"  Disk Usage: {escape_md_v2(format_bytes_to_readable(radarr_stats['total_size_on_disk_bytes']))}"
                    ])
                else:
                    info_parts_display.append(
                        f"  {escape_md_v2(radarr_stats.get('error'))}")

        formatted_server_info_for_menu_display = "\n".join(info_parts_display)

        await display_plex_server_tools_sub_menu(update, context, server_info_text=formatted_server_info_for_menu_display)
        return
    else:
        logger.warning(f"Unhandled Plex server action: {callback_data_str}")
        result_message_raw = "⚠️ Unrecognized Plex server action."

    await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(result_message_raw), parse_mode="MarkdownV2")
    if callback_data_str in [CallbackData.CMD_PLEX_CLEAN_BUNDLES.value, CallbackData.CMD_PLEX_OPTIMIZE_DB.value]:

        await display_plex_server_tools_sub_menu(update, context)


async def plex_empty_trash_select_library_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_role = app_config_holder.get_user_role(str(chat_id))

    await query.answer()

    if user_role != app_config_holder.ROLE_ADMIN:
        logger.warning(
            f"Plex empty trash select lib attempt by non-admin {chat_id} (Role: {user_role}).")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied. Emptying trash is for administrators.", parse_mode=None)
        return

    if not app_config_holder.is_plex_enabled():
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Plex features are disabled.", parse_mode=None)

        await display_plex_server_tools_sub_menu(update, context)
        return

    libraries = get_plex_libraries()
    if not libraries:
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ No Plex libraries found or error fetching them.", parse_mode=None)

        await display_plex_server_tools_sub_menu(update, context)
        return

    keyboard = [[InlineKeyboardButton("➡️ Empty Trash for ALL Libraries ⬅️",
                                      callback_data=f"{CallbackData.CMD_PLEX_EMPTY_TRASH_EXECUTE_PREFIX.value}all")]]
    for lib in libraries:
        base_button_text = f"{lib['title']} ({lib['type']})"

        button_text = _truncate_button_text_plex_lib(
            base_button_text, lib.get('item_count', 0), "Empty Trash: ")
        keyboard.append([InlineKeyboardButton(
            button_text, callback_data=f"{CallbackData.CMD_PLEX_EMPTY_TRASH_EXECUTE_PREFIX.value}{lib['key']}")])

    keyboard.append([InlineKeyboardButton("🔙 Back to Server Maintenance",
                    callback_data=CallbackData.CMD_PLEX_SERVER_TOOLS_SUB_MENU.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_message_id = load_menu_message_id(str(chat_id))
    escaped_menu_title = escape_md_v2(PLEX_EMPTY_TRASH_LIBRARY_LIST_TEXT_RAW)

    if menu_message_id:
        try:
            current_content_key = f"menu_message_content_{chat_id}_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (escaped_menu_title, reply_markup.to_json())
            if old_content_tuple != new_content_tuple:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=menu_message_id,
                    text=escaped_menu_title,
                    reply_markup=reply_markup,
                    parse_mode="MarkdownV2"
                )
                context.bot_data[current_content_key] = new_content_tuple
            await send_or_edit_universal_status_message(context.bot, chat_id, "Select a library to empty its trash, or all.", parse_mode=None)
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                logger.error(
                    f"Error editing message for Plex Empty Trash list: {e}", exc_info=True)

            await display_plex_server_tools_sub_menu(update, context)
        except Exception as e:
            logger.error(
                f"Error editing message for Plex Empty Trash list: {e}", exc_info=True)

            await display_plex_server_tools_sub_menu(update, context)
    else:
        logger.error(
            "Cannot find menu_message_id for plex_empty_trash_select_library_callback")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Critical error displaying libraries for Empty Trash.", parse_mode=None)


async def plex_empty_trash_execute_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_role = app_config_holder.get_user_role(str(chat_id))

    await query.answer()

    if user_role != app_config_holder.ROLE_ADMIN:
        logger.warning(
            f"Plex empty trash execute attempt by non-admin {chat_id} (Role: {user_role}).")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied. Emptying trash is for administrators.", parse_mode=None)
        return

    data_parts = query.data.split(
        CallbackData.CMD_PLEX_EMPTY_TRASH_EXECUTE_PREFIX.value)
    if len(data_parts) < 2:
        logger.error(f"Invalid callback data for empty trash: {query.data}")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Error processing empty trash request.", parse_mode=None)
        return
    library_key_or_all = data_parts[1]

    if not app_config_holder.is_plex_enabled():
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Plex features are disabled.", parse_mode=None)
        return

    target_raw = "all libraries" if library_key_or_all == "all" else f"library key {library_key_or_all}"
    await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(f"⏳ Initiating Plex 'Empty Trash' for {target_raw}\\.\\.\\."), parse_mode="MarkdownV2")

    result_message_raw = empty_plex_trash(
        library_key_or_all if library_key_or_all != "all" else None)
    await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(result_message_raw), parse_mode="MarkdownV2")

    await display_plex_server_tools_sub_menu(update, context)
