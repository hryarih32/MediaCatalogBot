import os
import json
import logging
import requests
from src.app.app_file_utils import get_search_results_file_path
from src.services.sonarr.bot_sonarr_core import _sonarr_request
import src.app.app_config_holder as app_config_holder


logger = logging.getLogger(__name__)

SHOW_RESULTS_FILE_NAME = 'show_search_results.json'


def get_show_results_file_path_local():
    return get_search_results_file_path(SHOW_RESULTS_FILE_NAME)


def save_results(filename, results):
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(results, file, indent=4)
        logger.info(
            f"Saved {len(results)} Sonarr search results to {filename}")
    except IOError:
        logger.warning(
            f"IOError saving Sonarr results to {filename}", exc_info=True)
        pass


def load_results(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                data = json.load(file)
                logger.info(
                    f"Loaded {len(data)} Sonarr results from {filename}")
                return data
        except (IOError, json.JSONDecodeError) as e:
            logger.warning(
                f"Error loading Sonarr results from {filename}: {e}. Removing corrupt file.", exc_info=True)
            try:
                os.remove(filename)
            except OSError:
                pass
    return []


def get_root_folders():
    try:
        folders = _sonarr_request('get', '/rootfolder')
        if folders and isinstance(folders, list):
            accessible_folders = [rf for rf in folders if rf.get('accessible')]
            if accessible_folders:
                return [{'id': rf.get('id', rf['path']), 'path': rf['path']} for rf in accessible_folders]
            return [{'id': rf.get('id', rf['path']), 'path': rf['path']} for rf in folders]
        return []
    except Exception as e:
        logger.error(f"Error getting Sonarr root folders: {e}", exc_info=True)
        return []


def get_quality_profiles():
    try:
        profiles = _sonarr_request('get', '/qualityprofile')
        if profiles and isinstance(profiles, list):
            return [{'id': p['id'], 'name': p['name']} for p in profiles]
        return []
    except Exception as e:
        logger.error(
            f"Error getting Sonarr quality profiles: {e}", exc_info=True)
        return []


def get_language_profiles():
    try:
        profiles = _sonarr_request('get', '/languageprofile')
        if profiles and isinstance(profiles, list):
            return [{'id': p['id'], 'name': p['name']} for p in profiles]

        try:

            profiles_v2 = _sonarr_request('get', '/profile')
            if profiles_v2 and isinstance(profiles_v2, list) and any("language" in p.get("name", "").lower() for p in profiles_v2):
                logger.info(
                    "Found language profiles via /profile endpoint (likely Sonarr v4).")
                return [{'id': p['id'], 'name': p['name']} for p in profiles_v2 if "language" in p.get("name", "").lower()]
        except Exception as e_profile:
            logger.debug(
                f"Could not fetch language profiles via /profile: {e_profile}")
            pass
        return []
    except Exception as e:
        logger.error(
            f"Error getting Sonarr language profiles: {e}", exc_info=True)
        return []


def get_tags():
    try:
        tags_list = _sonarr_request('get', '/tag')
        if tags_list and isinstance(tags_list, list):
            return [{'id': t['id'], 'label': t['label']} for t in tags_list]
        return []
    except Exception as e:
        logger.error(f"Error getting Sonarr tags: {e}", exc_info=True)
        return []


def get_series_type_options():
    return [
        {"value": "standard", "label": "Standard"},
        {"value": "daily", "label": "Daily"},
        {"value": "anime", "label": "Anime"}
    ]


def get_episode_monitor_options():
    return [
        {"value": "all", "label": "All Episodes"},
        {"value": "future", "label": "Future Episodes Only"},
        {"value": "missing", "label": "Missing Episodes"},
        {"value": "existing", "label": "Existing Episodes"},
        {"value": "firstSeason", "label": "First Season"},
        {"value": "lastSeason", "label": "Last Season"},
        {"value": "none", "label": "None (Manual Monitoring)"}
    ]


def get_default_root_folder_path():
    try:
        root_folders = get_root_folders()
        if root_folders and len(root_folders) > 0:
            return root_folders[0]['path']
        return None
    except Exception as e:
        logger.error(
            f"Error getting default Sonarr root folder path: {e}", exc_info=True)
        return None


def get_default_quality_profile_id():
    desired_name_keywords = ["hd", "720p", "1080p", "good", "any"]
    try:
        profiles = get_quality_profiles()
        if profiles:
            for keyword in desired_name_keywords:
                for profile in profiles:
                    if keyword in profile.get("name", "").lower():
                        return profile.get("id")
            return profiles[0].get("id")
        return None
    except Exception as e:
        logger.error(
            f"Error getting default Sonarr quality profile ID: {e}", exc_info=True)
        return None


def get_default_language_profile_id():
    try:
        lang_profiles = get_language_profiles()
        if lang_profiles:
            for name_part in ["english", "any language"]:
                english_profile = next(
                    (lp for lp in lang_profiles if name_part in lp.get("name", "").lower()), None)
                if english_profile:
                    return english_profile['id']
            return lang_profiles[0]['id']
        logger.warning(
            "No language profiles found in Sonarr, defaulting to ID 1. This might not be 'English'.")

        return 1
    except Exception as e:
        logger.error(
            f"Error getting default Sonarr language profile ID: {e}", exc_info=True)
        return 1


def search_show(query):
    params = {'term': query}
    results_file_full_path = get_show_results_file_path_local()
    max_results_config = app_config_holder.get_add_media_max_search_results()

    try:
        results = _sonarr_request('get', '/series/lookup', params=params)
        if not results or not isinstance(results, list) or len(results) == 0:

            return f'No Sonarr results found for your query: \'{query}\'.'
        raw_count = len(results)
        filtered_results = [s for s in results if not s.get(
            'id') and not s.get('rootFolderPath')]
        filtered_count_after_initial = len(filtered_results)
        if not filtered_results and results:
            first_result_tvdb_id = results[0].get('tvdbId')
            if first_result_tvdb_id:
                try:
                    existing_series_list = _sonarr_request(
                        'get', '/series')
                    if any(s.get('tvdbId') == first_result_tvdb_id for s in existing_series_list):
                        return "All Sonarr results found are already in your library."
                except:
                    pass
            filtered_results = results
        if not filtered_results:

            return 'No new Sonarr results found (they might already be in your library).'

        display_results = filtered_results[:max_results_config]
        logger.info(
            f"Sonarr search for '{query}' found {raw_count} raw, {filtered_count_after_initial} initially filtered, limited to {len(display_results)} results based on config ({max_results_config}).")
        save_results(results_file_full_path, display_results)
        return display_results
    except ValueError as e:
        logger.error(f"Sonarr search ValueError: {e}", exc_info=True)
        return f"Sonarr configuration error: {str(e)}"
    except requests.exceptions.HTTPError as e:
        logger.error(f"Sonarr search HTTPError: {e}", exc_info=True)
        if e.response and e.response.status_code == 401:
            return "Sonarr API Key is invalid or unauthorized."
        return "Error communicating with Sonarr. Check logs."
    except Exception as e:
        logger.error(f"Error searching Sonarr: {e}", exc_info=True)

        return f"Error searching Sonarr: {type(e).__name__}. Check logs."


def add_show(tvdb_id, sonarr_show_object, quality_profile_id, root_folder_path, language_profile_id,
             series_type="standard", season_folder=True, monitor_episodes="all",
             search_for_missing=True, tags=None):

    tags_param = tags if tags is not None else []
    show_title_for_msg = sonarr_show_object.get('title', f"TVDB ID {tvdb_id}")

    try:
        existing_series_list = _sonarr_request('get', '/series')
        if existing_series_list and isinstance(existing_series_list, list):
            if any(s.get('tvdbId') == int(tvdb_id) for s in existing_series_list):
                title_for_existing_msg = f"TVDB ID {tvdb_id}"
                existing_show_obj = next(
                    (s for s in existing_series_list if s.get('tvdbId') == int(tvdb_id)), None)
                if existing_show_obj:
                    title_for_existing_msg = existing_show_obj.get(
                        'title', title_for_existing_msg)
                return f"Show '{title_for_existing_msg}' is already in Sonarr."
        show_to_add = sonarr_show_object
        if not show_to_add or not show_to_add.get("title"):
            logger.error(
                f"Invalid show_to_add object for TVDB ID {tvdb_id}. Object: {show_to_add}")
            return f"Could not use provided show details for TVDB ID {tvdb_id}."
    except requests.exceptions.HTTPError as e:
        logger.error(
            f"HTTPError during pre-add lookup for TVDB ID {tvdb_id} in Sonarr: {e}", exc_info=True)
        return f"Error looking up show in Sonarr: HTTP {e.response.status_code if e.response else 'Unknown'}"
    except Exception as e:
        logger.error(
            f"Error during pre-add lookup for TVDB ID {tvdb_id} in Sonarr: {e}", exc_info=True)
        return f"Error looking up show in Sonarr: {type(e).__name__}"

    payload = show_to_add.copy()
    payload['qualityProfileId'] = int(quality_profile_id)
    payload['languageProfileId'] = int(language_profile_id)
    payload['rootFolderPath'] = root_folder_path
    payload['monitored'] = True
    payload['seasonFolder'] = season_folder
    payload['seriesType'] = series_type
    payload['tags'] = [int(tag_id)
                       for tag_id in tags_param if str(tag_id).isdigit()]
    payload['addOptions'] = {"monitor": monitor_episodes,
                             "searchForMissingEpisodes": search_for_missing}
    payload.pop('id', None)
    payload.pop('statistics', None)
    payload.setdefault('title', show_to_add.get('title'))
    payload.setdefault('tvdbId', int(tvdb_id))
    payload.setdefault('year', show_to_add.get('year'))
    payload.setdefault('titleSlug', show_to_add.get('titleSlug'))
    payload.setdefault('seasons', show_to_add.get('seasons', []))
    payload.setdefault('images', show_to_add.get('images', []))
    headers = {'Content-Type': 'application/json'}

    try:
        add_response = _sonarr_request(
            'post', '/series', data=payload, headers=headers)
        title_to_log = payload.get("title", f"TVDB ID {tvdb_id}")
        if add_response and isinstance(add_response, dict) and add_response.get('id'):
            logger.info(
                f"Show '{title_to_log}' added to Sonarr successfully. ID: {add_response.get('id')}")
            return f"Show '{show_title_for_msg}' added to Sonarr successfully!"

        elif add_response is None and _sonarr_request.last_response_status in [201, 202]:
            logger.info(
                f"Show '{title_to_log}' added to Sonarr successfully (empty response with status {_sonarr_request.last_response_status}).")
            return f"Show '{show_title_for_msg}' added to Sonarr successfully!"
        else:
            logger.warning(
                f"Sonarr add show '{title_to_log}' completed, but response was unexpected: {add_response}")
            return f"Show '{show_title_for_msg}' add request sent to Sonarr, but status is unclear. Please verify in Sonarr."
    except requests.exceptions.HTTPError as e:
        title_to_log_err = payload.get("title", f"TVDB ID {tvdb_id}")
        if e.response:
            logger.error(
                f"HTTPError adding Sonarr show '{title_to_log_err}': {e.response.status_code} - {e.response.text[:200]}", exc_info=True)
            err_text = e.response.text.lower()
            if e.response.status_code == 400:
                if "already exists with tvdb id" in err_text or "series has already been added" in err_text:
                    return f"Show '{show_title_for_msg}' is already in Sonarr."

                try:
                    err_json = e.response.json()
                    if isinstance(err_json, list) and err_json and err_json[0].get('errorMessage'):
                        return f"Sonarr: Failed to add show - {err_json[0]['errorMessage']}"

                    elif isinstance(err_json, dict) and err_json.get('message'):
                        return f"Sonarr: Failed to add show - {err_json['message']}"
                except json.JSONDecodeError:
                    pass
                return f"Sonarr: Failed to add show - Bad request (400). Details: {err_text[:100]}"
            return f"Sonarr: Failed to add show - HTTP {e.response.status_code}. Check Sonarr logs."
        return f"Sonarr: Failed to add show - HTTP Error. Check Sonarr logs."
    except ValueError as e:
        logger.error(f"ValueError adding Sonarr show: {e}", exc_info=True)
        return str(e)
    except Exception as e:
        title_to_log_unexp = payload.get("title", f"TVDB ID {tvdb_id}")
        logger.error(
            f"Unexpected error adding Sonarr show '{title_to_log_unexp}': {e}", exc_info=True)
        return f"Sonarr: Failed to add show - {type(e).__name__}. Check bot logs."
