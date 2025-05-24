
import logging
import os
import sys
import signal
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, PicklePersistence, Application, JobQueue
from telegram.error import NetworkError, TimedOut

from src.app.app_lifecycle import (
    sigint_handler_sync,
    set_bot_application_instance,
)
from src.bot.bot_initialization import (
    set_bot_commands, show_or_edit_main_menu,
    send_or_edit_universal_status_message
)
from src.handlers.abdm import *
from src.bot.bot_telegram import setup_handlers
from src.app.app_setup import perform_initial_setup
from src.app import app_config_holder

logger = logging.getLogger(__name__)

MAX_STARTUP_RETRIES = 50
STARTUP_RETRY_DELAY = 30


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    project_version = app_config_holder.get_project_version()
    error_already_handled_by_startup_retry_logic = getattr(
        context, 'startup_error_retrying', False)
    log_level_for_error = logging.ERROR
    if isinstance(context.error, (NetworkError, TimedOut)):
        log_level_for_error = logging.DEBUG if error_already_handled_by_startup_retry_logic else logging.WARNING
    logger.log(log_level_for_error, msg=f"Version {project_version} - Exception in handler: {context.error}",
               exc_info=context.error if log_level_for_error >= logging.ERROR else None)
    admin_chat_id_str = app_config_holder.get_chat_id_str()
    if admin_chat_id_str and not error_already_handled_by_startup_retry_logic:
        try:
            chat_id = int(admin_chat_id_str)
            error_type_str = type(context.error).__name__
            error_details_str = str(context.error)
            plain_error_text = f"🚨 An error occurred: {error_type_str}\nDetail: {error_details_str}\nCheck bot logs."
            if len(plain_error_text) > 4096:
                plain_error_text = plain_error_text[:4093] + "..."
            await send_or_edit_universal_status_message(context.bot, chat_id, plain_error_text, parse_mode=None)
        except Exception as e_handler_ex:
            logger.critical(
                f"CRITICAL: Error in error_handler: {e_handler_ex}", exc_info=True)


async def post_init_tasks(application: Application) -> None:
    project_version = app_config_holder.get_project_version()
    logger.info(f"Version {project_version} - Post-init tasks started.")
    await set_bot_commands(application)
    admin_chat_id_str = app_config_holder.get_chat_id_str()
    if not admin_chat_id_str:
        logger.critical(
            f"Version {project_version} - Admin CHAT_ID not found in post_init.")
        raise RuntimeError("Admin CHAT_ID not configured.")
    admin_chat_id = int(admin_chat_id_str)
    logger.info(
        f"Post-init: Sending new main menu (force_send_new=True) for chat_id: {admin_chat_id}")
    menu_msg_id = await show_or_edit_main_menu(admin_chat_id_str, application, force_send_new=True)
    if not menu_msg_id:
        logger.error("Post-init: Failed to send main menu message.")
    else:
        logger.info(
            f"Post-init: Main menu sent/resent. Message ID: {menu_msg_id}")
    initial_status_text = "⏳ Media Bot is active. Awaiting commands..."
    enabled_features_count = sum([
        app_config_holder.is_plex_enabled(), app_config_holder.is_radarr_enabled(),
        app_config_holder.is_sonarr_enabled(), app_config_holder.is_pc_control_enabled(),
        any(app_config_holder.is_script_enabled(i) for i in range(1, 4))
    ])
    if enabled_features_count == 0:
        initial_status_text = "⚠️ No features enabled. Check /settings."
    logger.info(
        f"Post-init: Sending new universal status (force_send_new=True): {initial_status_text}")
    universal_msg_id = await send_or_edit_universal_status_message(
        application.bot, admin_chat_id, initial_status_text,
        parse_mode=None, force_send_new=True
    )
    if not universal_msg_id:
        logger.error(
            "Post-init: Failed to send initial universal status message.")
    else:
        logger.info(
            f"Post-init: Universal status sent/resent. Message ID: {universal_msg_id}")
    logger.info(
        f"Version {project_version} - Post-init tasks complete. Menu ID: {menu_msg_id}, Status ID: {universal_msg_id}")


