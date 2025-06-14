# Media Catalog Telegram Bot

**Version: 3.3.0**
[![GitHub Sponsors](https://img.shields.io/github/sponsors/hryarih32?style=social&label=Sponsor%20Project)](https://github.com/hryarih32/MediaCatalogBot#️-support-the-project)

**License:** GNU General Public License v3.0 (see `LICENSE` file)

The Media Catalog Telegram Bot is a versatile tool designed to help you manage and interact with your digital media collection and related services directly from Telegram. It integrates with Plex, Radarr, Sonarr, and AB Download Manager, and includes features for PC control, dynamic script/application launching, a ticketing system, and robust user management. Version 3.3.0 introduces a comprehensive ticketing system, API status indicators, and significant UI enhancements.

## Core Functionality

*   **Multi-User System with Roles:**
    *   **Primary Administrator:** Defined by `CHAT_ID` in `config.py`. Full control, including bot settings, dynamic launcher management, and the ability to assign other users as `ADMIN`.
    *   **Administrator (`ADMIN`):** Can be assigned by Primary Admin. Access to most control features, direct media addition, and management of user media requests (can approve users as `STANDARD_USER`).
    *   **Standard User (`STANDARD_USER`):** Can search/request media, view their own request statuses, and search/browse Plex content including item details.
    *   **Unknown User (`UNKNOWN`):** New users interacting with the bot; presented with an option to request access.
*   **User Access Request & Management System (Primary Admin Focused):**
    *   Unknown users can request access to the bot.
    *   The Primary Administrator has a unified "Manage Users & Requests" menu.
        *   View pending access requests and approve (assigning `ADMIN` or `STANDARD_USER` roles) or deny them.
        *   View a list of all existing users (excluding self).
        *   Change the role of existing users (Admin, Standard User).
        *   Remove users (revokes access).
        *   Add new users by providing their Telegram Chat ID and assigning a role.
    *   Other Administrators can view and process *media* requests but do not have access to the unified user management/access request menu.
*   **Media Request Workflow:**
    *   Standard users can search for movies (Radarr) and TV shows (Sonarr) and submit them as requests for admin approval via the "📮 Requests" menu.
    *   Administrators can directly add media or approve/reject user requests. Media request status is updated accurately upon completion or cancellation of the add flow.
    *   Users can track the status of their requests via a "My Requests" menu.
*   **Ticketing System:**
    *   Users can create, view, reply to, and close their own support tickets.
    *   Administrators can manage all open tickets, reply to users, and close tickets.
    *   Notifications for ticket events are handled via the Universal Status Message.
*   **Service Integrations:**
    *   **API Status Indicators (Admin Main Menu):** Admins see live status (Online, Offline, Config Error, Disabled, Unknown) for Plex, Radarr, Sonarr, and ABDM.
    *   **Plex:**
        *   View "Now Playing" status and stop streams (Admin).
        *   View "Recently Added" items (Admin).
        *   Search Plex content (Admin & Standard User: view rich results and navigate item, season, episode details). Administrative actions like "Refresh Metadata" are restricted to Admins.
        *   Library & Server Tools (Admin only): Scan libraries, refresh metadata, clean bundles, empty trash, optimize database, view server info.
    *   **Radarr (Movies):** Admins add directly or fulfill approved requests; users request. Queue (with remove/blocklist only/blocklist-and-search actions) and library maintenance for admins.
    *   **Sonarr (TV Shows):** Admins add directly or fulfill approved requests; users request. Queue (with remove/blocklist only/blocklist-and-search actions), wanted episodes, and library maintenance for admins.
    *   **AB Download Manager:** Primary admin can submit direct download URLs.
*   **Dynamic Launchers & Scripts (Primary Admin Focused):**
    *   Configure custom buttons in the "Launchers" menu to execute local applications or scripts on the bot's host machine.
    *   Launchers are managed via the Bot Settings GUI (`/settings`).
    *   Supports organizing launchers into user-defined subgroups.
    *   Automatic migration of legacy static launcher settings from `config.py` is supported.
*   **Local PC Control (Primary Admin Focused):**
    *   "🎧 Media & Sound" and "🔌 System Power" controls are now directly on the main menu for the Primary Administrator.
    *   Control PC media playback, volume (requires `pycaw`), and system power (shutdown/restart with confirmation).
*   **User Interface & Configuration:**
    *   Interactive Telegram menus using inline buttons, tailored to user roles. Menus for all authenticated users are refreshed upon bot startup.
    *   GUI for bot configuration (`/settings` command for Primary Admin), including user management and dynamic launcher setup.
    *   Persistent, user-specific main menu and status messages (state stored in `data/bot_state.json`).
    *   Automatic regeneration of `data/config.py` from a template on startup, preserving user values and ensuring configuration consistency.
    *   Automatic refresh of users' Telegram usernames.
*   **Log Management:**
    *   Logs are stored in a dedicated `data/log/` directory.
    *   Daily log rotation is implemented, keeping a configurable number of backup log files.

## Getting Started

1.  **Get the Code:**
    *   **Clone (Recommended):** `git clone https://github.com/hryarih32/MediaCatalogBot.git`
    *   **Download Release:** Visit the Releases Page.
2.  **Setup & Configuration:**
    *   Detailed instructions for Python setup, dependency installation, and bot configuration are in:
        **`SETUP_INSTRUCTIONS.md`**
3.  **Usage:**
    *   Once set up, learn how to interact with the bot's features and menus by reading:
        **`BOT_USAGE.MD`**

Key Telegram commands after setup:
*   `/start` or `/home`: Displays the main menu (role-dependent). For new users, this includes an option to request access.
*   `/settings`: (Primary Admin Only) Opens the configuration GUI.
*   `/status`: (Authenticated Users) Refreshes the bot's status message for your chat.
*   `/tickets`: (Authenticated Users) Opens the ticketing menu.

## Project Structure

The bot's code is organized within the `src/` directory. Runtime data, including your `config.py`, `requests.json` (for media requests), `bot_state.json` (for user roles, dynamic launchers, message persistence, etc.), and logs (in `data/log/`), will be stored in the `data/` directory (created on first run). Template configuration is in `config_templates/`.

## ❤️ Support the Project

If you find this Media Catalog Telegram Bot useful and appreciate the work, please consider showing your support!

### Sponsor with Cryptocurrency

*   **Bitcoin (BTC - SegWit):**
    `bc1q6gxjcw9krnm5zyx8xxxx93aq7q965ygxnpefy3`
*   **Ethereum (ETH) & USDT (ERC-20 on Ethereum):**
    `0x419df8dc3d710af15998d1b307140952ef147095`

*(Please double-check addresses and ensure you are sending on the correct network.)*

### Other Ways to Support
*   Star the project on GitHub! ⭐
*   Share the bot with others who might find it useful.

Thank you!

## License

GNU General Public License v3.0. See the `LICENSE` file for full details.

## Contributing

Contributions, bug reports, and feature requests are welcome! Please open an issue on the project's GitHub repository.

## Disclaimer

This software is provided "as is". Use responsibly. The author(s) are not responsible for any unintended consequences. Keep API keys secure.
