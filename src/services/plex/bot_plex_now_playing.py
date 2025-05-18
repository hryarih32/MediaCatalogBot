import logging
from src.bot.bot_text_utils import escape_md_v1, escape_md_v2
from .bot_plex_core import _plex_request, get_plex_server_connection
from plexapi.exceptions import PlexApiException, NotFound, BadRequest as PlexApiBadRequest

logger = logging.getLogger(__name__)


def get_now_playing_structured():
    plex = get_plex_server_connection()
    if not plex:

        return {"error": "Plex not configured or connection failed.", "playing": [], "summary_text": escape_md_v2("Plex not configured/connection failed.")}

    try:
        sessions = _plex_request(plex.sessions)
        if not sessions:
            return {"playing": [], "summary_text": escape_md_v2("Nothing is currently playing.")}

        playing_items = []

        summary_parts = [escape_md_v2("*Now Playing:*\n")]
        for session in sessions:
            user_title_raw = session.user.title if session.user else "Unknown User"
            media_title_raw = session.title or "Unknown Title"

            user_md = escape_md_v2(user_title_raw)
            title_md = escape_md_v2(media_title_raw)
            media_type_md = escape_md_v2(session.type or "unknown")
            state_raw = session.players[0].state if session.players else "Unknown State"
            state_md = escape_md_v2(state_raw)

            progress_percent = 0
            if hasattr(session, 'duration') and session.duration and \
               hasattr(session, 'viewOffset') and session.viewOffset is not None:
                if session.duration > 0:
                    progress_percent = round(
                        session.viewOffset / session.duration * 100, 1)

            progress_percent_md = escape_md_v2(f"{progress_percent}%")

            item_summary = f"\\- *User:* {user_md}\n  *Title:* {title_md} \\({media_type_md}\\)\n  *State:* {state_md} \\({progress_percent_md}\\)\n"

            session_id_for_stop = getattr(session, 'sessionKey', None)
            if not session_id_for_stop and hasattr(session, 'session') and session.session:
                session_id_for_stop = getattr(session.session, 'id', None)

            player_identifier = None
            if session.players:
                player_identifier = getattr(
                    session.players[0], 'machineIdentifier', None)

            if not session_id_for_stop and not player_identifier:
                logger.warning(
                    f"Could not determine a unique sessionKey/ID or player ID for session: User='{user_title_raw}', Title='{media_title_raw}'. Stop button might not work reliably.")

            item_data = {
                'user_title': user_title_raw,
                'media_title': media_title_raw,
                'type': session.type,
                'session_id_for_stop': session_id_for_stop,
                'player_identifier_for_stop': player_identifier,
                'summary_text_md': item_summary
            }

            if session.type == 'episode':
                show_title_md_v2 = escape_md_v2(
                    session.grandparentTitle or "Unknown Show")
                season_index_md_v2 = escape_md_v2(
                    str(session.parentIndex) if session.parentIndex is not None else "N/A")
                episode_index_md_v2 = escape_md_v2(
                    str(session.index) if session.index is not None else "N/A")
                item_data['summary_text_md'] += f"  *Show:* {show_title_md_v2}\n  *Season:* {season_index_md_v2}, *Episode:* {episode_index_md_v2}\n"
            elif session.type == 'movie' and hasattr(session, 'year'):
                year_str_md_v2 = escape_md_v2(
                    str(session.year) if session.year else "N/A")
                item_data['summary_text_md'] += f"  *Year:* {year_str_md_v2}\n"

            item_data['summary_text_md'] += "\n"
            summary_parts.append(item_data['summary_text_md'])
            playing_items.append(item_data)

        full_summary_text = "".join(summary_parts).strip()
        if not playing_items:
            full_summary_text = escape_md_v2("Nothing is currently playing.")

        return {"playing": playing_items, "summary_text": full_summary_text}

    except Exception as e:
        logger.error(
            f"Error in get_now_playing_structured: {e}", exc_info=True)
        return {"error": "Error fetching 'Now Playing' data from Plex.", "playing": [], "summary_text": escape_md_v2("Error fetching 'Now Playing' data.")}


