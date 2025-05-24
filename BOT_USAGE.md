# Media Catalog Telegram Bot - User Guide (v2.0.0)

---

This guide explains how to interact with the Media Catalog Telegram Bot once it has been set up and is running. The bot's primary configuration is stored in `data/config.py`.

## User Roles

*   **Primary Administrator:** The user whose Telegram Chat ID is set in the `CHAT_ID` field of `config.py`. This user has full access to all features, including bot settings via `/settings`.
*   **Administrator (Admin):** (Functionally the same as Primary Admin for most features in v2.0.0, except `/settings`). Future versions will allow adding more Admins via a user management system.
*   **Standard User:** (Currently, any user interacting with the bot who is not the Primary Admin). Can request media and view their own requests. Cannot access most control features or bot settings.
*   **Unknown User:** Users who have not been assigned a role. They will have very limited interaction (e.g., a prompt to request access in future versions).

## Core Telegram Commands

*   `/start` or `/home`: Displays/refreshes the main interactive menu. The menu content and available actions will vary based on your user role.
*   `/settings`: (Primary Admin Only) Opens the graphical configuration window on the bot's host machine to modify `data/config.py`.
*   `/status`: (Admins and Standard Users) Updates the bot's "universal status message" for your chat, which provides context, prompts, or results of actions.

## Interacting with Menus

The bot primarily uses **inline keyboard buttons** attached to messages.
*   Tap these buttons to navigate through menus and trigger actions.
*   The main menu message (the one with the most buttons) usually edits itself to show new options.
*   The "universal status message" is typically the last message sent by the bot *without* buttons. It provides feedback, prompts for input (like search terms or rejection reasons), and shows results of operations.

## Main Menu Structure (Examples by Role)

*(Visible options depend on your role and the features enabled in `data/config.py`)*

### Primary Administrator / Administrator View:

The main menu for Admins will typically show:

1.  **Bot Status Header:** Version, service health indicators (Plex, Sonarr, Radarr, ABDM), and bot uptime.
2.  **Media Addition:**
    *   `➕ Add Movie (Admin)`: Directly add movies to Radarr.
    *   `➕ Add TV Show (Admin)`: Directly add TV shows to Sonarr.
3.  **Download Management:**
    *   `📥 Add Download (ABDM)`: (Primary Admin Only) Submit a URL to AB Download Manager.
4.  **Request Management:**
    *   `📮 Admin Requests (X)`: View and manage pending requests from Standard Users (X is the count of pending requests). This section includes options to view request details, approve, or reject them.
    *   `📜 View History` (within Admin Requests): See a log of approved and rejected requests.
5.  **Personal Requests (Admin):**
    *   `📋 My Requests`: If an Admin uses the "Request" flow (e.g., for testing), their own requests appear here, similar to a Standard User.
6.  **Service Controls:**
    *   `🎬 Radarr Controls`: Access Radarr-specific functions like viewing the download queue or library maintenance.
    *   `🎞️ Sonarr Controls`: Access Sonarr-specific functions like viewing the queue, wanted episodes, or library maintenance.
    *   `🌐 Plex Controls`: Access Plex functions like viewing "Now Playing," "Recently Added," searching content, or server/library tools.
7.  **System & Launchers:**
    *   `🚀 Launchers & Scripts`: Launch configured applications or custom scripts on the bot's host.
    *   `🖥️ PC Control`: If enabled, control PC media, sound, or system power.
8.  **Bot Configuration:**
    *   `⚙️ Bot Settings`: (Primary Admin Only) Opens the GUI to edit `data/config.py`.

### Standard User View:

The main menu for Standard Users is more focused:

1.  **Simplified Header:** Bot version and a welcome message.
2.  **Media Requests:**
    *   `➕ Request Movie`: Search for a movie and submit a request for it.
    *   `➕ Request TV Show`: Search for a TV show and submit a request for it.
3.  **Tracking Requests:**
    *   `📋 My Requests`: View the status (Pending, Approved, Rejected) of your submitted media requests.

*(Standard Users will not see direct add buttons, service control menus like Radarr/Plex Controls, Launchers, PC Control, or the Bot Settings option).*

## Requesting Media (Standard User Flow)

1.  From your main menu, tap "➕ Request Movie" or "➕ Request TV Show".
2.  The bot will prompt you to enter the name of the movie or TV show. Send the name as a regular text message in the chat.
3.  The bot will search Radarr (for movies) or Sonarr (for TV shows) and display a list of results as buttons.
    *   If many results are found, pagination buttons (`◀️ Prev`, `Next ▶️`) may appear.
4.  Tap on the button corresponding to the media item you want.
5.  The bot will show you details of your selected item (title, year, overview).
6.  Tap the "✅ Submit Request" button.
7.  Your request is now submitted to the administrators for approval.
8.  You can check the status of your request at any time by tapping "📋 My Requests" on your main menu. *You will not receive a direct message when your request is approved or rejected; you need to check "My Requests".*

## Managing Requests (Administrator Flow)

1.  From your main menu, tap "📮 Admin Requests (X)". The `(X)` indicates the number of pending requests.
2.  You will see a list of pending requests. Tap "👁️ View: [Title]" for a specific request you want to process.
3.  The bot will display the details of the selected request. You will have options:
    *   **`✅ Approve`**:
        *   The bot will then present *you* (the Admin) with the standard Radarr/Sonarr add flow: "Add with Defaults" or "Customize Settings".
        *   Choose how you want to add it. Upon successful addition to Radarr/Sonarr, the request status will be updated to "approved".
    *   **`❌ Reject`**:
        *   The bot will prompt you to enter an optional reason for rejection. Send the reason as a text message.
        *   You can also send `/skip` if you don't want to provide a specific reason (a default note like "Rejected by admin" will be used).
        *   The request status will be updated to "rejected", and your reason will be logged.
4.  To see requests that have already been approved or rejected, navigate from the "Admin Requests" menu to "📜 View History".

## General Tips

*   **Status Message:** Always pay attention to the bot's last message that doesn't have buttons. This is the "universal status message" and will provide prompts (e.g., "Enter movie name:"), feedback on actions, and error messages.
*   **Navigation:** Use the "🔙 Back" buttons provided within menus. Using `/start` or `/home` will always reset you to your main menu.
*   **Configuration Changes:** If the Primary Admin changes settings via the `/settings` GUI, most changes are applied immediately. However, changes to the `LOG_LEVEL` typically require a full restart of the bot application on the host machine.
*   **Log Files:** For troubleshooting, the bot's detailed activity and error logs are stored in the `data/mediabot.log` file, located in the project's root directory on the machine where the bot is running.