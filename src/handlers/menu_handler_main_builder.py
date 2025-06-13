
from src.app.app_api_status_manager import (
    API_STATUS_ONLINE, API_STATUS_OFFLINE,
    API_STATUS_CONFIG_ERROR, API_STATUS_DISABLED,
    API_STATUS_UNKNOWN
)
import logging
import os
import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup  # Keep this

import src.app.app_config_holder as app_config_holder

from src.app.app_file_utils import load_requests_data
import src.app.user_manager as user_manager

from src.bot.bot_callback_data import CallbackData
from src.app.app_file_utils import load_tickets_data  # New import for ticket counts
from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)


def get_pending_request_count() -> int:
    """Counts the number of media requests with 'pending' status."""
    all_requests = load_requests_data()
    pending_count = sum(
        1 for req in all_requests if req.get("status") == "pending")
    return pending_count


def get_pending_access_request_count() -> int:
    """Counts the number of pending user access requests."""

    pending_access_requests = user_manager.get_pending_access_requests()
    return len(pending_access_requests)


def get_actionable_ticket_counts(chat_id_str: str, user_role: str) -> tuple[int, int]:
    """
    Gets counts for actionable tickets.
    Returns: (admin_actionable_count, user_actionable_count)
    """
    all_tickets = load_tickets_data()
    admin_actionable_count = 0
    user_actionable_count = 0

    if user_role == app_config_holder.ROLE_ADMIN:
        for ticket_data in all_tickets.values():
            if ticket_data.get("status") in ["open_by_user", "user_replied"]:
                admin_actionable_count += 1

    # For any user (including admin viewing their own tickets if they submitted any)
    for ticket_data in all_tickets.values():
        if ticket_data.get("user_chat_id") == chat_id_str and \
           ticket_data.get("status") in ["open_by_admin", "admin_replied"]:
            user_actionable_count += 1

    return admin_actionable_count, user_actionable_count


