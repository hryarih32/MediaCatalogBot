
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.bot_text_utils import escape_md_v2, escape_for_inline_code
import src.app.app_config_holder as app_config_holder
from src.bot.bot_callback_data import CallbackData
from src.bot.bot_initialization import (
    send_or_edit_universal_status_message,
    show_or_edit_main_menu
)
from src.bot.bot_message_persistence import load_menu_message_id
from src.services.plex.bot_plex_media_items import get_plex_item_details
from src.services.plex.bot_plex_library import trigger_item_metadata_refresh
from src.handlers.plex.menu_handler_plex_controls import display_plex_controls_menu
from src.handlers.plex.menu_handler_plex_show_navigation import plex_search_list_seasons_callback

logger = logging.getLogger(__name__)

PLEX_ITEM_DETAILS_TEXT_RAW = "ℹ️ Plex Item Details:"
PLEX_EPISODE_DETAILS_TEXT_RAW = "🎞️ Plex Episode Details:"


async def plex_search_show_details_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_role = app_config_holder.get_user_role(str(chat_id))

    await query.answer()

    if user_role not in [app_config_holder.ROLE_ADMIN, app_config_holder.ROLE_STANDARD_USER]:
        logger.warning(
            f"Plex item details attempt by unauthorized role {user_role} for chat_id {chat_id}.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied to Plex item details.", parse_mode=None)
        return

    rating_key = query.data.split(
        CallbackData.CMD_PLEX_SEARCH_SHOW_DETAILS_PREFIX.value)[-1]

    if not app_config_holder.is_plex_enabled():
        logger.info(
            f"Plex item details request by {chat_id}, but Plex feature is disabled.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Plex features are disabled.", parse_mode=None)
        return

    status_msg_fetching = f"⏳ Fetching details for Plex item \\(RK: {escape_md_v2(rating_key)}\\)\\.\\.\\."
    await send_or_edit_universal_status_message(context.bot, chat_id, status_msg_fetching, parse_mode="MarkdownV2")
    item_data = get_plex_item_details(rating_key)

    if "error" in item_data:
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(item_data["error"]), parse_mode="MarkdownV2")

        await (display_plex_controls_menu(update, context) if user_role == app_config_holder.ROLE_ADMIN
               else show_or_edit_main_menu(str(chat_id), context))
        return

    details = item_data.get("details", {})
    item_type_from_details = details.get('type', 'N/A')

    context.user_data['plex_current_item_details_context'] = details
    context.user_data['plex_refresh_target_rating_key'] = rating_key

    context.user_data['plex_refresh_target_type'] = item_type_from_details

    title_md = escape_md_v2(details.get('title', 'N/A'))
    year_val = details.get('year', '')
    year_str_formatted = str(year_val) if year_val and str(
        year_val) != 'N/A' else ''
    year_md = f", {escape_md_v2(year_str_formatted)}" if year_str_formatted else ""
    type_md = escape_md_v2(item_type_from_details.capitalize())
    rating_md = escape_md_v2(details.get('rating', 'N/A'))
    summary_md = escape_md_v2(details.get('summary', 'N/A'))
    directors_md = escape_md_v2(details.get('directors', ''))
    writers_md = escape_md_v2(details.get('writers', ''))
    genres_md = escape_md_v2(details.get('genres', ''))
    total_size_gb_md = escape_md_v2(details.get('total_size_gb', 'N/A'))

    details_text_parts = [f"*{title_md}* \\({type_md}{year_md}\\)\n"]
    details_text_parts.append(f"*Rating:* {rating_md}\n")
    details_text_parts.append(f"*Summary:* {summary_md}\n")
    if details.get("directors"):
        details_text_parts.append(f"*Directors:* {directors_md}\n")
    if details.get("writers"):
        details_text_parts.append(f"*Writers:* {writers_md}\n")
    if details.get("genres"):
        details_text_parts.append(f"*Genres:* {genres_md}\n")

    if item_type_from_details == 'movie':
        file_info_parts = ["\n*File Info:*"]
        if details.get("file_info"):
            for fi in details["file_info"]:
                path_text = fi.get('path', 'N/A')

                escaped_path_text_display = escape_for_inline_code(
                    path_text, markdown_version=2)
                file_info_parts.append(f"  Path: {escaped_path_text_display}")
                file_info_parts.append(
                    f"  Size: {escape_md_v2(fi.get('size_gb', 'N/A'))}")
        else:
            file_info_parts.append("  Not available\\.")
        details_text_parts.append("\n".join(file_info_parts))
        details_text_parts.append(f"\n*Total Size:* {total_size_gb_md}")
    elif item_type_from_details == 'show':
        details_text_parts.append("\n*File Info:* _Available per episode\\._")

    final_details_text = "".join(details_text_parts)
    if len(final_details_text) > 4096:

        final_details_text = final_details_text[:4090] + "\\.\\.\\."

    await send_or_edit_universal_status_message(context.bot, chat_id, final_details_text, parse_mode="MarkdownV2")

    keyboard = []
    if user_role == app_config_holder.ROLE_ADMIN:
        keyboard.append([InlineKeyboardButton("♻️ Refresh Metadata",
                        callback_data=f"{CallbackData.CMD_PLEX_SEARCH_REFRESH_ITEM_METADATA_PREFIX.value}{rating_key}")])

    if item_type_from_details == 'show':
        keyboard.append([InlineKeyboardButton(
            f"➡️ View Seasons", callback_data=f"{CallbackData.CMD_PLEX_SEARCH_LIST_SEASONS_PREFIX.value}{rating_key}")])

    if user_role == app_config_holder.ROLE_ADMIN:
        keyboard.append([InlineKeyboardButton("⏪ Back to Plex Controls",
                        callback_data=CallbackData.CMD_PLEX_CONTROLS.value)])
    else:
        keyboard.append([InlineKeyboardButton("⏪ Back to Main Menu",
                        callback_data=CallbackData.CMD_HOME_BACK.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_message_id = load_menu_message_id(str(chat_id))

    if menu_message_id:
        try:
            menu_display_title = escape_md_v2(PLEX_ITEM_DETAILS_TEXT_RAW)
            current_content_key = f"menu_message_content_{chat_id}_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (menu_display_title, reply_markup.to_json())

            if old_content_tuple != new_content_tuple:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=menu_message_id,
                    text=menu_display_title,
                    reply_markup=reply_markup,
                    parse_mode="MarkdownV2"
                )
                context.bot_data[current_content_key] = new_content_tuple
            logger.info(
                f"Plex item details menu (type: {item_type_from_details}) displayed by editing message {menu_message_id}")
        except Exception as e:
            if "message is not modified" in str(e).lower():
                logger.debug(
                    f"Plex item details menu already displayed for message {menu_message_id}. Edit skipped.")
            else:
                logger.error(
                    f"Error editing message for Plex item details menu: {e}", exc_info=True)
                await (display_plex_controls_menu(update, context) if user_role == app_config_holder.ROLE_ADMIN
                       else show_or_edit_main_menu(str(chat_id), context, force_send_new=True))
    else:
        logger.error(
            "Cannot find menu_message_id for plex_search_show_details_callback (menu display)")


async def plex_search_show_episode_details_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_role = app_config_holder.get_user_role(str(chat_id))

    await query.answer()

    if user_role not in [app_config_holder.ROLE_ADMIN, app_config_holder.ROLE_STANDARD_USER]:
        logger.warning(
            f"Plex episode details attempt by unauthorized role {user_role} for chat_id {chat_id}.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied to Plex episode details.", parse_mode=None)
        return

    episode_rating_key = query.data.replace(
        CallbackData.CMD_PLEX_SEARCH_SHOW_EPISODE_DETAILS_PREFIX.value, "")

    if not app_config_holder.is_plex_enabled():
        logger.info(
            f"Plex episode details request by {chat_id}, but Plex feature is disabled.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Plex features are disabled.", parse_mode=None)
        return

    status_msg_fetching_ep = f"⏳ Fetching details for Plex episode \\(RK: {escape_md_v2(episode_rating_key)}\\)\\.\\.\\."
    await send_or_edit_universal_status_message(context.bot, chat_id, status_msg_fetching_ep, parse_mode="MarkdownV2")
    item_data = get_plex_item_details(episode_rating_key)

    if "error" in item_data:
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(item_data["error"]), parse_mode="MarkdownV2")
        await (display_plex_controls_menu(update, context) if user_role == app_config_holder.ROLE_ADMIN
               else show_or_edit_main_menu(str(chat_id), context))
        return

    details = item_data.get("details", {})
    if details.get('type') != 'episode':
        logger.warning(
            f"Expected episode details for RK {episode_rating_key}, but got type {details.get('type')}.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Error: Expected episode details, received different item type\\.", parse_mode="MarkdownV2")

        show_rk_from_context = context.user_data.get(
            'plex_search_current_show_rating_key')
        if show_rk_from_context:

            class DummyQuerySeasons:
                def __init__(self, data, message_obj, from_user_obj):
                    self.data = data
                    self.message = message_obj
                    self.from_user = from_user_obj

                async def answer(self): pass

            class DummyMessageSeasons:
                def __init__(self, chat_id_val, message_id_val): self.chat_id = chat_id_val; self.message_id = message_id_val; self.chat = type(
                    'DummyChat', (), {'id': chat_id_val})()

            class DummyUpdateSeasons:
                def __init__(self, callback_query_obj, effective_user_obj, effective_chat_obj):
                    self.callback_query = callback_query_obj
                    self.effective_user = effective_user_obj
                    self.effective_chat = effective_chat_obj

            original_menu_msg_id = query.message.message_id if query.message else load_menu_message_id(
                str(chat_id))
            if original_menu_msg_id:
                dummy_msg_seasons = DummyMessageSeasons(
                    chat_id, original_menu_msg_id)
                dummy_query_data_seasons = f"{CallbackData.CMD_PLEX_SEARCH_LIST_SEASONS_PREFIX.value}{show_rk_from_context}"
                dummy_q_obj_seasons = DummyQuerySeasons(
                    dummy_query_data_seasons, dummy_msg_seasons, update.effective_user)
                dummy_upd_seasons = DummyUpdateSeasons(
                    dummy_q_obj_seasons, update.effective_user, update.effective_chat)
                await plex_search_list_seasons_callback(dummy_upd_seasons, context)
                return

        await (display_plex_controls_menu(update, context) if user_role == app_config_holder.ROLE_ADMIN

               else show_or_edit_main_menu(str(chat_id), context))
        return

    context.user_data['plex_current_item_details_context'] = details
    context.user_data['plex_refresh_target_rating_key'] = episode_rating_key
    context.user_data['plex_refresh_target_type'] = 'episode'

    ep_title_md = escape_md_v2(details.get('title', 'N/A'))
    show_title_md = escape_md_v2(details.get('show_title', 'N/A'))
    season_episode_md = escape_md_v2(
        details.get('season_episode', 'N/A'))
    rating_md = escape_md_v2(details.get('rating', 'N/A'))
    summary_md = escape_md_v2(details.get('summary', 'N/A'))
    total_size_gb_md = escape_md_v2(details.get('total_size_gb', 'N/A'))

    details_text_parts = [f"*{ep_title_md}*\n"]
    details_text_parts.append(f"*Show:* {show_title_md}\n")
    details_text_parts.append(f"*Season/Episode:* {season_episode_md}\n")
    details_text_parts.append(f"*Rating:* {rating_md}\n")
    details_text_parts.append(f"*Summary:* {summary_md}\n")

    file_info_parts = ["\n*File Info:*"]
    if details.get("file_info"):
        for fi in details["file_info"]:
            path_text = fi.get('path', 'N/A')
            escaped_path_text_display = escape_for_inline_code(
                path_text, markdown_version=2)
            file_info_parts.append(f"  Path: {escaped_path_text_display}")
            file_info_parts.append(
                f"  Size: {escape_md_v2(fi.get('size_gb', 'N/A'))}")
    else:
        file_info_parts.append("  Not available\\.")
    details_text_parts.append("\n".join(file_info_parts))
    details_text_parts.append(f"\n*Total Size:* {total_size_gb_md}")

    final_details_text = "".join(details_text_parts)
    if len(final_details_text) > 4096:
        final_details_text = final_details_text[:4090] + "\\.\\.\\."

    await send_or_edit_universal_status_message(context.bot, chat_id, final_details_text, parse_mode="MarkdownV2")

    keyboard = []
    if user_role == app_config_holder.ROLE_ADMIN:
        keyboard.append([InlineKeyboardButton("♻️ Refresh Episode Metadata",
                        callback_data=f"{CallbackData.CMD_PLEX_SEARCH_REFRESH_ITEM_METADATA_PREFIX.value}{episode_rating_key}")])

    show_rk_internal = details.get('show_rating_key_internal')
    current_season_num = details.get('season_number_internal')

    if show_rk_internal is not None and current_season_num is not None:
        back_to_ep_list_for_season_cb = f"{CallbackData.CMD_PLEX_SEARCH_LIST_EPISODES_PREFIX.value}{show_rk_internal}_{current_season_num}"
        keyboard.append([InlineKeyboardButton(
            f"🔙 Back to Episode List (S{current_season_num})", callback_data=back_to_ep_list_for_season_cb)])

        button_show_title_short = details.get('show_title', 'Show')[:20] + "..." if len(
            details.get('show_title', 'Show')) > 20 else details.get('show_title', 'Show')
        keyboard.append([InlineKeyboardButton(
            f"🔙 Seasons ({button_show_title_short})", callback_data=f"{CallbackData.CMD_PLEX_SEARCH_LIST_SEASONS_PREFIX.value}{show_rk_internal}")])

    if user_role == app_config_holder.ROLE_ADMIN:
        keyboard.append([InlineKeyboardButton("⏪ Back to Plex Controls",
                        callback_data=CallbackData.CMD_PLEX_CONTROLS.value)])
    else:
        keyboard.append([InlineKeyboardButton(
            "⏪ Back to Main Menu", callback_data=CallbackData.CMD_HOME_BACK.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_message_id = load_menu_message_id(str(chat_id))

    if menu_message_id:
        try:
            menu_display_title = escape_md_v2(PLEX_EPISODE_DETAILS_TEXT_RAW)
            current_content_key = f"menu_message_content_{chat_id}_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (menu_display_title, reply_markup.to_json())
            if old_content_tuple != new_content_tuple:
                await context.bot.edit_message_text(
                    chat_id=chat_id, message_id=menu_message_id,
                    text=menu_display_title, reply_markup=reply_markup,
                    parse_mode="MarkdownV2"
                )
                context.bot_data[current_content_key] = new_content_tuple
        except Exception as e:
            if "message is not modified" in str(e).lower():
                logger.debug(
                    f"Plex episode details menu already displayed for message {menu_message_id}. Edit skipped.")
            else:
                logger.error(
                    f"Error editing message for Plex episode details menu: {e}", exc_info=True)
    else:
        logger.error(
            "Cannot find menu_message_id for plex_search_show_episode_details_callback (menu display)")


async def plex_search_refresh_item_metadata_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_role = app_config_holder.get_user_role(str(chat_id))

    await query.answer()

    if user_role != app_config_holder.ROLE_ADMIN:
        logger.warning(
            f"Plex refresh metadata attempt by non-admin {chat_id} (Role: {user_role}).")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied. Refreshing metadata is for administrators.", parse_mode=None)
        return

    rating_key = query.data.split(
        CallbackData.CMD_PLEX_SEARCH_REFRESH_ITEM_METADATA_PREFIX.value)[-1]

    item_type_refreshed = context.user_data.get(
        'plex_refresh_target_type', None)

    if not app_config_holder.is_plex_enabled():
        logger.info(
            f"Plex refresh metadata request by {chat_id}, but Plex feature is disabled.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Plex features are disabled.", parse_mode=None)
        return

    status_msg_initiating_refresh = f"⏳ Initiating metadata refresh for item {escape_md_v2(rating_key)}\\.\\.\\."
    await send_or_edit_universal_status_message(context.bot, chat_id, status_msg_initiating_refresh, parse_mode="MarkdownV2")

    refresh_result = trigger_item_metadata_refresh(
        rating_key)
    await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(refresh_result), parse_mode="MarkdownV2")

    class DummyQuery:
        def __init__(self, data, message_obj, from_user_obj):
            self.data = data
            self.message = message_obj
            self.from_user = from_user_obj

        async def answer(self): pass

    class DummyMessage:
        def __init__(self, chat_id_val, message_id_val): self.chat_id = chat_id_val; self.message_id = message_id_val; self.chat = type(
            'DummyChat', (), {'id': chat_id_val})()

    class DummyUpdate:
        def __init__(self, callback_query_obj, effective_user_obj, effective_chat_obj):
            self.callback_query = callback_query_obj
            self.effective_user = effective_user_obj
            self.effective_chat = effective_chat_obj

    original_menu_message_id = query.message.message_id if query.message else load_menu_message_id(
        str(chat_id))
    if not original_menu_message_id:
        logger.error(
            "Cannot determine original menu message ID for Plex refresh metadata callback post-action. Aborting re-display.")
        await display_plex_controls_menu(update, context)
        return

    original_user = update.effective_user
    dummy_message_obj = DummyMessage(chat_id, original_menu_message_id)

    dummy_query_data_for_details_view = ""
    target_callback_function = None

    if item_type_refreshed == 'episode':
        dummy_query_data_for_details_view = f"{CallbackData.CMD_PLEX_SEARCH_SHOW_EPISODE_DETAILS_PREFIX.value}{rating_key}"
        target_callback_function = plex_search_show_episode_details_callback
    elif item_type_refreshed == 'show' or item_type_refreshed == 'movie':
        dummy_query_data_for_details_view = f"{CallbackData.CMD_PLEX_SEARCH_SHOW_DETAILS_PREFIX.value}{rating_key}"
        target_callback_function = plex_search_show_details_callback
    else:
        logger.warning(
            f"Refresh metadata callback: Unknown item type '{item_type_refreshed}' for rating key {rating_key}. Returning to Plex controls menu.")
        await display_plex_controls_menu(update, context)
        return

    if target_callback_function and dummy_query_data_for_details_view:
        dummy_q_obj = DummyQuery(
            dummy_query_data_for_details_view, dummy_message_obj, original_user)
        dummy_update_for_details = DummyUpdate(
            dummy_q_obj, original_user, update.effective_chat)
        await target_callback_function(dummy_update_for_details, context)
    else:
        logger.error(
            f"Refresh metadata callback: Could not determine target view for type '{item_type_refreshed}'. Fallback to Plex controls.")
        await display_plex_controls_menu(update, context)
