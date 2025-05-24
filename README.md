# Media Catalog Telegram Bot

**Version:** 2.0.0
[![GitHub Sponsors](https://img.shields.io/github/sponsors/hryarih32?style=social&label=Sponsor%20Project)](https://github.com/hryarih32/MediaCatalogBot#️-support-the-project)

**License:** GNU General Public License v3.0 (see `LICENSE` file)

The Media Catalog Telegram Bot is a versatile tool designed to help you manage and interact with your digital media collection and related services directly from Telegram. It offers integration with popular self-hosted applications like Plex, Radarr, and Sonarr, along with features for local PC control and custom script execution. Version 2.0.0 introduces user roles and a media request system.

## Key Features

*   **Multi-User Roles (New in 2.0.0):**
    *   `ADMIN` role for full control (primary admin defined in `config.py`).
    *   `STANDARD_USER` role for requesting media and viewing personal requests.
    *   (Full user management via GUI planned for a future update).

*   **Media Request System (New in 2.0.0):**
    *   `STANDARD_USER`s can search for and request Movies (via Radarr) and TV Shows (via Sonarr).
    *   `STANDARD_USER`s can view their submitted requests and their status (Pending, Approved, Rejected) in a "My Requests" menu.
    *   `ADMIN`s have an "Admin Requests" menu to view, approve, or reject pending user requests.
        *   Approval by an admin triggers the Radarr/Sonarr add flow for the admin (choice of default or custom settings).
        *   Rejection allows admins to provide an optional reason.
    *   Admins can view a history of processed requests.

*   **Plex Media Server Integration (Admin Focused):**
    *   View "Now Playing" status and stop active streams.
    *   Browse "Recently Added" items from your Plex libraries.
    *   Search your Plex libraries for movies, TV shows, seasons, and individual episodes.
    *   View detailed metadata for Plex items.
    *   Trigger library scans and metadata refreshes for your Plex server.
    *   Perform server maintenance: clean bundles, empty trash, optimize database, view server info.

*   **Radarr (Movie Management) Integration:**
    *   `ADMIN`s can search for movies and add them directly with default or custom settings.
    *   `STANDARD_USER`s can search for movies and submit them as requests.
    *   `ADMIN`s can view and manage the Radarr download queue and perform library maintenance.

*   **Sonarr (TV Show Management) Integration:**
    *   `ADMIN`s can search for TV shows and add them directly with default or custom settings.
    *   `STANDARD_USER`s can search for TV shows and submit them as requests.
    *   `ADMIN`s can view and manage the Sonarr download queue, "Wanted Episodes", and perform library maintenance.

*   **AB Download Manager Integration (Primary Admin Only):**
    *   The primary `ADMIN` (defined by `CHAT_ID` in `config.py`) can add direct downloads to AB Download Manager by providing a URL.
    *   Configurable ABDM API port and optional launcher via GUI.

*   **PC Control (Admin Focused, Local Machine):**
    *   (Requires `pyautogui` and `pycaw` Python libraries)
    *   Control media playback, system volume, and mute.
    *   Initiate PC shutdown or restart commands (with confirmation).

*   **Application Launchers & Custom Scripts (Admin Focused):**
    *   Configure buttons to launch applications (Plex, Sonarr, Radarr, Prowlarr, Torrent Client, AB Download Manager) or run custom scripts on the bot's host machine.

*   **User-Friendly Configuration:**
    *   Graphical User Interface (GUI) for setup and modification of settings (stored in `data/config.py`).
    *   A template is provided in `config_templates/config.py.default`.

*   **Interactive Telegram Menus:**
    *   Intuitive inline keyboard buttons for navigation.
    *   Persistent main menu (per user) and a dedicated status message area (per user).

## Project Structure Overview

*   `MediaCatalog.py`: Main application script (in project root).
*   `VERSION`: File containing the current bot version (e.g., `2.0.0`).
*   `LICENSE`: The license file for the project.
*   `src/`: Contains all core Python modules.
    *   `src/app/`: Core application logic, configuration, file utilities.
    *   `src/bot/`: Telegram bot specific logic (initialization, handlers, callback data).
    *   `src/config/`: Configuration definitions and management.
    *   `src/handlers/`: Callback query and command handlers, organized by feature.
        *   `src/handlers/admin_requests/`: Handlers for admin management of user requests.
        *   `src/handlers/user_requests/`: Handlers for users viewing their own requests.
        *   `src/handlers/abdm/`, `src/handlers/plex/`, `src/handlers/radarr/`, `src/handlers/sonarr/`, `src/handlers/pc_control/`, `src/handlers/shared/`
    *   `src/services/`: Integrations with external services (Plex, Radarr, Sonarr, ABDM).
*   `data/`: For runtime data (created by the bot on first run if it doesn't exist):
    *   `config.py`: **Your active configuration file.** (Generated from template or GUI).
    *   `requests.json`: Stores all user media requests.
    *   `mediabot.log`: Bot activity and error logs.
    *   `msg_id_menu_CHATID.txt`, `msg_id_universal_status_CHATID.txt`: Per-user message ID persistence files (these will be consolidated into `bot_state.json` in a future update).
    *   `msg_last_startup_time.txt`: Stores the last startup time of the bot.
    *   `search_results/`: Temporary storage for Radarr/Sonarr search results.
*   `build_tools/`: Scripts for building the application (e.g., `build_application.bat`).
*   `config_templates/`: Contains `config.py.default` (the template for `data/config.py`).
*   `resources/`: Static resources like `ico.ico` (for the GUI and build).
*   `requirements/`: Contains `requirements.txt`.
*   `venv/`: Python virtual environment (created by user during setup).

## Getting Started

For detailed instructions on Python installation, setting up the virtual environment, installing dependencies, and initial configuration, please refer to:

**`SETUP_INSTRUCTIONS.md`**

## Usage

Once the bot is set up and running (e.g., using `Run Media Catalog Bot.bat` on Windows, or `python MediaCatalog.py` from the project root after activating the venv), interact with it via Telegram.

Key Telegram commands:
*   `/start` or `/home`: Displays/refreshes the main menu (menu content varies by user role).
*   `/settings`: (Primary Admin Only) Opens the configuration GUI on the bot's host.
*   `/status`: (Admins and Standard Users) Refreshes the bot's universal status message for your chat.

For a guide on using the bot's menus and features, see:
**`BOT_USAGE.md`**

## Configuration (`data/config.py`)

The bot's behavior is controlled by `data/config.py`. Use the GUI (`/settings` by Primary Admin) for easy management.

Key settings:
*   **Telegram Bot Token:** Your unique bot token from `@BotFather`.
*   **Chat ID:** The numerical Telegram User ID of the **Primary Administrator**. This user has the highest level of access, including `/settings`.
*   Enable/disable flags and API details for Plex, Radarr, Sonarr, AB Download Manager, PC Control.
*   Paths/names for custom scripts and launchers.
*   Logging level and UI preferences (e.g., items per page in search results).

*(Full user management for adding other Admins and Standard Users via the GUI is planned for a future update. For version 2.0.0, any user interacting with the bot who is not the Primary Admin is treated as a Standard User for media request features).*

## Stopping the Bot

*   **`Run Media Catalog Bot.bat` (Windows background):** Use Task Manager to end the `python.exe` process running `MediaCatalog.py`.
*   **`python MediaCatalog.py` (terminal):** Press `Ctrl+C`.

## Building a Standalone Executable (Windows Optional)

Refer to `SETUP_INSTRUCTIONS.md` ("Optional: Creating a Standalone Executable") for using `build_tools/build_application.bat`. This bundles Python and dependencies into a single `.exe` file.

## ❤️ Support the Project

If you find this Media Catalog Telegram Bot useful and appreciate the work, please consider showing your support! Every contribution helps in maintaining and improving the bot.

### Sponsor with Cryptocurrency

You can support the project by sending cryptocurrency to the following addresses. **Please double-check the address and ensure you are sending on the correct network before confirming any transaction.**

*   **Bitcoin (BTC - SegWit):**
    *(Please send only Bitcoin (BTC) to this address. Ensure your wallet supports sending to SegWit (bech32/bc1...) addresses.)*
    ```
    bc1q6gxjcw9krnm5zyx8xxxx93aq7q965ygxnpefy3
    ```

*   **Ethereum (ETH) & USDT (ERC-20 Token on Ethereum Network):**
    *(This single address accepts both native Ethereum (ETH) and USDT tokens that are on the Ethereum ERC-20 network.)*
    ```
    0x419df8dc3d710af15998d1b307140952ef147095
    ```

### Other Ways to Support
*   Consider **starring the project** on [GitHub](https://github.com/hryarih32/MediaCatalogBot)! ⭐
*   Spread the word about the bot if you find it helpful.

Thank you for your support!

## License

This project is licensed under the GNU General Public License v3.0 - see the `LICENSE` file for details.

## Contributing

Contributions, bug reports, and feature requests are welcome! Please feel free to open an issue on the [project's GitHub repository](https://github.com/hryarih32/MediaCatalogBot/issues).

## Disclaimer

This software is provided "as is", without warranty of any kind, express or implied. Use responsibly and at your own risk. The author(s) are not responsible for any unintended consequences resulting from its use or misuse. Always keep your API keys and sensitive information secure.