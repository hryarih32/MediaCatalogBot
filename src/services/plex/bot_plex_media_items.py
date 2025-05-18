import logging
import math
from src.bot.bot_text_utils import escape_md_v1, escape_md_v2, escape_for_inline_code
from .bot_plex_core import _plex_request, get_plex_server_connection
from plexapi.exceptions import PlexApiException, NotFound
import src.app.app_config_holder as app_config_holder

logger = logging.getLogger(__name__)


def get_recently_added_from_library(library_key_str: str, max_items: int = 10):
    plex = get_plex_server_connection()
    if not plex:
        return {"error": "Plex not configured or connection failed."}

    items_to_return = []
    try:
        section = _plex_request(plex.library.sectionByID, int(library_key_str))
        if not section:
            return {"error": f"Library with key {library_key_str} not found."}
        logger.info(
            f"Fetching up to {max_items} recently added for library '{section.title}' (type: {section.type})")
        if section.type == 'movie':
            recently_added_movies = _plex_request(
                section.recentlyAdded, maxresults=max_items)
            for item in recently_added_movies:
                items_to_return.append({
                    "type": "movie",
                    "ratingKey": item.ratingKey,
                    "display_text": f"{item.title} ({item.year})" if hasattr(item, 'year') else item.title
                })
        elif section.type == 'show':
            try:

                episodes = _plex_request(
                    section.all, libtype='episode', sort='addedAt:desc', maxresults=max_items * 2)
                for episode in episodes[:max_items]:
                    show_title = getattr(
                        episode, 'grandparentTitle', 'Unknown Show')
                    season_num = getattr(episode, 'parentIndex', '')
                    ep_num = getattr(episode, 'index', '')
                    ep_title = getattr(episode, 'title', 'Unknown Episode')
                    s_str = f"S{season_num:02d}" if isinstance(
                        season_num, int) else f"S{season_num}" if season_num else ""
                    e_str = f"E{ep_num:02d}" if isinstance(
                        ep_num, int) else f"E{ep_num}" if ep_num else ""
                    items_to_return.append({
                        "type": "episode",
                        "ratingKey": episode.ratingKey,
                        "display_text": f"{show_title} - {s_str}{e_str} - {ep_title}"
                    })
            except Exception as e_ep:
                logger.error(
                    f"Error fetching recent episodes for show library '{section.title}': {e_ep}", exc_info=True)
                return {"error": f"Could not fetch recent episodes for '{escape_md_v1(section.title)}'."}
        else:
            return {"error": f"Recently Added not supported for library type: {escape_md_v1(section.type)}."}
        if not items_to_return:
            return {"items": [], "message": f"No recently added items found in library '{escape_md_v1(section.title)}'."}
        return {"items": items_to_return, "message": f"Fetched {len(items_to_return)} recently added from '{escape_md_v1(section.title)}'."}
    except PlexApiException as e:
        if hasattr(e, 'response') and e.response and e.response.status_code == 401:
            return {"error": "Plex Error: Unauthorized. Check PLEX_TOKEN."}
        logger.error(
            f"Plex API error in get_recently_added_from_library (key {library_key_str}): {e}", exc_info=True)
        return {"error": "Error connecting to Plex or processing data."}
    except Exception as e:
        logger.error(
            f"Error getting recently added from library {library_key_str}: {e}", exc_info=True)
        return {"error": "Error getting recently added items. Check logs."}


def get_plex_item_details(rating_key_str: str):
    plex = get_plex_server_connection()
    if not plex:
        return {"error": "Plex not configured or connection failed."}
    try:
        rating_key = int(rating_key_str)
        item = _plex_request(plex.fetchItem, rating_key)
        if not item:
            return {"error": "Item not found in Plex."}
        details = {
            "ratingKey": item.ratingKey, "title": item.title, "type": item.type,
            "summary": getattr(item, 'summary', "N/A"), "rating": str(getattr(item, 'rating', "N/A")),
            "year": str(getattr(item, 'year', "N/A")),
            "directors": ", ".join([d.tag for d in getattr(item, 'directors', []) if hasattr(d, 'tag')]),
            "writers": ", ".join([w.tag for w in getattr(item, 'writers', []) if hasattr(w, 'tag')]),
            "genres": ", ".join([g.tag for g in getattr(item, 'genres', []) if hasattr(g, 'tag')]),
            "file_info": []
        }
        if item.type == 'episode':
            details["show_title"] = getattr(item, 'grandparentTitle', "N/A")
            season_num_detail = getattr(item, 'parentIndex', '')
            ep_num_detail = getattr(item, 'index', '')
            s_str_detail = f"S{season_num_detail:02d}" if isinstance(
                season_num_detail, int) else f"S{season_num_detail}" if season_num_detail else ""
            e_str_detail = f"E{ep_num_detail:02d}" if isinstance(
                ep_num_detail, int) else f"E{ep_num_detail}" if ep_num_detail else ""
            sep_se_detail = ""
            if s_str_detail and e_str_detail:
                sep_se_detail = ""
            details["season_episode"] = f"{s_str_detail}{sep_se_detail}{e_str_detail}"
            details["season_number_internal"] = season_num_detail
            details["show_rating_key_internal"] = getattr(item.show(
            ), 'ratingKey', None) if hasattr(item, 'show') and callable(item.show) else None
        total_size_bytes = 0
        if hasattr(item, 'media') and item.media:
            for medium in item.media:
                if hasattr(medium, 'parts') and medium.parts:
                    for part in medium.parts:
                        file_path = getattr(part, 'file', "Path not available")
                        file_size_bytes = getattr(part, 'size', 0)
                        if file_size_bytes is None:
                            file_size_bytes = 0
                        total_size_bytes += file_size_bytes
                        details["file_info"].append({
                            "path": file_path,
                            "size_gb": f"{file_size_bytes / (1024**3):.2f} GB" if file_size_bytes > 0 else "N/A"
                        })
        elif item.type == 'show':
            details["file_info"].append(
                {"path": "File info is available per episode for shows.", "size_gb": "N/A"})
        details["total_size_gb"] = f"{total_size_bytes / (1024**3):.2f} GB" if total_size_bytes > 0 else "N/A"
        return {"details": details}
    except NotFound:
        return {"error": f"Item with ratingKey {rating_key_str} not found."}
    except Exception as e:
        logger.error(
            f"Error getting Plex item details for ratingKey {rating_key_str}: {e}", exc_info=True)
        return {"error": "Error fetching item details from Plex. Check logs."}


