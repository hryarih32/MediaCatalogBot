import logging
import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import ContextTypes
from telegram.error import RetryAfter

from src.services.radarr.bot_radarr_add import search_movie, load_results as load_movie_results, get_movie_results_file_path_local
from src.bot.bot_initialization import (
    show_or_edit_main_menu,
    send_or_edit_universal_status_message,
    load_menu_message_id
)
from src.bot.bot_callback_data import CallbackData
import src.app.app_config_holder as app_config_holder
from src.bot.bot_text_utils import escape_md_v1

logger = logging.getLogger(__name__)

ADD_MOVIE_SEARCH_RESULTS_TEXT = "🎬 Radarr Search Results (Page {current_page}/{total_pages}):"


async def handle_radarr_search_initiation(update: Update, context: ContextTypes.DEFAULT_TYPE, query_text: str, chat_id: int):
    await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)
    await send_or_edit_universal_status_message(context.bot, chat_id, f"⏳ Searching Radarr for \"{escape_md_v1(query_text)}\"...", parse_mode="Markdown")
    search_output_data = search_movie(query_text)

    if isinstance(search_output_data, str):
        logger.warning(
            f"Radarr search for '{query_text}' returned an error string: {search_output_data}")
        await send_or_edit_universal_status_message(context.bot, chat_id, search_output_data, parse_mode="Markdown")

        await show_or_edit_main_menu(str(chat_id), context)
        return
    await display_radarr_search_results_page(update, context, page=1, user_chat_id=chat_id)


async def display_radarr_search_results_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1, user_chat_id: int | None = None):
    query = update.callback_query
    if query:
        await query.answer()
        chat_id_to_use = query.message.chat.id
    elif user_chat_id:
        chat_id_to_use = user_chat_id
    else:
        chat_id_to_use = update.effective_chat.id

    main_menu_msg_id = load_menu_message_id(
        str(chat_id_to_use))

    if not main_menu_msg_id:
        logger.error(
            f"Cannot display Radarr search results for chat {chat_id_to_use}: main_menu_message_id not found.")
        await send_or_edit_universal_status_message(context.bot, chat_id_to_use, "⚠️ Error: Could not display search results (menu ID missing).")
        await show_or_edit_main_menu(str(chat_id_to_use), context, force_send_new=True)
        return

    results = load_movie_results(get_movie_results_file_path_local())
    if not results:
        await send_or_edit_universal_status_message(context.bot, chat_id_to_use, "No Radarr results found or results expired.")
        await show_or_edit_main_menu(str(chat_id_to_use), context)
        return

    user_role = app_config_holder.get_user_role(str(chat_id_to_use))

    max_results = app_config_holder.get_add_media_max_search_results()
    items_per_page = app_config_holder.get_add_media_items_per_page()
    results_to_consider = results[:max_results]
    total_items_to_paginate = len(results_to_consider)
    total_pages = math.ceil(total_items_to_paginate / items_per_page)
    if total_pages == 0:
        total_pages = 1
    current_page = max(1, min(page, total_pages))
    start_index = (current_page - 1) * items_per_page
    end_index = start_index + items_per_page
    page_items = results_to_consider[start_index:end_index]
    keyboard = []

    if not page_items and current_page > 1:
        await send_or_edit_universal_status_message(context.bot, chat_id_to_use, "No more results on this page.")
    elif not page_items and current_page == 1:
        await send_or_edit_universal_status_message(context.bot, chat_id_to_use, "No Radarr results found.")

    for movie in page_items:
        button_text = f"{movie.get('title', 'Unknown Title')} ({movie.get('year', 'N/A')})"
        if len(button_text) > 50:
            button_text = button_text[:47] + "..."

        if user_role == app_config_holder.ROLE_ADMIN:
            cb_prefix = CallbackData.RADARR_SELECT_PREFIX.value
        else:
            cb_prefix = CallbackData.RADARR_REQUEST_PREFIX.value

        keyboard.append([InlineKeyboardButton(
            text=button_text, callback_data=f"{cb_prefix}{movie['tmdbId']}")])

    pagination_row = []
    if current_page > 1:
        pagination_row.append(InlineKeyboardButton(
            "◀️ Prev", callback_data=f"{CallbackData.RADARR_ADD_MEDIA_PAGE_PREFIX.value}{current_page-1}"))
    if current_page < total_pages:
        pagination_row.append(InlineKeyboardButton(
            "Next ▶️", callback_data=f"{CallbackData.RADARR_ADD_MEDIA_PAGE_PREFIX.value}{current_page+1}"))
    if pagination_row:
        keyboard.append(pagination_row)
    keyboard.append([InlineKeyboardButton("❌ Cancel Search",
                    callback_data=CallbackData.RADARR_CANCEL.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_text_display = ADD_MOVIE_SEARCH_RESULTS_TEXT.format(
        current_page=current_page, total_pages=total_pages)

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id_to_use, message_id=main_menu_msg_id, text=menu_text_display,
            reply_markup=reply_markup, parse_mode="Markdown"
        )
        context.bot_data[f"menu_message_content_{chat_id_to_use}_{main_menu_msg_id}"] = (
            menu_text_display, reply_markup.to_json())
        if not page_items and current_page == 1:
            status_msg_text = "No Radarr results found."
        else:
            status_msg_text = f"Displaying Radarr search results: Page {current_page} of {total_pages}."
        await send_or_edit_universal_status_message(context.bot, chat_id_to_use, status_msg_text, parse_mode=None)
    except RetryAfter as e:
        logger.warning(
            f"Rate limited while trying to display Radarr search page {current_page} for chat {chat_id_to_use}. Retrying after {e.retry_after}s.")
        await send_or_edit_universal_status_message(context.bot, chat_id_to_use, f"⏳ Telegram is busy, please wait a moment and try again. (Page {current_page})", parse_mode=None)
    except Exception as e:
        logger.error(
            f"Error editing main menu for Radarr search results (page {current_page}, chat {chat_id_to_use}): {e}", exc_info=True)
        await send_or_edit_universal_status_message(context.bot, chat_id_to_use, "⚠️ Error displaying Radarr search results.")
        await show_or_edit_main_menu(str(chat_id_to_use), context, force_send_new=True)


async def radarr_add_media_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    page_data = query.data.replace(
        CallbackData.RADARR_ADD_MEDIA_PAGE_PREFIX.value, "")
    try:
        page = int(page_data)
        await display_radarr_search_results_page(update, context, page=page, user_chat_id=query.message.chat.id)
    except ValueError:
        logger.error(
            f"Invalid page number in Radarr add media pagination: {page_data}")
        await send_or_edit_universal_status_message(context.bot, update.effective_chat.id, "⚠️ Invalid page request.")
