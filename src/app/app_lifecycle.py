import logging
import os
import threading
from telegram.ext import CallbackContext, Application

from .app_file_utils import get_data_storage_path, get_config_file_path
from src.config.config_manager import _load_config_module_from_path, validate_config_values
from .app_service_initializer import initialize_services_with_config
from src.bot.bot_initialization import send_or_edit_universal_status_message, show_or_edit_main_menu, set_bot_commands
import src.app.app_config_holder as app_config_holder
import sys
from .app_config_ui import run_config_ui
from src.config.config_definitions import ALL_USER_CONFIG_KEYS, CONFIG_FIELD_DEFINITIONS, LOG_LEVEL_OPTIONS
from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)

ui_thread = None
_app_for_ui_reload = None
_bot_application_instance_for_shutdown = None


def set_bot_application_instance(app_instance: Application):
    global _bot_application_instance_for_shutdown
    _bot_application_instance_for_shutdown = app_instance


def _run_tkinter_ui_thread_target(config_path_in_data, initial_vals):
    global _app_for_ui_reload
    logger.info(
        f"Config UI thread started for config path: {config_path_in_data}")
    try:

        ui_result = run_config_ui(config_path_in_data, initial_vals)
        logger.info(f"Config UI closed. Result: {ui_result}")
        if ui_result["saved"] and _app_for_ui_reload and _app_for_ui_reload.job_queue:
            job_data_for_reload = {
                'config_file_path': config_path_in_data,
                'log_level_changed_by_ui': ui_result.get("log_level_changed", False)
            }
            _app_for_ui_reload.job_queue.run_once(
                _handle_post_ui_config_reload, when=0.1, data=job_data_for_reload, name="PostUIConfigReload")
            logger.info("Scheduled _handle_post_ui_config_reload.")
    except Exception as e:
        logger.error(f"Exception in Tkinter UI thread: {e}", exc_info=True)
        if _app_for_ui_reload and _app_for_ui_reload.job_queue and app_config_holder.get_chat_id_str():
            _app_for_ui_reload.job_queue.run_once(lambda ctx: send_or_edit_universal_status_message(ctx.bot, int(
                app_config_holder.get_chat_id_str()), "🚨 Error in Settings UI. Check logs.", parse_mode=None), when=0, name="UIErrorNotify")
    finally:
        logger.info("Config UI thread finished.")


async def _handle_post_ui_config_reload(context: CallbackContext):
    job_data = context.job.data

    config_file_path_from_job = job_data.get('config_file_path')
    log_level_changed_by_ui = job_data.get('log_level_changed_by_ui', False)

    application = context.application
    logger.info(
        f"Handling post-UI configuration reload for: {config_file_path_from_job}")
    previous_chat_id_str = app_config_holder.get_chat_id_str()
    status_message_parts_raw = []

    try:

        reloaded_config_module = _load_config_module_from_path(
            config_file_path_from_job)

        if validate_config_values(reloaded_config_module, config_file_path_from_job):
            initialize_services_with_config(reloaded_config_module)
            new_admin_chat_id_str = app_config_holder.get_chat_id_str()
            target_chat_id_for_status = new_admin_chat_id_str or previous_chat_id_str
            status_message_parts_raw.append(
                "⚙️ Settings reloaded successfully!")
            if log_level_changed_by_ui:
                status_message_parts_raw.append(
                    "⚠️ Log level changed. Please restart the bot for this to take full effect.")
            if target_chat_id_for_status:
                logger.info(
                    f"Post-UI reload: Updating main menu for chat_id: {target_chat_id_for_status} (force_send_new=False).")
                await show_or_edit_main_menu(target_chat_id_for_status, application, force_send_new=False)
                await set_bot_commands(application)
            if target_chat_id_for_status and status_message_parts_raw:
                final_status_msg_raw = "\n".join(status_message_parts_raw)
                logger.info(
                    f"Post-UI reload: Sending new universal status to chat_id: {target_chat_id_for_status} (force_send_new=True).")
                await send_or_edit_universal_status_message(
                    application.bot, int(target_chat_id_for_status),
                    escape_md_v2(final_status_msg_raw), parse_mode="MarkdownV2", force_send_new=True
                )
            if previous_chat_id_str and not new_admin_chat_id_str:
                logger.warning(
                    "Admin CHAT_ID cleared/invalidated after config reload.")
        else:
            logger.error(
                f"Reloaded configuration is invalid: {config_file_path_from_job}")
            if previous_chat_id_str:
                await send_or_edit_universal_status_message(application.bot, int(previous_chat_id_str), "⚠️ Error: Reloaded settings are invalid.", parse_mode=None)
    except Exception as e:
        logger.error(
            f"Critical error reloading config after UI save from {config_file_path_from_job}: {e}", exc_info=True)
        if previous_chat_id_str:
            await send_or_edit_universal_status_message(application.bot, int(previous_chat_id_str), "🚨 Critical error reloading settings.", parse_mode=None)
            await show_or_edit_main_menu(previous_chat_id_str, application, force_send_new=True)


