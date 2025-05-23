import logging
import requests
import json
import src.app.app_config_holder as app_config_holder

logger = logging.getLogger(__name__)

ABDM_HOST_DEFAULT = "127.0.0.1"
ABDM_ENDPOINT_ADD = "/add"
REQUEST_TIMEOUT = 15


def _get_abdm_base_url():
    """Constructs the base URL for ABDM API using configured port."""
    port = app_config_holder.get_abdm_port()
    if not port:
        logger.error("ABDM port not configured. Cannot construct base URL.")
        return None
    return f"http://{ABDM_HOST_DEFAULT}:{port}"


def add_download_to_abdm(url: str, filename: str | None = None, destination_path: str | None = None,
                         silent_add: bool = True, silent_start: bool = True) -> str:
    """
    Attempts to add a download to AB Download Manager via its local API.

    Args:
        url (str): The URL of the file to download.
        filename (str | None): Optional. Desired filename. If None, ABDM will infer.
        destination_path (str | None): Optional. Desired save path. Note: ABDM API usually
                                      handles this internally based on its own settings,
                                      this parameter is for future flexibility or if ABDM's API
                                      changes. Currently not passed in payload.
        silent_add (bool): If true, download is added without showing a dialog.
        silent_start (bool): If true, download starts automatically after being added.

    Returns:
        str: A message indicating success or the nature of the error.
    """
    base_url = _get_abdm_base_url()
    if not base_url:
        return "❌ AB Download Manager: Port not configured."

    abdm_url = f"{base_url}{ABDM_ENDPOINT_ADD}"

    item_description = filename if filename else url.split(
        '/')[-1].split('?')[0]
    if not item_description:
        item_description = "unnamed_download"

    download_item = {
        "link": url,
        "downloadPage": None,
        "headers": None,
        "description": item_description
    }

    download_options = {
        "silentAdd": silent_add,
        "silentStart": silent_start,
    }

    payload = {
        "items": [download_item],
        "options": download_options,
    }

    headers = {'Content-Type': 'application/json'}

    logger.info(
        f"Sending ABDM download request to {abdm_url} for URL: {url} (Silent Add: {silent_add}, Silent Start: {silent_start})")
    logger.debug(f"ABDM Payload: {json.dumps(payload)}")

    try:
        response = requests.post(abdm_url, data=json.dumps(
            payload), headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        logger.info(f"ABDM response status: {response.status_code}")
        logger.debug(f"ABDM response body: {response.text}")

        return "✅ AB Download Manager: Download request sent successfully."

    except requests.exceptions.ConnectionError:
        logger.error(
            f"Could not connect to AB Download Manager at {abdm_url}.", exc_info=False)
        return f"❌ AB Download Manager: Could not connect to {ABDM_HOST_DEFAULT}:{app_config_holder.get_abdm_port()}. Is it running and listening on the correct port?"
    except requests.exceptions.Timeout:
        logger.error(
            f"Connection to AB Download Manager timed out after {REQUEST_TIMEOUT} seconds at {abdm_url}.", exc_info=False)
        return f"❌ AB Download Manager: Connection timed out to {ABDM_HOST_DEFAULT}:{app_config_holder.get_abdm_port()}."
    except requests.exceptions.HTTPError as e:
        error_details = f"HTTP Error {e.response.status_code}" if e.response else "Unknown HTTP Error"
        response_text_info = e.response.text[:
                                             200] if e.response and e.response.text else "No response body."
        logger.error(
            f"ABDM HTTP Error for {abdm_url}: {error_details} - {response_text_info}", exc_info=True)
        return f"❌ AB Download Manager: {error_details}. Details: {response_text_info.strip()}. Check ABDM logs."
    except json.JSONDecodeError:
        if response.status_code >= 200 and response.status_code < 300:
            logger.warning(
                f"ABDM: Server responded with status {response.status_code}, but content was not valid JSON. Response: '{response.text[:200]}'", exc_info=True)
            return "✅ AB Download Manager: Request sent, but server response was not valid JSON. (Likely successful)"
        else:
            logger.error(
                f"ABDM: Server response was invalid JSON or empty for non-success status {response.status_code}. Response: '{response.text[:200]}'", exc_info=True)
            return f"❌ AB Download Manager: Invalid server response (Code: {response.status_code}). Check ABDM logs."
    except Exception as e:
        logger.error(
            f"An unexpected error occurred when sending request to ABDM: {e}", exc_info=True)
        return f"❌ AB Download Manager: An unexpected error occurred: {type(e).__name__}."
