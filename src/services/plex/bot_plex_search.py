import logging
from src.bot.bot_text_utils import escape_md_v1
from .bot_plex_core import _plex_request, get_plex_server_connection
import src.app.app_config_holder as app_config_holder

logger = logging.getLogger(__name__)


def search_plex_media(query_text: str):
    plex = get_plex_server_connection()
    if not plex:
        return {"error": "Plex not configured or connection failed."}
    try:

        max_results_config = app_config_holder.get_add_media_max_search_results()

        raw_results = _plex_request(
            plex.search, query_text, limit=max_results_config * 2)

        formatted_results = []
        escaped_query_text = escape_md_v1(query_text)

        if not raw_results:
            return {"results": [], "message": f"No results found in Plex for '{escaped_query_text}'."}

        allowed_types = ['movie', 'show']

        for item in raw_results:
            item_type = getattr(item, 'type', 'unknown')
            if item_type in allowed_types and hasattr(item, 'title') and hasattr(item, 'ratingKey'):
                year_str = f" ({item.year})" if hasattr(
                    item, 'year') and item.year else ""
                title_display = item.title

                summary_short = getattr(item, 'summary', "")
                if summary_short and len(summary_short) > 100:
                    summary_short = summary_short[:100] + "..."
                elif not summary_short:
                    summary_short = "No summary."

                formatted_results.append({
                    "id": item.ratingKey,
                    "title": title_display,
                    "year_str": year_str,
                    "type": item_type,
                    "summary_short": summary_short
                })

            if len(formatted_results) >= max_results_config:
                break

        if not formatted_results:
            return {"results": [], "message": f"No relevant (Movie/Show) results found in Plex for '{escaped_query_text}'."}

        return {
            "results": formatted_results,
            "message": f"Found {len(formatted_results)} relevant results for '{escaped_query_text}'.",
        }

    except Exception as e:
        logger.error(
            f"Error searching Plex for '{query_text}': {e}", exc_info=True)
        return {"error": "Error searching Plex. Check logs."}
