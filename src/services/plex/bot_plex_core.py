import logging
from plexapi.server import PlexServer
from plexapi.exceptions import PlexApiException, NotFound, BadRequest as PlexApiBadRequest
import requests
import backoff

logger = logging.getLogger(__name__)

PLEX_URL_GLOBAL = None
PLEX_TOKEN_GLOBAL = None


def init_plex_config(url, token):
    global PLEX_URL_GLOBAL, PLEX_TOKEN_GLOBAL
    PLEX_URL_GLOBAL = url
    PLEX_TOKEN_GLOBAL = token


@backoff.on_exception(backoff.expo,
                      (requests.exceptions.RequestException, PlexApiException),
                      max_tries=3,
                      giveup=lambda e: isinstance(e, PlexApiException) and
                      hasattr(e, 'response') and
                      e.response is not None and
                      400 <= e.response.status_code < 500 and
                      e.response.status_code not in [401, 403, 429])
def _plex_request(func, *args, **kwargs):
    return func(*args, **kwargs)


def get_plex_server_connection():
    if not PLEX_URL_GLOBAL or not PLEX_TOKEN_GLOBAL:
        logger.error(
            "Plex URL or Token not configured for get_plex_server_connection.")
        return None
    try:
        plex = PlexServer(PLEX_URL_GLOBAL, PLEX_TOKEN_GLOBAL, timeout=10)
        _plex_request(getattr, plex, 'version')
        return plex
    except PlexApiException as e:
        logger.error(f"Plex API connection failed: {e}", exc_info=True)
        if hasattr(e, 'response') and e.response and e.response.status_code == 401:
            logger.error("Plex Error: Unauthorized. Check PLEX_TOKEN.")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Plex network connection failed: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error connecting to Plex server: {e}", exc_info=True)
        return None


def clean_plex_bundles():
    plex = get_plex_server_connection()
    if not plex:
        return "Plex not configured or connection failed."
    try:
        _plex_request(plex.library.cleanBundles)
        logger.info("Plex 'Clean Bundles' task initiated.")
        return "✅ Plex 'Clean Bundles' task initiated successfully."
    except Exception as e:
        logger.error(
            f"Error initiating Plex 'Clean Bundles': {e}", exc_info=True)
        return f"⚠️ Error initiating Plex 'Clean Bundles': {type(e).__name__}."


def empty_plex_trash(library_key=None):
    plex = get_plex_server_connection()
    if not plex:
        return "Plex not configured or connection failed."
    try:
        if library_key is None or str(library_key).lower() == 'all':
            _plex_request(plex.library.emptyTrash)
            logger.info("Plex 'Empty Trash' task initiated for all libraries.")
            return "✅ Plex 'Empty Trash' task initiated for all libraries."
        else:
            section = _plex_request(plex.library.sectionByID, int(library_key))
            if section:
                _plex_request(section.emptyTrash)
                logger.info(
                    f"Plex 'Empty Trash' task initiated for library: {section.title} (Key: {library_key})")
                return f"✅ Plex 'Empty Trash' task initiated for library: {section.title}."
            else:
                logger.warning(
                    f"Could not find Plex library with key {library_key} to empty trash.")
                return f"⚠️ Library with key {library_key} not found."
    except PlexApiException as e:
        logger.error(
            f"Plex API error during 'Empty Trash': {e}", exc_info=True)
        return "⚠️ Error during Plex 'Empty Trash' (API)."
    except Exception as e:
        logger.error(
            f"Unexpected error during Plex 'Empty Trash': {e}", exc_info=True)
        return f"⚠️ Unexpected error during Plex 'Empty Trash': {type(e).__name__}."


def optimize_plex_database():
    plex = get_plex_server_connection()
    if not plex:
        return "Plex not configured or connection failed."
    try:
        _plex_request(plex.library.optimize)
        logger.info("Plex 'Optimize Database' task initiated.")
        return "✅ Plex 'Optimize Database' task initiated successfully."
    except Exception as e:
        logger.error(
            f"Error initiating Plex 'Optimize Database': {e}", exc_info=True)
        return f"⚠️ Error initiating Plex 'Optimize Database': {type(e).__name__}."


def get_plex_server_info_formatted():
    plex = get_plex_server_connection()
    if not plex:
        return {"error": "Plex not configured or connection failed."}
    try:
        server_name = getattr(plex, 'friendlyName', 'N/A')
        version = getattr(plex, 'version', 'N/A')
        platform = getattr(plex, 'platform', 'N/A')
        platform_version = getattr(plex, 'platformVersion', 'N/A')
        active_transcodes = _plex_request(plex.transcodeSessions)

        info = {
            "Server Name": server_name,
            "Version": version,
            "Platform": f"{platform} ({platform_version})",
            "Transcoder Active Sessions": str(len(active_transcodes)) if active_transcodes is not None else "0",
        }
        return info
    except AttributeError as ae:
        logger.error(
            f"AttributeError fetching Plex server info: {ae}", exc_info=True)
        return {"error": f"Error fetching Plex server info (Attribute Error): {ae}."}
    except Exception as e:
        logger.error(f"Error fetching Plex server info: {e}", exc_info=True)
        return {"error": f"Error fetching Plex server info: {type(e).__name__}."}