def main():
    telegram_bot_token, current_data_path, project_version_loaded = perform_initial_setup()
    persistence_file = os.path.join(
        current_data_path, "mediabot_persistence.pickle")
    persistence = None
    try:
        persistence = PicklePersistence(filepath=persistence_file)
        logger.info(f"Using PicklePersistence: {persistence_file}")
    except Exception as e:
        logger.error(f"Failed to init PicklePersistence: {e}.", exc_info=True)
    application = None
    for attempt in range(MAX_STARTUP_RETRIES):
        temp_app_for_context = application if application else ApplicationBuilder(
        ).token(telegram_bot_token).build()
        context = ContextTypes.DEFAULT_TYPE(application=temp_app_for_context)
        context.startup_error_retrying = True
        try:
            logger.info(
                f"Building Telegram app (Attempt {attempt + 1}/{MAX_STARTUP_RETRIES})...")
            job_queue = JobQueue()
            builder = ApplicationBuilder().token(telegram_bot_token).job_queue(job_queue)
            if persistence:
                builder = builder.persistence(persistence)
            builder = builder.connect_timeout(
                30).read_timeout(30).write_timeout(30)
            application = builder.build()
            if not application.job_queue:
                logger.critical("JobQueue is None after application build!")
                raise RuntimeError("JobQueue initialization failed.")
            application.post_init = post_init_tasks
            set_bot_application_instance(application)
            logger.info("Application built.")
            break
        except (NetworkError, TimedOut) as ne:
            logger.warning(
                f"Startup Net/Timeout (Attempt {attempt + 1}): {ne}")
            if attempt + 1 == MAX_STARTUP_RETRIES:
                logger.critical(
                    f"Max startup retries due to network issues. Exiting.")
                sys.exit(1)
            time.sleep(STARTUP_RETRY_DELAY)
        except RuntimeError as re:
            logger.error(f"Startup RuntimeError (Attempt {attempt + 1}): {re}")
            if "JobQueue" in str(re) or "CHAT_ID" in str(re):
                logger.critical(f"Unrecoverable startup error: {re}. Exiting.")
                sys.exit(1)
            if attempt + 1 == MAX_STARTUP_RETRIES:
                logger.critical(
                    f"Max startup retries due to runtime error. Exiting.")
                sys.exit(1)
            time.sleep(STARTUP_RETRY_DELAY)
        except Exception as e:
            logger.critical(
                f"Unexpected error during app build (Attempt {attempt + 1}): {e}", exc_info=True)
            if attempt + 1 == MAX_STARTUP_RETRIES:
                logger.critical(
                    f"Max startup retries due to unexpected error. Exiting.")
                sys.exit(1)
            time.sleep(STARTUP_RETRY_DELAY)
    else:
        logger.critical(
            "Exhausted all startup retries for Telegram application build. Exiting.")
        sys.exit(1)

    application.add_error_handler(error_handler)
    setup_handlers(application)
    logger.info(
        f"Bot polling starting. Data path: {current_data_path}. Ctrl+C to stop.")
    try:
        signal.signal(signal.SIGINT, sigint_handler_sync)
        if os.name != 'nt':
            signal.signal(signal.SIGTERM, sigint_handler_sync)
        application.run_polling(
            allowed_updates=Update.ALL_TYPES, stop_signals=None)
    except Exception as e:
        logger.critical(
            f"Unhandled exception in run_polling: {e}", exc_info=True)
    finally:
        logger.info("Bot polling loop ended.")
        if application and application.persistence:
            try:
                logger.info("Flushing persistence...")
                application.persistence.flush()
                logger.info("Persistence flushed.")
            except Exception as final_flush_e:
                logger.error(
                    f"Error flushing persistence during final shutdown: {final_flush_e}", exc_info=True)
        logger.info(
            f"--- Media Bot Version: {project_version_loaded} shutdown ---")


if __name__ == '__main__':

    main()