def build_main_menu_content(version: str, user_role: str, chat_id_str: str, bot_data: dict):
    is_primary_admin = app_config_holder.is_primary_admin(chat_id_str)
    is_general_admin = (user_role == app_config_holder.ROLE_ADMIN)
    is_standard_user = (user_role == app_config_holder.ROLE_STANDARD_USER)
    is_unknown_user = (user_role == app_config_holder.ROLE_UNKNOWN)

    def get_emoji_for_status(service_name: str, enabled_func, config_check_func, bot_data_key: str) -> str:
        if not enabled_func():
            return "🔘"  # Disabled
        if not config_check_func():
            return "⚠️"  # Config error

        live_status = bot_data.get(bot_data_key, API_STATUS_UNKNOWN)
        if live_status == API_STATUS_ONLINE:
            return "✅"
        elif live_status == API_STATUS_OFFLINE:
            return "🔌"
        else:  # API_STATUS_UNKNOWN or other error during check
            return "❓"

    # Plex Status
    plex_status_emoji = get_emoji_for_status(
        "Plex",
        app_config_holder.is_plex_enabled,
        lambda: app_config_holder.get_plex_url() and app_config_holder.get_plex_token(),
        "plex_api_status"
    )

    # Radarr Status
    radarr_status_emoji = get_emoji_for_status(
        "Radarr",
        app_config_holder.is_radarr_enabled,
        lambda: app_config_holder.get_radarr_base_api_url(
        ) and app_config_holder.get_radarr_api_key(),
        "radarr_api_status"
    )

    # Sonarr Status
    sonarr_status_emoji = get_emoji_for_status(
        "Sonarr",
        app_config_holder.is_sonarr_enabled,
        lambda: app_config_holder.get_sonarr_base_api_url(
        ) and app_config_holder.get_sonarr_api_key(),
        "sonarr_api_status"
    )

    # ABDM Status
    abdm_status_emoji = get_emoji_for_status(
        "ABDM",
        app_config_holder.is_abdm_enabled,
        lambda: app_config_holder.get_abdm_port() is not None,
        "abdm_api_status"
    )

    formatted_startup_time = "Unknown"
    iso_startup_timestamp = user_manager.get_last_startup_time_str()
    if iso_startup_timestamp:
        try:
            utc_startup_time_obj = datetime.datetime.fromisoformat(
                iso_startup_timestamp)
            local_startup_time_obj = utc_startup_time_obj.astimezone()
            formatted_startup_time = local_startup_time_obj.strftime(
                "%Y-%m-%d %H:%M")
        except ValueError:
            logger.warning(
                f"Could not parse startup timestamp '{iso_startup_timestamp}' from bot_state. Using 'Invalid Format'.")
            formatted_startup_time = "Invalid Format"
        except Exception as e_time:
            logger.error(
                f"Error converting startup timestamp '{iso_startup_timestamp}': {e_time}", exc_info=True)
            formatted_startup_time = "Error Converting Time"
    else:
        logger.info("Last startup time not yet recorded in bot_state.json.")
        formatted_startup_time = "Not yet recorded"

    escaped_version = escape_md_v2(version)
    escaped_startup_time = escape_md_v2(formatted_startup_time)
    separator_line = "—" * 17

    header_parts = [f"🎬 Media Catalog Bot \\(v{escaped_version}\\)"]
    if is_general_admin:
        header_parts.append(escape_md_v2(separator_line))
        header_parts.append(
            f"Plex: {plex_status_emoji} Sonarr: {sonarr_status_emoji} Radarr: {radarr_status_emoji} ABDM: {abdm_status_emoji}"
        )
        header_parts.append(f"Up Since: {escaped_startup_time}")
    elif is_standard_user:
        header_parts.append(escape_md_v2(separator_line))
        header_parts.append("Welcome\\! Select an option below\\.")
    elif is_unknown_user:
        header_parts.append(escape_md_v2(separator_line))

        header_parts.append("Access to this bot is restricted\\.")
    else:
        header_parts.append(escape_md_v2(separator_line))
        header_parts.append("Your access level is currently undefined\\.")

    dynamic_menu_text = "\n".join(header_parts)
    keyboard = []

    if is_standard_user:
        standard_user_media_buttons = []
        if app_config_holder.is_radarr_enabled():
            standard_user_media_buttons.append(InlineKeyboardButton("➕ Request Movie",
                                                                    callback_data=CallbackData.CMD_ADD_MOVIE_INIT.value))
        if app_config_holder.is_sonarr_enabled():
            standard_user_media_buttons.append(InlineKeyboardButton("➕ Request TV Show",
                                                                    callback_data=CallbackData.CMD_ADD_SHOW_INIT.value))
        if standard_user_media_buttons:
            keyboard.append(standard_user_media_buttons)

        if app_config_holder.is_plex_enabled():
            keyboard.append([InlineKeyboardButton("🔍 Search Plex",
                                                  callback_data=CallbackData.CMD_PLEX_INITIATE_SEARCH.value)])
        my_requests_tickets_row = []
        my_requests_tickets_row.append(InlineKeyboardButton("📋 My Requests",
                                                            callback_data=CallbackData.CMD_MY_REQUESTS_MENU.value))
        my_requests_tickets_row.append(InlineKeyboardButton("🎫 My Tickets",  # Ensured button is here
                                                            callback_data=CallbackData.CMD_TICKETS_MENU.value))
        keyboard.append(my_requests_tickets_row)

    elif is_general_admin:
        admin_add_media_buttons = []
        if app_config_holder.is_radarr_enabled():
            admin_add_media_buttons.append(
                InlineKeyboardButton("➕ Add Movie",
                                     callback_data=CallbackData.CMD_ADD_MOVIE_INIT.value)
            )
        if app_config_holder.is_sonarr_enabled():
            admin_add_media_buttons.append(InlineKeyboardButton("➕ Add TV Show",
                                                                callback_data=CallbackData.CMD_ADD_SHOW_INIT.value))
        if admin_add_media_buttons:
            keyboard.append(admin_add_media_buttons)

        if is_primary_admin and app_config_holder.is_abdm_enabled():
            keyboard.append([InlineKeyboardButton("📥 Add Download (ABDM)",
                                                  callback_data=CallbackData.CMD_ADD_DOWNLOAD_INIT.value)])

        media_requests_tickets_row = []
        pending_media_req_count = get_pending_request_count()
        # Renamed
        admin_media_req_button_text = f"📮 Requests ({pending_media_req_count}❗️)" if pending_media_req_count > 0 else "📮 Requests"
        media_requests_tickets_row.append(InlineKeyboardButton(admin_media_req_button_text,
                                                               callback_data=CallbackData.CMD_ADMIN_REQUESTS_MENU.value))

        admin_actionable_tickets, _ = get_actionable_ticket_counts(
            chat_id_str, user_role)
        admin_tickets_button_text = f"🎫 Tickets ({admin_actionable_tickets}❗️)" if admin_actionable_tickets > 0 else "🎫 Tickets"
        media_requests_tickets_row.append(InlineKeyboardButton(admin_tickets_button_text,
                                                               callback_data=CallbackData.CMD_TICKETS_MENU.value))
        keyboard.append(media_requests_tickets_row)

        media_services_row = []
        if app_config_holder.is_plex_enabled():
            media_services_row.append(InlineKeyboardButton("🌐 Plex",
                                                           callback_data=CallbackData.CMD_PLEX_CONTROLS.value))
        if app_config_holder.is_sonarr_enabled():
            media_services_row.append(InlineKeyboardButton("🎞️ Sonarr",
                                                           callback_data=CallbackData.CMD_SONARR_CONTROLS.value))
        if app_config_holder.is_radarr_enabled():
            media_services_row.append(InlineKeyboardButton("🎬 Radarr",
                                                           callback_data=CallbackData.CMD_RADARR_CONTROLS.value))
        if media_services_row:
            keyboard.append(media_services_row)

        # PC Direct Controls (Primary Admin Only)
        if app_config_holder.is_pc_control_enabled() and is_primary_admin:
            pc_direct_controls_row = []
            pc_direct_controls_row.append(InlineKeyboardButton("🎧 Media & Sound",
                                                               callback_data=CallbackData.CMD_PC_SHOW_MEDIA_SOUND_MENU.value))
            pc_direct_controls_row.append(InlineKeyboardButton("🔌 System Power",
                                                               callback_data=CallbackData.CMD_PC_SHOW_SYSTEM_POWER_MENU.value))
            keyboard.append(pc_direct_controls_row)

        if is_primary_admin:
            primary_admin_extra_row = []
            primary_admin_extra_row.append(InlineKeyboardButton("🚀 Launchers",
                                                                callback_data=CallbackData.CMD_LAUNCHERS_MENU.value))

            pending_access_req_count = get_pending_access_request_count()

            manage_users_button_text = f"👑 Users ({pending_access_req_count}❗️)" if pending_access_req_count > 0 else "👑 Users"
            primary_admin_extra_row.append(InlineKeyboardButton(manage_users_button_text,
                                                                callback_data=CallbackData.CMD_ADMIN_MANAGE_USERS_MENU.value))
            keyboard.append(primary_admin_extra_row)

    # Removed redundant elif is_standard_user block for tickets; it's handled above.
    elif is_unknown_user:
        # For unknown users, only show request access if no pending request exists for them
        pending_user_access_requests = user_manager.get_pending_access_requests()
        if str(chat_id_str) not in pending_user_access_requests:
            keyboard.append([InlineKeyboardButton("🚪 Request Access",
                                                  callback_data=CallbackData.CMD_REQUEST_ACCESS.value)])

    if is_primary_admin:
        keyboard.append([InlineKeyboardButton("⚙️ Bot Settings",
                        callback_data=CallbackData.CMD_SETTINGS.value)])

    # Check for open tickets initiated by admin for this user
    support_tickets_store = bot_data.get('support_tickets', {})
    user_has_new_ticket_from_admin = False
    newest_ticket_id_from_admin = None

    for ticket_id, ticket_data in support_tickets_store.items():
        if ticket_data.get("user_chat_id") == chat_id_str and \
           ticket_data.get("status") == "open_by_admin" and \
           (not ticket_data.get("user_viewed_initial_admin_msg", False)):  # New flag to track if user saw it
            user_has_new_ticket_from_admin = True
            newest_ticket_id_from_admin = ticket_id  # Simplification: just link to one
            break
    if user_has_new_ticket_from_admin and newest_ticket_id_from_admin:
        dynamic_menu_text += f"\n\n📬 *New ticket from Admin\\!*"
        view_message_button = [InlineKeyboardButton("✉️ View Ticket",
                               callback_data=f"{CallbackData.CMD_USER_VIEW_TICKET_PREFIX.value}{newest_ticket_id_from_admin}")]
        # Add to the beginning of the keyboard
        keyboard.insert(0, view_message_button)

    # Check for unread user replies for the primary admin
    if is_primary_admin:
        unread_user_replies = bot_data.get(
            'unread_user_replies', {}).get(chat_id_str, [])
        if unread_user_replies:  # Check if the list is not empty
            # For simplicity, we'll just show one button to view the oldest reply.
            # More complex logic could show a count or individual buttons if needed.
            # Get the first (oldest) reply
            oldest_unread_reply = unread_user_replies[0]
            dynamic_menu_text += f"\n\n📬 *New reply from a user\\!*"
            view_reply_button = [InlineKeyboardButton("✉️ View User Reply",
                                                      callback_data=f"{CallbackData.CMD_ADMIN_VIEW_USER_REPLY_PREFIX.value}{oldest_unread_reply['id']}")]
            keyboard.insert(0, view_reply_button)  # Add to the beginning

    if not keyboard:
        if is_primary_admin:
            keyboard.append([InlineKeyboardButton(
                "⚙️ Bot Settings", callback_data=CallbackData.CMD_SETTINGS.value)])

        no_features_text_parts = ["\n" + escape_md_v2(separator_line)]
        if is_unknown_user:
            no_features_text_parts.append(escape_md_v2(
                "Use the button above to request access."))
        elif not is_primary_admin and not is_standard_user and not is_general_admin:
            no_features_text_parts.append(escape_md_v2(
                "No options currently available for your access level."))
        else:
            no_features_text_parts.append(
                escape_md_v2("No features currently available for your role." if not is_primary_admin else
                             "No features currently enabled. Please check settings via the /settings command.")
            )

        if not (is_unknown_user and len(keyboard) == 1 and keyboard[0][0].callback_data == CallbackData.CMD_REQUEST_ACCESS.value):
            dynamic_menu_text += "\n" + "\n".join(no_features_text_parts)

    reply_markup = InlineKeyboardMarkup(keyboard)
    return dynamic_menu_text, reply_markup
