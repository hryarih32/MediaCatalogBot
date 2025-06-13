
import logging
import os
import threading

from telegram.ext import CallbackContext, Application

from .app_file_utils import get_config_file_path
from src.config.config_manager import _load_config_module_from_path, validate_config_values
from .app_service_initializer import initialize_services_with_config
from src.bot.bot_initialization import send_or_edit_universal_status_message, show_or_edit_main_menu, set_bot_commands
import src.app.app_config_holder as app_config_holder

import src.app.user_manager as user_manager
from src.app.app_api_status_manager import update_all_api_statuses_once  # New Import
import sys
from .app_config_ui import run_config_ui
from src.config.config_definitions import ALL_USER_CONFIG_KEYS, CONFIG_FIELD_DEFINITIONS, LOG_LEVEL_OPTIONS
from src.bot.bot_text_utils import escape_md_v2

logger = logging.getLogger(__name__)

ui_thread = None
_app_for_ui_reload: Application | None = None
_bot_application_instance_for_shutdown: Application | None = None


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

        if ui_result.get("saved") and _app_for_ui_reload and _app_for_ui_reload.job_queue:
            job_data_for_reload = {
                'config_file_path': config_path_in_data,
                'log_level_changed_by_ui': ui_result.get("log_level_changed", False),

                'affected_users_for_refresh': ui_result.get("affected_users_for_refresh", [])
            }
            _app_for_ui_reload.job_queue.run_once(
                _handle_post_ui_config_reload,
                when=0.2,
                data=job_data_for_reload,
                name="PostUIConfigReload"
            )
            logger.info(
                f"Scheduled _handle_post_ui_config_reload with affected_users: {job_data_for_reload['affected_users_for_refresh']}.")
    except Exception as e:
        logger.error(f"Exception in Tkinter UI thread: {e}", exc_info=True)
        if _app_for_ui_reload and _app_for_ui_reload.job_queue and app_config_holder.get_chat_id_str():
            primary_admin_chat_id = app_config_holder.get_chat_id_str()
            if primary_admin_chat_id:
                _app_for_ui_reload.job_queue.run_once(
                    lambda ctx: send_or_edit_universal_status_message(
                        ctx.bot,

                        int(primary_admin_chat_id),
                        "🚨 Error in Settings UI. Check logs.",
                        parse_mode=None
                    ),
                    when=0,
                    name="UIErrorNotify"
                )
    finally:
        logger.info("Config UI thread finished.")


