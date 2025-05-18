import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.bot_text_utils import escape_md_v1, escape_md_v2
import src.app.app_config_holder as app_config_holder
from src.config.config_definitions import CallbackData
from src.bot.bot_initialization import send_or_edit_universal_status_message
from src.bot.bot_message_persistence import load_menu_message_id
from src.services.plex.bot_plex_media_items import get_plex_show_seasons, get_plex_season_episodes
from src.handlers.plex.menu_handler_plex_controls import display_plex_controls_menu

logger = logging.getLogger(__name__)

PLEX_SHOW_SEASONS_MENU_TEXT_RAW = "🗓️ Seasons for *{show_title}*:"

PLEX_SEASON_EPISODES_MENU_TEXT_RAW = "📺 Episodes for *{show_title}* / *{season_title}*:"


async def plex_search_list_seasons_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    show_rating_key = query.data.replace(
        CallbackData.CMD_PLEX_SEARCH_LIST_SEASONS_PREFIX.value, "")

    if not app_config_holder.is_plex_enabled():
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Plex features are disabled.", parse_mode=None)
        return

    await send_or_edit_universal_status_message(context.bot, chat_id, f"⏳ Fetching seasons...", parse_mode=None)
    seasons_data_result = get_plex_show_seasons(show_rating_key)

    if "error" in seasons_data_result:
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(seasons_data_result["error"]), parse_mode="MarkdownV2")
        await display_plex_controls_menu(update, context)
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
            callback_ep_list = f"{CallbackData.CMD_PLEX_SEARCH_LIST_EPISODES_PREFIX.value}{show_rating_key}_{season['season_number']}"
            keyboard.append([InlineKeyboardButton(
                f"➡️ {button_season_title}", callback_data=callback_ep_list)])
    else:
        await send_or_edit_universal_status_message(context.bot, chat_id, f"ℹ️ No seasons found for '{escape_md_v1(show_title_raw)}'\\.", parse_mode="MarkdownV2")

    button_show_title_short = show_title_raw[:25] + \
        "..." if len(show_title_raw) > 25 else show_title_raw
    keyboard.append([InlineKeyboardButton(f"🔙 Return to Show: {button_show_title_short}",
                    callback_data=f"{CallbackData.CMD_PLEX_SEARCH_SHOW_DETAILS_PREFIX.value}{show_rating_key}")])
    keyboard.append([InlineKeyboardButton("♻️ Refresh Show Metadata",
                    callback_data=f"{CallbackData.CMD_PLEX_SEARCH_REFRESH_ITEM_METADATA_PREFIX.value}{show_rating_key}")])
    keyboard.append([InlineKeyboardButton("⏪ Back to Plex Controls",
                    callback_data=CallbackData.CMD_PLEX_CONTROLS.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_message_id = load_menu_message_id()

    escaped_show_title_for_menu = escape_md_v2(show_title_raw)
    menu_text_display = PLEX_SHOW_SEASONS_MENU_TEXT_RAW.format(
        show_title=escaped_show_title_for_menu)

    if menu_message_id:
        try:
            current_content_key = f"menu_message_content_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (menu_text_display, reply_markup.to_json())
            if old_content_tuple != new_content_tuple:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=menu_message_id, text=menu_text_display, reply_markup=reply_markup, parse_mode="MarkdownV2")
                context.bot_data[current_content_key] = new_content_tuple
            await send_or_edit_universal_status_message(context.bot, chat_id, f"Displaying seasons for '{escape_md_v2(show_title_raw)}'\\.", parse_mode="MarkdownV2")
        except Exception as e:
            if "message is not modified" in str(e).lower():
                logger.debug(
                    f"Plex show seasons menu already displayed for message {menu_message_id}. Edit skipped.")
                await send_or_edit_universal_status_message(context.bot, chat_id, f"Displaying seasons for '{escape_md_v2(show_title_raw)}'\\.", parse_mode="MarkdownV2")
            else:
                logger.error(
                    f"Error editing message for Plex show seasons: {e}", exc_info=True)
                await display_plex_controls_menu(update, context)
    else:
        logger.error(
            "Cannot find menu_message_id for plex_search_list_seasons_callback")
        await display_plex_controls_menu(update, context)


async def plex_search_list_episodes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
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

    await send_or_edit_universal_status_message(context.bot, chat_id, f"⏳ Fetching episodes...", parse_mode=None)

    episodes_data_result = get_plex_season_episodes(
        show_rating_key, season_number_str)

    if "error" in episodes_data_result:
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(episodes_data_result["error"]), parse_mode="MarkdownV2")
        await display_plex_controls_menu(update, context)
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
    if episodes:

        for episode in episodes:
            ep_display_title_button = episode['title'][:55] + \
                "..." if len(episode['title']) > 55 else episode['title']
            keyboard.append([InlineKeyboardButton(
                f"{ep_display_title_button}", callback_data=f"{CallbackData.CMD_PLEX_SEARCH_SHOW_EPISODE_DETAILS_PREFIX.value}{episode['ratingKey']}")])

    else:
        status_msg_raw = f"ℹ️ No episodes found for '{show_title_raw} - {season_title_raw}'\\."
        await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(status_msg_raw), parse_mode="MarkdownV2")

    button_show_title_short = show_title_raw[:20] + \
        "..." if len(show_title_raw) > 20 else show_title_raw
    keyboard.extend([
        [InlineKeyboardButton(f"🔙 Back to Seasons ({button_show_title_short})",
                              callback_data=f"{CallbackData.CMD_PLEX_SEARCH_LIST_SEASONS_PREFIX.value}{show_rating_key}")],
        [InlineKeyboardButton("⏪ Back to Plex Controls",
                              callback_data=CallbackData.CMD_PLEX_CONTROLS.value)]
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_message_id = load_menu_message_id()

    escaped_show_title_menu, escaped_season_title_menu = escape_md_v2(
        show_title_raw), escape_md_v2(season_title_raw)

    menu_text_display = PLEX_SEASON_EPISODES_MENU_TEXT_RAW.format(
        show_title=escaped_show_title_menu, season_title=escaped_season_title_menu,
        current_page=1, total_pages=1
    ).replace(" (Page 1/1)", "")

    if menu_message_id:
        try:
            current_content_key = f"menu_message_content_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (menu_text_display, reply_markup.to_json())
            if old_content_tuple != new_content_tuple:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=menu_message_id, text=menu_text_display, reply_markup=reply_markup, parse_mode="MarkdownV2")
                context.bot_data[current_content_key] = new_content_tuple

            status_msg_raw_disp = f"Displaying episodes for '{show_title_raw} - {season_title_raw}'\\."
            if not episodes:
                status_msg_raw_disp = f"No episodes found in '{show_title_raw} - {season_title_raw}'\\."
            await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(status_msg_raw_disp), parse_mode="MarkdownV2")
        except Exception as e:
            if "message is not modified" in str(e).lower():
                logger.debug(
                    f"Plex season episodes menu already displayed for message {menu_message_id}. Edit skipped.")
                status_msg_raw_disp_no_mod = f"Displaying episodes for '{show_title_raw} - {season_title_raw}'\\."
                if not episodes:
                    status_msg_raw_disp_no_mod = f"No episodes found in '{show_title_raw} - {season_title_raw}'\\."
                await send_or_edit_universal_status_message(context.bot, chat_id, escape_md_v2(status_msg_raw_disp_no_mod), parse_mode="MarkdownV2")
            else:
                logger.error(
                    f"Error editing message for Plex season episodes: {e}", exc_info=True)
                await display_plex_controls_menu(update, context)
    else:
        logger.error(
            "Cannot find menu_message_id for plex_search_list_episodes_callback")
        await display_plex_controls_menu(update, context)
