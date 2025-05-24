import logging
import os
import uuid
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from src.bot.bot_text_utils import (
    format_media_title_for_md2, format_overview_for_md2,
    format_selected_option_for_md2, escape_md_v2,
    escape_for_inline_code, escape_md_v1
)
from src.services.sonarr.bot_sonarr_add import (
    add_show as sonarr_add_show_func,
    get_root_folders as get_sonarr_root_folders,
    get_quality_profiles as get_sonarr_quality_profiles,
    get_language_profiles as get_sonarr_language_profiles,
    get_tags as get_sonarr_tags,
    get_series_type_options, get_episode_monitor_options,
    get_default_root_folder_path, get_default_quality_profile_id,
    get_default_language_profile_id
)
from src.services.sonarr.bot_sonarr_core import _sonarr_request as sonarr_api_get
from src.bot.bot_initialization import (
    show_or_edit_main_menu,
    send_or_edit_universal_status_message
)
from src.bot.bot_callback_data import CallbackData
import src.app.app_config_holder as app_config_holder
from src.app.app_file_utils import load_requests_data, save_requests_data

logger = logging.getLogger(__name__)

SONARR_CB_PREFIX = "sonarr_cfg_"
CB_SELECT_ROOT_S = f"{SONARR_CB_PREFIX}root_"
CB_SELECT_QUALITY_S = f"{SONARR_CB_PREFIX}quality_"
CB_SELECT_LANGUAGE_S = f"{SONARR_CB_PREFIX}lang_"
CB_SELECT_SERIES_TYPE_S = f"{SONARR_CB_PREFIX}type_"
CB_SELECT_SEASON_FOLDER_S = f"{SONARR_CB_PREFIX}seasonf_"
CB_SELECT_MONITOR_EPS_S = f"{SONARR_CB_PREFIX}moneps_"
CB_SELECT_SEARCH_MISSING_S = f"{SONARR_CB_PREFIX}searchmiss_"
CB_SELECT_TAG_S = f"{SONARR_CB_PREFIX}tag_"

CB_START_CUSTOMIZE_SONARR = f"{SONARR_CB_PREFIX}start_cfg"
CB_SKIP_TAGS_S = f"{SONARR_CB_PREFIX}skiptags"
CB_CONFIRM_ADD_S = f"{SONARR_CB_PREFIX}confirm"
CB_ADD_DEFAULT_S = f"{SONARR_CB_PREFIX}default"

CB_SUBMIT_REQUEST_SONARR = f"{SONARR_CB_PREFIX}submit_request"

CB_NO_OP_SONARR = f"{SONARR_CB_PREFIX}no_op"
MAX_OVERVIEW_LENGTH_SONARR = 250


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


