
import logging
import pyautogui
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import src.app.app_config_holder as app_config_holder
from src.bot.bot_initialization import (
    load_menu_message_id,
    send_or_edit_universal_status_message
)
from src.bot.bot_callback_data import CallbackData
from .menu_handler_pc_root import display_pc_control_categories_menu
from src.bot.bot_text_utils import escape_md_v2

try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    PYCAW_AVAILABLE = True
except ImportError:
    PYCAW_AVAILABLE = False
    pass

logger = logging.getLogger(__name__)

PC_MEDIA_SOUND_MENU_TEXT_RAW = "🎧 PC Media & Sound Controls"

PC_CONTROL_CALLBACK_PREFIX = "cb_pc_"

MEDIA_ACTION_MAP = {
    f"{PC_CONTROL_CALLBACK_PREFIX}prev": "prevtrack",
    f"{PC_CONTROL_CALLBACK_PREFIX}playpause": "playpause",
    f"{PC_CONTROL_CALLBACK_PREFIX}next": "nexttrack",
    f"{PC_CONTROL_CALLBACK_PREFIX}mute": "volumemute",
    f"{PC_CONTROL_CALLBACK_PREFIX}stop": "stop",

    f"{PC_CONTROL_CALLBACK_PREFIX}seek_bwd": "left",

    f"{PC_CONTROL_CALLBACK_PREFIX}seek_fwd": "right",
}


def set_system_volume(level_percent: int) -> bool:
    if not PYCAW_AVAILABLE:
        logger.error("pycaw library not available. Cannot set system volume.")
        return False
    if not 0 <= level_percent <= 100:
        logger.error(f"Volume % out of range: {level_percent}")
        return False
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))

        level_scalar = level_percent / 100.0
        volume.SetMasterVolumeLevelScalar(level_scalar, None)
        logger.info(f"PC Volume set to {level_percent}% using pycaw.")
        return True
    except Exception as e:
        logger.error(f"Failed to set PC volume using pycaw: {e}")
        return False


async def display_media_sound_controls_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    is_primary_admin_check = app_config_holder.is_primary_admin(str(chat_id))

    if query:
        await query.answer()

    if not is_primary_admin_check:
        logger.warning(
            f"PC media controls attempt by non-primary admin {chat_id}.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied. PC Media Controls are for administrators.", parse_mode=None)
        return

    if not app_config_holder.is_pc_control_enabled():
        logger.info(
            f"PC media controls menu request by {chat_id}, but PC control feature is disabled.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ PC Control features are currently disabled.", parse_mode=None)
        return

    keyboard = [
        [
            InlineKeyboardButton(
                "⏮️ Prev", callback_data=f"{PC_CONTROL_CALLBACK_PREFIX}prev"),
            InlineKeyboardButton(
                "⏯️ Play/Pause", callback_data=f"{PC_CONTROL_CALLBACK_PREFIX}playpause"),
            InlineKeyboardButton(
                "⏭️ Next", callback_data=f"{PC_CONTROL_CALLBACK_PREFIX}next")
        ],
        [
            InlineKeyboardButton(
                "⏪ Seek", callback_data=f"{PC_CONTROL_CALLBACK_PREFIX}seek_bwd"),
            InlineKeyboardButton(
                "⏹️ Stop", callback_data=f"{PC_CONTROL_CALLBACK_PREFIX}stop"),
            InlineKeyboardButton(
                "⏩ Seek", callback_data=f"{PC_CONTROL_CALLBACK_PREFIX}seek_fwd")
        ]
    ]
    if PYCAW_AVAILABLE:
        keyboard.extend([
            [
                InlineKeyboardButton(
                    "Vol: 25%", callback_data=f"{PC_CONTROL_CALLBACK_PREFIX}vol25"),
                InlineKeyboardButton(
                    "Vol: 50%", callback_data=f"{PC_CONTROL_CALLBACK_PREFIX}vol50"),
                InlineKeyboardButton(
                    "Vol: 75%", callback_data=f"{PC_CONTROL_CALLBACK_PREFIX}vol75"),
                InlineKeyboardButton(
                    "Vol: 100%", callback_data=f"{PC_CONTROL_CALLBACK_PREFIX}vol100")
            ]
        ])
        keyboard.append([InlineKeyboardButton("🔇 Mute Toggle",
                                              callback_data=f"{PC_CONTROL_CALLBACK_PREFIX}mute")])
    else:
        keyboard.append([InlineKeyboardButton(
            "🔇 Mute Toggle (pyautogui)", callback_data=f"{PC_CONTROL_CALLBACK_PREFIX}mute")])
        keyboard.append([InlineKeyboardButton("(Advanced Volume requires pycaw)",
                        callback_data=f"{PC_CONTROL_CALLBACK_PREFIX}no_op_info")])

    keyboard.append([InlineKeyboardButton("🔙 Back to PC Controls",
                    callback_data=CallbackData.CMD_PC_CONTROL_ROOT.value)])
    reply_markup = InlineKeyboardMarkup(keyboard)

    menu_message_id = load_menu_message_id(str(chat_id))
    if not menu_message_id and context.bot_data:
        menu_message_id = context.bot_data.get(
            f"main_menu_message_id_{chat_id}")

    escaped_menu_title_for_display = escape_md_v2(PC_MEDIA_SOUND_MENU_TEXT_RAW)

    if menu_message_id:
        try:
            current_content_key = f"menu_message_content_{chat_id}_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (
                escaped_menu_title_for_display, reply_markup.to_json())

            if old_content_tuple != new_content_tuple:
                await context.bot.edit_message_text(
                    chat_id=chat_id, message_id=menu_message_id,
                    text=escaped_menu_title_for_display, reply_markup=reply_markup, parse_mode="MarkdownV2"
                )
                context.bot_data[current_content_key] = new_content_tuple
            await send_or_edit_universal_status_message(context.bot, chat_id, "Media & Sound controls displayed.", parse_mode=None)
        except Exception as e:
            logger.error(
                f"Error editing message for media/sound controls: {e}", exc_info=True)

            await display_pc_control_categories_menu(update, context)
    else:
        logger.error("Cannot find menu_message_id for media/sound controls.")
        await display_pc_control_categories_menu(update, context)


