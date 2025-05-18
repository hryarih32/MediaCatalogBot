# Media Catalog Telegram Bot - User Guide

---

This guide explains how to interact with the Media Catalog Telegram Bot once it has been set up and is running (refer to `SETUP_INSTRUCTIONS.md`). The bot's configuration is stored in `data/config.py`.

## Core Telegram Commands

*   `/start` or `/home`: Displays/refreshes the main interactive menu.
*   `/settings`: Opens the graphical configuration window on the bot's host machine to modify `data/config.py`.
*   `/status`: Updates the bot's "universal status message" (provides context, prompts, results).

## Interacting with Menus

The bot uses **inline keyboard buttons**.
*   Tap buttons to navigate.
*   The main menu message edits itself.
*   The status message (last message without buttons) provides prompts and feedback.

## Main Menu Structure Overview

*(Visible options depend on your `data/config.py` settings)*

1.  **➕ Add Movie (Radarr)**
    *   Prompts for movie name, searches Radarr.
    *   Select result -> Add with defaults or customize (root folder, quality, etc.).

2.  **➕ Add TV Show (Sonarr)**
    *   Prompts for show name, searches Sonarr.
    *   Select result -> Add with defaults or customize.

3.  **🎬 Radarr Controls** (If Radarr enabled)
    *   **View Download Queue:** Manage Radarr's active downloads.
    *   **Library Maintenance:** Scan files, refresh metadata, rename files for all movies.

4.  **🎞️ Sonarr Controls** (If Sonarr enabled)
    *   **View Download Queue:** Manage Sonarr's active downloads.
    *   **View Wanted Episodes:** List/search wanted episodes.
    *   **Library Maintenance:** Scan files, refresh metadata, rename files for all series.

5.  **🌐 Plex Controls** (If Plex enabled)
    *   **View Now Playing:** See and stop current Plex streams.
    *   **View Recently Added:** Browse recent additions to libraries.
    *   **Search Plex Content:** Search your Plex library (movies/shows), navigate seasons/episodes.
    *   **Library & Server Tools:**
        *   Scan Libraries
        *   Refresh Library Metadata
        *   Server Maintenance & Info (Clean Bundles, Empty Trash, Optimize DB, View Server/Library Info).

6.  **🚀 Launchers & Scripts** (If any configured)
    *   Directly launch configured applications or custom scripts on the bot's host.

7.  **🖥️ PC Control** (If PC Control enabled & dependencies met)
    *   **Media & Sound:** Playback keys, system volume, mute.
    *   **System Power:** PC shutdown/restart (with confirmation).

8.  **⚙️ Bot Settings**
    *   Same as `/settings`. Opens GUI to edit `data/config.py`.

## General Tips

*   Read the bot's status message for prompts and feedback.
*   Use "Back" buttons within menus. `/home` or `/start` resets to the main menu.
*   Config changes via GUI are usually applied quickly. Manual edits to `data/config.py` may require a bot restart (especially for `LOG_LEVEL`).
*   Logs: `data/mediabot.log` in the project directory on the host.