def stop_plex_stream(session_id_to_stop=None, player_identifier_to_stop=None):
    plex = get_plex_server_connection()
    if not plex:

        return escape_md_v2("Plex not configured or connection failed to stop stream.")
    if not session_id_to_stop and not player_identifier_to_stop:
        logger.warning(
            "Attempted to stop Plex stream with no session or player ID.")

        return escape_md_v2("⚠️ No session or player ID provided to stop.")

    try:
        if player_identifier_to_stop:
            try:
                client = _plex_request(plex.client, player_identifier_to_stop)
                if client:
                    try:
                        _plex_request(
                            client.stop, reason="Stopped via Telegram Bot")
                    except TypeError:
                        _plex_request(client.stop)
                    logger.info(
                        f"Successfully sent stop command to Plex client: '{client.title}' (ID: {player_identifier_to_stop})")

                    return f"✅ Stop command sent to player: *{escape_md_v2(client.title)}*\\."
            except NotFound:
                logger.warning(
                    f"Player with machineIdentifier '{player_identifier_to_stop}' not found. Will try session ID if available.")
            except PlexApiBadRequest as e_client_stop:
                logger.error(
                    f"BadRequest stopping client {player_identifier_to_stop}: {e_client_stop}")
            except Exception as e_client:
                logger.error(
                    f"Error stopping client {player_identifier_to_stop}: {e_client}")

        if session_id_to_stop:
            target_session_obj = None
            current_sessions = _plex_request(plex.sessions)
            for s in current_sessions:
                s_key = getattr(s, 'sessionKey', None)
                if not s_key and hasattr(s, 'session') and s.session:
                    s_key = getattr(s.session, 'id', None)
                if s_key and str(s_key) == str(session_id_to_stop):
                    target_session_obj = s
                    break
            if target_session_obj:
                _plex_request(target_session_obj.stop,
                              reason="Stopped via Telegram Bot")
                user_title = target_session_obj.user.title if target_session_obj.user else "Unknown User"
                media_title = target_session_obj.title or "Unknown Title"
                logger.info(
                    f"Successfully sent stop command to Plex session: User='{user_title}', Title='{media_title}', SessionID='{session_id_to_stop}'")

                return f"✅ Stop command sent for stream: *{escape_md_v2(media_title)}* \\(User: *{escape_md_v2(user_title)}*\\)\\."
            else:
                logger.warning(
                    f"Could not find Plex session with ID '{session_id_to_stop}' to stop. It might have already ended.")
                if player_identifier_to_stop:
                    return escape_md_v2("⚠️ Player not found and corresponding session also not found or already ended.")
                return escape_md_v2("⚠️ Stream session not found or already ended.")

        if player_identifier_to_stop and not session_id_to_stop:
            return escape_md_v2("⚠️ Could not stop player (not found or error) and no session ID was available to try as fallback.")

        return escape_md_v2("⚠️ Could not determine how to stop the stream with provided identifiers.")

    except NotFound:
        logger.warning(
            f"Plex session/client not found (NotFound exception). ID used: session='{session_id_to_stop}', player='{player_identifier_to_stop}'.")
        return escape_md_v2("⚠️ Stream not found (may have already ended).")
    except PlexApiBadRequest as pe:
        logger.error(
            f"Plex API BadRequest during stop stream operation: {pe}", exc_info=True)
        return escape_md_v2("⚠️ Plex returned a bad request trying to stop stream. Client might not support it.")
    except Exception as e:
        logger.error(
            f"Error stopping Plex stream (session: {session_id_to_stop}, player: {player_identifier_to_stop}): {e}", exc_info=True)
        return escape_md_v2(f"⚠️ Error stopping Plex stream. Check logs.")
