import os
import json
import logging
import requests
from src.app.app_file_utils import get_search_results_file_path
from src.services.radarr.bot_radarr_core import _radarr_request
import src.app.app_config_holder as app_config_holder


logger = logging.getLogger(__name__)

MOVIE_RESULTS_FILE_NAME = 'movie_search_results.json'


def get_movie_results_file_path_local():
    return get_search_results_file_path(MOVIE_RESULTS_FILE_NAME)


def save_results(filename, results):
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(results, file, indent=4)
        logger.info(
            f"Saved {len(results)} Radarr search results to {filename}")
    except IOError:
        logger.warning(
            f"IOError saving Radarr results to {filename}", exc_info=True)
        pass


def load_results(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                data = json.load(file)
                logger.info(
                    f"Loaded {len(data)} Radarr results from {filename}")
                return data
        except (IOError, json.JSONDecodeError) as e:
            logger.warning(
                f"Error loading Radarr results from {filename}: {e}. Removing corrupt file.", exc_info=True)
            try:
                os.remove(filename)
            except OSError:
                pass
    return []


def get_root_folders():
    try:
        folders = _radarr_request('get', '/rootfolder')
        if folders and isinstance(folders, list):
            accessible_folders = [rf for rf in folders if rf.get('accessible')]
            if accessible_folders:
                return [{'id': rf['id'], 'path': rf['path']} for rf in accessible_folders]
            return [{'id': rf['id'], 'path': rf['path']} for rf in folders]
        return []
    except Exception as e:
        logger.error(f"Error getting Radarr root folders: {e}", exc_info=True)
        return []


def get_quality_profiles():
    try:
        profiles = _radarr_request('get', '/qualityprofile')
        if profiles and isinstance(profiles, list):
            return [{'id': p['id'], 'name': p['name']} for p in profiles]
        return []
    except Exception as e:
        logger.error(
            f"Error getting Radarr quality profiles: {e}", exc_info=True)
        return []


def get_tags():
    try:
        tags_list = _radarr_request('get', '/tag')
        if tags_list and isinstance(tags_list, list):
            return [{'id': t['id'], 'label': t['label']} for t in tags_list]
        return []
    except Exception as e:
        logger.error(f"Error getting Radarr tags: {e}", exc_info=True)
        return []


def get_minimum_availability_options():
    return [
        {"value": "announced", "label": "Announced"},
        {"value": "inCinemas", "label": "In Cinemas"},
        {"value": "released", "label": "Released"},
        {"value": "preDB", "label": "PreDB"}
    ]


def get_default_root_folder_id():
    try:
        root_folders = get_root_folders()
        if root_folders and len(root_folders) > 0:
            return root_folders[0]['id']
        return None
    except Exception as e:
        logger.error(
            f"Error getting default Radarr root folder ID: {e}", exc_info=True)
        return None


def get_default_quality_profile_id():
    desired_name_keywords = ["1080p", "hd", "good"]
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
            f"Error getting default Radarr quality profile ID: {e}", exc_info=True)
        return None


def search_movie(query):
    params = {'term': query}
    results_file_full_path = get_movie_results_file_path_local()
    max_results_config = app_config_holder.get_add_media_max_search_results()

    try:
        results = _radarr_request('get', '/movie/lookup', params=params)
        if not results or not isinstance(results, list) or len(results) == 0:

            return f'No Radarr results found for your query: \'{query}\'.'
        raw_count = len(results)
        filtered_results = [m for m in results if not m.get(
            'id') and not m.get('path')]
        filtered_count_after_initial = len(filtered_results)
        if not filtered_results and results:
            first_result_tmdb_id = results[0].get('tmdbId')
            if first_result_tmdb_id:
                try:
                    existing = _radarr_request(
                        'get', f'/movie?tmdbId={first_result_tmdb_id}')
                    if existing:
                        return "All Radarr results found are already in your library."
                except Exception:
                    pass
            filtered_results = results
        if not filtered_results:

            return 'No new Radarr results found (they might already be in your library).'
        display_results = filtered_results[:max_results_config]
        logger.info(
            f"Radarr search for '{query}' found {raw_count} raw, {filtered_count_after_initial} initially filtered, limited to {len(display_results)} results based on config ({max_results_config}).")
        save_results(results_file_full_path, display_results)
        return display_results
    except ValueError as e:
        logger.error(f"Radarr search ValueError: {e}", exc_info=True)
        return f"Radarr configuration error: {str(e)}"
    except requests.exceptions.HTTPError as e:
        logger.error(f"Radarr search HTTPError: {e}", exc_info=True)
        if e.response and e.response.status_code == 401:
            return "Radarr API Key is invalid or unauthorized."
        return "Error communicating with Radarr. Check logs."
    except Exception as e:
        logger.error(f"Error searching Radarr: {e}", exc_info=True)

        return f"Error searching Radarr: {type(e).__name__}. Check logs."


