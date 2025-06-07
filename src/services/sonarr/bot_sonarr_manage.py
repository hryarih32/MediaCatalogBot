import logging
import json
import requests

from .bot_sonarr_core import _sonarr_request, get_all_series_ids_and_titles_cached

logger = logging.getLogger(__name__)


def rescan_all_series():

    series_map = get_all_series_ids_and_titles_cached(force_refresh=True)
    series_ids = list(series_map.keys())
    if not series_ids:
        return "ℹ️ No series found in Sonarr to rescan, or an error occurred fetching them."
    command_data = {"name": "RescanSeries", "seriesIds": series_ids}
    try:
        _sonarr_request('post', '/command', data=command_data)
        logger.info(
            f"Sonarr 'RescanSeries' command initiated for {len(series_ids)} series.")
        return f"✅ Sonarr disk rescan initiated for all {len(series_ids)} series."
    except Exception as e:
        logger.error(
            f"Error initiating Sonarr RescanSeries command for all series: {e}", exc_info=True)
        return f"⚠️ Error initiating Sonarr disk rescan: {type(e).__name__}. Check logs."


def refresh_all_series():

    series_map = get_all_series_ids_and_titles_cached(force_refresh=True)
    series_ids = list(series_map.keys())
    if not series_ids:
        return "ℹ️ No series found in Sonarr to refresh, or an error occurred fetching them."
    command_data = {"name": "RefreshSeries", "seriesIds": series_ids}
    try:
        _sonarr_request('post', '/command', data=command_data)
        logger.info(
            f"Sonarr 'RefreshSeries' command initiated for {len(series_ids)} series.")
        return f"✅ Sonarr metadata refresh initiated for all {len(series_ids)} series."
    except Exception as e:
        logger.error(
            f"Error initiating Sonarr RefreshSeries command for all series: {e}", exc_info=True)
        return f"⚠️ Error initiating Sonarr metadata refresh: {type(e).__name__}. Check logs."


def rename_all_series_files():

    series_map = get_all_series_ids_and_titles_cached(force_refresh=True)
    series_ids = list(series_map.keys())
    if not series_ids:
        return "ℹ️ No series found in Sonarr to rename, or an error occurred fetching them."
    command_data = {
        "name": "RenameSeries", "seriesIds": series_ids, "sendUpdatesToClient": True,
        "requiresDiskAccess": True, "updateScheduledTask": True, "isExclusive": False,
        "isLongRunning": False, "trigger": "manual", "suppressMessages": False
    }
    try:
        _sonarr_request('post', '/command', data=command_data)
        logger.info(
            f"Sonarr 'RenameSeries' command successfully queued for {len(series_ids)} series.")
        return f"✅ Sonarr series/episode file renaming initiated for all {len(series_ids)} series."
    except Exception as e:
        logger.error(
            f"Error initiating Sonarr 'RenameSeries' command: {e}", exc_info=True)
        return f"⚠️ Error initiating Sonarr series/episode file renaming: {type(e).__name__}. Check logs."


def get_wanted_missing_episodes(page=1, page_size=5, sort_key="airDateUtc", sort_dir="desc"):

    params = {
        "page": page, "pageSize": page_size, "sortKey": sort_key,
        "sortDir": sort_dir, "monitored": "true",
    }
    try:
        data = _sonarr_request('get', '/wanted/missing', params=params)
        if data and 'records' in data:
            current_cache = get_all_series_ids_and_titles_cached()
            for record in data['records']:
                if 'series' not in record or not record['series'].get('title'):
                    record['seriesTitle'] = current_cache.get(
                        record.get('seriesId'), 'Unknown Series')
                else:
                    record['seriesTitle'] = record['series'].get(
                        'title', 'Unknown Series')
        return data
    except Exception as e:
        logger.error(
            f"Error fetching wanted/missing episodes from Sonarr: {e}", exc_info=True)
        return {"error": "Could not fetch wanted episodes.", "records": [], "totalRecords": 0, "page": page, "pageSize": page_size}


def trigger_missing_episode_search():

    command_data = {
        "name": "MissingEpisodeSearch", "monitored": True, "sendUpdatesToClient": True,
        "updateScheduledTask": True, "requiresDiskAccess": False, "isExclusive": False,
        "isLongRunning": False, "trigger": "manual", "suppressMessages": False
    }
    try:
        _sonarr_request('post', '/command', data=command_data)
        logger.info(
            "Sonarr 'MissingEpisodeSearch' command successfully queued.")
        return "✅ Sonarr search for all wanted/missing episodes initiated."
    except Exception as e:
        logger.error(
            f"Error initiating Sonarr 'MissingEpisodeSearch' command: {e}", exc_info=True)
        return f"⚠️ Error initiating Sonarr search for wanted episodes: {type(e).__name__}. Check logs."


