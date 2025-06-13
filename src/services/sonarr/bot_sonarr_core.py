import logging
import requests
import backoff
import time

logger = logging.getLogger(__name__)

SONARR_API_URL_GLOBAL = None
SONARR_API_KEY_GLOBAL = None
REQUEST_TIMEOUT = 15
COMMAND_TIMEOUT = 90
SERIES_TITLE_CACHE = {}
SERIES_CACHE_LAST_REFRESH = 0
SERIES_CACHE_TTL = 300


def init_sonarr_config(base_api_url, api_key):
    global SONARR_API_URL_GLOBAL, SONARR_API_KEY_GLOBAL
    SONARR_API_URL_GLOBAL = base_api_url
    SONARR_API_KEY_GLOBAL = api_key

    global SERIES_TITLE_CACHE, SERIES_CACHE_LAST_REFRESH
    SERIES_TITLE_CACHE = {}
    SERIES_CACHE_LAST_REFRESH = 0


@backoff.on_exception(backoff.expo,
                      requests.exceptions.RequestException,
                      max_tries=3,
                      max_time=60,
                      # type: ignore
                      giveup=lambda e: hasattr(e, 'response') and e.response is not None and 400 <= e.response.status_code < 500 and e.response.status_code not in [401, 403, 429])
def _sonarr_request_impl(method, endpoint, params=None, data=None, headers=None, timeout_override=None):
    if not SONARR_API_URL_GLOBAL or not SONARR_API_KEY_GLOBAL:
        logger.error(
            "Sonarr API URL or Key not configured at time of request.")
        raise ValueError("Sonarr API URL or Key not configured")

    base_url_from_config = SONARR_API_URL_GLOBAL.strip()
    if not base_url_from_config.endswith('/'):
        base_url_from_config += '/'

    if 'api/v3' not in base_url_from_config:

        if base_url_from_config.count('/') == 2 and base_url_from_config.startswith(('http://', 'https://')):
            api_base_url = base_url_from_config + 'api/v3'
        elif base_url_from_config.count('/') > 2 and not base_url_from_config.endswith('api/v3/'):
            api_base_url = base_url_from_config.rstrip('/') + '/api/v3'
        else:
            api_base_url = base_url_from_config
    else:
        api_base_url = base_url_from_config

    if not api_base_url.endswith('/'):
        api_base_url += '/'

    request_endpoint = endpoint.lstrip('/')
    url = f'{api_base_url}{request_endpoint}'

    base_headers = {'X-Api-Key': SONARR_API_KEY_GLOBAL}
    if headers:
        base_headers.update(headers)

    current_timeout = timeout_override if timeout_override is not None else REQUEST_TIMEOUT
    if method.lower() == "post" and data and data.get("name") in ["RenameSeries", "MissingEpisodeSearch", "SeriesSearch", "RefreshSeries", "RescanSeries", "EpisodeSearch"] and timeout_override is None:
        current_timeout = COMMAND_TIMEOUT

    response_obj = None
    try:
        if method.lower() == 'get':
            response_obj = requests.get(
                url, params=params, headers=base_headers, timeout=current_timeout)
        elif method.lower() == 'post':
            response_obj = requests.post(
                url, params=params, json=data, headers=base_headers, timeout=current_timeout)
        elif method.lower() == 'delete':
            response_obj = requests.delete(
                url, params=params, headers=base_headers, timeout=current_timeout)

        else:
            logger.error(
                f"Invalid HTTP method specified for Sonarr request: {method}")
            raise ValueError(f"Invalid method: {method}")

        _sonarr_request.last_response_status = response_obj.status_code
        response_obj.raise_for_status()

        if method.lower() == 'delete' and (response_obj.status_code == 200 or response_obj.status_code == 204) and not response_obj.content:
            return None
        if response_obj.status_code == 204 or not response_obj.content:
            if method.lower() == 'post' and response_obj.status_code in [201, 202] and not response_obj.content:
                return None
            return response_obj.json() if response_obj.content else None
        return response_obj.json()
    except requests.exceptions.HTTPError as e:
        _sonarr_request.last_response_status = e.response.status_code if e.response else None
        logger.error(
            f"Sonarr HTTP Error for {method.upper()} {url}: {e.response.status_code if e.response else 'Unknown'} - {e.response.text[:200] if e.response else ''}", exc_info=True)
        if e.response and e.response.status_code in [401, 403]:
            logger.error(
                f"Sonarr API Key invalid or insufficient permissions.")
        raise
    except requests.exceptions.RequestException as e:
        _sonarr_request.last_response_status = None
        logger.error(
            f"Sonarr Request Exception for {method.upper()} {url}: {e}", exc_info=True)
        raise
    except Exception as e:
        _sonarr_request.last_response_status = None
        logger.error(
            f"Unexpected error in _sonarr_request for {method.upper()} {url}: {e}", exc_info=True)
        raise


_sonarr_request = _sonarr_request_impl
_sonarr_request.last_response_status = None


def get_all_series_ids_and_titles_cached(force_refresh=False):
    global SERIES_TITLE_CACHE, SERIES_CACHE_LAST_REFRESH
    current_time = time.time()
    if not force_refresh and SERIES_TITLE_CACHE and (current_time - SERIES_CACHE_LAST_REFRESH < SERIES_CACHE_TTL):
        logger.debug("Using cached series titles.")
        return SERIES_TITLE_CACHE

    logger.debug("Fetching or refreshing series titles from Sonarr.")
    try:
        series_list = _sonarr_request('get', '/series')
        if series_list and isinstance(series_list, list):
            SERIES_TITLE_CACHE = {s['id']: s.get('title', 'Unknown Series')
                                  for s in series_list if 'id' in s}
            SERIES_CACHE_LAST_REFRESH = current_time
            logger.info(
                f"Refreshed Sonarr series title cache with {len(SERIES_TITLE_CACHE)} items.")
            return SERIES_TITLE_CACHE
        logger.warning(
            "No series data returned from Sonarr for title cache, or data was not a list.")
        return {}
    except Exception as e:
        logger.error(
            f"Error getting all series from Sonarr for title cache: {e}", exc_info=True)

        return SERIES_TITLE_CACHE if SERIES_TITLE_CACHE else {}


def get_series_title_by_id(series_id: int, force_refresh_cache=False) -> str:
    series_map = get_all_series_ids_and_titles_cached(
        force_refresh=force_refresh_cache)
    return series_map.get(series_id, "Unknown Series")


def check_sonarr_connection() -> bool:
    """Performs a quick health check for Sonarr."""
    if not SONARR_API_URL_GLOBAL or not SONARR_API_KEY_GLOBAL:
        return False
    try:
        # Make a lightweight call to /system/status
        _sonarr_request('get', '/system/status', timeout_override=3)
        logger.debug("Sonarr health check: PASSED")
        return True
    except Exception as e:
        # Log at debug, as this is a health check
        logger.debug(
            f"Sonarr health check: FAILED - {type(e).__name__}: {e}", exc_info=False)
        return False