async def display_sonarr_customization_step(context: ContextTypes.DEFAULT_TYPE, flow_data: dict):
    chat_id = flow_data['chat_id']
    message_id = flow_data.get('main_menu_message_id')
    step = flow_data['current_step']

    title_year_display = format_media_title_for_md2(
        flow_data['show_title'], flow_data.get('show_year'))
    text = f"🎞️ Customize Add: {title_year_display}\n\n"
    keyboard_buttons = []
    step_counter = 0

    if step == 'select_root_folder_s':
        step_counter = 1
        text += escape_md_v2(f"**Step {step_counter}: Select Root Folder**")
        root_folders = get_sonarr_root_folders()
        if not root_folders:
            err_text = "Error: Could not fetch root folders from Sonarr."
            if message_id:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=escape_md_v2(err_text), reply_markup=None, parse_mode="MarkdownV2")
            return
        for rf in root_folders:
            keyboard_buttons.append([InlineKeyboardButton(os.path.basename(
                rf['path'].rstrip('/\\')), callback_data=f"{CB_SELECT_ROOT_S}{rf['path']}")])
    elif step == 'select_quality_profile_s':
        step_counter = 2
        text += escape_md_v2(f"**Step {step_counter}: Select Quality Profile**")
        quality_profiles = get_sonarr_quality_profiles()
        if not quality_profiles:
            err_text = "Error: Could not fetch quality profiles from Sonarr."
            if message_id:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=escape_md_v2(err_text), reply_markup=None, parse_mode="MarkdownV2")
            return
        for qp in quality_profiles:
            keyboard_buttons.append([InlineKeyboardButton(
                qp['name'], callback_data=f"{CB_SELECT_QUALITY_S}{qp['id']}")])
    elif step == 'select_language_profile_s':
        step_counter = 3
        text += escape_md_v2(f"**Step {step_counter}: Select Language Profile**")
        lang_profiles = get_sonarr_language_profiles()
        if not lang_profiles:
            err_text = "Error: Could not fetch language profiles from Sonarr."
            if message_id:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=escape_md_v2(err_text), reply_markup=None, parse_mode="MarkdownV2")
            return
        for lp in lang_profiles:
            keyboard_buttons.append([InlineKeyboardButton(
                lp['name'], callback_data=f"{CB_SELECT_LANGUAGE_S}{lp['id']}")])
    elif step == 'select_series_type_s':
        step_counter = 4
        text += escape_md_v2(f"**Step {step_counter}: Select Series Type**")
        for opt in get_series_type_options():
            keyboard_buttons.append([InlineKeyboardButton(
                opt['label'], callback_data=f"{CB_SELECT_SERIES_TYPE_S}{opt['value']}")])
    elif step == 'select_season_folder_s':
        step_counter = 5
        text += escape_md_v2(f"**Step {step_counter}: Use Season Folders?**")
        keyboard_buttons.append([InlineKeyboardButton(
            "Yes", callback_data=f"{CB_SELECT_SEASON_FOLDER_S}true")])
        keyboard_buttons.append([InlineKeyboardButton(
            "No", callback_data=f"{CB_SELECT_SEASON_FOLDER_S}false")])
    elif step == 'select_monitor_episodes_s':
        step_counter = 6
        text += escape_md_v2(f"**Step {step_counter}: Monitor Which Episodes?**")
        for opt in get_episode_monitor_options():
            keyboard_buttons.append([InlineKeyboardButton(
                opt['label'], callback_data=f"{CB_SELECT_MONITOR_EPS_S}{opt['value']}")])
    elif step == 'select_search_missing_s':
        step_counter = 7
        text += escape_md_v2(
            f"**Step {step_counter}: Search for missing episodes on add?**")
        keyboard_buttons.append([InlineKeyboardButton(
            "Yes, search now", callback_data=f"{CB_SELECT_SEARCH_MISSING_S}true")])
        keyboard_buttons.append([InlineKeyboardButton(
            "No, don't search", callback_data=f"{CB_SELECT_SEARCH_MISSING_S}false")])
    elif step == 'select_tags_s':
        step_counter = 8
        text += escape_md_v2(
            f"**Step {step_counter}: Select Tags (Optional)**\n_Choose multiple then 'Done with Tags'_")
        all_tags = get_sonarr_tags()
        current_tags_ids = flow_data.get('tags_s', [])
        if all_tags:
            for tag_idx, tag in enumerate(all_tags):
                if tag_idx >= 15 and len(all_tags) > 18:
                    keyboard_buttons.append([InlineKeyboardButton(
                        "...(more tags not shown)", callback_data=CB_NO_OP_SONARR)])
                    break
                prefix = "✅ " if tag['id'] in current_tags_ids else "☑️ "
                keyboard_buttons.append([InlineKeyboardButton(
                    prefix + tag['label'], callback_data=f"{CB_SELECT_TAG_S}{tag['id']}")])
        keyboard_buttons.append([InlineKeyboardButton(
            "Done with Tags / Skip Tags", callback_data=CB_SKIP_TAGS_S)])
    elif step == 'confirm_add_s':
        step_counter = 9
        text += escape_md_v2(f"**Step {step_counter}: Confirm Add**") + "\n\n"
        rf_path = flow_data.get('root_folder_path_s',
                                get_default_root_folder_path() or "Not Set")
        qp_id = flow_data.get('quality_profile_id_s',
                              get_default_quality_profile_id())
        lp_id = flow_data.get('language_profile_id_s',
                              get_default_language_profile_id())
        stype = flow_data.get('series_type_s', 'standard')
        sfolder = flow_data.get('season_folder_s', True)
        moneps = flow_data.get('monitor_episodes_s', 'all')
        searchmiss = flow_data.get('search_missing_s', True)
        tags_ids = flow_data.get('tags_s', [])

        rf_display = os.path.basename(rf_path.rstrip(
            '/\\')) if rf_path != "Not Set" else "Default (Not Set)"

        qp_name_display = "Default (Not Set)"
        if qp_id:
            sel_qp_confirm = next(
                (q['name'] for q in get_sonarr_quality_profiles() if q['id'] == qp_id), None)
            qp_name_display = sel_qp_confirm if sel_qp_confirm else qp_name_display

        lp_name_display = "Default (Not Set)"
        if lp_id:
            sel_lp_confirm = next(
                (l['name'] for l in get_sonarr_language_profiles() if l['id'] == lp_id), None)
            lp_name_display = sel_lp_confirm if sel_lp_confirm else lp_name_display

        stype_display = next((s['label'] for s in get_series_type_options(
        ) if s['value'] == stype), stype.capitalize())
        sfolder_display = "Yes" if sfolder else "No"
        moneps_display = next((m['label'] for m in get_episode_monitor_options(
        ) if m['value'] == moneps), moneps.capitalize())
        searchmiss_display = "Yes" if searchmiss else "No"

        tags_str_display = "None"
        if tags_ids:
            sel_tag_labels = [t['label']
                              for t in get_sonarr_tags() if t['id'] in tags_ids]
            tags_str_display = ", ".join(
                sel_tag_labels) if sel_tag_labels else tags_str_display

        text += format_selected_option_for_md2("Root Folder", rf_display)
        text += format_selected_option_for_md2(
            "Quality Profile", qp_name_display)
        text += format_selected_option_for_md2(
            "Language Profile", lp_name_display)
        text += format_selected_option_for_md2("Series Type", stype_display)
        text += format_selected_option_for_md2(
            "Season Folders", sfolder_display)
        text += format_selected_option_for_md2(
            "Monitor Episodes", moneps_display)
        text += format_selected_option_for_md2(
            "Search on Add", searchmiss_display)
        text += format_selected_option_for_md2("Tags", tags_str_display)
        keyboard_buttons.append([InlineKeyboardButton(
            "✅ Confirm and Add Show", callback_data=CB_CONFIRM_ADD_S)])

    keyboard_buttons.append([InlineKeyboardButton(
        "Cancel Add", callback_data=CallbackData.SONARR_CANCEL.value)])
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)

    try:
        if message_id:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup, parse_mode="MarkdownV2")
            context.bot_data[f"menu_message_content_{chat_id}_{message_id}"] = (
                text, reply_markup.to_json())
        else:
            logger.error(
                "Sonarr customization step called without main_menu_message_id. This indicates a flow error.")
            await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Flow error: Cannot display customization options.", parse_mode=None)
            await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)
            return
    except BadRequest as e:
        if "message is not modified" not in str(e).lower():
            logger.error(
                f"Error displaying Sonarr customization step {step}: {e}", exc_info=True)
            await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ An error occurred displaying Sonarr options. Please try again.", parse_mode=None)
            context.user_data.pop('sonarr_add_flow', None)
            await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)
    except Exception as e:
        logger.error(
            f"Unexpected error in display_sonarr_customization_step for {step}: {e}", exc_info=True)
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ An unexpected error occurred. Please try again.", parse_mode=None)
        context.user_data.pop('sonarr_add_flow', None)
        await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)