def add_movie(movie_tmdb_id, radarr_movie_object, quality_profile_id, root_folder_path_or_id,
              minimum_availability="released", monitored=True, search_on_add=True, tags=None,
              add_options_monitor="movieOnly"):
    root_folder_path_value = root_folder_path_or_id
    if isinstance(root_folder_path_or_id, int):
        all_folders = get_root_folders()
        found_folder = next(
            (folder for folder in all_folders if folder['id'] == root_folder_path_or_id), None)
        if found_folder:
            root_folder_path_value = found_folder['path']
        else:
            return f"Error: Root folder ID {root_folder_path_or_id} not found in Radarr."

    tags_param = tags if tags is not None else []
    movie_title_for_msg = radarr_movie_object.get(
        'title', f"TMDB ID {movie_tmdb_id}")

    try:
        existing_movies = _radarr_request(
            'get', f'/movie?tmdbId={movie_tmdb_id}')
        if existing_movies and isinstance(existing_movies, list) and len(existing_movies) > 0:
            movie_title_existing = existing_movies[0].get(
                'title', f"TMDB ID {movie_tmdb_id}")
            return f"Movie '{movie_title_existing}' is already in Radarr."
        movie_details_to_add = radarr_movie_object
        if not movie_details_to_add or not movie_details_to_add.get("title"):
            logger.error(
                f"Invalid movie_details_to_add object for TMDB ID {movie_tmdb_id}. Object: {movie_details_to_add}")
            return f"Could not use provided movie details for TMDB ID {movie_tmdb_id}."
    except requests.exceptions.HTTPError as e:
        logger.error(
            f"HTTPError looking up movie {movie_tmdb_id} in Radarr: {e}", exc_info=True)
        return f"Error looking up movie in Radarr: HTTP {e.response.status_code if e.response else 'Unknown'}"
    except Exception as e:
        logger.error(
            f"Error looking up movie {movie_tmdb_id} in Radarr: {e}", exc_info=True)
        return f"Error looking up movie in Radarr: {type(e).__name__}"

    data = movie_details_to_add.copy()
    data['qualityProfileId'] = int(quality_profile_id)
    data['rootFolderPath'] = root_folder_path_value
    data['monitored'] = monitored
    data['minimumAvailability'] = minimum_availability
    data['tags'] = [int(tag_id)
                    for tag_id in tags_param if str(tag_id).isdigit()]
    data['addOptions'] = {"searchForMovie": search_on_add,
                          "monitor": add_options_monitor}
    data.pop('id', None)
    data.pop('path', None)
    data.setdefault('title', movie_details_to_add.get('title'))
    data.setdefault('tmdbId', int(movie_tmdb_id))
    data.setdefault('year', movie_details_to_add.get('year'))
    data.setdefault('titleSlug', movie_details_to_add.get('titleSlug'))
    data.setdefault('images', movie_details_to_add.get('images', []))
    headers = {'Content-Type': 'application/json'}

    try:
        add_response = _radarr_request(
            'post', '/movie', data=data, headers=headers)
        if add_response and isinstance(add_response, dict) and add_response.get('id'):
            return f"Movie '{movie_title_for_msg}' added to Radarr successfully!"
        elif add_response is None and _radarr_request.last_response_status in [201, 202]:
            return f"Movie '{movie_title_for_msg}' added to Radarr successfully!"
        else:
            logger.warning(
                f"Radarr add movie '{data['title']}' completed, but response was unexpected: {add_response}")
            return f"Movie '{movie_title_for_msg}' add request sent to Radarr, but status is unclear. Please verify in Radarr."
    except requests.exceptions.HTTPError as e:
        if e.response:
            logger.error(
                f"HTTPError adding Radarr movie '{data['title']}': {e.response.status_code} - {e.response.text[:200]}", exc_info=True)
            err_text = e.response.text.lower()
            if e.response.status_code == 400:
                if "already been added" in err_text or "already exists with tmdbid" in err_text:
                    return f"Movie '{movie_title_for_msg}' is already in Radarr."
                try:
                    err_json = e.response.json()
                    if isinstance(err_json, list) and err_json and err_json[0].get('errorMessage'):
                        return f"Radarr: Failed to add movie - {err_json[0]['errorMessage']}"
                    elif isinstance(err_json, dict) and err_json.get('message'):
                        return f"Radarr: Failed to add movie - {err_json['message']}"
                except json.JSONDecodeError:
                    pass
                return f"Radarr: Failed to add movie - Bad request (400). Details: {err_text[:100]}"
            return f"Radarr: Failed to add movie - HTTP {e.response.status_code}. Check Radarr logs."
        return f"Radarr: Failed to add movie - HTTP Error. Check Radarr logs."
    except ValueError as e:
        logger.error(
            f"ValueError adding Radarr movie '{data['title']}': {e}", exc_info=True)
        return str(e)
    except Exception as e:
        logger.error(
            f"Unexpected error adding Radarr movie '{data['title']}': {e}", exc_info=True)
        return f"Radarr: Failed to add movie - {type(e).__name__}. Check bot logs."
