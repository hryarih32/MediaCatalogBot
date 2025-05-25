# Media Catalog Telegram Bot - Setup Instructions (v2.0.0)

---

This guide will walk you through setting up the Media Catalog Telegram Bot on your system.

## Prerequisites

*   **Python 3.12.x:** (e.g., Python 3.12.9 recommended)
    *   Download from the official Python website: [python.org/downloads/](https://www.python.org/downloads/)
    *   During installation on Windows, **ensure you check the box that says "Add Python to PATH"**.
    *   On Linux/macOS, Python 3.12 might be available via your system's package manager (e.g., `apt`, `yum`, `brew`).
*   **Git (Recommended):**
    *   For easily cloning the repository. Download from [git-scm.com/downloads](https://git-scm.com/downloads).

## Information & Software to Gather Before Setup

You'll need the following details and software installed/accessible to configure the bot. It's helpful to have these ready:

1.  **Telegram Bot Token & Your Chat ID:**
    *   **Bot Token:**
        1.  Open Telegram and search for the user `@BotFather`.
        2.  Send the `/newbot` command to `@BotFather`.
        3.  Follow the prompts to name your bot and choose a username for it (the username must end in `bot`, e.g., `MyMediaPalBot`).
        4.  `@BotFather` will provide you with an **API Token**. Copy this token carefully; it's essential for the bot to connect to Telegram.
    *   **Your Telegram Chat ID (for Primary Admin):**
        1.  This is your personal, numerical Telegram User ID.
        2.  Open Telegram and search for the user `@userinfobot`.
        3.  Send the `/start` command to `@userinfobot`. It will reply with your User ID. Note this number. This ID will be configured as the **Primary Administrator** of the bot, granting full access including the `/settings` command.

2.  **Plex Media Server (Optional):**
    *   **Software:** Download and install Plex Media Server from [plex.tv/media-server-downloads/](https://www.plex.tv/media-server-downloads/).
    *   **Plex URL:** The full URL of your Plex server (e.g., `http://localhost:32400` if on the same machine as the bot, or `https://your-plex-domain.com` if hosted elsewhere).
    *   **Plex Token (X-Plex-Token):** This token authenticates the bot with your Plex server.
        *   Refer to the official Plex support article: [Finding an Authentication Token / X-Plex-Token](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/).
        *   The easiest way is usually to log into your Plex Web App (app.plex.tv), browse to one of your library items, right-click on its poster, choose "Get Info", then click "View XML". In the XML data, look for the `X-Plex-Token="YOUR_TOKEN_HERE"` attribute in the URL at the top.

3.  **Radarr (Optional - for Movie Management):**
    *   **Software:** Download Radarr from its official site [radarr.video](https://radarr.video/) (links to GitHub: [https://github.com/Radarr/Radarr](https://github.com/Radarr/Radarr)) or follow installation guides on the [Servarr Wiki](https://wiki.servarr.com/radarr/installation).
    *   **Radarr API URL:** The full URL to your Radarr instance, including any base path if configured (e.g., `http://localhost:7878` or `http://your-server/radarr`).
    *   **Radarr API Key:** In your Radarr web interface, go to `Settings` > `General` > `Security` section, and copy the `API Key`.

4.  **Sonarr (Optional - for TV Show Management):**
    *   **Software:** Download Sonarr from its official site [sonarr.tv](https://sonarr.tv/) (links to GitHub: [https://github.com/Sonarr/Sonarr](https://github.com/Sonarr/Sonarr)) or follow installation guides on the [Servarr Wiki](https://wiki.servarr.com/sonarr/installation).
    *   **Sonarr API URL:** The full URL to your Sonarr instance (e.g., `http://localhost:8989` or `http://your-server/sonarr`).
    *   **Sonarr API Key:** In your Sonarr web interface, go to `Settings` > `General` > `Security` section, and copy the `API Key`.

5.  **AB Download Manager (ABDM) (Optional - for Direct Downloads, Primary Admin Only):**
    *   **Software:** Download "AB Download Manager" from its official GitHub repository: [https://github.com/amir1376/ab-download-manager](https://github.com/amir1376/ab-download-manager). Follow their instructions for installation.
    *   **ABDM API Port & Enabling API:** For the bot to communicate with ABDM, its "Browser Integration" HTTP API must be enabled:
        1.  Open the AB Download Manager application.
        2.  Navigate to its settings, typically found under `Tools > Settings` (or a similar menu).
        3.  Look for a tab or section named "Browser Integration" or "API".
        4.  Ensure the option **"Enable browser integration HTTP API"** (or similar wording) is **checked/enabled**.
        5.  Note the **"Port"** number specified in this section (the default is often `15151`). You will need this port number for the bot's configuration.

6.  **Application Launcher Paths (Optional):**
    *   If you want to use the bot to launch applications like Plex, Sonarr, Radarr, Prowlarr, your Torrent client, or ABDM itself, you will need the **full executable path** to these programs on the machine where the bot will run.
    *   **Prowlarr:** Download from [prowlarr.com](https://prowlarr.com/) (links to GitHub: [https://github.com/Prowlarr/Prowlarr](https://github.com/Prowlarr/Prowlarr)) or the [Servarr Wiki](https://wiki.servarr.com/prowlarr/installation).
    *   **Torrent Client:** (e.g., qBittorrent, Deluge, Transmission). Download from their official websites.
        *   qBittorrent: [qbittorrent.org](https://www.qbittorrent.org/) (GitHub: [https://github.com/qbittorrent/qBittorrent](https://github.com/qbittorrent/qBittorrent))
    *   You'll need to locate the `.exe` file (Windows) or the main executable (Linux/macOS) for each.

## Setup Steps

### 1. Get the Bot Code

*   **Option A (Using Git - Recommended):**
    1.  Open your terminal or command prompt.
    2.  Navigate to the directory where you want to store the bot.
    3.  Run: `git clone https://github.com/hryarih32/MediaCatalogBot.git`
    4.  Change into the bot's directory: `cd MediaCatalogBot`

*   **Option B (Download ZIP):**
    1.  Go to the GitHub repository: [https://github.com/hryarih32/MediaCatalogBot](https://github.com/hryarih32/MediaCatalogBot)
    2.  Click the "Code" button, then "Download ZIP".
    3.  Extract the ZIP file to a folder on your computer.
    4.  Open your terminal/command prompt and navigate into this extracted folder (e.g., `cd path/to/your/MediaCatalogBot-main`).

### 2. Setup Python Virtual Environment & Install Dependencies

*(Perform these commands from the project's root folder, e.g., `MediaCatalogBot/`)*

1.  **Create a Virtual Environment:**
    This isolates the bot's Python packages from your system-wide Python.
    ```bash
    python -m venv venv
    ```
    *(If you have multiple Python versions, you might need to use `py -3.12 -m venv venv` or the full path to your Python 3.12 executable).*

2.  **Activate the Virtual Environment:**
    *   **Windows (Command Prompt):** `.\venv\Scripts\activate.bat`
    *   **Windows (PowerShell):** `.\venv\Scripts\Activate.ps1`
        *(If PowerShell gives an error about execution policies, you might need to run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` once in an Administrator PowerShell and then try activating again).*
    *   **macOS/Linux (Bash/Zsh):** `source venv/bin/activate`
    Your command prompt should now show `(venv)` at the beginning, indicating the virtual environment is active.

3.  **Install Required Libraries:**
    With the `(venv)` active, install the dependencies listed in `requirements/requirements.txt`:
    ```bash
    pip install -r requirements/requirements.txt
    ```

### 3. First Run & Configuration (Primary Administrator)

The bot uses a Graphical User Interface (GUI) for initial setup and subsequent configuration changes. The active configuration will be created and stored in `data/config.py`.

1.  **Ensure the virtual environment (`venv`) is active** in your terminal/command prompt.
2.  **Run the bot for the first time:**
    *   **Windows (Recommended):** In File Explorer, navigate to the project's root folder and double-click the `Run Media Catalog Bot.bat` file. This will run the bot in the background.
    *   **Terminal (All Operating Systems):** From the project's root folder, run: `python MediaCatalog.py`
3.  A **Configuration GUI** window should appear on the screen of the machine running the bot.
    *   If the GUI doesn't appear, check the terminal output for any error messages. Also, a log file named `mediabot.log` will be created in a new `data/` subdirectory within your project folder – check this log for errors.
4.  **Fill in the GUI fields** using the information you gathered earlier:
    *   **Telegram Bot Token:** Paste the token from `@BotFather`.
    *   **Telegram Chat ID:** Enter your numerical User ID (this will be the **Primary Admin**).
    *   **Service Configurations (Plex, Radarr, Sonarr, ABDM):**
        *   Check the "Enable" box for each service you want to use.
        *   Enter the API URL, API Key/Token, and Port (for ABDM) accurately.
        *   **Firewall Note:** If these services are running on different machines or in Docker containers, ensure your firewall(s) allow the machine running the bot to connect to them on their respective ports.
    *   **Application Launchers & Custom Scripts (Optional):**
        *   For each launcher or script you want, check "Enable".
        *   Provide a "Button Name" (this text will appear on the Telegram button).
        *   Provide the full "Executable Path" to the application or script on the machine hosting the bot.
    *   **PC Control (Optional):**
        *   Check "Enable PC Keyboard/System Controls" if you want to use features like media key simulation or remote shutdown/restart. The necessary Python libraries (`pyautogui`, `pycaw`) are included in `requirements.txt`.
    *   **Logging Level (Optional):**
        *   The default is "INFO". You can change it to "DEBUG" for more detailed logs during troubleshooting, or "WARNING" / "ERROR" for less verbose logging. Changes to this setting typically require a full bot restart to take effect.
    *   **UI Behavior:**
        *   `Max API Search Results`: Controls how many items are fetched from Radarr/Sonarr during a search.
        *   `Items Per Page`: Controls how many items are shown per page in paginated menus (like search results or "My Requests").
5.  **Save Configuration in the GUI:**
    *   Click the "Save Configuration" button.
    *   This will create (or update) the `data/config.py` file.
    *   The bot will attempt to reload the new settings. **A full restart of the bot application is highly recommended after the very first setup, or if you change critical settings like `LOG_LEVEL`.** The application might exit after the first save to encourage this restart.

*(Full user management for adding other Admins or Standard Users via the GUI is planned for a future update. For version 2.0.0, any user interacting with the bot who is not the Primary Admin will initially be treated as a Standard User for media request features).*

### 4. Running the Bot (After First Setup)

1.  Navigate to the project's root directory in your terminal or command prompt.
2.  **Activate the virtual environment (`venv`)** as described in Step 2.2.
3.  **Run the bot:**
    *   **Windows:** Double-click `Run Media Catalog Bot.bat` for background operation.
    *   **Terminal (All OS):** `python MediaCatalog.py` (you'll see log output directly in the terminal).
4.  The bot should now connect to Telegram and be ready for commands.
5.  Detailed logs are stored in `data/mediabot.log`.
6.  Interact with your bot in Telegram using the commands and menus described in `BOT_USAGE.md`.

## Stopping the Bot

*   If you used `Run Media Catalog Bot.bat` (Windows):
    *   Open Task Manager (`Ctrl+Shift+Esc`).
    *   Go to the "Details" or "Processes" tab.
    *   Find the `python.exe` or `pythonw.exe` process that is running the `MediaCatalog.py` script (you might need to check the "Command Line" column if available).
    *   Select it and click "End Task".
*   If you ran `python MediaCatalog.py` in a terminal:
    *   Press `Ctrl+C` in the terminal window where the bot is running.

## Optional: Creating a Standalone Executable (Windows .exe)

This process bundles the Python interpreter and all necessary libraries into a single `.exe` file, making it easier to run on other Windows machines without a full Python setup (though they'll still need access to any configured network services).

*   **Prerequisites:**
    1.  Complete Steps 1 and 2 above (Get the Code, Setup Python Virtual Environment & Install Dependencies). The `pyinstaller` library is installed as part of `requirements/requirements.txt`.
    2.  Ensure the `VERSION` file (containing `2.0.0` or your current version) and `LICENSE` file are present in the project's root directory.
    3.  (Optional) You can update `COMPANY_NAME` in `build_tools/build_set_version_info.py` if desired before building.
*   **Build Command:**
    1.  Ensure your virtual environment (`venv`) is active in your terminal/command prompt.
    2.  Navigate to the project's root directory.
    3.  Run the build script:
        ```bash
        .\build_tools\build_application.bat
        ```
*   **Output:**
    *   The standalone executable (e.g., `Media Catalog Telegram Bot.exe`) will be created in a new `bin/` directory within your project root.
    *   When running this `.exe` on a new machine for the first time (or if the `data/` directory is missing), it will attempt to create a `data/` directory and a default `config.py.default` file inside it. You would then:
        1.  Copy `data/config.py.default` to `data/config.py`.
        2.  Run the executable again. The Configuration GUI should appear, allowing you to set up your actual `data/config.py`.

## Troubleshooting Common Issues

*   **Bot doesn't start / Configuration errors:**
    *   Always ensure your virtual environment (`venv`) is activated before running the bot.
    *   Double-check that `data/config.py` contains the correct `TELEGRAM_BOT_TOKEN` and your `CHAT_ID`.
    *   Review `data/mediabot.log` for detailed error messages.
*   **`pip install` errors:**
    *   Ensure `venv` is active.
    *   Check your internet connection.
    *   You might need to install Python development tools or C++ build tools if a package fails to compile (though this is less common with the listed dependencies).
*   **API Service Integration Issues (Plex, Radarr, Sonarr, ABDM):**
    *   **Verify URLs, API Keys/Tokens, and Ports:** Triple-check these values in your `data/config.py` (or via the `/settings` GUI).
    *   **Service Running:** Ensure the respective applications (Plex server, Radarr, Sonarr, ABDM) are actually running on their configured hosts and ports.
    *   **Firewall:** Make sure no firewall (Windows Firewall, router firewall, or other security software) is blocking the bot's outgoing connections to these services, or incoming connections if a service requires it (though this bot primarily makes outgoing calls).
    *   **Network Accessibility:** If services are on a different machine or Docker, ensure the bot's machine can reach them over the network (e.g., try pinging the host or accessing the service's web UI from the bot's machine).
    *   **ABDM API:** Specifically for AB Download Manager, ensure the "Enable browser integration HTTP API" option is checked in its settings, and the port matches your bot config.
*   **PC Control Issues:**
    *   Confirm `PC_CONTROL_ENABLED = True` in `data/config.py`.
    *   Ensure the `pyautogui` and `pycaw` (for advanced volume) libraries were installed correctly from `requirements.txt`. On some Linux systems, `pyautogui` may have additional X11 dependencies.
*   **`[Errno 11001] getaddrinfo failed` / `telegram.error.NetworkError`:** This usually indicates a DNS resolution problem or network connectivity issue on the machine hosting the bot. Check your internet connection, DNS server settings (try public DNS like `8.8.8.8` or `1.1.1.1`), and firewall settings.