def get_plex_show_seasons(show_rating_key_str: str):
    plex = get_plex_server_connection()
    if not plex:
        return {"error": "Plex not configured or connection failed."}
    try:
        show_rating_key = int(show_rating_key_str)
        show_item = _plex_request(plex.fetchItem, show_rating_key)
        if not show_item or show_item.type != 'show':
            return {"error": f"Item with ratingKey {show_rating_key} is not a show or not found."}
        seasons_data = []
        plex_seasons = _plex_request(show_item.seasons)
        for season_obj in plex_seasons:
            season_title = getattr(season_obj, 'title',
                                   f"Season {season_obj.index}")
            if season_obj.index == 0 and "Specials" not in season_title and "Season 0" in season_title:
                season_title = "Specials"
            seasons_data.append({
                "title": season_title, "season_number": season_obj.index,
                "ratingKey": season_obj.ratingKey, "show_rating_key": show_rating_key,
                "show_title": show_item.title
            })
        return {"seasons": seasons_data, "show_title": show_item.title, "show_rating_key": show_rating_key}
    except NotFound:
        return {"error": f"Show with ratingKey {show_rating_key_str} not found."}
    except Exception as e:
        logger.error(
            f"Error getting seasons for show {show_rating_key_str}: {e}", exc_info=True)
        return {"error": "Error fetching show seasons from Plex."}


def get_plex_season_episodes(show_rating_key_str: str, season_number_str: str):
    plex = get_plex_server_connection()
    if not plex:
        return {"error": "Plex not configured or connection failed."}
    try:
        show_rating_key = int(show_rating_key_str)
        show_item = _plex_request(plex.fetchItem, show_rating_key)
        if not show_item or show_item.type != 'show':
            return {"error": f"Item with ratingKey {show_rating_key} is not a show."}

        season_number = int(season_number_str)
        target_season = _plex_request(show_item.season, season=season_number)
        if not target_season:
            return {"error": f"Season {season_number} not found for show '{escape_md_v1(show_item.title)}'."}

        all_episodes_in_season = _plex_request(
            target_season.episodes)
        if not all_episodes_in_season:
            return {
                "records": [], "totalRecords": 0,
                "show_title": show_item.title, "season_title": target_season.title,
                "show_rating_key": show_rating_key, "season_number": season_number
            }

        episodes_data = []
        for ep_obj in all_episodes_in_season:
            ep_title = getattr(ep_obj, 'title', f"Episode {ep_obj.index}")
            s_num_disp = getattr(ep_obj, 'parentIndex', season_number)
            e_num_disp = getattr(ep_obj, 'index', '?')
            episodes_data.append({
                "ratingKey": ep_obj.ratingKey,

                "title": f"S{s_num_disp:02d}E{e_num_disp:02d} - {ep_title}",
                "show_rating_key": show_rating_key,
                "season_number": season_number
            })

        return {
            "records": episodes_data,

            "totalRecords": len(episodes_data),

            "show_title": show_item.title,
            "season_title": target_season.title,
            "show_rating_key": show_rating_key,
            "season_number": season_number
        }
    except NotFound:
        return {"error": f"Show or season not found (Show RK: {show_rating_key_str}, S#: {season_number_str})."}
    except Exception as e:
        logger.error(
            f"Error getting episodes for show {show_rating_key_str}, season {season_number_str}: {e}", exc_info=True)
        return {"error": "Error fetching episodes from Plex."}
