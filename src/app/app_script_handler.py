import logging
import os

import subprocess
import src.app.app_config_holder as app_config_holder

logger = logging.getLogger(__name__)

SERVICE_LAUNCHER_IDENTIFIERS = {
    "PLEX": "PLEX_LAUNCHER",
    "SONARR": "SONARR_LAUNCHER",
    "RADARR": "RADARR_LAUNCHER",
    "PROWLARR": "PROWLARR_LAUNCHER",
    "TORRENT": "TORRENT_LAUNCHER"
}


async def run_script_by_identifier(identifier: str) -> str:
    script_enabled = False
    script_name = f"Script/Launcher '{identifier}'"
    script_path = None

    if identifier.startswith("SCRIPT_"):
        try:
            script_number = int(identifier.split("_")[1])
            if 1 <= script_number <= 3:
                script_enabled = app_config_holder.is_script_enabled(
                    script_number)
                script_name = app_config_holder.get_script_name(
                    script_number) or f"Script {script_number}"
                script_path = app_config_holder.get_script_path(script_number)
        except (ValueError, IndexError):
            logger.error(
                f"Invalid custom script identifier format: {identifier}")
            return f"❌ Invalid script identifier: {identifier}"
    elif identifier in SERVICE_LAUNCHER_IDENTIFIERS:
        service_prefix = identifier
        script_enabled = app_config_holder.is_service_launcher_enabled(
            service_prefix)
        script_name = app_config_holder.get_service_launcher_name(
            service_prefix) or f"Launch {service_prefix.capitalize()}"
        script_path = app_config_holder.get_service_launcher_path(
            service_prefix)
    else:
        logger.error(f"Unknown script/launcher identifier: {identifier}")
        return f"❌ Unknown script or launcher: {identifier}"

    if not script_enabled:
        return f"ℹ️ '{script_name}' is not enabled in configuration."

    if not script_path or not os.path.exists(script_path):
        logger.warning(
            f"Attempted to run '{script_name}' but path is invalid or missing: {script_path}")
        return f"❌ Path for '{script_name}' not found or not configured correctly."

    logger.info(
        f"Attempting to start '{script_name}' from path: {script_path}")
    try:
        if os.name == 'nt':
            os.startfile(script_path)
        else:

            subprocess.Popen([script_path], shell=False, stdin=None,
                             stdout=None, stderr=None, close_fds=True)

        logger.info(f"Launch command issued for '{script_name}'.")
        return f"✅ Launch command for '{script_name}' sent. Please check your system."

    except FileNotFoundError:
        logger.error(
            f"Error starting '{script_name}': Configured path not found at runtime - {script_path}", exc_info=True)
        return f"❌ Error starting '{script_name}': Path not found."
    except PermissionError:
        logger.error(
            f"Permission error starting '{script_name}' from '{script_path}'. Ensure it's executable.", exc_info=True)
        return f"❌ Permission error for '{script_name}'. Check executable permissions."
    except Exception as e:
        logger.error(
            f"Error starting '{script_name}' from '{script_path}': {e}", exc_info=True)
        return f"❌ Error starting '{script_name}': {type(e).__name__}."


def is_process_running_by_path(script_path_to_check: str, process_alias_for_log: str) -> bool:

    if not script_path_to_check:
        return False
    executable_name = os.path.basename(script_path_to_check)
    if not executable_name:
        return False

    if os.name == 'nt':
        try:

            command = f'tasklist /FI "IMAGENAME eq {executable_name}" /NH /FO CSV'

            output = subprocess.check_output(command, shell=True, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                                             creationflags=subprocess.CREATE_NO_WINDOW).decode('utf-8', errors='ignore').strip()

            is_running = f'"{executable_name.lower()}"' in output.lower()
            if is_running:
                logger.debug(
                    f"Process check for '{process_alias_for_log}' (IMAGENAME: {executable_name}): Found in tasklist.")
            else:
                logger.debug(
                    f"Process check for '{process_alias_for_log}' (IMAGENAME: {executable_name}): Not found in tasklist.")
            return is_running
        except subprocess.CalledProcessError:

            logger.debug(
                f"Tasklist found no process with IMAGENAME {executable_name} (for '{process_alias_for_log}').")
            return False
        except FileNotFoundError:
            logger.error(
                "tasklist command not found. Cannot check if script is running.")
            return False
        except Exception as e:
            logger.error(
                f"Exception while checking if script '{executable_name}' (for '{process_alias_for_log}') is running: {e}", exc_info=False)
            return False
    else:
        try:

            command = ["pgrep", "-f", script_path_to_check]
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, _ = process.communicate()
            is_running = process.returncode == 0 and bool(stdout.strip())
            if is_running:
                logger.debug(
                    f"Process check for '{process_alias_for_log}' (path: {script_path_to_check}): Found with pgrep -f.")
            else:
                logger.debug(
                    f"Process check for '{process_alias_for_log}' (path: {script_path_to_check}): Not found with pgrep -f.")
            return is_running
        except FileNotFoundError:
            logger.warning(
                f"pgrep command not found. Cannot reliably check if '{process_alias_for_log}' is running on non-Windows.")
            return False
        except Exception as e:
            logger.error(
                f"Exception checking script status on non-Windows for '{process_alias_for_log}' (path: {script_path_to_check}): {e}", exc_info=False)
            return False


async def run_configured_script(script_number: int) -> str:
    """Helper to run one of the 3 configured custom scripts."""
    return await run_script_by_identifier(f"SCRIPT_{script_number}")


def is_script_running(script_number: int) -> bool:
    """Checks if one of the 3 configured custom scripts appears to be running."""
    script_path = app_config_holder.get_script_path(script_number)
    script_name = app_config_holder.get_script_name(
        script_number) or f"Script {script_number}"
    if not script_path:
        return False
    return is_process_running_by_path(script_path, script_name)
