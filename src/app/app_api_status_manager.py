import logging
from telegram.ext import CallbackContext

import src.app.app_config_holder as app_config_holder
from src.services.plex.bot_plex_core import check_plex_connection
from src.services.radarr.bot_radarr_core import check_radarr_connection
from src.services.sonarr.bot_sonarr_core import check_sonarr_connection
from src.services.abdm.bot_abdm_core import check_abdm_connection

logger = logging.getLogger(__name__)

API_STATUS_ONLINE = "online"
API_STATUS_OFFLINE = "offline"
API_STATUS_CONFIG_ERROR = "config_error"
API_STATUS_DISABLED = "disabled"  # Explicitly for when service is off in config
# Default if check hasn't run or failed unexpectedly
API_STATUS_UNKNOWN = "unknown"

SERVICE_CHECK_MAP = {
    "plex": {
        "is_enabled_func": app_config_holder.is_plex_enabled,
        "config_check_func": lambda: app_config_holder.get_plex_url() and app_config_holder.get_plex_token(),
        "connection_check_func": check_plex_connection,
        "bot_data_key": "plex_api_status"
    },
    "radarr": {
        "is_enabled_func": app_config_holder.is_radarr_enabled,
        "config_check_func": lambda: app_config_holder.get_radarr_base_api_url() and app_config_holder.get_radarr_api_key(),
        "connection_check_func": check_radarr_connection,
        "bot_data_key": "radarr_api_status"
    },
    "sonarr": {
        "is_enabled_func": app_config_holder.is_sonarr_enabled,
        "config_check_func": lambda: app_config_holder.get_sonarr_base_api_url() and app_config_holder.get_sonarr_api_key(),
        "connection_check_func": check_sonarr_connection,
        "bot_data_key": "sonarr_api_status"
    },
    "abdm": {
        "is_enabled_func": app_config_holder.is_abdm_enabled,
        "config_check_func": lambda: app_config_holder.get_abdm_port() is not None,
        "connection_check_func": check_abdm_connection,
        "bot_data_key": "abdm_api_status"
    }
}


async def update_all_api_statuses_once(bot_data: dict) -> None:
    """
    Performs a one-time update of all API statuses and stores them in bot_data.
    This is suitable for calling on startup or after config changes.
    """
    logger.info("Performing one-time update of all API statuses...")
    for service_name, checks in SERVICE_CHECK_MAP.items():
        status_to_set = API_STATUS_UNKNOWN
        if not checks["is_enabled_func"]():
            status_to_set = API_STATUS_DISABLED
        elif not checks["config_check_func"]():
            status_to_set = API_STATUS_CONFIG_ERROR
        else:
            try:
                if checks["connection_check_func"]():
                    status_to_set = API_STATUS_ONLINE
                else:
                    status_to_set = API_STATUS_OFFLINE
            except Exception as e:
                logger.error(
                    f"Error during {service_name} connection check for initial status: {e}", exc_info=False)
                status_to_set = API_STATUS_UNKNOWN  # Or a specific error status

        bot_data[checks["bot_data_key"]] = status_to_set
        logger.debug(f"Initial status for {service_name}: {status_to_set}")
    logger.info("One-time API status update complete.")


async def periodic_api_status_check(context: CallbackContext) -> None:
    """
    Periodically checks the status of all configured APIs and updates bot_data.
    This function is intended to be run as a repeating job.
    """
    if not context.bot_data:
        logger.warning(
            "periodic_api_status_check: context.bot_data is not available. Skipping check.")
        return

    logger.debug("Performing periodic API status check...")
    # We can reuse the logic from update_all_api_statuses_once
    # It's designed to work with a bot_data dict directly.
    await update_all_api_statuses_once(context.bot_data)
    logger.debug("Periodic API status check complete.")
