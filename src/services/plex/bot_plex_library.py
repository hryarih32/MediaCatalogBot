import logging

import time
from .bot_plex_core import _plex_request, get_plex_server_connection
from plexapi.exceptions import PlexApiException

logger = logging.getLogger(__name__)

PLEX_LIBRARIES_CACHE = None
PLEX_LIBRARIES_CACHE_TIMESTAMP = 0
PLEX_LIBRARIES_CACHE_TTL = 900


def get_plex_libraries(force_refresh: bool = False):
    global PLEX_LIBRARIES_CACHE, PLEX_LIBRARIES_CACHE_TIMESTAMP

    current_time = time.time()
    if not force_refresh and PLEX_LIBRARIES_CACHE and \
       (current_time - PLEX_LIBRARIES_CACHE_TIMESTAMP < PLEX_LIBRARIES_CACHE_TTL):
        logger.info("Returning cached Plex library details (basic info).")
        return PLEX_LIBRARIES_CACHE

    logger.info(
        f"Fetching Plex library details (basic info, force_refresh={force_refresh}).")
    plex = get_plex_server_connection()
    if not plex:
        return []
    try:
        sections = _plex_request(plex.library.sections)
        libraries_details = []

        for section in sections:
            if section.type in ['movie', 'show', 'artist', 'photo', 'clip']:
                item_count = 0
                try:
                    item_count = section.totalSize
                except Exception as e_count:
                    logger.warning(
                        f"Could not determine item count for library '{section.title}': {e_count}")

                libraries_details.append({
                    'key': section.key,
                    'title': section.title,
                    'type': section.type,
                    'item_count': item_count,

                })

        PLEX_LIBRARIES_CACHE = libraries_details
        PLEX_LIBRARIES_CACHE_TIMESTAMP = current_time
        logger.info(
            f"Plex library basic details fetched and cached. Count: {len(libraries_details)}")
        return libraries_details
    except Exception as e:
        logger.error(
            f"Error getting Plex libraries basic details: {e}", exc_info=True)
        return PLEX_LIBRARIES_CACHE if PLEX_LIBRARIES_CACHE is not None else []


def format_bytes_to_readable(size_bytes: int) -> str:
    if size_bytes is None:
        return "N/A"
    size_gb = size_bytes / (1024**3)
    size_tb = size_bytes / (1024**4)
    if size_tb >= 1:
        return f"{size_tb:.2f} TB"
    elif size_gb >= 0.01:
        return f"{size_gb:.2f} GB"
    elif size_bytes > 0:
        return f"{size_bytes / (1024**2):.2f} MB"
    elif size_bytes == 0:
        return "0 B"
    return "N/A"


def trigger_library_scan(library_key=None):
    plex = get_plex_server_connection()
    if not plex:
        return "Plex not configured or connection failed."
    try:
        if library_key is None or str(library_key).lower() == 'all':
            _plex_request(plex.library.update)
            logger.info("Plex scan initiated for all libraries.")
            return "✅ Plex scan initiated for all libraries."
        else:
            section = _plex_request(plex.library.sectionByID, int(library_key))
            if section:
                _plex_request(section.update)
                logger.info(
                    f"Plex scan initiated for library: {section.title} (Key: {library_key})")
                return f"✅ Plex scan initiated for library: {section.title}."
            return f"⚠️ Library with key {library_key} not found."
    except Exception as e:
        logger.error(f"Error Plex library scan: {e}", exc_info=True)
        return "⚠️ Error during Plex library scan."


def trigger_metadata_refresh(library_key=None):
    plex = get_plex_server_connection()
    if not plex:
        return "Plex not configured or connection failed."
    try:
        if library_key is None or str(library_key).lower() == 'all':
            sections = _plex_request(plex.library.sections)
            refreshed_count = 0
            for section in sections:
                if section.type in ['movie', 'show', 'artist']:
                    _plex_request(section.refresh)
                    logger.info(
                        f"Plex metadata refresh initiated for library: {section.title}")
                    refreshed_count += 1
            return f"✅ Plex metadata refresh initiated for all eligible libraries ({refreshed_count} sections)." if refreshed_count > 0 else "ℹ️ No eligible libraries found."
        else:
            section = _plex_request(plex.library.sectionByID, int(library_key))
            if section and section.type in ['movie', 'show', 'artist']:
                _plex_request(section.refresh)
                logger.info(
                    f"Plex metadata refresh initiated for library: {section.title} (Key: {library_key})")
                return f"✅ Plex metadata refresh initiated for library: {section.title}."
            elif section:
                return f"⚠️ Library '{section.title}' (type: {section.type}) not eligible."
            return f"⚠️ Library with key {library_key} not found."
    except Exception as e:
        logger.error(f"Error Plex metadata refresh: {e}", exc_info=True)
        return "⚠️ Error during Plex metadata refresh."


def trigger_item_metadata_refresh(rating_key):
    plex = get_plex_server_connection()
    if not plex:
        return "Plex not configured or connection failed."
    try:
        item = _plex_request(plex.fetchItem, int(rating_key))
        if item:
            _plex_request(item.refresh)
            logger.info(
                f"Plex metadata refresh initiated for item: {item.title} (ratingKey: {rating_key})")
            return f"✅ Metadata refresh initiated for {item.title}."
        return f"⚠️ Item with ratingKey {rating_key} not found."
    except PlexApiException as e:
        if hasattr(e, 'response') and e.response and e.response.status_code == 404:
            return f"⚠️ Item with ratingKey {rating_key} not found."
        logger.error(
            f"Plex API error refreshing item metadata for {rating_key}: {e}", exc_info=True)
        return "⚠️ Error refreshing item metadata (API)."
    except Exception as e:
        logger.error(
            f"Error refreshing Plex item metadata for {rating_key}: {e}", exc_info=True)
        return "⚠️ Error refreshing item metadata."
