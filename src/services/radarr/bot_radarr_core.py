import logging
import requests
import backoff

logger = logging.getLogger(__name__)

RADARR_API_URL_GLOBAL = None
RADARR_API_KEY_GLOBAL = None
REQUEST_TIMEOUT = 15
COMMAND_TIMEOUT = 90


def init_radarr_config(base_api_url, api_key):
    global RADARR_API_URL_GLOBAL, RADARR_API_KEY_GLOBAL
    RADARR_API_URL_GLOBAL = base_api_url
    RADARR_API_KEY_GLOBAL = api_key


@backoff.on_exception(backoff.expo,
                      requests.exceptions.RequestException,
                      max_tries=3,
                      max_time=60,
                      giveup=lambda e: hasattr(e, 'response') and e.response is not None and 400 <= e.response.status_code < 500 and e.response.status_code not in [401, 403, 429])
def _radarr_request_impl(method, endpoint, params=None, data=None, headers=None):
    if not RADARR_API_URL_GLOBAL or not RADARR_API_KEY_GLOBAL:
        logger.error(
            "Radarr API URL or Key not configured at time of request.")
        raise ValueError("Radarr API URL or Key not configured")

    base_url_from_config = RADARR_API_URL_GLOBAL.strip()
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

    base_headers = {'X-Api-Key': RADARR_API_KEY_GLOBAL}
    if headers:
        base_headers.update(headers)

    current_timeout = REQUEST_TIMEOUT
    if endpoint == "movie/editor" and method.lower() == "put":
        current_timeout = 60
    elif method.lower() == "post" and data and data.get("name") in ["RenameMovie", "RefreshMovie", "RescanMovie", "MovieSearch"]:
        current_timeout = COMMAND_TIMEOUT

    response_obj = None
    try:
        if method.lower() == 'get':
            response_obj = requests.get(
                url, params=params, headers=base_headers, timeout=current_timeout)
        elif method.lower() == 'post':
            response_obj = requests.post(
                url, params=params, json=data, headers=base_headers, timeout=current_timeout)
        elif method.lower() == 'put':
            response_obj = requests.put(
                url, params=params, json=data, headers=base_headers, timeout=current_timeout)
        elif method.lower() == 'delete':
            response_obj = requests.delete(
                url, params=params, headers=base_headers, timeout=current_timeout)
        else:
            logger.error(
                f"Invalid HTTP method specified for Radarr request: {method}")
            raise ValueError(f"Invalid method: {method}")

        _radarr_request.last_response_status = response_obj.status_code
        response_obj.raise_for_status()

        if method.lower() == 'delete' and (response_obj.status_code == 200 or response_obj.status_code == 204) and not response_obj.content:
            return None
        if response_obj.status_code == 204 or not response_obj.content:

            if method.lower() in ['post', 'put'] and response_obj.status_code in [200, 201, 202] and not response_obj.content:
                return None
            return response_obj.json() if response_obj.content else None
        return response_obj.json()
    except requests.exceptions.HTTPError as e:
        _radarr_request.last_response_status = e.response.status_code if e.response else None
        logger.error(
            f"Radarr HTTP Error for {method.upper()} {url}: {e.response.status_code if e.response else 'Unknown'} - {e.response.text[:200] if e.response else ''}", exc_info=True)
        if e.response and e.response.status_code in [401, 403]:
            logger.error(
                f"Radarr API Key invalid or insufficient permissions.")
        raise
    except requests.exceptions.RequestException as e:
        _radarr_request.last_response_status = None
        logger.error(
            f"Radarr Request Exception for {method.upper()} {url}: {e}", exc_info=True)
        raise
    except Exception as e:
        _radarr_request.last_response_status = None
        logger.error(
            f"Unexpected error in _radarr_request for {method.upper()} {url}: {e}", exc_info=True)
        raise


_radarr_request = _radarr_request_impl
_radarr_request.last_response_status = None
