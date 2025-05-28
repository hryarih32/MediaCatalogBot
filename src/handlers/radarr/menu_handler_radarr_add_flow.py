
import logging
import os
import uuid
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from src.bot.bot_text_utils import format_media_title_for_md2, format_overview_for_md2, format_selected_option_for_md2, escape_md_v2, escape_for_inline_code, escape_md_v1
from src.services.radarr.bot_radarr_add import (
    add_movie as radarr_add_movie_func,
    get_root_folders, get_quality_profiles, get_tags,
    get_default_root_folder_id, get_default_quality_profile_id,
    get_minimum_availability_options
)
from src.services.radarr.bot_radarr_core import _radarr_request as radarr_api_get
from src.bot.bot_initialization import (
    show_or_edit_main_menu,
    send_or_edit_universal_status_message,
    refresh_main_menus_for_all_admins
)
from src.bot.bot_callback_data import CallbackData
import src.app.app_config_holder as app_config_holder
from src.app.app_file_utils import load_requests_data, save_requests_data

logger = logging.getLogger(__name__)

RADARR_CB_PREFIX = "radarr_cfg_"
CB_SELECT_ROOT_PREFIX = f"{RADARR_CB_PREFIX}root_"
CB_SELECT_QUALITY_PREFIX = f"{RADARR_CB_PREFIX}quality_"
CB_SELECT_AVAILABILITY_PREFIX = f"{RADARR_CB_PREFIX}avail_"
CB_SELECT_COLLECTION_MONITOR_PREFIX = f"{RADARR_CB_PREFIX}collmon_"
CB_SELECT_SEARCH_ON_ADD_PREFIX = f"{RADARR_CB_PREFIX}searchadd_"
CB_SELECT_TAG_PREFIX = f"{RADARR_CB_PREFIX}tag_"

CB_START_CUSTOMIZE_ROOT = f"{RADARR_CB_PREFIX}start_root"
CB_SKIP_TAGS = f"{RADARR_CB_PREFIX}skiptags"
CB_CONFIRM_ADD = f"{RADARR_CB_PREFIX}confirm"
CB_ADD_DEFAULT = f"{RADARR_CB_PREFIX}default"

CB_SUBMIT_REQUEST_RADARR = f"{RADARR_CB_PREFIX}submit_request"
CB_NO_OP_RADARR = f"{RADARR_CB_PREFIX}no_op"

COLLECTION_MONITOR_OPTIONS = [
    {"value": "movieOnly", "label": "Movie Only"},
    {"value": "movieAndCollection", "label": "Movie and Collection"}
]

SEARCH_ON_ADD_OPTIONS = [
    {"value": "true", "label": "Yes, search on add"},
    {"value": "false", "label": "No, do not search yet"}
]
MAX_OVERVIEW_LENGTH_RADARR = 250


