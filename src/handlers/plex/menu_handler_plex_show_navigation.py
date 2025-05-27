
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.bot_text_utils import escape_md_v1, escape_md_v2
import src.app.app_config_holder as app_config_holder
from src.bot.bot_callback_data import CallbackData
from src.bot.bot_initialization import send_or_edit_universal_status_message, show_or_edit_main_menu
from src.bot.bot_message_persistence import load_menu_message_id
from src.services.plex.bot_plex_media_items import get_plex_show_seasons, get_plex_season_episodes
from src.handlers.plex.menu_handler_plex_controls import display_plex_controls_menu

logger = logging.getLogger(__name__)

PLEX_SHOW_SEASONS_MENU_TEXT_RAW = "🗓️ Seasons for *{show_title}*:"

PLEX_SEASON_EPISODES_MENU_TEXT_RAW = "📺 Episodes for *{show_title}* / *{season_title}*:"


async def plex_search_list_seasons_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_role = app_config_holder.get_user_role(str(chat_id))

    await query.answer()

    if user_role not in [app_config_holder.ROLE_ADMIN, app_config_holder.ROLE_STANDARD_USER]:
        logger.warning(
            f"Plex list seasons attempt by unauthorized role {user_role} for chat_id {chat_id}.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied to Plex show seasons.", parse_mode=None)
        return

    show_rating_key = query.data.replace(
        CallbackData.CMD_PLEX_SEARCH_LIST_SEASONS_PREFIX.value, "")

    if not app_config_holder.is_plex_enabled():
        logger.info(
            f"Plex list seasons request by {chat_id}, but Plex feature is disabled.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Plex features are disabled.", parse_mode=None)
        return

    status_msg_fetching_seasons = f"⏳ Fetching seasons for show RK: {escape_md_v2(show_rating_key)}\\.\\.\\."
    await send_or_edit_universal_status_message(context.bot, chat_id, status_msg_fetching_seasons, parse_mode="MarkdownV2")
    seasons_data_result = get_plex_show_seasons(show_rating_key)

    if "error" in seasons_data_result:
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(seasons_data_result["error"]), parse_mode="MarkdownV2")
        await (display_plex_controls_menu(update, context) if user_role == app_config_holder.ROLE_ADMIN
               else show_or_edit_main_menu(str(chat_id), context))
        return

    seasons = seasons_data_result.get("seasons", [])
    show_title_raw = seasons_data_result.get("show_title", "Unknown Show")

    context.user_data['plex_search_current_show_rating_key'] = show_rating_key
    context.user_data['plex_search_current_show_title'] = show_title_raw

    context.user_data.pop('plex_search_current_season_number', None)
    context.user_data.pop('plex_search_current_season_title', None)

    context.user_data.pop('plex_search_current_episode_page', None)

    keyboard = []
    if seasons:

        seasons.sort(key=lambda s: s.get("season_number", 999))
        for season in seasons:
            button_season_title = season['title']
            if len(button_season_title) > 50:
                button_season_title = button_season_title[:47] + "..."
            callback_ep_list = f"{CallbackData.CMD_PLEX_SEARCH_LIST_EPISODES_PREFIX.value}{show_rating_key}_{season['season_number']}"
            keyboard.append([InlineKeyboardButton(
                f"➡️ {button_season_title}", callback_data=callback_ep_list)])
    else:

        await send_or_edit_universal_status_message(context.bot, chat_id, f"ℹ️ No seasons found for '{escape_md_v1(show_title_raw)}'\\.", parse_mode="MarkdownV2")

    button_show_title_short = show_title_raw[:25] + \
        "..." if len(show_title_raw) > 25 else show_title_raw
    keyboard.append([InlineKeyboardButton(f"🔙 Return to Show: {button_show_title_short}",
                    callback_data=f"{CallbackData.CMD_PLEX_SEARCH_SHOW_DETAILS_PREFIX.value}{show_rating_key}")])

    if user_role == app_config_holder.ROLE_ADMIN:
        keyboard.append([InlineKeyboardButton("♻️ Refresh Show Metadata",
                        callback_data=f"{CallbackData.CMD_PLEX_SEARCH_REFRESH_ITEM_METADATA_PREFIX.value}{show_rating_key}")])

    if user_role == app_config_holder.ROLE_ADMIN:
        keyboard.append([InlineKeyboardButton("⏪ Back to Plex Controls",
                        callback_data=CallbackData.CMD_PLEX_CONTROLS.value)])
    else:
        keyboard.append([InlineKeyboardButton(
            "⏪ Back to Main Menu", callback_data=CallbackData.CMD_HOME_BACK.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_message_id = load_menu_message_id(str(chat_id))

    escaped_show_title_for_menu = escape_md_v2(show_title_raw)
    menu_text_display = PLEX_SHOW_SEASONS_MENU_TEXT_RAW.format(
        show_title=escaped_show_title_for_menu)

    if menu_message_id:
        try:
            current_content_key = f"menu_message_content_{chat_id}_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (menu_text_display, reply_markup.to_json())
            if old_content_tuple != new_content_tuple:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=menu_message_id,
                    text=menu_text_display,
                    reply_markup=reply_markup,
                    parse_mode="MarkdownV2"
                )
                context.bot_data[current_content_key] = new_content_tuple

            if seasons:
                await send_or_edit_universal_status_message(context.bot, chat_id, f"Displaying seasons for '{escape_md_v2(show_title_raw)}'\\.", parse_mode="MarkdownV2")
        except Exception as e:
            if "message is not modified" in str(e).lower():
                logger.debug(
                    f"Plex show seasons menu already displayed for message {menu_message_id}. Edit skipped.")
                if seasons:
                    await send_or_edit_universal_status_message(context.bot, chat_id, f"Displaying seasons for '{escape_md_v2(show_title_raw)}'\\.", parse_mode="MarkdownV2")
            else:
                logger.error(
                    f"Error editing message for Plex show seasons: {e}", exc_info=True)
                await (display_plex_controls_menu(update, context) if user_role == app_config_holder.ROLE_ADMIN

                       else show_or_edit_main_menu(str(chat_id), context))
    else:
        logger.error(
            "Cannot find menu_message_id for plex_search_list_seasons_callback")
        await (display_plex_controls_menu(update, context) if user_role == app_config_holder.ROLE_ADMIN
               else show_or_edit_main_menu(str(chat_id), context))


async def plex_search_list_episodes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_role = app_config_holder.get_user_role(str(chat_id))

    await query.answer()

    if user_role not in [app_config_holder.ROLE_ADMIN, app_config_holder.ROLE_STANDARD_USER]:
        logger.warning(
            f"Plex list episodes attempt by unauthorized role {user_role} for chat_id {chat_id}.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied to Plex episodes.", parse_mode=None)
        return

    show_rating_key, season_number_str = "", ""

    if query.data.startswith(CallbackData.CMD_PLEX_SEARCH_LIST_EPISODES_PREFIX.value):
        data_str = query.data.replace(
            CallbackData.CMD_PLEX_SEARCH_LIST_EPISODES_PREFIX.value, "")
        parts = data_str.split("_", 1)
        if len(parts) == 2:
            show_rating_key, season_number_str = parts[0], parts[1]
        else:
            logger.error(
                f"Invalid payload for CMD_PLEX_SEARCH_LIST_EPISODES_PREFIX: {query.data}")
            await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Error: Invalid request for episodes.", parse_mode=None)
            return
    else:
        logger.error(
            f"plex_search_list_episodes_callback called with unhandled data: {query.data}")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Error: Unrecognized episode list command.", parse_mode=None)
        return

    if not app_config_holder.is_plex_enabled():
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Plex features are disabled.", parse_mode=None)
        return

    status_msg_fetching_eps = f"⏳ Fetching episodes for S{escape_md_v2(season_number_str)} of show RK: {escape_md_v2(show_rating_key)}\\.\\.\\."
    await send_or_edit_universal_status_message(context.bot, chat_id, status_msg_fetching_eps, parse_mode="MarkdownV2")
    episodes_data_result = get_plex_season_episodes(
        show_rating_key, season_number_str)

    if "error" in episodes_data_result:
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(episodes_data_result["error"]), parse_mode="MarkdownV2")
        await (display_plex_controls_menu(update, context) if user_role == app_config_holder.ROLE_ADMIN
               else show_or_edit_main_menu(str(chat_id), context))
        return

    episodes = episodes_data_result.get("records", [])
    show_title_raw = episodes_data_result.get("show_title", "Unknown Show")
    season_title_raw = episodes_data_result.get(
        "season_title", f"Season {season_number_str}")

    context.user_data.update({

        'plex_search_current_show_rating_key': show_rating_key,
        'plex_search_current_show_title': show_title_raw,
        'plex_search_current_season_number': season_number_str,
        'plex_search_current_season_title': season_title_raw,
        'plex_search_current_episode_page': 1
    })

    keyboard = []
    status_msg_raw_disp = ""
    if episodes:

        for episode in episodes[:30]:
            ep_display_title_button = episode['title']
            if len(ep_display_title_button) > 55:
                ep_display_title_button = ep_display_title_button[:52] + "..."

            keyboard.append([InlineKeyboardButton(
                f"{ep_display_title_button}", callback_data=f"{CallbackData.CMD_PLEX_SEARCH_SHOW_EPISODE_DETAILS_PREFIX.value}{episode['ratingKey']}")])
        if len(episodes) > 30:

            keyboard.append([InlineKeyboardButton(
                f"... and {len(episodes)-30} more episodes (not listed).", callback_data=CallbackData.CMD_PLEX_MENU_BACK.value)])

        status_msg_raw_disp = f"Displaying episodes for '{show_title_raw} - {season_title_raw}'\\."
    else:
        status_msg_raw_disp = f"ℹ️ No episodes found in '{show_title_raw} - {season_title_raw}'\\."

    await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(status_msg_raw_disp), parse_mode="MarkdownV2")

    button_show_title_short = show_title_raw[:20] + \
        "..." if len(show_title_raw) > 20 else show_title_raw
    keyboard.extend([
        [InlineKeyboardButton(f"🔙 Back to Seasons ({button_show_title_short})",
                              callback_data=f"{CallbackData.CMD_PLEX_SEARCH_LIST_SEASONS_PREFIX.value}{show_rating_key}")],
    ])
    if user_role == app_config_holder.ROLE_ADMIN:
        keyboard.append([InlineKeyboardButton(
            "⏪ Back to Plex Controls", callback_data=CallbackData.CMD_PLEX_CONTROLS.value)])
    else:
        keyboard.append([InlineKeyboardButton(
            "⏪ Back to Main Menu", callback_data=CallbackData.CMD_HOME_BACK.value)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_message_id = load_menu_message_id(str(chat_id))

    escaped_show_title_menu, escaped_season_title_menu = escape_md_v2(
        show_title_raw), escape_md_v2(season_title_raw)
    menu_text_display = PLEX_SEASON_EPISODES_MENU_TEXT_RAW.format(
        show_title=escaped_show_title_menu, season_title=escaped_season_title_menu
    )

    if menu_message_id:
        try:
            current_content_key = f"menu_message_content_{chat_id}_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (menu_text_display, reply_markup.to_json())
            if old_content_tuple != new_content_tuple:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=menu_message_id,
                    text=menu_text_display,
                    reply_markup=reply_markup,
                    parse_mode="MarkdownV2"
                )
                context.bot_data[current_content_key] = new_content_tuple
        except Exception as e:
            if "message is not modified" in str(e).lower():
                logger.debug(
                    f"Plex season episodes menu already displayed for message {menu_message_id}. Edit skipped.")
            else:
                logger.error(
                    f"Error editing message for Plex season episodes: {e}", exc_info=True)
                await (display_plex_controls_menu(update, context) if user_role == app_config_holder.ROLE_ADMIN

                       else show_or_edit_main_menu(str(chat_id), context))
    else:
        logger.error(
            "Cannot find menu_message_id for plex_search_list_episodes_callback")
        await (display_plex_controls_menu(update, context) if user_role == app_config_holder.ROLE_ADMIN
               else show_or_edit_main_menu(str(chat_id), context))
