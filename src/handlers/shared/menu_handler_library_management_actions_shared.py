import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.bot.bot_message_persistence import load_menu_message_id
from src.bot.bot_initialization import send_or_edit_universal_status_message
from src.bot.bot_callback_data import CallbackData
from src.bot.bot_text_utils import escape_md_v2

from src.handlers.radarr.menu_handler_library_management_radarr import display_radarr_queue_menu
from src.handlers.sonarr.menu_handler_library_management_sonarr import display_sonarr_queue_menu

logger = logging.getLogger(__name__)

QUEUE_ITEM_ACTIONS_MENU_TEXT_TEMPLATE_RAW = "🛠️ Actions for: *{item_title_short}*"


async def display_queue_item_action_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, service_name: str, item_id: str, item_title_from_queue: str, search_id: str) -> None:
    query = update.callback_query
    if query:
        await query.answer()
    chat_id = update.effective_chat.id

    item_title_short_raw = item_title_from_queue.replace(
        "➡️ ", "")
    if len(item_title_short_raw) > 40:
        item_title_short_raw = item_title_short_raw[:37] + "..."

    escaped_item_title_short_for_menu = escape_md_v2(item_title_short_raw)
    menu_text = QUEUE_ITEM_ACTIONS_MENU_TEXT_TEMPLATE_RAW.format(
        item_title_short=escaped_item_title_short_for_menu)

    keyboard = []

    if service_name == "Radarr":
        keyboard.append([InlineKeyboardButton("🗑️ Remove (No Blocklist)",
                        callback_data=f"{CallbackData.CMD_RADARR_QUEUE_ITEM_REMOVE_NO_BLOCKLIST_PREFIX.value}{item_id}")])
        keyboard.append([InlineKeyboardButton("🚫 Blocklist Only",
                        callback_data=f"{CallbackData.CMD_RADARR_QUEUE_ITEM_BLOCKLIST_ONLY_PREFIX.value}{item_id}")])

        keyboard.append([InlineKeyboardButton("🚫🔍 Blocklist & Search Again",
                                              callback_data=f"{CallbackData.CMD_RADARR_QUEUE_ITEM_BLOCKLIST_SEARCH_PREFIX.value}{item_id}_{search_id}")])
        keyboard.append([InlineKeyboardButton("🔄 Refresh Queue List",
                        callback_data=CallbackData.CMD_RADARR_QUEUE_REFRESH.value)])

        keyboard.append([InlineKeyboardButton("🔙 Back to Queue List",
                        callback_data=CallbackData.CMD_RADARR_QUEUE_BACK_TO_LIST.value)])
    elif service_name == "Sonarr":
        keyboard.append([InlineKeyboardButton("🗑️ Remove (No Blocklist)",
                        callback_data=f"{CallbackData.CMD_SONARR_QUEUE_ITEM_REMOVE_NO_BLOCKLIST_PREFIX.value}{item_id}")])
        keyboard.append([InlineKeyboardButton("🚫 Blocklist Only",
                        callback_data=f"{CallbackData.CMD_SONARR_QUEUE_ITEM_BLOCKLIST_ONLY_PREFIX.value}{item_id}")])

        keyboard.append([InlineKeyboardButton("🚫🔍 Blocklist & Search Again",
                                              callback_data=f"{CallbackData.CMD_SONARR_QUEUE_ITEM_BLOCKLIST_SEARCH_PREFIX.value}{item_id}_{search_id}")])
        keyboard.append([InlineKeyboardButton("🔄 Refresh Queue List",
                        callback_data=CallbackData.CMD_SONARR_QUEUE_REFRESH.value)])

        keyboard.append([InlineKeyboardButton("🔙 Back to Queue List",
                        callback_data=CallbackData.CMD_SONARR_QUEUE_BACK_TO_LIST.value)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_message_id = load_menu_message_id(str(chat_id))
    if not menu_message_id and context.bot_data:
        menu_message_id = context.bot_data.get(
            f"main_menu_message_id_{chat_id}")

    if menu_message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=menu_message_id,
                text=menu_text, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )
            context.bot_data[f"menu_message_content_{menu_message_id}"] = (
                menu_text, reply_markup.to_json())
            await send_or_edit_universal_status_message(context.bot, chat_id, f"Select action for queue item.", parse_mode=None)
        except Exception as e:
            logger.error(
                f"Error displaying queue item action menu for {service_name} item {item_id}: {e}", exc_info=True)
            current_page = context.user_data.get(
                f'{service_name.lower()}_queue_current_page', 1)
            if service_name == "Radarr":
                await display_radarr_queue_menu(update, context, page=current_page)
            elif service_name == "Sonarr":
                await display_sonarr_queue_menu(update, context, page=current_page)
    else:
        logger.error(
            f"Cannot find menu_message_id for {service_name} queue item action menu.")