async def handle_media_sound_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    callback_data = query.data

    chat_id_for_status_obj = query.message.chat if query.message else update.effective_chat
    if not chat_id_for_status_obj:
        logger.error(
            "Could not determine chat_id in handle_media_sound_action")
        await query.answer("Error: Could not process action.", show_alert=True)
        return
    chat_id_for_status = chat_id_for_status_obj.id

    is_primary_admin_check = app_config_holder.is_primary_admin(
        str(chat_id_for_status))

    if not is_primary_admin_check:
        logger.warning(
            f"PC media action attempt by non-primary admin {chat_id_for_status}.")
        await query.answer("Access Denied.", show_alert=True)
        return

    if not app_config_holder.is_pc_control_enabled():
        logger.info(
            f"PC media action by {chat_id_for_status}, but PC control feature is disabled.")
        await query.answer("PC Control features are currently disabled.", show_alert=True)
        return

    if callback_data == f"{PC_CONTROL_CALLBACK_PREFIX}no_op_info":
        await query.answer("Advanced volume controls require the 'pycaw' library to be installed on the bot's host machine.", show_alert=True)
        return

    if callback_data.startswith(f"{PC_CONTROL_CALLBACK_PREFIX}vol"):
        await query.answer()
        try:
            level_str = callback_data.replace(
                f"{PC_CONTROL_CALLBACK_PREFIX}vol", "")
            level_percent = int(level_str)
            success = set_system_volume(level_percent)
            status_msg = f"PC Volume set to {level_percent}%" if success else "PC Volume error (pycaw missing or error)"
            if not PYCAW_AVAILABLE and success is False:
                status_msg = "⚠️ PC Volume control requires 'pycaw' library."
            await send_or_edit_universal_status_message(context.bot, chat_id_for_status, status_msg, parse_mode=None)
        except ValueError:
            await send_or_edit_universal_status_message(context.bot, chat_id_for_status, "Invalid volume value.", parse_mode=None)
        except Exception as e:
            logger.error(f"Error setting volume via callback: {e}")
            await send_or_edit_universal_status_message(context.bot, chat_id_for_status, "Error setting volume.", parse_mode=None)
        return

    py_action = MEDIA_ACTION_MAP.get(callback_data)
    if py_action:
        await query.answer()
        try:
            pyautogui.press(py_action)
            logger.info(
                f"Executed pyautogui.press('{py_action}') for PC control from user {chat_id_for_status}.")
            action_display_name = py_action.capitalize()
            if py_action == "playpause":
                action_display_name = "Play/Pause"
            elif py_action == "prevtrack":
                action_display_name = "Previous Track"
            elif py_action == "nexttrack":
                action_display_name = "Next Track"
            elif py_action == "volumemute":
                action_display_name = "Volume Mute Toggle"
            await send_or_edit_universal_status_message(context.bot, chat_id_for_status, f"{action_display_name} command sent to PC.", parse_mode=None)
        except NameError:
            logger.error(
                "pyautogui not available. Cannot execute media key press.")
            await send_or_edit_universal_status_message(context.bot, chat_id_for_status, "Error: pyautogui library missing for media keys.", parse_mode=None)
        except Exception as e:
            logger.error(
                f"PyAutoGUI error for PC action '{py_action}': {e}", exc_info=True)
            await send_or_edit_universal_status_message(context.bot, chat_id_for_status, f"Error sending '{py_action}' command.", parse_mode=None)
        return

    logger.warning(f"Unhandled media/sound callback: {callback_data}")
    await query.answer("Unknown media/sound command.")
