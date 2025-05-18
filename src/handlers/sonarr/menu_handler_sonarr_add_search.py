import logging
import math

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import ContextTypes

from telegram.error import RetryAfter


from src.services.sonarr.bot_sonarr_add import search_show, load_results as load_show_results, get_show_results_file_path_local
from src.services.sonarr.bot_sonarr_core import _sonarr_request as sonarr_api_get
from src.bot.bot_initialization import (
    show_or_edit_main_menu,
    send_or_edit_universal_status_message,
    load_menu_message_id
)
from src.config.config_definitions import CallbackData
import src.app.app_config_holder as app_config_holder

from src.handlers.sonarr.menu_handler_sonarr_add_flow import CB_ADD_DEFAULT_S, CB_START_CUSTOMIZE_SONARR, CB_CANCEL_ADD_FLOW_S

from src.bot.bot_text_utils import escape_md_v1, escape_md_v2, format_media_title_for_md2, format_overview_for_md2

logger = logging.getLogger(__name__)

ADD_SHOW_SEARCH_RESULTS_TEXT = "🎞️ Sonarr Search Results (Page {current_page}/{total_pages}):"
MAX_OVERVIEW_LENGTH = 250


async def handle_sonarr_search_initiation(update: Update, context: ContextTypes.DEFAULT_TYPE, query_text: str, chat_id: int):
    await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)

    await send_or_edit_universal_status_message(
        context.bot,
        chat_id,

        f"⏳ Searching Sonarr for \"{escape_md_v2(query_text)}\"\\.\\.\\.",
        parse_mode="MarkdownV2"
    )

    search_output_data = search_show(query_text)
    admin_chat_id_str = app_config_holder.get_chat_id_str()

    if isinstance(search_output_data, str):
        logger.warning(
            f"Sonarr search for '{query_text}' returned an error string: {search_output_data}")

        await send_or_edit_universal_status_message(context.bot, chat_id, search_output_data, parse_mode="Markdown")
        if admin_chat_id_str:
            await show_or_edit_main_menu(admin_chat_id_str, context)
        return
    await display_sonarr_search_results_page(update, context, page=1)


async def display_sonarr_search_results_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1):
    query = update.callback_query
    if query:
        await query.answer()
    chat_id = update.effective_chat.id
    main_menu_msg_id = load_menu_message_id()

    if not main_menu_msg_id:
        logger.error(
            "Cannot display Sonarr search results: main_menu_message_id not found.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Error: Could not display search results (menu ID missing).", parse_mode=None)
        admin_chat_id_str = app_config_holder.get_chat_id_str()
        if admin_chat_id_str:
            await show_or_edit_main_menu(admin_chat_id_str, context, force_send_new=True)
        return

    results = load_show_results(get_show_results_file_path_local())
    if not results:
        await send_or_edit_universal_status_message(context.bot, chat_id, "No Sonarr results found or results expired.", parse_mode=None)
        admin_chat_id_str = app_config_holder.get_chat_id_str()
        if admin_chat_id_str:
            await show_or_edit_main_menu(admin_chat_id_str, context)
        return

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

    status_for_page_display_raw = ""
    if not page_items and current_page > 1:
        status_for_page_display_raw = "No more results on this page."
    elif not page_items and current_page == 1:
        status_for_page_display_raw = "No Sonarr results found."

    if status_for_page_display_raw:
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(status_for_page_display_raw), parse_mode="MarkdownV2")

    for show in page_items:
        button_text = f"{show.get('title', 'Unknown Title')} ({show.get('year', 'N/A')})"
        if len(button_text) > 50:
            button_text = button_text[:47] + "..."
        keyboard.append([InlineKeyboardButton(
            text=button_text, callback_data=f"{CallbackData.SONARR_SELECT_PREFIX.value}{show['tvdbId']}")])

    pagination_row = []
    if current_page > 1:
        pagination_row.append(InlineKeyboardButton(
            "◀️ Prev", callback_data=f"{CallbackData.SONARR_ADD_MEDIA_PAGE_PREFIX.value}{current_page-1}"))
    if current_page < total_pages:
        pagination_row.append(InlineKeyboardButton(
            "Next ▶️", callback_data=f"{CallbackData.SONARR_ADD_MEDIA_PAGE_PREFIX.value}{current_page+1}"))
    if pagination_row:
        keyboard.append(pagination_row)
    keyboard.append([InlineKeyboardButton("❌ Cancel Search",
                    callback_data=CallbackData.SONARR_CANCEL.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)

    menu_text_display_v2 = escape_md_v2(ADD_SHOW_SEARCH_RESULTS_TEXT.format(
        current_page=current_page, total_pages=total_pages))

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=main_menu_msg_id, text=menu_text_display_v2,

            reply_markup=reply_markup, parse_mode="MarkdownV2"
        )
        context.bot_data[f"menu_message_content_{main_menu_msg_id}"] = (
            menu_text_display_v2, reply_markup.to_json())

        status_msg_text_raw_final = ""
        if not page_items and current_page == 1:
            status_msg_text_raw_final = "No Sonarr results found."

        elif page_items:
            status_msg_text_raw_final = f"Displaying Sonarr search results: Page {current_page} of {total_pages}."

        if status_msg_text_raw_final:
            await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(status_msg_text_raw_final), parse_mode="MarkdownV2")

    except RetryAfter as e:
        logger.warning(
            f"Rate limited while trying to display Sonarr search page {current_page}. Retrying after {e.retry_after}s.")
        await send_or_edit_universal_status_message(context.bot, chat_id, f"⏳ Telegram is busy, please wait a moment and try again. (Page {current_page})", parse_mode=None)
    except Exception as e:
        logger.error(
            f"Error editing main menu for Sonarr search results (page {current_page}): {e}", exc_info=True)
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Error displaying Sonarr search results.", parse_mode=None)
        admin_chat_id_str = app_config_holder.get_chat_id_str()
        if admin_chat_id_str:
            await show_or_edit_main_menu(admin_chat_id_str, context, force_send_new=True)


