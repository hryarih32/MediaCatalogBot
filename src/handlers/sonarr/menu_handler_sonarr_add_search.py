
import logging
import math

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import ContextTypes
from telegram.error import RetryAfter, BadRequest

from src.services.sonarr.bot_sonarr_add import search_show, load_results as load_show_results, get_show_results_file_path_local

from src.bot.bot_initialization import (
    show_or_edit_main_menu,
    send_or_edit_universal_status_message,
    load_menu_message_id
)
from src.bot.bot_callback_data import CallbackData
import src.app.app_config_holder as app_config_holder

from src.bot.bot_text_utils import escape_md_v1, escape_md_v2, format_media_title_for_md2, format_overview_for_md2

logger = logging.getLogger(__name__)

ADD_SHOW_SEARCH_RESULTS_TEXT_MD2_TEMPLATE = "🎞️ Sonarr Search Results \\(Page {current_page}/{total_pages}\\):"

MAX_OVERVIEW_LENGTH_SONARR = 250


async def handle_sonarr_search_initiation(update: Update, context: ContextTypes.DEFAULT_TYPE, query_text: str, chat_id: int):

    if not app_config_holder.is_sonarr_enabled():
        logger.info(
            f"Sonarr search initiation by {chat_id} aborted, Sonarr is disabled.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Sonarr API features are disabled.", parse_mode=None)
        await show_or_edit_main_menu(str(chat_id), context)
        return

    await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)
    await send_or_edit_universal_status_message(
        context.bot,
        chat_id,

        f"⏳ Searching Sonarr for \"{escape_md_v2(query_text)}\"\\.\\.\\.",
        parse_mode="MarkdownV2"
    )

    search_output_data = search_show(query_text)

    if isinstance(search_output_data, str):
        logger.warning(
            f"Sonarr search for '{query_text}' by {chat_id} returned an error string: {search_output_data}")

        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v1(search_output_data), parse_mode="Markdown")

        await show_or_edit_main_menu(str(chat_id), context)
        return

    await display_sonarr_search_results_page(update, context, page=1, user_chat_id=chat_id)