async def _handle_post_ui_config_reload(context: CallbackContext):
    if not context.job or not context.job.data:
        logger.error("_handle_post_ui_config_reload called without job data.")
        return

    job_data = context.job.data
    config_file_path_from_job = job_data.get('config_file_path')
    log_level_changed_by_ui = job_data.get('log_level_changed_by_ui', False)
    affected_users_for_refresh = job_data.get(
        'affected_users_for_refresh', [])

    application = context.application
    logger.info(
        f"Handling post-UI configuration reload for: {config_file_path_from_job}")

    previous_primary_admin_chat_id_str = app_config_holder.get_chat_id_str()
    status_message_parts_raw = []

    try:
        reloaded_config_module = _load_config_module_from_path(
            config_file_path_from_job)
        if validate_config_values(reloaded_config_module, config_file_path_from_job):

            initialize_services_with_config(reloaded_config_module)

            user_manager.ensure_initial_bot_state()
            logger.info(
                "User state re-initialized from user_manager after config reload.")

            new_primary_admin_chat_id_str = app_config_holder.get_chat_id_str()

            # Refresh API statuses in bot_data after config reload
            await update_all_api_statuses_once(application.bot_data)

            status_message_parts_raw.append(
                "⚙️ Settings reloaded successfully!")
            if log_level_changed_by_ui:
                status_message_parts_raw.append(
                    "⚠️ Log level changed. Please restart the bot for this to take full effect.")

            admin_to_refresh_menu = new_primary_admin_chat_id_str or previous_primary_admin_chat_id_str
            if admin_to_refresh_menu:
                logger.info(
                    f"Post-UI reload: Updating main menu for primary admin: {admin_to_refresh_menu}.")

                await show_or_edit_main_menu(admin_to_refresh_menu, application, force_send_new=True)

                await set_bot_commands(application)

                final_status_msg_raw = "\n".join(status_message_parts_raw)
                await send_or_edit_universal_status_message(
                    application.bot, int(admin_to_refresh_menu),
                    escape_md_v2(final_status_msg_raw), parse_mode="MarkdownV2", force_send_new=True
                )

            if affected_users_for_refresh:
                logger.info(
                    f"Processing menu/status refresh for affected users: {affected_users_for_refresh}")
                for user_chat_id_str in affected_users_for_refresh:
                    if user_chat_id_str == admin_to_refresh_menu:
                        continue
                    try:

                        current_role_for_user = user_manager.get_role_for_chat_id(
                            user_chat_id_str)

                        logger.info(
                            f"Scheduling immediate refresh for affected user: {user_chat_id_str} (New Role: {current_role_for_user})")

                        async def refresh_affected_user_job(job_context: CallbackContext):
                            target_user_id_str = job_context.job.data.get(
                                "target_user_id")
                            app_instance = job_context.application

                            logger.info(
                                f"Job: Refreshing main menu for affected user {target_user_id_str}.")
                            await show_or_edit_main_menu(str(target_user_id_str), app_instance, force_send_new=True)

                            status_for_affected = "Your access permissions or role has been updated by an administrator."
                            if user_manager.get_role_for_chat_id(target_user_id_str, force_reload_state=True) == app_config_holder.ROLE_UNKNOWN:
                                status_for_affected = "Your access to the bot has been revoked or changed."

                            await send_or_edit_universal_status_message(
                                app_instance.bot, int(target_user_id_str),
                                escape_md_v2(status_for_affected),
                                parse_mode="MarkdownV2", force_send_new=True
                            )

                        application.job_queue.run_once(
                            refresh_affected_user_job,
                            when=0.1,
                            data={"target_user_id": user_chat_id_str},

                            name=f"refresh_affected_user_{user_chat_id_str}_{os.urandom(4).hex()}"
                        )
                    except Exception as e_user_refresh:
                        logger.error(
                            f"Failed to schedule refresh for affected user {user_chat_id_str}: {e_user_refresh}", exc_info=True)

            if previous_primary_admin_chat_id_str and not new_primary_admin_chat_id_str:
                logger.warning(
                    "Primary Admin CHAT_ID was cleared/invalidated after config reload from GUI.")

        else:
            logger.error(
                f"Reloaded configuration from {config_file_path_from_job} is invalid.")
            if previous_primary_admin_chat_id_str:
                await send_or_edit_universal_status_message(
                    application.bot, int(previous_primary_admin_chat_id_str),
                    "⚠️ Error: Reloaded settings from GUI are invalid. Previous settings remain active. Please check config.py or use /settings again.",
                    parse_mode=None, force_send_new=True
                )

                await show_or_edit_main_menu(previous_primary_admin_chat_id_str, application, force_send_new=True)

    except Exception as e:
        logger.error(
            f"Critical error reloading config after UI save from {config_file_path_from_job}: {e}", exc_info=True)
        if previous_primary_admin_chat_id_str:
            await send_or_edit_universal_status_message(
                application.bot, int(previous_primary_admin_chat_id_str),
                "🚨 Critical error reloading settings after GUI save. Bot might be unstable. Previous settings attempted to be restored.",
                parse_mode=None, force_send_new=True
            )

            await show_or_edit_main_menu(previous_primary_admin_chat_id_str, application, force_send_new=True)


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
                f"Could not load initial values for UI from '{config_file_path_for_ui}': {e}. Using defaults from definitions.")
            for key_ in ALL_USER_CONFIG_KEYS:
                field_def = CONFIG_FIELD_DEFINITIONS.get(key_, {})
                default_val = field_def.get("default", "")
                initial_values_for_ui[key_] = bool(default_val) if field_def.get("type") in ["checkbutton_in_frame_title", "checkbutton"] else (
                    field_def.get("default", "INFO") if field_def.get("type") == "combobox" and key_ == "LOG_LEVEL" else default_val)
    else:
        logger.info(
            f"No config file found at '{config_file_path_for_ui}', populating UI with definition defaults.")
        for key_ in ALL_USER_CONFIG_KEYS:
            field_def = CONFIG_FIELD_DEFINITIONS.get(key_, {})
            default_val = field_def.get("default", "")
            initial_values_for_ui[key_] = bool(default_val) if field_def.get("type") in ["checkbutton_in_frame_title", "checkbutton"] else (
                field_def.get("default", "INFO") if field_def.get("type") == "combobox" and key_ == "LOG_LEVEL" else default_val)

    ui_thread = threading.Thread(target=_run_tkinter_ui_thread_target, args=(
        config_file_path_for_ui, initial_values_for_ui), daemon=True)
    ui_thread.start()
    if admin_chat_id_for_message:
        await send_or_edit_universal_status_message(application.bot, int(admin_chat_id_for_message), "⚙️ Attempting to open settings panel on the bot's host machine...", parse_mode=None)


def sigint_handler_sync(signum, frame):
    global _bot_application_instance_for_shutdown
    logger.info(f"SIGINT ({signum}) received. Scheduling async shutdown.")
    if _bot_application_instance_for_shutdown and hasattr(_bot_application_instance_for_shutdown, 'job_queue') and _bot_application_instance_for_shutdown.job_queue:
        _bot_application_instance_for_shutdown.job_queue.run_once(
            actual_shutdown_task, 0, name="AsyncShutdownSIGINT")
    else:
        logger.warning(
            "Bot app instance/job_queue not available for graceful shutdown during SIGINT. Exiting more directly.")
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
    logger.info("Async shutdown task finished. Bot should exit polling soon.")