async def trigger_config_ui_from_bot(application: Application):
    global ui_thread, _app_for_ui_reload
    _app_for_ui_reload = application
    admin_chat_id_for_message = app_config_holder.get_chat_id_str()

    if ui_thread and ui_thread.is_alive():
        if admin_chat_id_for_message:
            await send_or_edit_universal_status_message(application.bot, int(admin_chat_id_for_message), "⚙️ Settings panel is already open.", parse_mode=None)
        return

    logger.info("Triggering Config UI from bot command...")

    config_file_path_for_ui = get_config_file_path()

    logger.info(
        f"Config UI will attempt to load/save from: {config_file_path_for_ui}")

    initial_values_for_ui = {}
    if os.path.exists(config_file_path_for_ui):
        try:

            temp_config_for_ui = _load_config_module_from_path(
                config_file_path_for_ui)
            for key_ in ALL_USER_CONFIG_KEYS:
                field_def = CONFIG_FIELD_DEFINITIONS.get(key_, {})
                default_val_for_key = field_def.get("default", "")
                if field_def.get("type") in ["checkbutton_in_frame_title", "checkbutton"]:
                    default_val_for_key = bool(default_val_for_key)
                elif field_def.get("type") == "combobox" and key_ == "LOG_LEVEL":
                    default_val_for_key = field_def.get("default", "INFO")
                current_val = getattr(temp_config_for_ui,
                                      key_, default_val_for_key)
                if field_def.get("type") in ["checkbutton_in_frame_title", "checkbutton"]:
                    initial_values_for_ui[key_] = bool(current_val)
                elif field_def.get("type") == "combobox" and key_ == "LOG_LEVEL":
                    initial_values_for_ui[key_] = str(current_val).upper() if str(
                        current_val).upper() in LOG_LEVEL_OPTIONS else default_val_for_key
                else:
                    initial_values_for_ui[key_] = current_val
        except Exception as e:
            logger.warning(
                f"Could not load initial values for UI from '{config_file_path_for_ui}': {e}. Using defaults.")

            for key_ in ALL_USER_CONFIG_KEYS:
                field_def = CONFIG_FIELD_DEFINITIONS.get(key_, {})
                default_val = field_def.get("default", "")
                initial_values_for_ui[key_] = bool(default_val) if field_def.get("type") in ["checkbutton_in_frame_title", "checkbutton"] else (
                    field_def.get("default", "INFO") if field_def.get("type") == "combobox" and key_ == "LOG_LEVEL" else default_val)
    else:
        logger.info(
            f"No config file found at '{config_file_path_for_ui}', populating UI with defaults.")
        for key_ in ALL_USER_CONFIG_KEYS:
            field_def = CONFIG_FIELD_DEFINITIONS.get(key_, {})
            default_val = field_def.get("default", "")
            initial_values_for_ui[key_] = bool(default_val) if field_def.get("type") in ["checkbutton_in_frame_title", "checkbutton"] else (
                field_def.get("default", "INFO") if field_def.get("type") == "combobox" and key_ == "LOG_LEVEL" else default_val)

    ui_thread = threading.Thread(target=_run_tkinter_ui_thread_target, args=(
        config_file_path_for_ui, initial_values_for_ui), daemon=True)
    ui_thread.start()


def sigint_handler_sync(signum, frame):
    global _bot_application_instance_for_shutdown
    logger.info(f"SIGINT ({signum}) received. Scheduling async shutdown.")
    if _bot_application_instance_for_shutdown and hasattr(_bot_application_instance_for_shutdown, 'job_queue'):
        _bot_application_instance_for_shutdown.job_queue.run_once(
            actual_shutdown_task, 0, name="AsyncShutdownSIGINT")
    else:
        logger.warning(
            "Bot app instance/job_queue not available for graceful shutdown. Exiting.")
        sys.exit(0)


async def actual_shutdown_task(context: CallbackContext):
    logger.info("Async shutdown task running...")
    if context.application and context.application.persistence:
        try:
            logger.info("Flushing persistence...")
            context.application.persistence.flush()
            logger.info("Persistence flushed.")
        except Exception as flush_e:
            logger.error(
                f"Error flushing persistence: {flush_e}", exc_info=True)
    logger.info("Async shutdown task finished.")
