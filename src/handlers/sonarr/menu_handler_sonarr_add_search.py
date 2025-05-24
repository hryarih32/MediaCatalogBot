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
from src.bot.bot_callback_data import CallbackData
import src.app.app_config_holder as app_config_holder

from src.handlers.sonarr.menu_handler_sonarr_add_flow import CB_ADD_DEFAULT_S, CB_START_CUSTOMIZE_SONARR, CB_SUBMIT_REQUEST_SONARR

from src.bot.bot_text_utils import escape_md_v1, escape_md_v2, format_media_title_for_md2, format_overview_for_md2

logger = logging.getLogger(__name__)

ADD_SHOW_SEARCH_RESULTS_TEXT = "🎞️ Sonarr Search Results (Page {current_page}/{total_pages}):"

MAX_OVERVIEW_LENGTH_SONARR = 250


async def handle_sonarr_search_initiation(update: Update, context: ContextTypes.DEFAULT_TYPE, query_text: str, chat_id: int):
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
            f"Sonarr search for '{query_text}' returned an error string: {search_output_data}")
        await send_or_edit_universal_status_message(context.bot, chat_id, search_output_data, parse_mode="Markdown")
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

    main_menu_msg_id = load_menu_message_id(str(chat_id_to_use))

    if not main_menu_msg_id:
        logger.error(
            f"Cannot display Sonarr search results for chat {chat_id_to_use}: main_menu_message_id not found.")
        await send_or_edit_universal_status_message(context.bot, chat_id_to_use, "⚠️ Error: Could not display search results (menu ID missing).", parse_mode=None)
        await show_or_edit_main_menu(str(chat_id_to_use), context, force_send_new=True)
        return

    results = load_show_results(get_show_results_file_path_local())
    if not results:
        await send_or_edit_universal_status_message(context.bot, chat_id_to_use, "No Sonarr results found or results expired.", parse_mode=None)
        await show_or_edit_main_menu(str(chat_id_to_use), context)
        return

    user_role = app_config_holder.get_user_role(str(chat_id_to_use))

    max_results = app_config_holder.get_add_media_max_search_results()
    items_per_page = app_config_holder.get_add_media_items_per_page()
    results_to_consider = results[:max_results]
    total_items_to_paginate = len(results_to_consider)
    total_pages = math.ceil(total_items_to_paginate /
                            items_per_page) if total_items_to_paginate > 0 else 1
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

    menu_text_display_v2 = escape_md_v2(ADD_SHOW_SEARCH_RESULTS_TEXT.format(
        current_page=current_page, total_pages=total_pages).replace("(", "\\(").replace(")", "\\)"))

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id_to_use, message_id=main_menu_msg_id, text=menu_text_display_v2,
            reply_markup=reply_markup, parse_mode="MarkdownV2"
        )
        context.bot_data[f"menu_message_content_{chat_id_to_use}_{main_menu_msg_id}"] = (
            menu_text_display_v2, reply_markup.to_json())

        status_msg_text_raw_final = ""
        if not page_items and current_page == 1:
            pass
        elif page_items:
            status_msg_text_raw_final = f"Displaying Sonarr search results: Page {current_page} of {total_pages}."

        if status_msg_text_raw_final:
            await send_or_edit_universal_status_message(context.bot, chat_id_to_use, escape_md_v2(status_msg_text_raw_final), parse_mode="MarkdownV2")

    except RetryAfter as e:
        logger.warning(
            f"Rate limited while trying to display Sonarr search page {current_page} for chat {chat_id_to_use}. Retrying after {e.retry_after}s.")
        await send_or_edit_universal_status_message(context.bot, chat_id_to_use, f"⏳ Telegram is busy, please wait a moment and try again. (Page {current_page})", parse_mode=None)
    except Exception as e:
        logger.error(
            f"Error editing main menu for Sonarr search results (page {current_page}, chat {chat_id_to_use}): {e}", exc_info=True)
        await send_or_edit_universal_status_message(context.bot, chat_id_to_use, "⚠️ Error displaying Sonarr search results.", parse_mode=None)
        await show_or_edit_main_menu(str(chat_id_to_use), context, force_send_new=True)


