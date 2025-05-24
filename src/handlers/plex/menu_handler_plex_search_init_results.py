import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.bot_text_utils import escape_md_v1, escape_md_v2
import src.app.app_config_holder as app_config_holder
from src.bot.bot_callback_data import CallbackData
from src.bot.bot_initialization import send_or_edit_universal_status_message
from src.bot.bot_message_persistence import load_menu_message_id

from src.handlers.plex.menu_handler_plex_controls import display_plex_controls_menu

from src.bot.bot_initialization import show_or_edit_main_menu

logger = logging.getLogger(__name__)

PLEX_SEARCH_RESULTS_TEXT_RAW = "🔍 Plex Search Results:"


async def plex_search_initiate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    admin_chat_id_str = app_config_holder.get_chat_id_str()
    if not admin_chat_id_str or str(chat_id) != admin_chat_id_str:
        logger.warning(
            f"Plex search initiate attempt by non-primary admin {chat_id}.")
        return

    if not app_config_holder.is_plex_enabled():
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ Plex features are disabled.", parse_mode=None)
        return

    context.user_data['pending_plex_search'] = True

    context.user_data.pop('plex_search_current_show_rating_key', None)

    plex_keys_to_clear = ['plex_search_current_show_rating_key', 'plex_search_current_show_title',
                          'plex_search_current_season_number', 'plex_search_current_season_title',
                          'plex_search_current_episode_page', 'plex_current_item_details_context',
                          'plex_refresh_target_rating_key', 'plex_refresh_target_type',
                          'plex_recently_added_current_library_key', 'plex_recently_added_all_items',
                          'plex_return_to_menu_id']
    for key in plex_keys_to_clear:
        context.user_data.pop(key, None)

    if query and query.message:

        context.user_data['plex_return_to_menu_id'] = query.message.message_id
    await send_or_edit_universal_status_message(context.bot, chat_id, "📝 Enter your Plex search query:", parse_mode=None)


async def display_plex_search_results(update: Update, context: ContextTypes.DEFAULT_TYPE, search_results_data: dict) -> None:
    chat_id = update.effective_chat.id

    admin_chat_id_str = app_config_holder.get_chat_id_str()
    if not admin_chat_id_str or str(chat_id) != admin_chat_id_str:
        logger.warning(
            f"Plex search results display attempt by non-primary admin {chat_id}.")
        return

    menu_message_id = load_menu_message_id()
    results = search_results_data.get("results", [])
    message_text_from_plex = search_results_data.get("message", "No results.")

    await send_or_edit_universal_status_message(context.bot, chat_id, message_text_from_plex, parse_mode="Markdown")

    keyboard = []
    if results:
        for item in results:
            button_item_title = item['title']
            button_year_str = item['year_str'] if item['year_str'] else ""
            btn_text_core = f"{item['type'].capitalize()}: {button_item_title}{button_year_str}"
            if len(btn_text_core) > 60:
                btn_text_core = btn_text_core[:57] + "..."
            callback_value = ""
            if item['type'] == 'show' or item['type'] == 'movie':
                callback_value = f"{CallbackData.CMD_PLEX_SEARCH_SHOW_DETAILS_PREFIX.value}{item['id']}"

            if callback_value:
                keyboard.append([InlineKeyboardButton(
                    btn_text_core, callback_data=callback_value)])
            else:
                logger.debug(
                    f"Plex search: Ignoring item type '{item['type']}' for button creation: {item['title']}")

    keyboard.append([InlineKeyboardButton("🔙 Back to Plex Controls",
                    callback_data=CallbackData.CMD_PLEX_CONTROLS.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)

    escaped_menu_title = escape_md_v2(PLEX_SEARCH_RESULTS_TEXT_RAW)

    if menu_message_id:
        try:
            current_content_key = f"menu_message_content_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (escaped_menu_title, reply_markup.to_json())
            if old_content_tuple != new_content_tuple:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=menu_message_id, text=escaped_menu_title, reply_markup=reply_markup, parse_mode="MarkdownV2")
                context.bot_data[current_content_key] = new_content_tuple
            logger.info(
                f"Plex search results displayed by editing message {menu_message_id}")
        except Exception as e:
            if "message is not modified" in str(e).lower():
                logger.debug(
                    f"Plex search results menu already displayed for message {menu_message_id}. Edit skipped.")
            else:
                logger.error(
                    f"Error editing message for Plex search results: {e}", exc_info=True)

                await display_plex_controls_menu(update, context)
    else:
        logger.error(
            "Cannot find menu_message_id for display_plex_search_results")
        if admin_chat_id_str:
            await show_or_edit_main_menu(admin_chat_id_str, context, force_send_new=True)
