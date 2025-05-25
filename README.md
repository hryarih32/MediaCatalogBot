# Media Catalog Telegram Bot

**Version:** 2.0.0
[![GitHub Sponsors](https://img.shields.io/github/sponsors/hryarih32?style=social&label=Sponsor%20Project)](https://github.com/hryarih32/MediaCatalogBot#️-support-the-project)

**License:** GNU General Public License v3.0 (see `LICENSE` file)

The Media Catalog Telegram Bot is a versatile tool designed to help you manage and interact with your digital media collection and related services directly from Telegram. It integrates with Plex, Radarr, Sonarr, and AB Download Manager, and includes features for PC control and custom script execution. Version 2.0.0 introduces user roles and a media request system.

## Core Functionality

*   **Multi-User System:** Supports `ADMIN` and `STANDARD_USER` roles with differentiated features.
*   **Media Request Workflow:** Standard users can request movies and TV shows; Admins can approve or reject these requests.
*   **Service Integrations:**
    *   **Plex:** View playback, browse library, search, and manage server/library tasks.
    *   **Radarr (Movies):** Admins add directly; users request. Queue and library management for admins.
    *   **Sonarr (TV Shows):** Admins add directly; users request. Queue, wanted episodes, and library management for admins.
    *   **AB Download Manager:** Primary admin can submit direct download URLs.
*   **Local Control (Admin Focused):**
    *   Launch configured applications (Plex, Radarr, Sonarr, etc.) and custom scripts.
    *   Control PC media playback, volume, and system power (requires extra dependencies).
*   **User Interface:**
    *   Interactive Telegram menus using inline buttons.
    *   GUI for bot configuration (`/settings` command for Primary Admin).

## Getting Started

1.  **Get the Code:**
    *   **Clone (Recommended):** `git clone https://github.com/hryarih32/MediaCatalogBot.git`
    *   **Download Release:** Visit the [Releases Page](https://github.com/hryarih32/MediaCatalogBot/releases).
2.  **Setup & Configuration:**
    *   Detailed instructions for Python setup, dependency installation, and bot configuration are in:
        **`SETUP_INSTRUCTIONS.md`**
3.  **Usage:**
    *   Once set up, learn how to interact with the bot's features and menus by reading:
        **`BOT_USAGE.md`**

Key Telegram commands after setup:
*   `/start` or `/home`: Displays the main menu (role-dependent).
*   `/settings`: (Primary Admin Only) Opens the configuration GUI.
*   `/status`: (Authenticated Users) Refreshes the bot's status message for your chat.

## Project Structure

The bot's code is organized within the `src/` directory. Runtime data, including your `config.py`, `requests.json` (for media requests), and logs, will be stored in the `data/` directory (created on first run). Template configuration is in `config_templates/`.

## ❤️ Support the Project

If you find this Media Catalog Telegram Bot useful and appreciate the work, please consider showing your support!

### Sponsor with Cryptocurrency

*   **Bitcoin (BTC - SegWit):**
    `bc1q6gxjcw9krnm5zyx8xxxx93aq7q965ygxnpefy3`
*   **Ethereum (ETH) & USDT (ERC-20 on Ethereum):**
    `0x419df8dc3d710af15998d1b307140952ef147095`

*(Please double-check addresses and ensure you are sending on the correct network.)*

### Other Ways to Support
*   Star the project on [GitHub](https://github.com/hryarih32/MediaCatalogBot)! ⭐
*   Share the bot with others who might find it useful.

Thank you!

## License

GNU General Public License v3.0. See the `LICENSE` file for full details.

## Contributing

Contributions, bug reports, and feature requests are welcome! Please open an issue on the [project's GitHub repository](https://github.com/hryarih32/MediaCatalogBot/issues).

## Disclaimer

This software is provided "as is". Use responsibly. The author(s) are not responsible for any unintended consequences. Keep API keys secure.