async def sonarr_show_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    flow_data_key = 'sonarr_add_flow'

    flow_data_from_context_copy = context.user_data.get(
        flow_data_key, {}).copy()

    data_to_process = None

    if 'initiator_action_data' in flow_data_from_context_copy:
        data_to_process = flow_data_from_context_copy.pop(
            'initiator_action_data')

        context.user_data[flow_data_key] = flow_data_from_context_copy
        logger.debug(
            f"Sonarr selection: Using initiator_action_data: {data_to_process}")
    else:
        data_to_process = query.data
        logger.debug(f"Sonarr selection: Using query.data: {data_to_process}")

    chat_id = update.effective_chat.id
    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.first_name or str(
        user_id)

    user_role = app_config_holder.get_user_role(str(chat_id))

    try:
        is_admin_add_flow = data_to_process.startswith(
            CallbackData.SONARR_SELECT_PREFIX.value)
        is_user_request_flow = data_to_process.startswith(
            CallbackData.SONARR_REQUEST_PREFIX.value)

        tvdb_id_str = ""
        if is_admin_add_flow:
            tvdb_id_str = data_to_process.replace(
                CallbackData.SONARR_SELECT_PREFIX.value, "")
        elif is_user_request_flow:
            tvdb_id_str = data_to_process.replace(
                CallbackData.SONARR_REQUEST_PREFIX.value, "")
        else:
            logger.error(
                f"Unknown prefix in sonarr_show_selection_callback with data: {data_to_process}")
            return

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
                await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)
                return
            if show_api_details.get('overview'):
                raw_overview = show_api_details.get('overview')

        except Exception as e_lookup:
            logger.warning(
                f"Could not pre-fetch full show details for Sonarr (TVDB ID {tvdb_id}): {e_lookup}", exc_info=True)
            await send_or_edit_universal_status_message(context.bot, chat_id, f"⚠️ Error: Could not fetch details for selected show \\(TVDB ID: {tvdb_id}\\)\\.", parse_mode="MarkdownV2")
            await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)
            return

        current_flow_data_for_update = context.user_data.get(flow_data_key, {})
        current_flow_data_for_update.update({
            'show_tvdb_id': show_api_details['tvdbId'],
            'show_title': show_api_details.get('title', 'Unknown Title'),
            'show_year': show_api_details.get('year'),
            'raw_overview': raw_overview,
            'sonarr_show_object_from_lookup': show_api_details,
            'current_step': 'initial_choice_sonarr',
            'chat_id': chat_id,
            'user_id': user_id,
            'username': username,
            'main_menu_message_id': query.message.message_id
        })

        if 'approved_request_id' in flow_data_from_context_copy:
            current_flow_data_for_update['approved_request_id'] = flow_data_from_context_copy['approved_request_id']
            current_flow_data_for_update['approved_request_original_user_id'] = flow_data_from_context_copy['approved_request_original_user_id']
            current_flow_data_for_update['approved_request_original_username'] = flow_data_from_context_copy['approved_request_original_username']

        context.user_data[flow_data_key] = current_flow_data_for_update
        active_flow_data = context.user_data[flow_data_key]

        keyboard = []
        is_from_admin_approval = 'approved_request_id' in active_flow_data

        if user_role == app_config_holder.ROLE_ADMIN and (is_admin_add_flow or is_from_admin_approval):
            keyboard = [
                [InlineKeyboardButton("Add with Defaults",
                                      callback_data=CB_ADD_DEFAULT_S)],
                [InlineKeyboardButton("Customize Settings",
                                      callback_data=CB_START_CUSTOMIZE_SONARR)],
                [InlineKeyboardButton(
                    "Cancel Add", callback_data=CallbackData.SONARR_CANCEL.value)]
            ]
        elif (user_role == app_config_holder.ROLE_STANDARD_USER or user_role == app_config_holder.ROLE_ADMIN) and is_user_request_flow and not is_from_admin_approval:
            keyboard = [
                [InlineKeyboardButton("✅ Submit Request",
                                      callback_data=CB_SUBMIT_REQUEST_SONARR)],
                [InlineKeyboardButton(
                    "Cancel Request", callback_data=CallbackData.SONARR_CANCEL.value)]
            ]
        else:
            logger.warning(
                f"sonarr_show_selection_callback: Role/flow mismatch. Role: {user_role}, is_admin_add: {is_admin_add_flow}, is_user_request: {is_user_request_flow}, is_from_admin_approval: {is_from_admin_approval}")
            await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Action not available for your role or current flow.", parse_mode=None)
            await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)
            return

        reply_markup = InlineKeyboardMarkup(keyboard)

        formatted_title_year = format_media_title_for_md2(
            active_flow_data['show_title'],
            active_flow_data['show_year']
        )
        formatted_overview = format_overview_for_md2(
            active_flow_data['raw_overview'],
            MAX_OVERVIEW_LENGTH_SONARR
        )

        msg_text = f"🎞️ {formatted_title_year}\n\n"
        msg_text += f"{formatted_overview}\n\n"
        if user_role == app_config_holder.ROLE_ADMIN and (is_admin_add_flow or is_from_admin_approval):
            prompt_action_text = "add to Sonarr"
            if is_from_admin_approval:
                prompt_action_text = f"add to Sonarr (fulfilling request from {escape_md_v2(str(active_flow_data.get('approved_request_original_username', 'user')))})"
            msg_text += escape_md_v2(f"Choose how to {prompt_action_text}:")
        else:
            msg_text += escape_md_v2("Confirm your request for this TV show:")

        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=query.message.message_id, text=msg_text,
            reply_markup=reply_markup, parse_mode="MarkdownV2"
        )
        context.bot_data[f"menu_message_content_{chat_id}_{query.message.message_id}"] = (
            msg_text, reply_markup.to_json())
    except (IndexError, ValueError, KeyError) as e:
        logger.error(
            f"Error in Sonarr show selection processing: {e}", exc_info=True)
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Error processing Sonarr selection.", parse_mode=None)
        await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)


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
