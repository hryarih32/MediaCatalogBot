# Media Catalog Telegram Bot - Bot Usage Guide

This guide explains how to use the various features of the Media Catalog Telegram Bot.

## Initial Setup

1.  Ensure you have followed the `SETUP_INSTRUCTIONS.md` to install and configure the bot.
2.  The user whose Telegram `CHAT_ID` is set in `data/config.py` will be the **Primary Administrator**.

## Roles

*   **Primary Administrator:** Full control, including `/settings`, managing dynamic launchers, and all user management functions (approving access, assigning any role, adding/removing users).
*   **Administrator (`ADMIN`):** Access to most control features, media addition, and management of user *media* requests. Cannot manage users or access requests.
*   **Standard User (`STANDARD_USER`):** Can search/request media, view their requests, and search/browse Plex content including details.
*   **Unknown User (`UNKNOWN`):** New users; can only "Request Access".

## Common Commands

*   `/start` or `/home`: Displays the main menu (role-dependent). For new users, this includes an option to request access. All authenticated users' menus are refreshed on bot startup.
*   `/settings`: (Primary Administrator only) Opens the GUI for bot configuration, user management, and dynamic launcher setup.
*   `/status`: (Administrators and Standard Users) Refreshes the universal status message at the bottom of your chat with the bot.

## Main Menu Options

The main menu buttons adapt based on your assigned role and enabled features.

### For Standard Users

*   **"➕ Request Movie" / "➕ Request TV Show"**:
    1.  Click the button.
    2.  The bot will prompt you to enter the movie or TV show name.
    3.  Type the name and send it.
    4.  A list of search results will appear as buttons.
    5.  Click a result to see a confirmation screen.
    6.  Click "✅ Submit Request" to send your request for admin approval. Admin menus will update with new request counts.
*   **"🔍 Search Plex"**:
    1.  Click the button.
    2.  The bot will prompt you to enter your search query.
    3.  Type the query and send it.
    4.  A list of search results from Plex will appear as buttons.
    5.  Click a result (movie or show) to view its details.
    6.  If it's a show, you can navigate to its seasons and then to individual episode details.
*   **"📋 My Requests"**:
    *   View a paginated list of your submitted media requests and their current status (Pending, Approved, Rejected, Add Failed).

### For Administrators (ADMIN & Primary Administrator)

*   **"➕ Add Movie" / "➕ Add TV Show"**:
    1.  Click the button.
    2.  The bot will prompt you to enter the movie or TV show name.
    3.  Type the name and send it.
    4.  A list of search results will appear as buttons.
    5.  Click a result to see options:
        *   "Add with Defaults": Adds the media using pre-defined quality/path settings.
        *   "Customize Settings": Allows you to choose root folder, quality profile, tags, etc. before adding.
        *   "Cancel Add".
    *   If fulfilling an approved user request, the request status updates accurately upon successful add, failure, or cancellation of this add flow.
*   **"📥 Add Download (ABDM)"** (Primary Administrator only, if ABDM is enabled):
    1.  Click the button.
    2.  The bot prompts for a URL.
    3.  Paste the direct download URL and send. The download will be added to AB Download Manager.
*   **"📮 Media Requests (X)"**:
    *   `(X)` shows the number of pending user media requests.
    *   View a list of pending requests.
    *   Click a request to see details and options to "✅ Approve" or "❌ Reject".
        *   **Approve:** Initiates the standard admin add flow for that media item.
        *   **Reject:** Allows providing an optional reason for rejection.
    *   Access "📜 View History" for previously processed requests.
*   **"👑 Manage Users & Requests (X)"** (Primary Administrator only):
    *   `(X)` shows the number of pending user access requests.
    *   The menu displays pending access requests at the top:
        *   Click "✅ Approve" for a user to assign them `STANDARD_USER` or `ADMIN` role.
        *   Click "❌ Deny" to reject an access request.
    *   Below pending requests, a paginated list of existing users is shown:
        *   Click "✏️ Edit" next to a user to change their role or remove them.
    *   An "➕ Add New User" button allows adding users directly by their Telegram Chat ID and assigning a role.
*   **"🎬 Radarr Controls"** (if Radarr is enabled):
    *   **"📥 View Download Queue"**: See items currently downloading in Radarr. Click an item for actions (Remove, Blocklist Only, Blocklist & Search).
    *   **"🛠️ Library Maintenance"**:
        *   "🔄 Scan Files (Disk Sync)": Refresh Radarr's view of movie files on disk.
        *   "♻️ Update All Metadata": Refresh metadata for all movies.
        *   "✍️ Rename All Movie Files": Trigger Radarr's file renaming task.
*   **"🎞️ Sonarr Controls"** (if Sonarr is enabled):
    *   **"📥 View Download Queue"**: See items currently downloading in Sonarr. Click an item for actions.
    *   **"🎯 View Wanted Episodes"**: See a list of episodes Sonarr is actively searching for. Click an episode to trigger an individual search.
    *   **"🛠️ Library Maintenance"**:
        *   "🔄 Scan Files (Disk Sync)": Refresh Sonarr's view of series files.
        *   "♻️ Update All Metadata": Refresh metadata for all series.
        *   "✍️ Rename All Episode Files": Trigger Sonarr's file renaming task.
*   **"🌐 Plex Controls"** (if Plex is enabled):
    *   **"📺 View Now Playing"**: See current Plex streams and stop them.
    *   **"🆕 View Recently Added"**: Browse recently added items per library.
    *   **"🔍 Search Plex Content"**: (This is within Plex Controls for Admins) Search and navigate Plex content.
    *   **"🛠️ Library & Server Tools"**:
        *   "🔄 Scan Libraries": Initiate a scan for new/updated media in Plex libraries.
        *   "♻️ Refresh Library Metadata": Refresh all metadata for selected Plex libraries.
        *   "🔧 Server Maintenance & Info":
            *   "🧹 Clean Bundles"
            *   "🗑️ Empty Trash..." (for specific or all libraries)
            *   "⚙️ Optimize Database"
            *   "ℹ️ Server Info": View Plex server details and library/service statistics.
*   **"🖥️ PC Control"** (if PC Control is enabled):
    *   **"🎧 Media & Sound"**: Control media playback (play/pause, next, prev, stop, seek) and system volume.
    *   **"🔌 System Power"**: Initiate PC shutdown or restart (requires two-click confirmation).
*   **"🚀 Launchers"** (Primary Administrator only):
    *   Displays a menu of dynamically configured launchers and scripts.
    *   Launchers can be organized into subgroups.
    *   Click a launcher to execute the application or script on the bot's host machine.
    *   Manage launchers via the `/settings` GUI.

## Notes

*   The bot attempts to delete your command messages (like `/start`) and text inputs (like search queries) to keep the chat clean.
*   The "Universal Status Message" at the bottom of your chat provides feedback on actions and current menu context.
*   Configuration for API keys, URLs, enabled features, and dynamic launchers is done via the `/settings` command (Primary Admin only), which opens a GUI.
*   Log files are now stored daily in the `data/log/` directory.
*   Regularly check the `CHANGELOG.md` for new features and updates.
