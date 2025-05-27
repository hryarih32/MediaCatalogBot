
import logging
import os
import subprocess

import src.app.user_manager as user_manager

import src.app.app_config_holder as app_config_holder

logger = logging.getLogger(__name__)

_dynamic_launchers_cache = None
_dynamic_launchers_cache_timestamp = 0
DYNAMIC_LAUNCHERS_CACHE_TTL = 300


def _load_all_dynamic_launchers_from_state(force_reload: bool = False) -> list[dict]:
    """
    Loads the dynamic launchers list from bot_state.json via user_manager.
    Uses a simple time-based cache.
    """
    global _dynamic_launchers_cache, _dynamic_launchers_cache_timestamp

    current_time = os.times().system
    if not force_reload and \
       _dynamic_launchers_cache is not None and \
       (current_time - _dynamic_launchers_cache_timestamp < DYNAMIC_LAUNCHERS_CACHE_TTL):
        logger.debug("Returning cached dynamic launchers.")
        return _dynamic_launchers_cache

    logger.debug("Loading dynamic launchers from bot_state via user_manager.")

    launchers_list = user_manager.get_dynamic_launchers()

    if not isinstance(launchers_list, list):
        logger.error(
            f"Dynamic launchers data from user_manager is not a list: {type(launchers_list)}. Returning empty list.")
        _dynamic_launchers_cache = []
    else:
        _dynamic_launchers_cache = launchers_list

    _dynamic_launchers_cache_timestamp = current_time
    logger.info(
        f"Dynamic launchers cache updated with {len(_dynamic_launchers_cache)} items.")
    return _dynamic_launchers_cache


def get_all_dynamic_launchers(force_refresh: bool = False) -> list[dict]:
    """Returns a list of all configured dynamic launchers."""
    return _load_all_dynamic_launchers_from_state(force_reload=force_refresh)


def get_all_subgroups(force_refresh: bool = False) -> list[str]:
    """Returns a sorted, unique list of all subgroup names from dynamic launchers."""
    launchers = get_all_dynamic_launchers(force_refresh=force_refresh)
    subgroups = set()
    for launcher in launchers:
        if launcher.get("subgroup"):
            subgroups.add(launcher["subgroup"])
    return sorted(list(subgroups))


def get_launchers_by_subgroup(subgroup_name: str | None, force_refresh: bool = False) -> list[dict]:
    """
    Returns a list of launchers filtered by a specific subgroup name.
    If subgroup_name is None, returns launchers with no subgroup.
    """
    launchers = get_all_dynamic_launchers(force_refresh=force_refresh)
    if subgroup_name is None:
        return [l for l in launchers if not l.get("subgroup")]
    else:
        return [l for l in launchers if l.get("subgroup") == subgroup_name]


def get_launcher_details(launcher_id: str, force_refresh: bool = False) -> dict | None:
    """Retrieves details for a specific dynamic launcher by its ID."""
    if not launcher_id:
        return None
    launchers = get_all_dynamic_launchers(force_refresh=force_refresh)
    for launcher in launchers:
        if launcher.get("id") == launcher_id:
            return launcher.copy()
    return None


def run_dynamic_launcher(launcher_id: str) -> str:
    """
    Executes the dynamic launcher identified by launcher_id.
    Returns a status message.
    """
    if not launcher_id:
        return "❌ Error: No launcher ID provided."

    launcher_details = get_launcher_details(
        launcher_id, force_refresh=True)

    if not launcher_details:
        return f"❌ Error: Launcher with ID '{launcher_id}' not found."

    launcher_name = launcher_details.get(
        "name", f"Unnamed Launcher (ID: {launcher_id})")
    launcher_path = launcher_details.get("path")

    if not launcher_path:
        logger.warning(
            f"Attempted to run launcher '{launcher_name}' but path is missing.")
        return f"❌ Path for launcher '{launcher_name}' is not configured."

    if not os.path.exists(launcher_path):

        logger.warning(
            f"Attempted to run launcher '{launcher_name}' but path does not exist: {launcher_path}")
        return f"❌ Path for launcher '{launcher_name}' not found on system: {launcher_path}"

    logger.info(
        f"Attempting to start dynamic launcher '{launcher_name}' from path: {launcher_path}")
    try:
        if os.name == 'nt':
            os.startfile(launcher_path)
        else:

            subprocess.Popen([launcher_path], shell=False, stdin=None,
                             stdout=None, stderr=None, close_fds=True)

        logger.info(
            f"Launch command issued for dynamic launcher '{launcher_name}'.")
        return f"✅ Launch command for '{launcher_name}' sent. Please check your system."

    except FileNotFoundError:
        logger.error(
            f"Error starting launcher '{launcher_name}': Path not found at runtime - {launcher_path}", exc_info=True)
        return f"❌ Error starting '{launcher_name}': Path not found."
    except PermissionError:
        logger.error(
            f"Permission error starting launcher '{launcher_name}' from '{launcher_path}'. Ensure it's executable.", exc_info=True)
        return f"❌ Permission error for '{launcher_name}'. Check executable permissions."
    except Exception as e:
        logger.error(
            f"Error starting dynamic launcher '{launcher_name}' from '{launcher_path}': {e}", exc_info=True)
        return f"❌ Error starting '{launcher_name}': {type(e).__name__}."


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    print("Launcher Manager - Test Area")