async def sonarr_customization_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    flow_data_key = 'sonarr_add_flow'
    flow_data = context.user_data.get(flow_data_key)

    if not flow_data:
        if query.message:
            await query.edit_message_text(text="Sonarr session expired or data lost. Please start over.")
        await show_or_edit_main_menu(str(update.effective_chat.id), context, force_send_new=True)
        return

    chat_id = flow_data['chat_id']
    user_id = flow_data.get('user_id')
    username = flow_data.get('username')

    is_from_admin_approval = 'approved_request_id' in flow_data
    approved_request_id = flow_data.get('approved_request_id')
    original_requesting_user_id = flow_data.get(
        'approved_request_original_user_id')
    original_requesting_username = flow_data.get(
        'approved_request_original_username')

    next_step_s = None

    if data == CB_NO_OP_SONARR:
        return
    elif data == CallbackData.SONARR_CANCEL.value:
        context.user_data.pop(flow_data_key, None)
        if is_from_admin_approval and approved_request_id:
            all_reqs = load_requests_data()
            for req in all_reqs:
                if req.get("request_id") == approved_request_id and req.get("status") == "processing_approval":
                    req["status"] = "pending"
                    req["admin_notes"] = "Admin cancelled add process."
                    save_requests_data(all_reqs)
                    logger.info(
                        f"Admin cancelled add for approved Sonarr request {approved_request_id}. Reverted to pending.")
                    break
        await send_or_edit_universal_status_message(context.bot, chat_id, "❌ Sonarr process cancelled.", parse_mode=None)
        if is_from_admin_approval:
            from src.handlers.admin_requests.menu_handler_admin_requests import display_admin_pending_requests_menu
            dummy_message_obj = type('DummyMessage', (), {'chat_id': chat_id, 'message_id': flow_data.get(
                'main_menu_message_id'), 'chat': type('DummyChat', (), {'id': chat_id})()})()
            dummy_callback_query_obj = type('DummyQuery', (), {
                                            'data': CallbackData.CMD_ADMIN_REQUESTS_MENU.value, 'message': dummy_message_obj, 'from_user': query.from_user, 'answer': query.answer})()

            effective_chat_obj = query.message.chat if query.message else type(
                'DummyChat', (), {'id': chat_id})()
            dummy_update_obj = type('DummyUpdate', (), {
                                    'callback_query': dummy_callback_query_obj, 'effective_chat': effective_chat_obj, 'effective_user': query.from_user})()
            await display_admin_pending_requests_menu(dummy_update_obj, context)
        else:
            await show_or_edit_main_menu(str(chat_id), context)
        return
    elif data == CB_SUBMIT_REQUEST_SONARR:
        await send_or_edit_universal_status_message(context.bot, chat_id, f"⏳ Submitting your request for '{escape_md_v2(flow_data['show_title'])}'\\.\\.\\.", parse_mode="MarkdownV2")

        request_id = str(uuid.uuid4())
        new_request = {
            "request_id": request_id,
            "user_id": user_id,
            "username": username,
            "media_type": "tv",
            "media_tvdb_id": flow_data['show_tvdb_id'],
            "media_title": flow_data['show_title'],
            "media_year": flow_data.get('show_year'),
            "request_timestamp": time.time(),
            "status": "pending",
            "status_timestamp": time.time(),
            "admin_notes": None
        }

        requests_list = load_requests_data()
        requests_list.append(new_request)
        if save_requests_data(requests_list):
            result_msg_raw = f"✅ Your request for '{flow_data['show_title']}' has been submitted for admin approval."
            logger.info(
                f"TV show request submitted by user {user_id} ({username}) for '{flow_data['show_title']}' (TVDB ID: {flow_data['show_tvdb_id']}). Request ID: {request_id}")
        else:
            result_msg_raw = f"⚠️ Failed to save your request for '{flow_data['show_title']}'. Please try again or contact admin."
            logger.error(
                f"Failed to save TV show request for user {user_id} for '{flow_data['show_title']}'")

        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(result_msg_raw), parse_mode="MarkdownV2")
        context.user_data.pop(flow_data_key, None)
        await show_or_edit_main_menu(str(chat_id), context)
        return

    elif data == CB_ADD_DEFAULT_S or data == CB_CONFIRM_ADD_S:
        await send_or_edit_universal_status_message(context.bot, chat_id, f"⏳ Processing Sonarr add for '{escape_md_v2(flow_data['show_title'])}'\\.\\.\\.", parse_mode="MarkdownV2")
        add_params = {
            'tvdb_id': flow_data['show_tvdb_id'],
            'sonarr_show_object': flow_data['sonarr_show_object_from_lookup'],
            'series_type': "standard", 'season_folder': True,
            'monitor_episodes': "all", 'search_for_missing': True, 'tags': []
        }
        if data == CB_ADD_DEFAULT_S:
            add_params['quality_profile_id'] = get_default_quality_profile_id()
            add_params['root_folder_path'] = get_default_root_folder_path()
            add_params['language_profile_id'] = get_default_language_profile_id()
        else:
            add_params['quality_profile_id'] = flow_data.get(
                'quality_profile_id_s', get_default_quality_profile_id())
            add_params['root_folder_path'] = flow_data.get(
                'root_folder_path_s', get_default_root_folder_path())
            add_params['language_profile_id'] = flow_data.get(
                'language_profile_id_s', get_default_language_profile_id())
            add_params['series_type'] = flow_data.get(
                'series_type_s', "standard")
            add_params['season_folder'] = flow_data.get(
                'season_folder_s', True)
            add_params['monitor_episodes'] = flow_data.get(
                'monitor_episodes_s', "all")
            add_params['search_for_missing'] = flow_data.get(
                'search_missing_s', True)
            add_params['tags'] = flow_data.get('tags_s', [])

        result_msg_raw = ""
        if not add_params['quality_profile_id'] or not add_params['root_folder_path'] or not add_params['language_profile_id']:
            error_detail_raw = ""
            if not add_params['quality_profile_id']:
                error_detail_raw += "Quality profile not found. "
            if not add_params['root_folder_path']:
                error_detail_raw += "Root folder not found. "
            if not add_params['language_profile_id']:
                error_detail_raw += "Language profile not found. "
            result_msg_raw = f"⚠️ Error: {error_detail_raw}Check Sonarr/bot settings or logs."
            logger.error(
                f"Missing critical params for Sonarr add. QP: {add_params['quality_profile_id']}, RF: {add_params['root_folder_path']}, LP: {add_params['language_profile_id']}")
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
            result_msg_raw = sonarr_add_show_func(**add_params)
            if is_from_admin_approval and approved_request_id:
                success_keywords = ["successfully", "already in Sonarr"]
                is_add_successful = any(
                    keyword.lower() in result_msg_raw.lower() for keyword in success_keywords)

                all_reqs = load_requests_data()
                updated_req = False
                for req_idx, req_item in enumerate(all_reqs):
                    if req_item.get("request_id") == approved_request_id:
                        all_reqs[req_idx]["status"] = "approved" if is_add_successful else "add_failed"
                        all_reqs[req_idx][
                            "admin_notes"] = f"Admin approved. Sonarr response: {result_msg_raw}"
                        all_reqs[req_idx]["status_timestamp"] = time.time()
                        updated_req = True
                        break
                if updated_req:
                    save_requests_data(all_reqs)

        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(result_msg_raw), parse_mode="MarkdownV2")
        context.user_data.pop(flow_data_key, None)

        if is_from_admin_approval:
            from src.handlers.admin_requests.menu_handler_admin_requests import display_admin_pending_requests_menu
            dummy_message_obj = type('DummyMessage', (), {'chat_id': chat_id, 'message_id': flow_data.get(
                'main_menu_message_id'), 'chat': type('DummyChat', (), {'id': chat_id})()})()
            from_user_for_dummy = query.from_user if query and query.from_user else context.bot
            effective_chat_for_dummy = query.message.chat if query and query.message else type(
                'DummyChat', (), {'id': chat_id})()

            dummy_callback_query_obj = type('DummyQuery', (), {'data': CallbackData.CMD_ADMIN_REQUESTS_MENU.value,
                                            'message': dummy_message_obj, 'from_user': from_user_for_dummy, 'answer': query.answer if query else (lambda: None)})()
            dummy_update_obj = type('DummyUpdate', (), {'callback_query': dummy_callback_query_obj,
                                    'effective_chat': effective_chat_for_dummy, 'effective_user': from_user_for_dummy})()
            await display_admin_pending_requests_menu(dummy_update_obj, context)
        else:
            await show_or_edit_main_menu(str(chat_id), context)
        return

    elif data == CB_START_CUSTOMIZE_SONARR:
        next_step_s = 'select_root_folder_s'
    elif data.startswith(CB_SELECT_ROOT_S):
        flow_data['root_folder_path_s'] = data.replace(CB_SELECT_ROOT_S, "")
        next_step_s = 'select_quality_profile_s'
    elif data.startswith(CB_SELECT_QUALITY_S):
        flow_data['quality_profile_id_s'] = int(
            data.replace(CB_SELECT_QUALITY_S, ""))
        next_step_s = 'select_language_profile_s'
    elif data.startswith(CB_SELECT_LANGUAGE_S):
        flow_data['language_profile_id_s'] = int(
            data.replace(CB_SELECT_LANGUAGE_S, ""))
        next_step_s = 'select_series_type_s'
    elif data.startswith(CB_SELECT_SERIES_TYPE_S):
        flow_data['series_type_s'] = data.replace(CB_SELECT_SERIES_TYPE_S, "")
        next_step_s = 'select_season_folder_s'
    elif data.startswith(CB_SELECT_SEASON_FOLDER_S):
        flow_data['season_folder_s'] = (data.replace(
            CB_SELECT_SEASON_FOLDER_S, "") == "true")
        next_step_s = 'select_monitor_episodes_s'
    elif data.startswith(CB_SELECT_MONITOR_EPS_S):
        flow_data['monitor_episodes_s'] = data.replace(
            CB_SELECT_MONITOR_EPS_S, "")
        next_step_s = 'select_search_missing_s'
    elif data.startswith(CB_SELECT_SEARCH_MISSING_S):
        flow_data['search_missing_s'] = (data.replace(
            CB_SELECT_SEARCH_MISSING_S, "") == "true")
        next_step_s = 'select_tags_s'
        flow_data.setdefault('tags_s', [])
    elif data.startswith(CB_SELECT_TAG_S):
        tag_id_str = data.replace(CB_SELECT_TAG_S, "")
        if tag_id_str.isdigit():
            tag_id = int(tag_id_str)
            current_tags = flow_data.get('tags_s', [])
            if tag_id in current_tags:
                current_tags.remove(tag_id)
            else:
                current_tags.append(tag_id)
            flow_data['tags_s'] = current_tags
        next_step_s = 'select_tags_s'
    elif data == CB_SKIP_TAGS_S:
        next_step_s = 'confirm_add_s'

    if next_step_s:
        flow_data['current_step'] = next_step_s
        context.user_data[flow_data_key] = flow_data
        await display_sonarr_customization_step(context, flow_data)
    elif query.message and not data.startswith(CB_SELECT_TAG_S) and data != CB_NO_OP_SONARR:
        logger.error(
            f"Sonarr customization callback reached unhandled state with data: {data}")
        context.user_data.pop(flow_data_key, None)
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Unexpected error in Sonarr flow.", parse_mode=None)
        await show_or_edit_main_menu(str(chat_id), context, force_send_new=True)