async def radarr_movie_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    flow_data_key = 'radarr_add_flow'

    flow_data_from_context_copy = context.user_data.get(
        flow_data_key, {}).copy()

    data_to_process = None

    if 'initiator_action_data' in flow_data_from_context_copy:
        data_to_process = flow_data_from_context_copy.pop(
            'initiator_action_data')

        context.user_data[flow_data_key] = flow_data_from_context_copy
        logger.debug(
            f"Radarr selection: Using initiator_action_data: {data_to_process}")
    else:
        data_to_process = query.data
        logger.debug(f"Radarr selection: Using query.data: {data_to_process}")

    chat_id = update.effective_chat.id
    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.first_name or str(
        user_id)
    user_role = app_config_holder.get_user_role(str(chat_id))

    try:
        is_admin_add_flow = data_to_process.startswith(
            CallbackData.RADARR_SELECT_PREFIX.value)
        is_user_request_flow = data_to_process.startswith(
            CallbackData.RADARR_REQUEST_PREFIX.value)

        tmdb_id_str = ""
        if is_admin_add_flow:
            tmdb_id_str = data_to_process.replace(
                CallbackData.RADARR_SELECT_PREFIX.value, "")
        elif is_user_request_flow:
            tmdb_id_str = data_to_process.replace(
                CallbackData.RADARR_REQUEST_PREFIX.value, "")
        else:
            logger.error(
                f"Unknown prefix in radarr_movie_selection_callback with data: {data_to_process}")
            return

        if not tmdb_id_str.isdigit():
            raise ValueError("Invalid TMDB ID format in callback data.")
        tmdb_id = int(tmdb_id_str)

        if not app_config_holder.is_radarr_enabled():
            logger.info(
                f"Radarr movie selection by {chat_id}, but Radarr feature is disabled.")
            await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Radarr API features are disabled.", parse_mode=None)

            await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)
            return

        movie_api_details = None
        raw_overview = "Overview not available."
        has_collection_info = False
        try:
            lookup_response = radarr_api_get(
                'get', f'/movie/lookup/tmdb?tmdbId={tmdb_id}')
            if isinstance(lookup_response, list) and lookup_response:
                movie_api_details = lookup_response[0]
            elif isinstance(lookup_response, dict):
                movie_api_details = lookup_response

            if not movie_api_details or not movie_api_details.get("tmdbId"):
                logger.error(
                    f"Could not fetch valid movie details for TMDB ID {tmdb_id}. Response: {lookup_response}")
                await send_or_edit_universal_status_message(context.bot, chat_id, f"⚠️ Error: Could not fetch details for selected movie \\(TMDB ID: {tmdb_id}\\)\\.", parse_mode="MarkdownV2")
                await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)
                return

            if movie_api_details.get('overview'):
                raw_overview = movie_api_details.get('overview')
            collection_obj = movie_api_details.get('collection')
            if collection_obj and isinstance(collection_obj, dict) and \
               (collection_obj.get('title') or collection_obj.get('tmdbId')):
                has_collection_info = True
        except Exception as e_lookup:
            logger.warning(
                f"Could not pre-fetch full movie details for Radarr: {e_lookup}", exc_info=True)
            await send_or_edit_universal_status_message(context.bot, chat_id, f"⚠️ Error: Could not fetch details for selected movie \\(TMDB ID: {tmdb_id}\\)\\. Check bot logs\\.", parse_mode="MarkdownV2")
            await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)
            return

        active_flow_data = context.user_data.get(flow_data_key, {})
        active_flow_data.update({
            'movie_tmdb_id': movie_api_details['tmdbId'],
            'movie_title': movie_api_details.get('title', 'Unknown Title'),
            'movie_year': movie_api_details.get('year'),
            'movie_has_collection': has_collection_info,
            'radarr_movie_object_from_lookup': movie_api_details,
            'current_step': 'initial_choice_radarr',
            'chat_id': chat_id,
            'user_id': user_id,
            'username': username,
            'main_menu_message_id': query.message.message_id
        })

        if 'approved_request_id' in flow_data_from_context_copy:
            active_flow_data['approved_request_id'] = flow_data_from_context_copy['approved_request_id']
            active_flow_data['approved_request_original_user_id'] = flow_data_from_context_copy['approved_request_original_user_id']
            active_flow_data['approved_request_original_username'] = flow_data_from_context_copy['approved_request_original_username']

        context.user_data[flow_data_key] = active_flow_data
        is_from_admin_approval = 'approved_request_id' in active_flow_data

        keyboard = []
        if is_admin_add_flow:
            if user_role != app_config_holder.ROLE_ADMIN:
                logger.error(
                    f"Radarr: Non-admin user ({chat_id}, Role: {user_role}) in RADARR_SELECT_PREFIX flow. This should not happen if search result prefixes are correct for roles.")
                keyboard = [[InlineKeyboardButton(
                    "Cancel Operation", callback_data=CallbackData.RADARR_CANCEL.value)]]
            else:
                keyboard = [
                    [InlineKeyboardButton(
                        "Add with Defaults", callback_data=CB_ADD_DEFAULT)],
                    [InlineKeyboardButton(
                        "Customize Settings", callback_data=CB_START_CUSTOMIZE_ROOT)],
                    [InlineKeyboardButton(
                        "Cancel Add", callback_data=CallbackData.RADARR_CANCEL.value)]
                ]
        elif is_user_request_flow:
            keyboard = [
                [InlineKeyboardButton("✅ Submit Request",
                                      callback_data=CB_SUBMIT_REQUEST_RADARR)],
                [InlineKeyboardButton(
                    "Cancel Request", callback_data=CallbackData.RADARR_CANCEL.value)]
            ]
        else:
            logger.warning(
                f"radarr_movie_selection_callback: Role/flow mismatch. Role: {user_role}, is_admin_add_flow: {is_admin_add_flow}, is_user_request_flow: {is_user_request_flow}, is_from_admin_approval: {is_from_admin_approval}")
            await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Action not available for your role or current flow.", parse_mode=None)
            await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)
            return

        reply_markup = InlineKeyboardMarkup(keyboard)
        formatted_title_year = format_media_title_for_md2(
            active_flow_data['movie_title'], active_flow_data['movie_year']
        )
        formatted_overview = format_overview_for_md2(
            raw_overview, MAX_OVERVIEW_LENGTH_RADARR)

        msg_text_parts = [f"🎬 {formatted_title_year}\n\n",
                          f"{formatted_overview}\n\n"]
        if active_flow_data['movie_has_collection']:
            msg_text_parts.append(escape_md_v2(
                "ℹ️ _This movie is part of a collection._\n"))

        if is_admin_add_flow and user_role == app_config_holder.ROLE_ADMIN:
            prompt_action_text = "add to Radarr"
            if is_from_admin_approval:
                original_user_disp = escape_md_v2(
                    str(active_flow_data.get('approved_request_original_username', 'user')))
                prompt_action_text = f"add to Radarr (fulfilling request from {original_user_disp})"
            msg_text_parts.append(escape_md_v2(
                f"Choose how to {prompt_action_text}:"))
        elif is_user_request_flow:
            msg_text_parts.append(escape_md_v2(
                "Confirm your request for this movie:"))

        final_msg_text = "".join(msg_text_parts)

        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=query.message.message_id,
            text=final_msg_text,
            reply_markup=reply_markup,
            parse_mode="MarkdownV2"
        )
        context.bot_data[f"menu_message_content_{chat_id}_{query.message.message_id}"] = (
            final_msg_text, reply_markup.to_json())

    except (IndexError, ValueError, KeyError) as e:
        logger.error(
            f"Error in Radarr movie selection processing: {e}", exc_info=True)
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Error processing Radarr selection. Please try again.", parse_mode=None)
        await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)


