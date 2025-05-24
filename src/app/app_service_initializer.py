import logging
import src.app.app_config_holder as app_config_holder

from src.services.plex.bot_plex_core import init_plex_config
from src.services.radarr.bot_radarr_core import init_radarr_config
from src.services.sonarr.bot_sonarr_core import init_sonarr_config

logger = logging.getLogger(__name__)


def initialize_services_with_config(cfg_module):
    logger.info("Initializing services based on configuration...")
    app_config_holder.set_config(cfg_module)

    if app_config_holder.is_plex_enabled():
        plex_url = app_config_holder.get_plex_url()
        plex_token = app_config_holder.get_plex_token()
        if plex_url and plex_token:
            init_plex_config(plex_url, plex_token)
            logger.info("Plex actions initialized.")
        else:
            logger.warning(
                "Plex is enabled but URL or Token is missing. Plex features may not work.")
    else:
        logger.info("Plex features are disabled in config.")
        init_plex_config(None, None)

    if app_config_holder.is_radarr_enabled():
        radarr_url = app_config_holder.get_radarr_base_api_url()
        radarr_key = app_config_holder.get_radarr_api_key()
        if radarr_url and radarr_key:
            init_radarr_config(radarr_url, radarr_key)
            logger.info("Radarr bot initialized.")
        else:
            logger.warning(
                "Radarr is enabled but API URL or Key is missing. Radarr features may not work.")
    else:
        logger.info("Radarr features are disabled in config.")
        init_radarr_config(None, None)

    if app_config_holder.is_sonarr_enabled():
        sonarr_url = app_config_holder.get_sonarr_base_api_url()
        sonarr_key = app_config_holder.get_sonarr_api_key()
        if sonarr_url and sonarr_key:
            init_sonarr_config(sonarr_url, sonarr_key)
            logger.info("Sonarr bot initialized.")
        else:
            logger.warning(
                "Sonarr is enabled but API URL or Key is missing. Sonarr features may not work.")
    else:
        logger.info("Sonarr features are disabled in config.")
        init_sonarr_config(None, None)

    logger.info("Service initialization check complete.")