def trigger_episode_search(episode_ids: list) -> tuple[bool, str]:

    if not episode_ids or not all(isinstance(eid, int) and eid > 0 for eid in episode_ids):
        logger.warning(
            f"Invalid episode_ids ({episode_ids}) provided for Sonarr search.")
        return False, "ℹ️ No valid episode IDs provided for search."
    command_data = {
        "name": "EpisodeSearch", "episodeIds": episode_ids, "sendUpdatesToClient": True,
        "updateScheduledTask": False, "requiresDiskAccess": False, "isExclusive": True,
        "isLongRunning": True, "trigger": "manual", "suppressMessages": False
    }
    try:
        _sonarr_request('post', '/command', data=command_data)
        logger.info(
            f"Sonarr 'EpisodeSearch' command successfully queued for episode IDs: {episode_ids}.")
        if len(episode_ids) == 1:
            return True, f"✅ Sonarr search initiated for episode ID {episode_ids[0]}."
        else:
            return True, f"✅ Sonarr search initiated for {len(episode_ids)} episodes."
    except Exception as e:
        logger.error(
            f"Error initiating Sonarr 'EpisodeSearch' for IDs {episode_ids}: {e}", exc_info=True)
        return False, f"⚠️ Error initiating Sonarr episode search: {type(e).__name__}. Check logs."


def get_sonarr_queue(page=1, page_size=10, sort_key="timeleft", sort_dir="asc", include_unknown_series_items=True):

    params = {
        "page": page, "pageSize": page_size, "sortKey": sort_key, "sortDir": sort_dir,
        "includeUnknownSeriesItems": str(include_unknown_series_items).lower(),
        "includeSeries": "true", "includeEpisode": "true"
    }
    try:
        queue_data = _sonarr_request('get', '/queue', params=params)
        if queue_data and 'records' in queue_data:
            current_cache = get_all_series_ids_and_titles_cached()
            for record in queue_data['records']:
                if 'series' in record and isinstance(record['series'], dict) and 'title' in record['series']:
                    record['seriesTitle'] = record['series']['title']
                elif 'seriesId' in record:
                    record['seriesTitle'] = current_cache.get(
                        record['seriesId'], 'Unknown Series')
                else:
                    record['seriesTitle'] = 'Unknown Series'
            return queue_data
        logger.warning(
            f"Unexpected response structure from Sonarr /queue: {queue_data}")
        return {"error": "Unexpected response from Sonarr queue.", "records": [], "totalRecords": 0, "page": page, "pageSize": page_size}
    except Exception as e:
        logger.error(f"Error fetching Sonarr queue: {e}", exc_info=True)
        return {"error": "Could not fetch Sonarr queue.", "records": [], "totalRecords": 0, "page": page, "pageSize": page_size}


def remove_queue_item(item_id: str, blocklist: bool) -> tuple[bool, str]:

    params = {
        "removeFromClient": "true", "blocklist": str(blocklist).lower(),
        "skipRedownload": "false", "changeCategory": "false"
    }
    try:
        _sonarr_request('delete', f'/queue/{item_id}', params=params)
        action_taken = "blocklisted and removed" if blocklist else "removed (not blocklisted)"
        logger.info(
            f"Sonarr queue item {item_id} {action_taken} successfully.")
        return True, f"✅ Sonarr item {item_id} {action_taken} from queue."
    except requests.exceptions.HTTPError as e:
        if e.response and e.response.status_code == 404:
            logger.warning(
                f"Sonarr queue item {item_id} not found (404) for removal.")
            return False, f"⚠️ Sonarr item {item_id} not found in queue. It might have already completed or been removed."
        logger.error(
            f"HTTPError removing Sonarr queue item {item_id}: {e}", exc_info=True)
        return False, f"⚠️ Error removing Sonarr item {item_id} from queue (HTTP {e.response.status_code if e.response else 'Unknown'})."
    except Exception as e:
        logger.error(
            f"Error removing Sonarr queue item {item_id}: {e}", exc_info=True)
        return False, f"⚠️ Error removing Sonarr item {item_id} from queue: {type(e).__name__}. Check logs."


def get_sonarr_library_stats():
    """Fetches all series from Sonarr and returns total series count, episode count, and disk size."""
    total_series = 0
    total_episodes = 0
    total_size_on_disk_bytes = 0
    error_message = None
    try:
        series_list = _sonarr_request('get', '/series')
        if series_list and isinstance(series_list, list):
            total_series = len(series_list)
            for series_item in series_list:
                if isinstance(series_item, dict):
                    if 'statistics' in series_item and isinstance(series_item['statistics'], dict):

                        total_episodes += series_item['statistics'].get(
                            'episodeFileCount', 0)
                        total_size_on_disk_bytes += series_item['statistics'].get(
                            'sizeOnDisk', 0)
        elif series_list is None:
            pass
        else:
            logger.warning(
                f"Unexpected response from Sonarr /series endpoint: {type(series_list)}")
            error_message = "Unexpected response from Sonarr when fetching series."
    except Exception as e:
        logger.error(f"Error getting Sonarr library stats: {e}", exc_info=True)
        error_message = f"Error fetching Sonarr library stats: {type(e).__name__}"

    return {
        "total_series": total_series,
        "total_episodes": total_episodes,
        "total_size_on_disk_bytes": total_size_on_disk_bytes,
        "error": error_message
    }
