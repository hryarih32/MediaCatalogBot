import logging
import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, Application


import src.app.app_config_holder as app_config_holder
from src.bot.bot_initialization import (
    load_menu_message_id,
    send_or_edit_universal_status_message

)
from src.config.config_definitions import CallbackData
from .menu_handler_pc_root import display_pc_control_categories_menu
from src.app.app_lifecycle import _bot_application_instance_for_shutdown as global_app_instance
from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)

CONFIRMATION_WINDOW_SECONDS = 30
POWER_ACTION_DELAY_SECONDS = 15
PC_CONTROL_CALLBACK_PREFIX = "cb_pc_"

PC_SYSTEM_POWER_MENU_TEXT_RAW = (
    "🔌 *PC System Power Controls*\n\n"
    "⚠️ *Warning:* Shutdown/Restart require confirmation within "
    f"{CONFIRMATION_WINDOW_SECONDS} seconds."
)


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
    if query:
        await query.answer()
    chat_id = update.effective_chat.id
    admin_chat_id_str = app_config_holder.get_chat_id_str()

    keyboard = [
        [InlineKeyboardButton(
            "🔴 SHUTDOWN", callback_data=f"{PC_CONTROL_CALLBACK_PREFIX}shutdown")],
        [InlineKeyboardButton(
            "🔄 RESTART", callback_data=f"{PC_CONTROL_CALLBACK_PREFIX}restart")],
        [InlineKeyboardButton(
            "🔙 Back to PC Controls", callback_data=CallbackData.CMD_PC_CONTROL_ROOT.value)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_message_id = load_menu_message_id()
    if not menu_message_id and context.bot_data:
        menu_message_id = context.bot_data.get("main_menu_message_id")

    escaped_menu_title_for_display = escape_md_v2(
        f"🔌 *PC System Power Controls*\n\n"
        f"⚠️ *Warning:* Shutdown/Restart require confirmation within "
        f"{CONFIRMATION_WINDOW_SECONDS} seconds\\."
    )

    if menu_message_id:
        try:
            current_content_key = f"menu_message_content_{menu_message_id}"
            old_content_tuple = context.bot_data.get(current_content_key)
            new_content_tuple = (
                escaped_menu_title_for_display, reply_markup.to_json())

            if old_content_tuple != new_content_tuple:
                await context.bot.edit_message_text(
                    chat_id=chat_id, message_id=menu_message_id,
                    text=escaped_menu_title_for_display, reply_markup=reply_markup, parse_mode="MarkdownV2"
                )
                context.bot_data[current_content_key] = new_content_tuple
            await send_or_edit_universal_status_message(context.bot, chat_id, "System Power controls displayed. Use with caution.", parse_mode=None)
        except Exception as e:
            logger.error(
                f"Error editing message for system power controls: {e}", exc_info=True)
            if admin_chat_id_str:
                await display_pc_control_categories_menu(update, context)
    else:
        logger.error("Cannot find menu_message_id for system power controls.")
        if admin_chat_id_str:
            await display_pc_control_categories_menu(update, context)


async def clear_pending_pc_power_action_job(context: ContextTypes.DEFAULT_TYPE) -> None:
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
    job_data = context.job.data
    command_to_run = job_data.get("command")
    action_type = job_data.get("action_type", "action")
    chat_id = job_data.get("chat_id")

    if command_to_run:
        logger.warning(
            f"Executing PC power action '{action_type}' via job: {command_to_run}")
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
    await query.answer()

    job_queue = get_job_queue_from_context_or_global(context)
    if not job_queue:
        logger.error("Job queue unavailable in handle_power_action.")
        if query.message:
            await send_or_edit_universal_status_message(context.bot, query.message.chat.id, "⚠️ Error: System component (JobQueue) unavailable for power action.", parse_mode=None)
        return

    callback_data = query.data
    chat_id = query.message.chat.id if query.message else update.effective_chat.id
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
                f"CONFIRMED: PC {action_name_upper} sequence initiated!")

            command_to_run = ""
            actual_os_delay = POWER_ACTION_DELAY_SECONDS

            bot_job_schedule_delay = max(
                1, actual_os_delay - 2) if actual_os_delay > 2 else 0.1

            if os.name == 'nt':
                command_to_run = f"shutdown /{('s' if pending_action == 'shutdown' else 'r')} /t {actual_os_delay} /f"
            elif os.name == 'posix':
                delay_minutes_for_os_shutdown = int(actual_os_delay / 60)
                if delay_minutes_for_os_shutdown > 0:
                    command_to_run = f"sudo shutdown -{('h' if pending_action == 'shutdown' else 'r')} +{delay_minutes_for_os_shutdown}"
                else:
                    command_to_run = f"sleep {actual_os_delay} && sudo shutdown -{('h' if pending_action == 'shutdown' else 'r')} now"
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
                name=f"exec_pc_power_{pending_action}_{chat_id}"
            )
            admin_chat_id_str_main = app_config_holder.get_chat_id_str()
            if admin_chat_id_str_main:
                from src.bot.bot_initialization import show_or_edit_main_menu
                await show_or_edit_main_menu(admin_chat_id_str_main, context)
            return
        else:
            logger.info(
                f"PC Confirmation attempt for '{pending_action}' outside timeout window.")
            await send_or_edit_universal_status_message(context.bot, chat_id, f"Confirmation time for PC {pending_action.upper()} expired. Please press the button again to re-initiate.", parse_mode=None)
            context.chat_data.pop('pc_pending_power_action', None)
            context.chat_data.pop('pc_pending_power_time', None)
            await display_system_power_controls_menu(update, context)
            return
    elif pending_action and pending_action != requested_action_type:
        logger.info(
            f"Different PC power button '{requested_action_type}' pressed while '{pending_action}' was pending. Clearing old pending action.")
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
        logger.info(f"Initiating PC confirmation for {action_name_upper}")
        context.chat_data['pc_pending_power_action'] = requested_action_type
        context.chat_data['pc_pending_power_time'] = current_time
        job_queue.run_once(
            clear_pending_pc_power_action_job, CONFIRMATION_WINDOW_SECONDS,
            chat_id=chat_id, name=f"clear_pending_pc_power_{chat_id}",
            data={"action_name": requested_action_type}
        )
        await send_or_edit_universal_status_message(context.bot, chat_id, f"Press PC {action_name_upper} again within {CONFIRMATION_WINDOW_SECONDS}s to confirm.", parse_mode=None)
        return