async def sonarr_show_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id
    admin_chat_id_str = app_config_holder.get_chat_id_str()
    if not admin_chat_id_str or chat_id != int(admin_chat_id_str):
        logger.warning(
            "Sonarr show selection from non-admin or unconfigured admin.")
        return

    try:
        tvdb_id_str = data.replace(CallbackData.SONARR_SELECT_PREFIX.value, "")
        if not tvdb_id_str.isdigit():
            raise ValueError("Invalid TVDB ID format in callback data.")
        tvdb_id = int(tvdb_id_str)
        show_api_details = None
        raw_overview = "Overview not available."
        try:
            lookup_result = sonarr_api_get(
                'get', f'/series/lookup', params={'term': f'tvdb:{tvdb_id}'})
            if isinstance(lookup_result, list) and lookup_result:
                show_api_details = lookup_result[0]
            elif isinstance(lookup_result, dict) and lookup_result.get("tvdbId"):
                show_api_details = lookup_result
            if not show_api_details or not show_api_details.get("tvdbId"):
                logger.error(
                    f"Could not fetch valid show details for TVDB ID {tvdb_id}. Response: {lookup_result}")
                await send_or_edit_universal_status_message(context.bot, chat_id, f"⚠️ Error: Could not fetch details for selected show \\(TVDB ID: {tvdb_id}\\)\\.", parse_mode="MarkdownV2")
                if admin_chat_id_str:
                    await show_or_edit_main_menu(admin_chat_id_str, context, force_send_new=True)
                return
            if show_api_details.get('overview'):
                raw_overview = show_api_details.get('overview')

        except Exception as e_lookup:
            logger.warning(
                f"Could not pre-fetch full show details for Sonarr (TVDB ID {tvdb_id}): {e_lookup}", exc_info=True)
            await send_or_edit_universal_status_message(context.bot, chat_id, f"⚠️ Error: Could not fetch details for selected show \\(TVDB ID: {tvdb_id}\\)\\.", parse_mode="MarkdownV2")
            if admin_chat_id_str:
                await show_or_edit_main_menu(admin_chat_id_str, context, force_send_new=True)
            return

        context.user_data['sonarr_add_flow'] = {
            'show_tvdb_id': show_api_details['tvdbId'],

            'show_title': show_api_details.get('title', 'Unknown Title'),
            'show_year': show_api_details.get('year'),
            'raw_overview': raw_overview,
            'sonarr_show_object_from_lookup': show_api_details,
            'current_step': 'initial_choice_sonarr',
            'chat_id': chat_id,
            'main_menu_message_id': query.message.message_id
        }
        keyboard = [
            [InlineKeyboardButton("Add with Defaults",
                                  callback_data=CB_ADD_DEFAULT_S)],
            [InlineKeyboardButton("Customize Settings",
                                  callback_data=CB_START_CUSTOMIZE_SONARR)],
            [InlineKeyboardButton(
                "Cancel Add", callback_data=CB_CANCEL_ADD_FLOW_S)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        formatted_title_year = format_media_title_for_md2(
            context.user_data['sonarr_add_flow']['show_title'],
            context.user_data['sonarr_add_flow']['show_year']
        )
        formatted_overview = format_overview_for_md2(
            context.user_data['sonarr_add_flow']['raw_overview'],
            MAX_OVERVIEW_LENGTH
        )

        msg_text = f"🎞️ {formatted_title_year}\n\n"
        msg_text += f"{formatted_overview}\n\n"
        msg_text += escape_md_v2("Choose how to proceed:")

        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=query.message.message_id, text=msg_text,
            reply_markup=reply_markup, parse_mode="MarkdownV2"
        )
        context.bot_data[f"menu_message_content_{query.message.message_id}"] = (
            msg_text, reply_markup.to_json())
    except (IndexError, ValueError, KeyError) as e:
        logger.error(
            f"Error in Sonarr show selection processing: {e}", exc_info=True)
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Error processing Sonarr selection.", parse_mode=None)
        if admin_chat_id_str:
            await show_or_edit_main_menu(admin_chat_id_str, context, force_send_new=True)


async def sonarr_add_media_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    page_data = query.data.replace(
        CallbackData.SONARR_ADD_MEDIA_PAGE_PREFIX.value, "")
    try:
        page = int(page_data)
        await display_sonarr_search_results_page(update, context, page=page)
    except ValueError:
        logger.error(
            f"Invalid page number in Sonarr add media pagination: {page_data}")
        await send_or_edit_universal_status_message(context.bot, update.effective_chat.id, "⚠️ Invalid page request.", parse_mode=None)
