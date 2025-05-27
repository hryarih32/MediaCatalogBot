
import logging
import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

from telegram.ext import ContextTypes, Application

import src.app.app_config_holder as app_config_holder
from src.bot.bot_initialization import (
    load_menu_message_id,
    send_or_edit_universal_status_message,
    show_or_edit_main_menu
)
from src.bot.bot_callback_data import CallbackData
from .menu_handler_pc_root import display_pc_control_categories_menu

from src.app.app_lifecycle import _bot_application_instance_for_shutdown as global_app_instance
from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)

CONFIRMATION_WINDOW_SECONDS = 30
POWER_ACTION_DELAY_SECONDS = 15

PC_CONTROL_CALLBACK_PREFIX = "cb_pc_"


def get_job_queue_from_context_or_global(context: ContextTypes.DEFAULT_TYPE):
    if hasattr(context, 'application') and context.application and context.application.job_queue:
        return context.application.job_queue
    if global_app_instance and global_app_instance.job_queue:
        logger.warning(
            "Falling back to global_app_instance for job_queue in PC power controls.")
        return global_app_instance.job_queue
    logger.error(
        "Job queue not found in context.application or global_app_instance for PC power!")
    return None


async def display_system_power_controls_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_role = app_config_holder.get_user_role(str(chat_id))

    if query:
        await query.answer()

    if user_role != app_config_holder.ROLE_ADMIN:
        logger.warning(
            f"PC power controls attempt by non-admin {chat_id} (Role: {user_role}).")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied. PC Power Controls are for administrators.", parse_mode=None)
        return

    if not app_config_holder.is_pc_control_enabled():
        logger.info(
            f"PC power controls menu request by {chat_id}, but PC control feature is disabled.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ PC Control features are currently disabled.", parse_mode=None)
        return

    keyboard = [
        [InlineKeyboardButton(
            "🔴 SHUTDOWN", callback_data=f"{PC_CONTROL_CALLBACK_PREFIX}shutdown")],
        [InlineKeyboardButton(
            "🔄 RESTART", callback_data=f"{PC_CONTROL_CALLBACK_PREFIX}restart")],
        [InlineKeyboardButton(
            "🔙 Back to PC Controls", callback_data=CallbackData.CMD_PC_CONTROL_ROOT.value)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_message_id = load_menu_message_id(str(chat_id))
    if not menu_message_id and context.bot_data:
        menu_message_id = context.bot_data.get(
            f"main_menu_message_id_{chat_id}")

    final_menu_text_md2 = (
        f"🔌 *PC System Power Controls*\n\n"
        f"⚠️ *Warning:* Shutdown/Restart require confirmation within "
        f"{CONFIRMATION_WINDOW_SECONDS} seconds\\."
    )

    if menu_message_id:
        try:
            current_content_key = f"menu_message_content_{chat_id}_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (
                final_menu_text_md2, reply_markup.to_json())

            if old_content_tuple != new_content_tuple:
                await context.bot.edit_message_text(
                    chat_id=chat_id, message_id=menu_message_id,
                    text=final_menu_text_md2, reply_markup=reply_markup, parse_mode="MarkdownV2"
                )
                context.bot_data[current_content_key] = new_content_tuple
            await send_or_edit_universal_status_message(context.bot, chat_id, "System Power controls displayed. Use with caution.", parse_mode=None)
        except Exception as e:
            logger.error(
                f"Error editing message for system power controls: {e}", exc_info=True)

            await display_pc_control_categories_menu(update, context)
    else:
        logger.error("Cannot find menu_message_id for system power controls.")
        await display_pc_control_categories_menu(update, context)


async def clear_pending_pc_power_action_job(context: ContextTypes.DEFAULT_TYPE) -> None:

    if not context.job or not context.job.data or not context.job.chat_id:
        logger.error(
            "clear_pending_pc_power_action_job called with invalid job context.")
        return

    chat_id = context.job.chat_id
    action_cleared = False
    pending_action_name = context.job.data.get("action_name", "unknown")

    if 'pc_pending_power_action' in context.chat_data and context.chat_data['pc_pending_power_action'] == pending_action_name:
        context.chat_data.pop('pc_pending_power_action')
        action_cleared = True
    if 'pc_pending_power_time' in context.chat_data:
        context.chat_data.pop('pc_pending_power_time')

    if action_cleared:
        logger.info(
            f"Timeout reached for PC pending power action '{pending_action_name}' in chat {chat_id}. State cleared.")
        await send_or_edit_universal_status_message(context.bot, chat_id, f"PC {pending_action_name.upper()} confirmation timed out.", parse_mode=None)


async def execute_actual_power_off_action_job(context: ContextTypes.DEFAULT_TYPE):
    if not context.job or not context.job.data:
        logger.error(
            "execute_actual_power_off_action_job called with invalid job context.")
        return

    job_data = context.job.data
    command_to_run = job_data.get("command")
    action_type = job_data.get("action_type", "action")

    chat_id = job_data.get("chat_id")

    if command_to_run:
        logger.warning(
            f"Executing PC power action '{action_type}' via job: {command_to_run} for chat_id {chat_id}")
        try:
            if chat_id:
                final_exec_message = f"✅ PC {action_type.upper()} command sent to OS. This may take a moment."

                await context.bot.send_message(chat_id=chat_id, text=final_exec_message)
            os.system(command_to_run)
        except Exception as e:
            logger.error(
                f"Exception during scheduled PC power action '{action_type}': {e}", exc_info=True)
            if chat_id:
                await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Error executing PC {action_type.upper()}: {e}")
    else:
        logger.error(
            f"execute_actual_power_off_action_job called without a command for action '{action_type}'.")


async def handle_power_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    chat_id_for_status_obj = query.message.chat if query.message else update.effective_chat
    if not chat_id_for_status_obj:
        logger.error("Could not determine chat_id in handle_power_action")
        await query.answer("Error: Could not process action.", show_alert=True)
        return
    chat_id = chat_id_for_status_obj.id

    user_role = app_config_holder.get_user_role(str(chat_id))
    await query.answer()

    if user_role != app_config_holder.ROLE_ADMIN:
        logger.warning(
            f"PC power action attempt by non-admin {chat_id} (Role: {user_role}).")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Access Denied for power action.", parse_mode=None)
        return

    if not app_config_holder.is_pc_control_enabled():
        logger.info(
            f"PC power action by {chat_id}, but PC control feature is disabled.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "ℹ️ PC Control features are currently disabled.", parse_mode=None)
        return

    job_queue = get_job_queue_from_context_or_global(context)
    if not job_queue:
        logger.error(
            "Job queue unavailable in handle_power_action for PC power command.")
        await send_or_edit_universal_status_message(context.bot, chat_id, "⚠️ Error: System component (JobQueue) unavailable for power action.", parse_mode=None)
        return

    callback_data = query.data
    current_time = time.time()
    pending_action = context.chat_data.get('pc_pending_power_action')
    pending_time = context.chat_data.get('pc_pending_power_time', 0)

    is_shutdown_press = callback_data == f"{PC_CONTROL_CALLBACK_PREFIX}shutdown"
    is_restart_press = callback_data == f"{PC_CONTROL_CALLBACK_PREFIX}restart"
    requested_action_type = 'shutdown' if is_shutdown_press else 'restart' if is_restart_press else None

    if not requested_action_type:
        logger.warning(
            f"handle_power_action called with non-power callback: {callback_data}")
        return

    if pending_action == requested_action_type:
        if current_time - pending_time <= CONFIRMATION_WINDOW_SECONDS:
            action_name_upper = pending_action.upper()
            action_verb_future = "be SHUT DOWN" if pending_action == 'shutdown' else "be RESTARTED"
            logger.warning(
                f"CONFIRMED: PC {action_name_upper} sequence initiated for chat {chat_id}!")

            command_to_run = ""

            actual_os_delay = POWER_ACTION_DELAY_SECONDS

            bot_job_schedule_delay = max(
                0.1, actual_os_delay - 2) if actual_os_delay > 2 else 0.1

            if os.name == 'nt':
                command_to_run = f"shutdown /{('s' if pending_action == 'shutdown' else 'r')} /t {actual_os_delay} /f"
            elif os.name == 'posix':

                if actual_os_delay < 60:
                    command_to_run = f"sleep {actual_os_delay} && sudo shutdown -{('h' if pending_action == 'shutdown' else 'r')} now"
                    bot_job_schedule_delay = 0.1
                else:
                    delay_minutes_for_os_shutdown = int(
                        round(actual_os_delay / 60.0))
                    command_to_run = f"sudo shutdown -{('h' if pending_action == 'shutdown' else 'r')} +{delay_minutes_for_os_shutdown}"

                    bot_job_schedule_delay = 0.1
            else:
                logger.error(f"Unsupported OS for power actions: {os.name}")
                await send_or_edit_universal_status_message(context.bot, chat_id, f"⚠️ Power actions not supported on your OS ({os.name}).", parse_mode=None)
                context.chat_data.pop('pc_pending_power_action', None)
                context.chat_data.pop('pc_pending_power_time', None)
                await display_system_power_controls_menu(update, context)
                return

            countdown_message_text = f"✅ PC will {action_verb_future} in approx. {actual_os_delay} seconds..."
            await send_or_edit_universal_status_message(context.bot, chat_id, countdown_message_text, parse_mode=None)

            context.chat_data.pop('pc_pending_power_action', None)
            context.chat_data.pop('pc_pending_power_time', None)
            confirmation_timeout_jobs = job_queue.get_jobs_by_name(
                f"clear_pending_pc_power_{chat_id}")
            for job in confirmation_timeout_jobs:
                job.schedule_removal()

            job_queue.run_once(
                execute_actual_power_off_action_job,
                bot_job_schedule_delay,
                data={"command": command_to_run,
                      "action_type": pending_action, "chat_id": chat_id},

                name=f"exec_pc_power_{pending_action}_{chat_id}_{int(time.time())}"
            )

            await show_or_edit_main_menu(str(chat_id), context)
            return
        else:
            logger.info(
                f"PC Confirmation attempt for '{pending_action}' by chat {chat_id} outside timeout window.")
            await send_or_edit_universal_status_message(context.bot, chat_id, f"Confirmation time for PC {pending_action.upper()} expired. Please press the button again to re-initiate.", parse_mode=None)
            context.chat_data.pop('pc_pending_power_action', None)
            context.chat_data.pop('pc_pending_power_time', None)

            await display_system_power_controls_menu(update, context)
            return
    elif pending_action and pending_action != requested_action_type:
        logger.info(
            f"Different PC power button '{requested_action_type}' pressed by chat {chat_id} while '{pending_action}' was pending. Clearing old.")
        old_pending_action_name = context.chat_data.pop(
            'pc_pending_power_action', 'previous action')
        context.chat_data.pop('pc_pending_power_time', None)

        confirmation_timeout_jobs = job_queue.get_jobs_by_name(
            f"clear_pending_pc_power_{chat_id}")
        for job in confirmation_timeout_jobs:
            job.schedule_removal()
        await send_or_edit_universal_status_message(context.bot, chat_id, f"Cancelled pending PC {old_pending_action_name.upper()}.", parse_mode=None)

        pending_action = None

    if not pending_action:
        action_name_upper = requested_action_type.upper()
        logger.info(
            f"Initiating PC confirmation for {action_name_upper} for chat {chat_id}")
        context.chat_data['pc_pending_power_action'] = requested_action_type
        context.chat_data['pc_pending_power_time'] = current_time

        old_confirm_jobs = job_queue.get_jobs_by_name(
            f"clear_pending_pc_power_{chat_id}_{requested_action_type}")
        for old_job in old_confirm_jobs:
            old_job.schedule_removal()

        job_queue.run_once(
            clear_pending_pc_power_action_job,
            CONFIRMATION_WINDOW_SECONDS,
            chat_id=chat_id,

            name=f"clear_pending_pc_power_{chat_id}_{requested_action_type}",
            data={"action_name": requested_action_type}
        )
        await send_or_edit_universal_status_message(context.bot, chat_id, f"Press PC {action_name_upper} again within {CONFIRMATION_WINDOW_SECONDS}s to confirm.", parse_mode=None)
        return
