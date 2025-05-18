import logging
import json
import requests
from .bot_radarr_core import _radarr_request

logger = logging.getLogger(__name__)


def _get_all_movie_ids():

    try:
        movies = _radarr_request('get', '/movie')
        if movies and isinstance(movies, list):
            return [movie['id'] for movie in movies if 'id' in movie]
        return []
    except Exception as e:
        logger.error(
            f"Error getting all movie IDs from Radarr: {e}", exc_info=True)
        return []


def rescan_all_movies():

    movie_ids = _get_all_movie_ids()
    if not movie_ids:
        return "ℹ️ No movies found in Radarr to rescan, or an error occurred fetching them."
    command_data = {"name": "RescanMovie", "movieIds": movie_ids}
    try:
        _radarr_request('post', '/command', data=command_data)
        logger.info(
            f"Radarr 'RescanMovie' command initiated for {len(movie_ids)} movies.")
        return f"✅ Radarr disk rescan initiated for all {len(movie_ids)} movies."
    except Exception as e:
        logger.error(
            f"Error initiating Radarr RescanMovie command for all movies: {e}", exc_info=True)
        return f"⚠️ Error initiating Radarr disk rescan: {type(e).__name__}. Check logs."


def refresh_all_movies():

    movie_ids = _get_all_movie_ids()
    if not movie_ids:
        return "ℹ️ No movies found in Radarr to refresh, or an error occurred fetching them."
    command_data = {"name": "RefreshMovie", "movieIds": movie_ids}
    try:
        _radarr_request('post', '/command', data=command_data)
        logger.info(
            f"Radarr 'RefreshMovie' command initiated for {len(movie_ids)} movies.")
        return f"✅ Radarr metadata refresh initiated for all {len(movie_ids)} movies."
    except Exception as e:
        logger.error(
            f"Error initiating Radarr RefreshMovie command for all movies: {e}", exc_info=True)
        return f"⚠️ Error initiating Radarr metadata refresh: {type(e).__name__}. Check logs."


def rename_all_movie_files():

    movie_ids = _get_all_movie_ids()
    if not movie_ids:
        return "ℹ️ No movies found in Radarr to rename, or an error occurred fetching them."
    command_data = {
        "name": "RenameMovie", "movieIds": movie_ids, "sendUpdatesToClient": True,
        "requiresDiskAccess": True, "updateScheduledTask": True, "isExclusive": False,
        "isTypeExclusive": False, "isLongRunning": False, "trigger": "manual", "suppressMessages": False
    }
    try:
        _radarr_request('post', '/command', data=command_data)
        logger.info(
            f"Radarr 'RenameMovie' command successfully queued for {len(movie_ids)} movies.")
        return f"✅ Radarr movie renaming initiated for all {len(movie_ids)} movies."
    except Exception as e:
        logger.error(
            f"Error initiating Radarr 'RenameMovie' command for all movies: {e}", exc_info=True)
        return f"⚠️ Error initiating Radarr movie renaming: {type(e).__name__}. Check logs."


def get_radarr_queue(page=1, page_size=10, sort_key="timeleft", sort_dir="asc"):

    params = {
        "page": page, "pageSize": page_size, "sortKey": sort_key,
        "sortDir": sort_dir, "includeMovie": "true"
    }
    try:
        queue_data = _radarr_request('get', '/queue', params=params)
        if isinstance(queue_data, dict) and 'records' in queue_data:
            return queue_data
        elif isinstance(queue_data, list):
            logger.warning(
                "Radarr /queue returned a list instead of a paginated object. Manual pagination applied.")
            total_records = len(queue_data)
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            paginated_records = queue_data[start_index:end_index]
            return {
                "page": page, "pageSize": page_size, "sortKey": sort_key,
                "sortDir": sort_dir, "totalRecords": total_records, "records": paginated_records
            }
        logger.warning(
            f"Unexpected response type from Radarr /queue: {type(queue_data)}. Data: {str(queue_data)[:200]}")
        return {"error": "Unexpected response from Radarr queue.", "records": [], "totalRecords": 0, "page": page, "pageSize": page_size}
    except Exception as e:
        logger.error(f"Error fetching Radarr queue: {e}", exc_info=True)
        return {"error": "Could not fetch Radarr queue.", "records": [], "totalRecords": 0, "page": page, "pageSize": page_size}


def remove_queue_item(item_id: str, blocklist: bool) -> str:

    params = {
        "removeFromClient": "true", "blocklist": str(blocklist).lower(),
        "skipRedownload": "false", "changeCategory": "false"
    }
    try:
        _radarr_request('delete', f'/queue/{item_id}', params=params)
        action_taken = "blocklisted and removed" if blocklist else "removed (not blocklisted)"
        logger.info(
            f"Radarr queue item {item_id} {action_taken} successfully.")
        return f"✅ Radarr item {item_id} {action_taken} from queue."
    except requests.exceptions.HTTPError as e:
        if e.response and e.response.status_code == 404:
            logger.warning(
                f"Radarr queue item {item_id} not found (404) for removal.")
            return f"⚠️ Radarr item {item_id} not found in queue. It might have already completed or been removed."
        logger.error(
            f"HTTPError removing Radarr queue item {item_id}: {e}", exc_info=True)
        return f"⚠️ Error removing Radarr item {item_id} from queue (HTTP {e.response.status_code if e.response else 'Unknown'})."
    except Exception as e:
        logger.error(
            f"Error removing Radarr queue item {item_id}: {e}", exc_info=True)
        return f"⚠️ Error removing Radarr item {item_id} from queue: {type(e).__name__}. Check logs."


def trigger_movie_search_for_id(movie_id: int) -> str:

    if not movie_id or movie_id == 0:
        logger.warning(
            f"Invalid movie_id ({movie_id}) provided for Radarr search.")
        return "⚠️ Cannot trigger search: Invalid Movie ID."
    command_data = {"name": "MovieSearch", "movieIds": [movie_id]}
    try:
        _radarr_request('post', '/command', data=command_data)
        logger.info(
            f"Radarr 'MovieSearch' command initiated for movie ID {movie_id}.")
        return f"✅ Radarr search initiated for movie ID {movie_id}."
    except Exception as e:
        logger.error(
            f"Error initiating Radarr MovieSearch for movie ID {movie_id}: {e}", exc_info=True)
        return f"⚠️ Error initiating Radarr search for movie ID {movie_id}: {type(e).__name__}. Check logs."


def get_radarr_library_stats():
    """Fetches all movies from Radarr and returns total count and disk size."""
    total_movies = 0
    total_size_on_disk_bytes = 0
    error_message = None
    try:
        movies = _radarr_request('get', '/movie')
        if movies and isinstance(movies, list):
            total_movies = len(movies)
            for movie in movies:
                if isinstance(movie, dict) and 'sizeOnDisk' in movie and movie['sizeOnDisk'] is not None:
                    total_size_on_disk_bytes += movie['sizeOnDisk']

        elif movies is None:
            pass
        else:
            logger.warning(
                f"Unexpected response from Radarr /movie endpoint: {type(movies)}")
            error_message = "Unexpected response from Radarr when fetching movies."

    except Exception as e:
        logger.error(f"Error getting Radarr library stats: {e}", exc_info=True)
        error_message = f"Error fetching Radarr library stats: {type(e).__name__}"

    return {
        "total_movies": total_movies,
        "total_size_on_disk_bytes": total_size_on_disk_bytes,
        "error": error_message
    }