async def display_sonarr_search_results_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1, user_chat_id: int | None = None):

    query = update.callback_query

    if query:
        await query.answer()
        chat_id_to_use = query.message.chat.id
    elif user_chat_id:
        chat_id_to_use = user_chat_id
    else:
        chat_id_to_use = update.effective_chat.id
        logger.warning(
            "display_sonarr_search_results_page called without query or user_chat_id.")

    main_menu_msg_id = load_menu_message_id(str(chat_id_to_use))
    if not main_menu_msg_id and context.bot_data:
        main_menu_msg_id = context.bot_data.get(
            f"main_menu_message_id_{chat_id_to_use}")

    if not main_menu_msg_id:
        logger.error(
            f"Cannot display Sonarr search results for chat {chat_id_to_use}: main_menu_message_id not found.")
        await send_or_edit_universal_status_message(context.bot, chat_id_to_use, "⚠️ Error: Could not display search results (menu ID missing). Please try /start.", parse_mode=None)
        return

    results = load_show_results(get_show_results_file_path_local())
    if not results:
        await send_or_edit_universal_status_message(context.bot, chat_id_to_use, "No Sonarr results found or results expired. Please try searching again.", parse_mode=None)

        await show_or_edit_main_menu(str(chat_id_to_use), context)
        return

    user_role = app_config_holder.get_user_role(
        str(chat_id_to_use))

    max_results_to_show = app_config_holder.get_add_media_max_search_results()
    items_per_page = app_config_holder.get_add_media_items_per_page()

    results_to_consider = results[:max_results_to_show]
    total_items_to_paginate = len(results_to_consider)
    total_pages = math.ceil(total_items_to_paginate /
                            items_per_page) if total_items_to_paginate > 0 else 1
    current_page = max(1, min(page, total_pages))

    start_index = (current_page - 1) * items_per_page
    end_index = start_index + items_per_page
    page_items = results_to_consider[start_index:end_index]

    keyboard = []
    status_for_page_display_raw = ""

    if not page_items:
        if current_page > 1:
            status_for_page_display_raw = "No more results on this page."
        else:
            status_for_page_display_raw = "No Sonarr results found for your search."

    if status_for_page_display_raw:
        await send_or_edit_universal_status_message(context.bot, chat_id_to_use, escape_md_v2(status_for_page_display_raw), parse_mode="MarkdownV2")

    for show in page_items:
        button_text = f"{show.get('title', 'Unknown Title')} ({show.get('year', 'N/A')})"
        if len(button_text) > 50:
            button_text = button_text[:47] + "..."

        if user_role == app_config_holder.ROLE_ADMIN:
            cb_prefix = CallbackData.SONARR_SELECT_PREFIX.value
        else:
            cb_prefix = CallbackData.SONARR_REQUEST_PREFIX.value

        keyboard.append([InlineKeyboardButton(
            text=button_text, callback_data=f"{cb_prefix}{show['tvdbId']}")])

    pagination_row = []
    if current_page > 1:
        pagination_row.append(InlineKeyboardButton(
            "◀️ Prev", callback_data=f"{CallbackData.SONARR_ADD_MEDIA_PAGE_PREFIX.value}{current_page-1}"))
    if current_page < total_pages:
        pagination_row.append(InlineKeyboardButton(
            "Next ▶️", callback_data=f"{CallbackData.SONARR_ADD_MEDIA_PAGE_PREFIX.value}{current_page+1}"))
    if pagination_row:
        keyboard.append(pagination_row)

    keyboard.append([InlineKeyboardButton("❌ Cancel Search/Request",
                    callback_data=CallbackData.SONARR_CANCEL.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)

    menu_text_display_v2 = ADD_SHOW_SEARCH_RESULTS_TEXT_MD2_TEMPLATE.format(
        current_page=escape_md_v2(str(current_page)),
        total_pages=escape_md_v2(str(total_pages))
    )

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id_to_use, message_id=main_menu_msg_id, text=menu_text_display_v2,
            reply_markup=reply_markup, parse_mode="MarkdownV2"
        )
        context.bot_data[f"menu_message_content_{chat_id_to_use}_{main_menu_msg_id}"] = (
            menu_text_display_v2, reply_markup.to_json())

        if not status_for_page_display_raw and page_items:
            status_msg_text = f"Displaying Sonarr search results: Page {current_page} of {total_pages}."
            await send_or_edit_universal_status_message(context.bot, chat_id_to_use, escape_md_v2(status_msg_text), parse_mode="MarkdownV2")

    except RetryAfter as e:
        logger.warning(
            f"Rate limited while trying to display Sonarr search page {current_page} for chat {chat_id_to_use}. Retrying after {e.retry_after}s.")
        await send_or_edit_universal_status_message(context.bot, chat_id_to_use, f"⏳ Telegram is busy, please wait a moment and try again. (Page {current_page})", parse_mode=None)
    except BadRequest as e:
        if "message is not modified" in str(e).lower():
            logger.debug(
                f"Sonarr search results page {current_page} for chat {chat_id_to_use} not modified.")
            if (not query or query.data != f"{CallbackData.SONARR_ADD_MEDIA_PAGE_PREFIX.value}{current_page}") and \
               not status_for_page_display_raw and page_items:
                status_msg_text = f"Displaying Sonarr search results: Page {current_page} of {total_pages}."
                await send_or_edit_universal_status_message(context.bot, chat_id_to_use, escape_md_v2(status_msg_text), parse_mode="MarkdownV2")
        else:
            logger.error(
                f"BadRequest editing main menu for Sonarr search results (page {current_page}, chat {chat_id_to_use}): {e}", exc_info=True)
            await send_or_edit_universal_status_message(context.bot, chat_id_to_use, "⚠️ Error displaying Sonarr search results.", parse_mode=None)
            await show_or_edit_main_menu(str(chat_id_to_use), context, force_send_new=True)
    except Exception as e:
        logger.error(
            f"Error editing main menu for Sonarr search results (page {current_page}, chat {chat_id_to_use}): {e}", exc_info=True)
        await send_or_edit_universal_status_message(context.bot, chat_id_to_use, "⚠️ Error displaying Sonarr search results.", parse_mode=None)
        await show_or_edit_main_menu(str(chat_id_to_use), context, force_send_new=True)


async def sonarr_add_media_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    page_data = query.data.replace(
        CallbackData.SONARR_ADD_MEDIA_PAGE_PREFIX.value, "")
    try:
        page = int(page_data)
        await display_sonarr_search_results_page(update, context, page=page, user_chat_id=query.message.chat.id)
    except ValueError:
        logger.error(
            f"Invalid page number in Sonarr add media pagination: {page_data}")
        await send_or_edit_universal_status_message(context.bot, update.effective_chat.id, "⚠️ Invalid page request.", parse_mode=None)