async def display_radarr_customization_step(context: ContextTypes.DEFAULT_TYPE, flow_data: dict):
    chat_id = flow_data['chat_id']
    message_id = flow_data.get('main_menu_message_id')
    step = flow_data['current_step']

    title_year_display = format_media_title_for_md2(
        flow_data['movie_title'], flow_data.get('movie_year'))
    text_parts = [f"🎬 Customize Add: {title_year_display}\n\n"]
    keyboard_buttons = []
    step_counter = 0

    if step == 'select_root_folder':
        step_counter = 1
        text_parts.append(escape_md_v2(
            f"**Step {step_counter}: Select Root Folder**"))
        root_folders = get_root_folders()
        if not root_folders:
            err_text = "Error: Could not fetch root folders from Radarr."
            logger.error(err_text)
            if message_id:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=escape_md_v2(err_text), reply_markup=None, parse_mode="MarkdownV2")
            return
        for rf in root_folders:
            keyboard_buttons.append([InlineKeyboardButton(os.path.basename(
                rf['path'].rstrip('/\\')), callback_data=f"{CB_SELECT_ROOT_PREFIX}{rf['id']}")])
    elif step == 'select_quality_profile':
        step_counter = 2
        text_parts.append(escape_md_v2(
            f"**Step {step_counter}: Select Quality Profile**"))
        quality_profiles = get_quality_profiles()
        if not quality_profiles:
            err_text = "Error: Could not fetch quality profiles from Radarr."
            if message_id:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=escape_md_v2(err_text), reply_markup=None, parse_mode="MarkdownV2")
            return
        for qp in quality_profiles:
            keyboard_buttons.append([InlineKeyboardButton(
                qp['name'], callback_data=f"{CB_SELECT_QUALITY_PREFIX}{qp['id']}")])
    elif step == 'select_minimum_availability':
        step_counter = 3
        text_parts.append(escape_md_v2(
            f"**Step {step_counter}: Select Minimum Availability**"))
        avail_options = get_minimum_availability_options()
        for opt in avail_options:
            keyboard_buttons.append([InlineKeyboardButton(
                opt['label'], callback_data=f"{CB_SELECT_AVAILABILITY_PREFIX}{opt['value']}")])
    elif step == 'select_collection_monitoring' and flow_data.get('movie_has_collection'):
        step_counter = 4
        text_parts.append(escape_md_v2(
            f"**Step {step_counter}: Select Collection Monitoring**"))
        for opt in COLLECTION_MONITOR_OPTIONS:
            keyboard_buttons.append([InlineKeyboardButton(
                opt['label'], callback_data=f"{CB_SELECT_COLLECTION_MONITOR_PREFIX}{opt['value']}")])
    elif step == 'select_search_on_add':
        step_counter = 4 if not flow_data.get('movie_has_collection') else 5
        text_parts.append(escape_md_v2(
            f"**Step {step_counter}: Search for movie after adding?**"))
        for opt in SEARCH_ON_ADD_OPTIONS:
            keyboard_buttons.append([InlineKeyboardButton(
                opt['label'], callback_data=f"{CB_SELECT_SEARCH_ON_ADD_PREFIX}{opt['value']}")])
    elif step == 'select_tags':
        step_counter = 5 if not flow_data.get('movie_has_collection') else 6
        text_parts.append(escape_md_v2(
            f"**Step {step_counter}: Select Tags (Optional)**\n_Choose multiple then 'Done with Tags'_"))
        all_tags = get_tags()
        current_tags_ids = flow_data.get('tags', [])
        if all_tags:
            for tag_idx, tag in enumerate(all_tags):
                if tag_idx >= 15 and len(all_tags) > 18:
                    keyboard_buttons.append([InlineKeyboardButton(
                        "...(more tags not shown)", callback_data=CB_NO_OP_RADARR)])
                    break
                prefix = "✅ " if tag['id'] in current_tags_ids else "☑️ "
                keyboard_buttons.append([InlineKeyboardButton(
                    prefix + tag['label'], callback_data=f"{CB_SELECT_TAG_PREFIX}{tag['id']}")])
        keyboard_buttons.append([InlineKeyboardButton(
            "Done with Tags / Skip Tags", callback_data=CB_SKIP_TAGS)])
    elif step == 'confirm_add':
        step_counter = 6 if not flow_data.get('movie_has_collection') else 7
        text_parts.append(escape_md_v2(
            f"**Step {step_counter}: Confirm Add**") + "\n\n")
        rf_id = flow_data.get('root_folder_id')
        qp_id = flow_data.get('quality_profile_id')
        avail = flow_data.get('minimum_availability', 'released')
        coll_mon = flow_data.get('collection_monitoring', 'movieOnly')
        search_add = flow_data.get('search_on_add', True)
        tags_ids = flow_data.get('tags', [])

        rf_path_display = "Default (Not Set)"
        if rf_id:
            all_rf_confirm = get_root_folders()
            sel_rf_confirm = next(
                (r for r in all_rf_confirm if r['id'] == rf_id), None)
            if sel_rf_confirm:
                rf_path_display = os.path.basename(
                    sel_rf_confirm['path'].rstrip('/\\'))

        qp_name_display = "Default (Not Set)"
        if qp_id:
            all_qp_confirm = get_quality_profiles()
            sel_qp_confirm = next(
                (q for q in all_qp_confirm if q['id'] == qp_id), None)
            if sel_qp_confirm:
                qp_name_display = sel_qp_confirm['name']

        avail_display = avail
        avail_option_found = next(
            (opt['label'] for opt in get_minimum_availability_options() if opt['value'] == avail), None)
        avail_display = avail_option_found if avail_option_found else avail.capitalize()

        coll_mon_label = next(
            (c['label'] for c in COLLECTION_MONITOR_OPTIONS if c['value'] == coll_mon), coll_mon.capitalize())
        search_add_label = "Yes" if search_add else "No"

        tags_str_display = "None"
        if tags_ids:
            all_tags_api_confirm = get_tags()
            sel_tag_labels = [t['label']
                              for t in all_tags_api_confirm if t['id'] in tags_ids]
            if sel_tag_labels:
                tags_str_display = ", ".join(sel_tag_labels)

        text_parts.append(format_selected_option_for_md2(
            "Root Folder", rf_path_display))
        text_parts.append(format_selected_option_for_md2(
            "Quality Profile", qp_name_display))
        text_parts.append(format_selected_option_for_md2(
            "Min\\. Availability", avail_display))
        if flow_data.get('movie_has_collection'):
            text_parts.append(format_selected_option_for_md2(
                "Collection Monitor", coll_mon_label))
        text_parts.append(format_selected_option_for_md2(
            "Search on Add", search_add_label))
        text_parts.append(format_selected_option_for_md2(
            "Tags", tags_str_display))
        keyboard_buttons.append([InlineKeyboardButton(
            "✅ Confirm and Add Movie", callback_data=CB_CONFIRM_ADD)])

    keyboard_buttons.append([InlineKeyboardButton(
        "Cancel Add", callback_data=CallbackData.RADARR_CANCEL.value)])
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    final_text_display = "".join(text_parts)

    try:
        if message_id:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=final_text_display, reply_markup=reply_markup, parse_mode="MarkdownV2")
            context.bot_data[f"menu_message_content_{chat_id}_{message_id}"] = (
                final_text_display, reply_markup.to_json())
        else:
            logger.error(
                "Radarr customization step called without main_menu_message_id. This indicates a flow error.")
            await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Flow error: Cannot display customization options.", parse_mode=None)
            await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)
            return
    except BadRequest as e:
        if "message is not modified" not in str(e).lower():
            logger.error(
                f"Error displaying Radarr customization step {step}: {e}", exc_info=True)
            await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ An error occurred displaying Radarr options. Please try again.", parse_mode=None)
            context.user_data.pop('radarr_add_flow', None)
            await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)
    except Exception as e:
        logger.error(
            f"Unexpected error in display_radarr_customization_step for {step}: {e}", exc_info=True)
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ An unexpected error occurred. Please try again.", parse_mode=None)
        context.user_data.pop('radarr_add_flow', None)
        await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)


