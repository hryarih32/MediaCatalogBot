# Media Catalog Telegram Bot - Setup Instructions

---

## Prerequisites

*   **Python 3.12.9:**
    *   Install from [python.org](https://www.python.org/downloads/release/python-3129/) or via package manager (e.g., `winget install -e --id Python.Python.3.12` on Windows).
    *   **Important (Windows):** Ensure "Add Python 3.12 to PATH" is checked during installation.

*   **Git (Optional, for cloning):**
    *   Install from [git-scm.com](https://git-scm.com/downloads) or via package manager (e.g., `winget install -e --id Git.Git`).

## 1. Get the Code

*   **Option A (Git):**
    ```bash
    git clone <repository_url_of_the_bot> MediaCatalogBot
    cd MediaCatalogBot
    ```
*   **Option B (Download ZIP):**
    1.  Download and extract the project ZIP.
    2.  Open your terminal and `cd` into the extracted project folder.

## 2. Setup Python Virtual Environment & Install Dependencies

*(Perform these commands from the project's root folder, e.g., `MediaCatalogBot/`)*

1.  **Create Virtual Environment:**
    ```bash
    python -m venv venv
    ```
    *(Use `py -3.12 -m venv venv` or full Python path if needed)*

2.  **Activate Virtual Environment:**
    *   Windows (Command Prompt): `.\venv\Scripts\activate.bat`
    *   Windows (PowerShell): `.\venv\Scripts\Activate.ps1`
        *(If PowerShell errors, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` once as Admin)*
    *   macOS/Linux: `source venv/bin/activate`
    Your prompt should now show `(venv)`.

3.  **Install Required Libraries:**
    With `(venv)` active:
    ```bash
    pip install -r requirements/requirements.txt
    ```
    *(Note the new path to `requirements.txt`)*

## 3. First Run & Configuration

The bot uses a GUI for initial setup. The active configuration will be stored in `data/config.py`.

1.  **Ensure `venv` is active.**
2.  **Run the bot:**
    *   **Windows (Recommended):** Double-click `Run Media Catalog Bot.bat` (located in the project root).
    *   **Terminal (All OS):** From the project root, run `python MediaCatalog.py`.

3.  A **Configuration GUI** should appear. If not, check `data/mediabot.log` (created in `data/`) or terminal output for errors.

4.  **Fill in GUI:**
    *   **Telegram Bot Token:** From `@BotFather` (`/newbot`).
    *   **Telegram Chat ID:** Your numerical User ID from `@userinfobot`.
    *   **Service Configuration (Plex, Radarr, Sonarr):** Enable, provide API URL and Key/Token.
        *   Ensure firewall allows connections if services are not on `localhost`.
    *   **Launchers & Custom Scripts (Optional):** Configure paths and names.
    *   **PC Control (Optional):** Enable (dependencies are in `requirements/requirements.txt`).
    *   **Logging Level (Optional):** Default is "INFO". Changes require a bot restart.

5.  **Save Configuration in GUI:**
    *   This creates/updates `data/config.py`.
    *   The bot will attempt to reload settings. **A restart is recommended after the very first setup or if `LOG_LEVEL` changes.** The application will exit after the first save to encourage this.

## 4. Running the Bot (After First Setup)

1.  Navigate to the project root.
2.  Activate `venv`.
3.  Run:
    *   Windows: `Run Media Catalog Bot.bat` (for background).
    *   Terminal: `python MediaCatalog.py` (for console output).
4.  Logs are in `data/mediabot.log`. Interact via Telegram (see `BOT_USAGE.md`).

## Stopping the Bot

*   **`Run Media Catalog Bot.bat`:** Use Task Manager to end `python.exe` running `MediaCatalog.py`.
*   **`python MediaCatalog.py` (terminal):** Press `Ctrl+C`.

## Optional: Creating a Standalone Executable (Windows .exe)

This bundles Python and dependencies into a single `.exe`.

*   **Prerequisites:**
    1.  Complete steps 1 and 2 (Get Code, Setup Venv & Install Dependencies). `pyinstaller` is installed from `requirements/requirements.txt`.
    2.  Ensure `VERSION` and `LICENSE` are in the project root.
    3.  (Optional) Update `COMPANY_NAME` in `build_tools/build_set_version_info.py`.
*   **Build Command:**
    (From project root, with `venv` active)
    ```bash
    .\build_tools\build_application.bat
    ```
*   **Output:**
    *   Executable (e.g., `Media Catalog Telegram Bot.exe`) will be in `bin/`.
    *   On first run on a new machine, it may create a default `config.py.default` in the `data/` directory (if `data/` doesn't exist, it will try to create it). You would then copy `config.py.default` to `config.py` inside `data/` and edit it, or let the GUI guide you on the next run if `data/config.py` is invalid/missing.

## Troubleshooting

*   **Bot doesn't start / Config errors:**
    *   Ensure `venv` is active.
    *   Check `data/config.py` has correct Token and Chat ID.
    *   Review `data/mediabot.log`.
*   **`pip install` errors:** Check `venv` active, internet.
*   **API Service Issues:** Verify URLs/Keys in `data/config.py`, firewall, network.
*   **PC Control Issues:** Check `PC_CONTROL_ENABLED` in `data/config.py`, `pyautogui`/`pycaw` install.