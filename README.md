# Media Catalog Telegram Bot

**Version:** (Refer to the `VERSION` file in the project root)
**License:** GNU General Public License v3.0 (see `LICENSE` file)

The Media Catalog Telegram Bot is a versatile tool designed to help you manage and interact with your digital media collection and related services directly from Telegram. It offers integration with popular self-hosted applications like Plex, Radarr, and Sonarr, along with features for local PC control and custom script execution.

## Key Features

*   **Plex Media Server Integration:**
    *   View "Now Playing" status and stop active streams.
    *   Browse "Recently Added" items from your Plex libraries.
    *   Search your Plex libraries for movies, TV shows, seasons, and individual episodes.
    *   View detailed metadata for Plex items.
    *   Trigger library scans and metadata refreshes for your Plex server.
    *   Perform server maintenance: clean bundles, empty trash, optimize database, view server info.

*   **Radarr (Movie Management) Integration:**
    *   Search for movies via Radarr (powered by TMDb).
    *   Add movies to Radarr with either default settings or a step-by-step customization flow.
    *   View and manage your Radarr download queue.
    *   Perform Radarr library maintenance: disk rescans, metadata refresh, file renaming.

*   **Sonarr (TV Show Management) Integration:**
    *   Search for TV shows via Sonarr (powered by TheTVDB).
    *   Add TV shows to Sonarr with default or customized settings.
    *   View and manage your Sonarr download queue.
    *   Access a list of "Wanted Episodes" and trigger searches.
    *   Perform Sonarr library maintenance: disk rescans, metadata refresh, file renaming.

*   **PC Control (Local Machine):**
    *   (Requires `pyautogui` and `pycaw` Python libraries)
    *   Control media playback, system volume, and mute.
    *   Initiate PC shutdown or restart commands (with confirmation).

*   **Application Launchers & Custom Scripts:**
    *   Configure buttons to launch applications or run custom scripts on the bot's host machine.

*   **User-Friendly Configuration:**
    *   Graphical User Interface (GUI) for setup and modification of settings (stored in `data/config.py`).
    *   A template is provided in `config_templates/config.py.default`.

*   **Interactive Telegram Menus:**
    *   Intuitive inline keyboard buttons for navigation.
    *   Persistent main menu and a dedicated status message area.

## Project Structure Overview

*   `MediaCatalog.py`: Main application script (in project root).
*   `src/`: Contains all core Python modules (app logic, bot handlers, services).
*   `data/`: For runtime data:
    *   `config.py`: **Your active configuration file (user-generated or copied from template).**
    *   `mediabot.log`: Bot activity and error logs.
    *   Persistence files (e.g., `mediabot_persistence.pickle`).
    *   Message ID files (e.g., `msg_id_menu.txt`).
    *   `search_results/`: Temporary storage for Radarr/Sonarr search results.
*   `build_tools/`: Scripts for building the application (e.g., `build_application.bat`).
*   `config_templates/`: Contains `config.py.default`.
*   `resources/`: Static resources like `ico.ico`.
*   `requirements/`: Contains `requirements.txt`.
*   `venv/`: Python virtual environment (created by user).

## Getting Started

For detailed instructions on Python installation, setting up the virtual environment, installing dependencies (from `requirements/requirements.txt`), and initial configuration, please refer to:

**`SETUP_INSTRUCTIONS.md`**

## Usage

Once the bot is set up and running (e.g., using `Run Media Catalog Bot.bat` on Windows, or `python MediaCatalog.py` from the project root after activating the venv), interact with it via Telegram.

Key Telegram commands:
*   `/start` or `/home`: Displays/refreshes the main menu.
*   `/settings`: Opens the configuration GUI on the bot's host.
*   `/status`: Refreshes the bot's universal status message.

For a guide on using the bot's menus, see:
**`BOT_USAGE.md`**

## Configuration (`data/config.py`)

The bot's behavior is controlled by `data/config.py`. A template is in `config_templates/config.py.default`. Use the GUI (`/settings`) for easy management.

Key settings:
*   Telegram Bot Token and Chat ID.
*   Enable/disable flags and API details for Plex, Radarr, Sonarr, PC Control.
*   Paths/names for custom scripts and launchers.
*   Logging level and UI preferences.

## Stopping the Bot

*   **`Run Media Catalog Bot.bat` (Windows background):** Use Task Manager to end the `python.exe` process running `MediaCatalog.py`.
*   **`python MediaCatalog.py` (terminal):** Press `Ctrl+C`.

## Building a Standalone Executable (Windows Optional)

Refer to `SETUP_INSTRUCTIONS.md` ("Optional: Creating a Standalone Executable") for using `build_tools/build_application.bat`.

## License

GNU General Public License v3.0. See `LICENSE`.