async def radarr_customization_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    flow_data_key = 'radarr_add_flow'
    flow_data = context.user_data.get(flow_data_key)

    if not flow_data:
        if query.message:
            await query.edit_message_text(text="Radarr session expired or data lost. Please start over.")
        await show_or_edit_main_menu(str(update.effective_chat.id), context, force_send_new=True)
        return

    chat_id = flow_data['chat_id']
    user_id = flow_data.get('user_id')
    username = flow_data.get('username')

    current_interacting_user_role = app_config_holder.get_user_role(
        str(update.effective_chat.id))

    is_from_admin_approval = 'approved_request_id' in flow_data
    approved_request_id = flow_data.get('approved_request_id')

    next_step = None

    if data == CB_NO_OP_RADARR:
        return
    elif data == CallbackData.RADARR_CANCEL.value:
        context.user_data.pop(flow_data_key, None)
        if is_from_admin_approval:
            logger.info(
                f"Admin ({update.effective_chat.id}) cancelled the add flow for previously approved request ID: {approved_request_id}. Request remains pending.")

            from src.handlers.admin_requests.menu_handler_admin_requests import display_admin_pending_requests_menu
            await display_admin_pending_requests_menu(update, context)
        else:
            await send_or_edit_universal_status_message(context.bot, chat_id, "❌ Radarr process cancelled.", parse_mode=None)
            await show_or_edit_main_menu(str(chat_id), context)
        return
    elif data == CB_SUBMIT_REQUEST_RADARR:
        await send_or_edit_universal_status_message(context.bot, chat_id, f"⏳ Submitting your request for '{escape_md_v2(flow_data['movie_title'])}'\\.\\.\\.", parse_mode="MarkdownV2")
        request_id = str(uuid.uuid4())
        new_request = {
            "request_id": request_id, "user_id": user_id, "username": username,
            "media_type": "movie", "media_tmdb_id": flow_data['movie_tmdb_id'],
            "media_title": flow_data['movie_title'], "media_year": flow_data.get('movie_year'),
            "request_timestamp": time.time(), "status": "pending",
            "status_timestamp": time.time(), "admin_notes": None
        }
        requests_list = load_requests_data()
        requests_list.append(new_request)
        result_msg_raw = ""
        if save_requests_data(requests_list):
            result_msg_raw = f"✅ Your request for '{flow_data['movie_title']}' has been submitted for admin approval."
            logger.info(
                f"Movie request submitted by user {user_id} ({username}) for '{flow_data['movie_title']}' (TMDB ID: {flow_data['movie_tmdb_id']}). Request ID: {request_id}")

            await refresh_main_menus_for_all_admins(context)
        else:
            result_msg_raw = f"⚠️ Failed to save your request for '{flow_data['movie_title']}'. Please try again or contact admin."
            logger.error(
                f"Failed to save movie request for user {user_id} for '{flow_data['movie_title']}'")
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(result_msg_raw), parse_mode="MarkdownV2")
        context.user_data.pop(flow_data_key, None)
        await show_or_edit_main_menu(str(chat_id), context)
        return

    if current_interacting_user_role != app_config_holder.ROLE_ADMIN:
        logger.warning(
            f"Non-admin {chat_id} (Role: {current_interacting_user_role}) attempting admin-only Radarr action '{data}'. Denying.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied to this Radarr action.", parse_mode=None)
        context.user_data.pop(flow_data_key, None)
        await show_or_edit_main_menu(str(chat_id), context)
        return

    if data == CB_ADD_DEFAULT or data == CB_CONFIRM_ADD:
        await send_or_edit_universal_status_message(context.bot, chat_id, f"⏳ Processing Radarr add for '{escape_md_v2(flow_data['movie_title'])}'\\.\\.\\.", parse_mode="MarkdownV2")
        add_params = {
            'movie_tmdb_id': flow_data['movie_tmdb_id'],
            'radarr_movie_object': flow_data['radarr_movie_object_from_lookup'],
            'minimum_availability': "released", 'tags': [],
            'add_options_monitor': "movieOnly", 'search_on_add': True
        }
        if data == CB_ADD_DEFAULT:
            add_params['quality_profile_id'] = get_default_quality_profile_id()
            add_params['root_folder_path_or_id'] = get_default_root_folder_id()
            if flow_data.get('movie_has_collection'):
                add_params['add_options_monitor'] = "movieAndCollection"
        else:
            add_params['quality_profile_id'] = flow_data.get(
                'quality_profile_id', get_default_quality_profile_id())
            add_params['root_folder_path_or_id'] = flow_data.get(
                'root_folder_id', get_default_root_folder_id())
            add_params['minimum_availability'] = flow_data.get(
                'minimum_availability', "released")
            if flow_data.get('movie_has_collection'):
                add_params['add_options_monitor'] = flow_data.get(
                    'collection_monitoring', "movieAndCollection")
            add_params['search_on_add'] = flow_data.get('search_on_add', True)
            add_params['tags'] = flow_data.get('tags', [])

        result_msg_raw = ""
        if not add_params['quality_profile_id'] or not add_params['root_folder_path_or_id']:
            error_detail_raw = "Default/selected quality profile or root folder not found. "
            result_msg_raw = f"⚠️ Error: {error_detail_raw}Please check Radarr settings or bot logs."
            logger.error(
                f"Missing quality profile or root folder for Radarr add. QP: {add_params['quality_profile_id']}, RF: {add_params['root_folder_path_or_id']}")
            if is_from_admin_approval and approved_request_id:
                all_reqs = load_requests_data()
                for req in all_reqs:
                    if req.get("request_id") == approved_request_id:
                        req["status"] = "add_failed"
                        req["admin_notes"] = f"Admin approved, but auto-add failed: {error_detail_raw}"
                        req["status_timestamp"] = time.time()
                        save_requests_data(all_reqs)
                        break
        else:
            result_msg_raw = radarr_add_movie_func(**add_params)
            if is_from_admin_approval and approved_request_id:
                success_keywords = ["successfully", "already in Radarr"]
                is_add_successful = any(
                    keyword.lower() in result_msg_raw.lower() for keyword in success_keywords)
                all_reqs = load_requests_data()
                updated_req = False
                for req_idx, req_item in enumerate(all_reqs):
                    if req_item.get("request_id") == approved_request_id:
                        all_reqs[req_idx]["status"] = "approved" if is_add_successful else "add_failed"
                        all_reqs[req_idx][
                            "admin_notes"] = f"Admin {username or chat_id} fulfilled. Radarr response: {result_msg_raw}"
                        all_reqs[req_idx]["status_timestamp"] = time.time()
                        updated_req = True
                        break
                if updated_req:
                    save_requests_data(all_reqs)

        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(result_msg_raw), parse_mode="MarkdownV2")
        context.user_data.pop(flow_data_key, None)
        if is_from_admin_approval:
            from src.handlers.admin_requests.menu_handler_admin_requests import display_admin_pending_requests_menu
            await display_admin_pending_requests_menu(update, context)

            await refresh_main_menus_for_all_admins(context)
        else:
            await show_or_edit_main_menu(str(chat_id), context)
        return

    elif data == CB_START_CUSTOMIZE_ROOT:
        next_step = 'select_root_folder'
    elif data.startswith(CB_SELECT_ROOT_PREFIX):
        flow_data['root_folder_id'] = int(
            data.replace(CB_SELECT_ROOT_PREFIX, ""))
        next_step = 'select_quality_profile'
    elif data.startswith(CB_SELECT_QUALITY_PREFIX):
        flow_data['quality_profile_id'] = int(
            data.replace(CB_SELECT_QUALITY_PREFIX, ""))
        next_step = 'select_minimum_availability'
    elif data.startswith(CB_SELECT_AVAILABILITY_PREFIX):
        flow_data['minimum_availability'] = data.replace(
            CB_SELECT_AVAILABILITY_PREFIX, "")
        next_step = 'select_collection_monitoring' if flow_data.get(
            'movie_has_collection') else 'select_search_on_add'
        flow_data.setdefault('tags', [])
    elif data.startswith(CB_SELECT_COLLECTION_MONITOR_PREFIX):
        flow_data['collection_monitoring'] = data.replace(
            CB_SELECT_COLLECTION_MONITOR_PREFIX, "")
        next_step = 'select_search_on_add'
        flow_data.setdefault('tags', [])
    elif data.startswith(CB_SELECT_SEARCH_ON_ADD_PREFIX):
        flow_data['search_on_add'] = (data.replace(
            CB_SELECT_SEARCH_ON_ADD_PREFIX, "") == "true")
        next_step = 'select_tags'
        flow_data.setdefault('tags', [])
    elif data.startswith(CB_SELECT_TAG_PREFIX):
        tag_id_str = data.replace(CB_SELECT_TAG_PREFIX, "")
        if tag_id_str.isdigit():
            tag_id = int(tag_id_str)
            current_tags = flow_data.get('tags', [])
            if tag_id in current_tags:
                current_tags.remove(tag_id)
            else:
                current_tags.append(tag_id)
            flow_data['tags'] = current_tags
        next_step = 'select_tags'
    elif data == CB_SKIP_TAGS:
        next_step = 'confirm_add'

    if next_step:
        flow_data['current_step'] = next_step
        context.user_data[flow_data_key] = flow_data
        await display_radarr_customization_step(context, flow_data)
    elif query.message and not data.startswith(CB_SELECT_TAG_PREFIX) and data != CB_NO_OP_RADARR:
        logger.error(
            f"Radarr customization callback reached unhandled state with data: {data}")
        context.user_data.pop(flow_data_key, None)
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Unexpected error in Radarr flow.", parse_mode=None)
        await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)
