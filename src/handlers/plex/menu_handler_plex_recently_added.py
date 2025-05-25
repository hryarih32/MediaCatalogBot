import logging
import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.bot_text_utils import escape_md_v1, escape_md_v2
import src.app.app_config_holder as app_config_holder
from src.bot.bot_callback_data import CallbackData
from src.bot.bot_initialization import send_or_edit_universal_status_message
from src.bot.bot_message_persistence import load_menu_message_id
from src.services.plex.bot_plex_library import get_plex_libraries
from src.services.plex.bot_plex_media_items import get_recently_added_from_library

from src.handlers.plex.menu_handler_plex_controls import display_plex_controls_menu

logger = logging.getLogger(__name__)

PLEX_LIBRARY_LIST_TEXT_RAW = "📚 Plex Libraries - Recently Added:"
PLEX_RECENTLY_ADDED_ITEMS_TEXT_TEMPLATE_RAW = "🆕 Recently Added in *{library_name}* (Page {current_page}/{total_pages}):"


async def plex_recently_added_select_library_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    admin_chat_id_str = app_config_holder.get_chat_id_str()
    if not admin_chat_id_str or str(chat_id) != admin_chat_id_str:
        logger.warning(
            f"Plex recently added select lib attempt by non-primary admin {chat_id}.")
        return

    if not app_config_holder.is_plex_enabled():
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Plex features are disabled.", parse_mode=None)
        return
    libraries = get_plex_libraries()
    if not libraries:
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ No Plex libraries found or error fetching them.", parse_mode=None)
        await display_plex_controls_menu(update, context)
        return
    keyboard = []
    for lib in libraries:
        button_lib_title = f"{lib['title']} ({lib['type']})"
        if len(button_lib_title) > 50:
            button_lib_title = button_lib_title[:47] + "..."
        callback_data_val = f"{CallbackData.CMD_PLEX_RECENTLY_ADDED_SHOW_ITEMS_FOR_LIB_PREFIX.value}{lib['key']}"
        keyboard.append([InlineKeyboardButton(
            button_lib_title, callback_data=callback_data_val)])

    keyboard.append([InlineKeyboardButton("🔙 Back to Plex Controls",
                    callback_data=CallbackData.CMD_PLEX_CONTROLS.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_message_id = load_menu_message_id(str(chat_id))
    escaped_menu_title = escape_md_v2(
        PLEX_LIBRARY_LIST_TEXT_RAW.replace("-", "\\-"))

    if menu_message_id:
        try:
            current_content_key = f"menu_message_content_{chat_id}_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (escaped_menu_title, reply_markup.to_json())
            if old_content_tuple != new_content_tuple:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=menu_message_id, text=escaped_menu_title, reply_markup=reply_markup, parse_mode="MarkdownV2")
                context.bot_data[current_content_key] = new_content_tuple
            else:
                logger.debug(
                    f"Plex library list for recently added (message {menu_message_id}) is already up to date.")
            await send_or_edit_universal_status_message(context.bot, chat_id, "Select a library to view recently added items.", parse_mode=None)
        except Exception as e:
            if "message is not modified" in str(e).lower():
                logger.debug(
                    f"Plex library list menu already displayed {menu_message_id}. Edit skipped.")
                await send_or_edit_universal_status_message(context.bot, chat_id, "Select a library to view recently added items.", parse_mode=None)
            else:
                logger.error(
                    f"Error editing message to show Plex library list for recently added: {e}", exc_info=True)
                await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Error displaying library list.", parse_mode=None)

                await display_plex_controls_menu(update, context)
    else:
        logger.error(
            "Cannot find menu_message_id for plex_recently_added_select_library_callback")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Critical error displaying libraries.", parse_mode=None)


async def plex_recently_added_show_results_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    admin_chat_id_str = app_config_holder.get_chat_id_str()
    if not admin_chat_id_str or str(chat_id) != admin_chat_id_str:
        logger.warning(
            f"Plex recently added results attempt by non-primary admin {chat_id}.")
        return

    library_key = ""
    if query.data.startswith(CallbackData.CMD_PLEX_RECENTLY_ADDED_SHOW_ITEMS_FOR_LIB_PREFIX.value):
        library_key = query.data.replace(
            CallbackData.CMD_PLEX_RECENTLY_ADDED_SHOW_ITEMS_FOR_LIB_PREFIX.value, "")
        page = 1
        context.user_data['plex_recently_added_current_library_key'] = library_key
        context.user_data.pop('plex_recently_added_all_items', None)
    elif query.data.startswith(CallbackData.CMD_PLEX_RECENTLY_ADDED_PAGE_PREFIX.value):
        payload = query.data.replace(
            CallbackData.CMD_PLEX_RECENTLY_ADDED_PAGE_PREFIX.value, "")
        parts = payload.split("_")
        if len(parts) == 2:
            library_key = parts[0]
            try:
                page = int(parts[1])
            except ValueError:
                logger.warning(
                    f"Invalid page number in recently added pagination: {parts[1]}")
                page = 1
            if context.user_data.get('plex_recently_added_current_library_key') != library_key:
                logger.warning(
                    "Library key mismatch in recently added pagination. Forcing refetch.")
                context.user_data['plex_recently_added_current_library_key'] = library_key
                context.user_data.pop('plex_recently_added_all_items', None)
                page = 1
        else:
            logger.error(
                f"Invalid payload for recently added page: {query.data}")
            await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Error: Invalid page request.", parse_mode=None)
            return
    else:
        logger.error(
            f"plex_recently_added_show_results_menu called with unhandled data: {query.data}")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Error: Unrecognized command.", parse_mode=None)
        return

    if not library_key or not library_key.isdigit():
        logger.error(
            f"Invalid library key for recently added items: {library_key}")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Error processing your request (invalid library key).", parse_mode=None)
        await display_plex_controls_menu(update, context)
        return

    if not app_config_holder.is_plex_enabled():
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Plex features are disabled.", parse_mode=None)
        return

    library_name_raw = "Selected Library"
    libs = get_plex_libraries()
    for lib_item in libs:
        if str(lib_item.get('key')) == library_key:
            library_name_raw = lib_item.get('title', library_name_raw)
            break
    escaped_library_name_status = escape_md_v1(library_name_raw)

    all_items = context.user_data.get('plex_recently_added_all_items')
    if not all_items:
        await send_or_edit_universal_status_message(context.bot, chat_id, f"⏳ Fetching recently added for '{escaped_library_name_status}'...", parse_mode="Markdown")
        max_fetch = app_config_holder.get_add_media_max_search_results()
        results_data = get_recently_added_from_library(
            library_key, max_items=max_fetch)
        if "error" in results_data:
            await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(results_data["error"]), parse_mode="MarkdownV2")
            await display_plex_controls_menu(update, context)
            return
        all_items = results_data.get("items", [])
        context.user_data['plex_recently_added_all_items'] = all_items
        status_message_on_fetch = results_data.get(
            "message", f"Recently added items for '{escaped_library_name_status}':")
        await send_or_edit_universal_status_message(context.bot, chat_id, status_message_on_fetch, parse_mode="Markdown")

    items_per_page = app_config_holder.get_add_media_items_per_page()
    total_records = len(all_items)
    total_pages = math.ceil(
        total_records / items_per_page) if total_records > 0 else 1
    current_page = max(1, min(page, total_pages))
    start_index = (current_page - 1) * items_per_page
    end_index = start_index + items_per_page
    page_items = all_items[start_index:end_index]

    if not query.data.startswith(CallbackData.CMD_PLEX_RECENTLY_ADDED_SHOW_ITEMS_FOR_LIB_PREFIX.value) or 'plex_recently_added_all_items' in context.user_data:
        status_message_paginated_raw = f"Displaying page {current_page} of {total_pages} for recently added in '{library_name_raw}'."
        if not page_items and current_page > 1:
            status_message_paginated_raw = f"No more items on page {current_page} for '{library_name_raw}'."
        elif not all_items:
            status_message_paginated_raw = f"No recently added items found in '{library_name_raw}'."
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(status_message_paginated_raw), parse_mode="MarkdownV2")

    keyboard = []
    if page_items:
        for item in page_items:
            btn_text = item['display_text']
            if len(btn_text) > 55:
                btn_text = btn_text[:52] + "..."
            keyboard.append([InlineKeyboardButton(
                btn_text, callback_data=f"{CallbackData.CMD_PLEX_SEARCH_SHOW_DETAILS_PREFIX.value}{item['ratingKey']}")])

    pagination_row_ra = []
    if current_page > 1:
        pagination_row_ra.append(InlineKeyboardButton(
            "◀️ Prev", callback_data=f"{CallbackData.CMD_PLEX_RECENTLY_ADDED_PAGE_PREFIX.value}{library_key}_{current_page-1}"))
    if current_page < total_pages:
        pagination_row_ra.append(InlineKeyboardButton(
            "Next ▶️", callback_data=f"{CallbackData.CMD_PLEX_RECENTLY_ADDED_PAGE_PREFIX.value}{library_key}_{current_page+1}"))
    if pagination_row_ra:
        keyboard.append(pagination_row_ra)

    keyboard.append([InlineKeyboardButton("🔄 Refresh Full List",
                    callback_data=f"{CallbackData.CMD_PLEX_RECENTLY_ADDED_SHOW_ITEMS_FOR_LIB_PREFIX.value}{library_key}")])

    keyboard.append([InlineKeyboardButton("📚 To Library List (Recent)",
                    callback_data=CallbackData.CMD_PLEX_VIEW_RECENTLY_ADDED.value)])

    keyboard.append([InlineKeyboardButton("⏪ To Plex Controls",
                    callback_data=CallbackData.CMD_PLEX_CONTROLS.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_message_id = load_menu_message_id(str(chat_id))

    if menu_message_id:
        try:
            escaped_library_name_menu_v2 = escape_md_v2(library_name_raw)
            menu_text_display = PLEX_RECENTLY_ADDED_ITEMS_TEXT_TEMPLATE_RAW.format(
                library_name=escaped_library_name_menu_v2, current_page=current_page, total_pages=total_pages).replace("(", "\\(").replace(")", "\\)")
            current_content_key = f"menu_message_content_{chat_id}_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (menu_text_display, reply_markup.to_json())
            if old_content_tuple != new_content_tuple:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=menu_message_id, text=menu_text_display, reply_markup=reply_markup, parse_mode="MarkdownV2")
                context.bot_data[current_content_key] = new_content_tuple
        except Exception as e:
            if "message is not modified" in str(e).lower():
                logger.debug(
                    f"Plex recently added items menu already displayed for {menu_message_id}. Edit skipped.")
            else:
                logger.error(
                    f"Error editing message for Plex recently added items: {e}", exc_info=True)

                await display_plex_controls_menu(update, context)
    else:
        logger.error(
            "Cannot find menu_message_id for plex_recently_added_show_results_menu")
