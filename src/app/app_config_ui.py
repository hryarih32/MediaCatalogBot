import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import logging

from src.config.config_definitions import (
    CONFIG_KEYS_CORE, CONFIG_KEYS_PLEX, CONFIG_KEYS_RADARR, CONFIG_KEYS_SONARR,
    CONFIG_KEYS_SCRIPT_1, CONFIG_KEYS_SCRIPT_2, CONFIG_KEYS_SCRIPT_3,
    CONFIG_KEYS_PC_CONTROL, CONFIG_KEYS_UI_BEHAVIOR,
    CONFIG_KEYS_PLEX_LAUNCHER, CONFIG_KEYS_SONARR_LAUNCHER, CONFIG_KEYS_RADARR_LAUNCHER,
    CONFIG_KEYS_PROWLARR_LAUNCHER, CONFIG_KEYS_TORRENT_LAUNCHER, CONFIG_KEYS_ABDM_LAUNCHER,
    ALL_USER_CONFIG_KEYS, CONFIG_FIELD_DEFINITIONS, CONFIG_KEYS_ABDM,
    CONFIG_KEYS_LOGGING, LOG_LEVEL_OPTIONS
)

from .app_file_utils import get_ico_file_path

logger_ui = logging.getLogger(__name__ + "_ui")


def run_config_ui(config_file_to_write_path, initial_values=None):
    if initial_values is None:
        initial_values = {}

    initial_log_level_on_ui_open = initial_values.get(
        "LOG_LEVEL", CONFIG_FIELD_DEFINITIONS.get("LOG_LEVEL", {}).get("default", "INFO"))

    root = tk.Tk()
    root.title("Media Bot Configuration")
    root.resizable(True, True)

    try:
        icon_path = get_ico_file_path()
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
        else:
            logger_ui.warning(f"Window icon not found: {icon_path}")
    except Exception as e:
        logger_ui.error(f"Error setting window icon: {e}", exc_info=False)

    canvas = tk.Canvas(root)
    scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(
        scrollregion=canvas.bbox("all")))

    def on_canvas_configure(event): canvas.itemconfig(
        canvas_frame_id, width=event.width)
    canvas_frame_id = canvas.create_window(
        (0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    canvas.bind("<Configure>", on_canvas_configure)

    def _on_mousewheel(event):
        delta = 0
        if event.num == 4:
            delta = -1
        elif event.num == 5:
            delta = 1
        else:
            delta = int(-1 * (event.delta / 120))
        canvas.yview_scroll(delta, "units")

    for widget_to_bind_scroll in [canvas, scrollable_frame, root]:
        widget_to_bind_scroll.bind_all("<MouseWheel>", _on_mousewheel)
        widget_to_bind_scroll.bind_all(
            "<Button-4>", _on_mousewheel)
        widget_to_bind_scroll.bind_all(
            "<Button-5>", _on_mousewheel)

    entries_vars = {}
    widgets_map = {}
    label_widgets_map = {}
    main_frame = ttk.Frame(scrollable_frame, padding="10")
    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    scrollable_frame.grid_rowconfigure(0, weight=1)
    scrollable_frame.grid_columnconfigure(0, weight=1)
    main_frame.grid_columnconfigure(0, weight=1)
    main_frame.grid_columnconfigure(1, weight=1)

    def make_toggle_dependent_fields_func(check_var_key, dependent_keys_list, associated_labels_keys=None):
        if associated_labels_keys is None:
            associated_labels_keys = []

        def toggle_fields():
            is_enabled = entries_vars[check_var_key].get()
            widget_state = tk.NORMAL if is_enabled else tk.DISABLED

            label_fg_color = "black" if is_enabled else "grey"
            for dep_key in dependent_keys_list:
                if dep_key in widgets_map:
                    for widget in widgets_map[dep_key]:
                        if hasattr(widget, 'config') and 'state' in widget.config():
                            widget.config(state=widget_state)
            for label_key in associated_labels_keys:
                if label_key in label_widgets_map:
                    label_widgets_map[label_key].config(
                        foreground=label_fg_color)
        return toggle_fields

    current_main_row = 0

    top_frames_data = [
        {"title": "Core Bot Settings", "keys": CONFIG_KEYS_CORE,
            "enable_key": None, "is_api": False},
        {"title": "Plex API",
            "keys": CONFIG_KEYS_PLEX[1:], "enable_key": "PLEX_ENABLED", "is_api": True},
        {"title": "Radarr API",
            "keys": CONFIG_KEYS_RADARR[1:], "enable_key": "RADARR_ENABLED", "is_api": True},
        {"title": "Sonarr API",
            "keys": CONFIG_KEYS_SONARR[1:], "enable_key": "SONARR_ENABLED", "is_api": True},
        {"title": "AB Download Manager",
            "keys": CONFIG_KEYS_ABDM[1:], "enable_key": "ABDM_ENABLED", "is_api": True},
    ]
    for idx, frame_data in enumerate(top_frames_data):
        frame_lf = ttk.LabelFrame(
            main_frame, text=frame_data["title"], padding="10")
        grid_row = current_main_row + (idx // 2)
        grid_col = idx % 2
        frame_lf.grid(row=grid_row, column=grid_col, sticky=(
            tk.W, tk.E, tk.N, tk.S), pady=(0, 10), padx=5)
        frame_lf.grid_columnconfigure(0, weight=1)
        current_internal_row = 0
        dependent_detail_keys = []
        associated_label_keys_for_frame = []

        if frame_data["enable_key"]:
            enable_key = frame_data["enable_key"]
            enable_def = CONFIG_FIELD_DEFINITIONS[enable_key]
            enabled_var = tk.BooleanVar(value=initial_values.get(
                enable_key, enable_def.get("default", False)))
            entries_vars[enable_key] = enabled_var
            check_button = ttk.Checkbutton(
                frame_lf, text=enable_def["label"], variable=enabled_var)
            check_button.grid(row=current_internal_row,
                              column=0, sticky=tk.W, pady=(0, 5), padx=5)
            widgets_map[enable_key] = [check_button]
            current_internal_row += 1

        for key in frame_data["keys"]:
            definition = CONFIG_FIELD_DEFINITIONS[key]
            label_widget = ttk.Label(frame_lf, text=definition["label"])
            label_widget.grid(row=current_internal_row,
                              column=0, sticky=tk.W, pady=(5, 0), padx=5)
            label_widgets_map[key] = label_widget
            associated_label_keys_for_frame.append(
                key)
            current_internal_row += 1
            entry_var = tk.StringVar(value=initial_values.get(
                key, definition.get("default", "")))
            entry_width = definition["width"] if "Core" in frame_data["title"] else int(
                definition["width"] * 0.85)
            if entry_width < 20:
                entry_width = 20
            entry = ttk.Entry(frame_lf, width=entry_width,
                              textvariable=entry_var)
            entry.grid(row=current_internal_row, column=0,
                       sticky=(tk.W, tk.E), pady=(0, 5), padx=5)
            entries_vars[key] = entry_var
            widgets_map.setdefault(key, []).append(entry)
            dependent_detail_keys.append(key)
            current_internal_row += 1

        if frame_data["enable_key"]:
            toggle_func = make_toggle_dependent_fields_func(
                frame_data["enable_key"],
                dependent_detail_keys,

                associated_labels_keys=associated_label_keys_for_frame
            )
            widgets_map[frame_data["enable_key"]
                        ][0].config(command=toggle_func)
            toggle_func()
    current_main_row += (len(top_frames_data) + 1) // 2

    general_settings_lf = ttk.LabelFrame(
        main_frame, text="General Settings (UI, PC Control & Logging)", padding="10")
    general_settings_lf.grid(row=current_main_row, column=0, columnspan=2, sticky=(
        tk.W, tk.E), pady=(0, 10), padx=5)
    general_settings_lf.grid_columnconfigure(0, weight=1)
    general_settings_lf.grid_columnconfigure(1, weight=0)
    general_settings_lf.grid_columnconfigure(2, weight=1)
    current_main_row += 1
    gs_row = 0
    pc_enable_key = CONFIG_KEYS_PC_CONTROL[0]
    pc_enable_def = CONFIG_FIELD_DEFINITIONS[pc_enable_key]
    pc_enabled_var = tk.BooleanVar(value=initial_values.get(
        pc_enable_key, pc_enable_def.get("default", False)))
    entries_vars[pc_enable_key] = pc_enabled_var
    pc_check_button = ttk.Checkbutton(
        general_settings_lf, text=pc_enable_def["label"], variable=pc_enabled_var)
    pc_check_button.grid(row=gs_row, column=0, columnspan=3,
                         sticky=tk.W, pady=(0, 10), padx=5)
    widgets_map[pc_enable_key] = [pc_check_button]
    gs_row += 1
    for key in CONFIG_KEYS_UI_BEHAVIOR:
        definition = CONFIG_FIELD_DEFINITIONS[key]
        label_widget = ttk.Label(general_settings_lf, text=definition["label"])
        label_widget.grid(row=gs_row, column=0, sticky=tk.W, pady=2, padx=5)
        label_widgets_map[key] = label_widget
        entry_var = tk.StringVar(value=initial_values.get(
            key, definition.get("default", "")))
        entry = ttk.Entry(general_settings_lf,
                          width=definition["width"], textvariable=entry_var)
        entry.grid(row=gs_row, column=1, sticky=tk.W, pady=2, padx=5)
        entries_vars[key] = entry_var
        widgets_map[key] = [entry]
        gs_row += 1
    log_level_key = "LOG_LEVEL"
    log_level_def = CONFIG_FIELD_DEFINITIONS[log_level_key]
    log_label = ttk.Label(general_settings_lf, text=log_level_def["label"])
    log_label.grid(row=gs_row, column=0, sticky=tk.W, pady=2, padx=5)
    log_level_var = tk.StringVar(value=initial_values.get(
        log_level_key, log_level_def.get("default", "INFO")))
    log_combobox = ttk.Combobox(general_settings_lf, textvariable=log_level_var,
                                values=log_level_def["options"], state="readonly", width=log_level_def["width"] - 2)
    log_combobox.grid(row=gs_row, column=1, sticky=tk.W, pady=2, padx=5)
    entries_vars[log_level_key] = log_level_var
    widgets_map[log_level_key] = [log_combobox]
    gs_row += 1

    launchers_main_lf = ttk.LabelFrame(
        main_frame, text="Application Launchers", padding="10")
    launchers_main_lf.grid(row=current_main_row, column=0, columnspan=2, sticky=(
        tk.W, tk.E), pady=(0, 10), padx=5)
    current_main_row += 1
    launchers_main_lf.grid_columnconfigure(0, weight=0)
    launchers_main_lf.grid_columnconfigure(1, weight=1)
    launchers_main_lf.grid_columnconfigure(2, weight=1)

    launcher_configs = [{"title": "Plex Media Server", "keys": CONFIG_KEYS_PLEX_LAUNCHER},
                        {"title": "Sonarr", "keys": CONFIG_KEYS_SONARR_LAUNCHER},
                        {"title": "Radarr", "keys": CONFIG_KEYS_RADARR_LAUNCHER},
                        {"title": "Prowlarr", "keys": CONFIG_KEYS_PROWLARR_LAUNCHER},
                        {"title": "Torrent Client",
                            "keys": CONFIG_KEYS_TORRENT_LAUNCHER},
                        {"title": "AB Download Manager", "keys": CONFIG_KEYS_ABDM_LAUNCHER},]

    current_launcher_row_internal = 0
    for launcher_info in launcher_configs:
        enabled_key, name_key, path_key = launcher_info["keys"]

        launcher_specific_associated_labels = [
            name_key, path_key]

        enable_def = CONFIG_FIELD_DEFINITIONS[enabled_key]
        enabled_var = tk.BooleanVar(value=initial_values.get(
            enabled_key, enable_def.get("default", False)))
        entries_vars[enabled_key] = enabled_var
        enable_check = ttk.Checkbutton(
            launchers_main_lf, text=launcher_info["title"], variable=enabled_var)
        enable_check.grid(row=current_launcher_row_internal,
                          column=0, sticky=tk.W, pady=(5, 0), padx=5)
        widgets_map.setdefault(enabled_key, []).append(enable_check)

        name_def = CONFIG_FIELD_DEFINITIONS[name_key]
        name_label = ttk.Label(launchers_main_lf, text=name_def["label"])
        name_label.grid(row=current_launcher_row_internal,
                        column=1, sticky=tk.W, pady=(5, 0), padx=(10, 2))
        label_widgets_map[name_key] = name_label

        path_def = CONFIG_FIELD_DEFINITIONS[path_key]
        path_label = ttk.Label(launchers_main_lf, text=path_def["label"])
        path_label.grid(row=current_launcher_row_internal,
                        column=2, sticky=tk.W, pady=(5, 0), padx=(10, 2))
        label_widgets_map[path_key] = path_label

        current_launcher_row_internal += 1

        name_var = tk.StringVar(value=initial_values.get(
            name_key, name_def.get("default", f"Launch {launcher_info['title']}")))
        name_entry = ttk.Entry(
            launchers_main_lf, width=25, textvariable=name_var)
        name_entry.grid(row=current_launcher_row_internal, column=1,
                        sticky=(tk.W, tk.E), pady=(0, 5), padx=(20, 5))
        entries_vars[name_key] = name_var
        widgets_map.setdefault(name_key, []).append(name_entry)

        path_var = tk.StringVar(value=initial_values.get(
            path_key, path_def.get("default", "")))
        path_entry_frame = ttk.Frame(launchers_main_lf)
        path_entry_frame.grid(row=current_launcher_row_internal, column=2, sticky=(
            tk.W, tk.E), pady=(0, 5), padx=(20, 5))
        path_entry_frame.grid_columnconfigure(0, weight=1)
        path_entry = ttk.Entry(path_entry_frame, textvariable=path_var)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def browse_file_launcher(e_var=path_var, p_key=path_key):
            current_path_val = e_var.get()
            filetypes = [("All files", "*.*"), ("Executable files", "*.exe"), ("Batch files",
                                                                               "*.bat;*.cmd"), ("Shell scripts", "*.sh"), ("Shortcut files", "*.lnk")]
            initial_dir_val = os.path.dirname(current_path_val) if current_path_val and os.path.exists(
                os.path.dirname(current_path_val)) else os.path.expanduser("~")
            filepath = filedialog.askopenfilename(
                title=f"Select {CONFIG_FIELD_DEFINITIONS[p_key]['label']}", filetypes=filetypes, initialdir=initial_dir_val)
            if filepath:
                e_var.set(filepath)
        browse_button = ttk.Button(path_entry_frame, text="Browse...",
                                   command=lambda ev=path_var, pk=path_key: browse_file_launcher(ev, pk))
        browse_button.pack(side=tk.LEFT, padx=(2, 0))
        entries_vars[path_key] = path_var
        widgets_map.setdefault(path_key, []).extend(
            [path_entry, browse_button])

        if launcher_info != launcher_configs[-1]:
            sep = ttk.Separator(launchers_main_lf, orient='horizontal')
            sep.grid(row=current_launcher_row_internal + 1, column=0,
                     columnspan=3, sticky='ew', pady=10, padx=5)

        current_launcher_row_internal += 2

        launcher_toggle_func = make_toggle_dependent_fields_func(
            enabled_key, [name_key, path_key],
            associated_labels_keys=launcher_specific_associated_labels
        )
        enable_check.config(command=launcher_toggle_func)
        launcher_toggle_func()

    scripts_main_lf = ttk.LabelFrame(
        main_frame, text="Custom Scripts", padding="10")
    scripts_main_lf.grid(row=current_main_row, column=0,
                         columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10), padx=5)
    current_main_row += 1
    scripts_main_lf.grid_columnconfigure(0, weight=0)
    scripts_main_lf.grid_columnconfigure(1, weight=1)
    scripts_main_lf.grid_columnconfigure(
        2, weight=2)
    script_keys_list = [CONFIG_KEYS_SCRIPT_1,
                        CONFIG_KEYS_SCRIPT_2, CONFIG_KEYS_SCRIPT_3]

    current_script_row_internal = 0
    for script_idx, script_keys_group in enumerate(script_keys_list):
        enabled_key, name_key, path_key = script_keys_group
        script_title = f"Custom Script {script_idx + 1}"

        script_specific_associated_labels = [
            name_key, path_key]

        enable_def = CONFIG_FIELD_DEFINITIONS[enabled_key]
        script_enabled_var = tk.BooleanVar(value=initial_values.get(
            enabled_key, enable_def.get("default", False)))
        entries_vars[enabled_key] = script_enabled_var
        script_check = ttk.Checkbutton(
            scripts_main_lf, text=script_title, variable=script_enabled_var)
        script_check.grid(row=current_script_row_internal,
                          column=0, sticky=tk.W, pady=(5, 0), padx=5)
        widgets_map.setdefault(enabled_key, []).append(script_check)

        name_def = CONFIG_FIELD_DEFINITIONS[name_key]
        name_label = ttk.Label(scripts_main_lf, text=name_def["label"])
        name_label.grid(row=current_script_row_internal, column=1,
                        sticky=tk.W, pady=(5, 0), padx=(10, 2))
        label_widgets_map[name_key] = name_label

        path_def = CONFIG_FIELD_DEFINITIONS[path_key]
        path_label = ttk.Label(scripts_main_lf, text=path_def["label"])
        path_label.grid(row=current_script_row_internal, column=2,
                        sticky=tk.W, pady=(5, 0), padx=(10, 2))
        label_widgets_map[path_key] = path_label

        current_script_row_internal += 1

        name_var = tk.StringVar(value=initial_values.get(
            name_key, name_def.get("default", f"Script {script_idx+1}")))
        name_entry = ttk.Entry(scripts_main_lf, width=25,
                               textvariable=name_var)
        name_entry.grid(row=current_script_row_internal, column=1,
                        sticky=(tk.W, tk.E), pady=(0, 5), padx=(20, 5))
        entries_vars[name_key] = name_var
        widgets_map.setdefault(name_key, []).append(name_entry)

        path_var = tk.StringVar(value=initial_values.get(
            path_key, path_def.get("default", "")))
        path_entry_frame_script = ttk.Frame(
            scripts_main_lf)
        path_entry_frame_script.grid(row=current_script_row_internal, column=2, sticky=(
            tk.W, tk.E), pady=(0, 5), padx=(20, 5))
        path_entry_frame_script.grid_columnconfigure(0, weight=1)
        path_entry_script = ttk.Entry(
            path_entry_frame_script, textvariable=path_var)
        path_entry_script.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def browse_file_custom_script(e_var=path_var, p_key=path_key):
            current_path_val = e_var.get()
            filetypes = [("All files", "*.*"), ("Executable files", "*.exe"), ("Batch files",
                                                                               "*.bat;*.cmd"), ("Shell scripts", "*.sh"), ("Shortcut files", "*.lnk")]
            initial_dir_val = os.path.dirname(current_path_val) if current_path_val and os.path.exists(
                os.path.dirname(current_path_val)) else os.path.expanduser("~")
            filepath = filedialog.askopenfilename(
                title=f"Select {CONFIG_FIELD_DEFINITIONS[p_key]['label']}", filetypes=filetypes, initialdir=initial_dir_val)
            if filepath:
                e_var.set(filepath)
        browse_button_script = ttk.Button(path_entry_frame_script, text="Browse...",
                                          command=lambda ev=path_var, pk=path_key: browse_file_custom_script(ev, pk))
        browse_button_script.pack(side=tk.LEFT, padx=(2, 0))
        entries_vars[path_key] = path_var
        widgets_map.setdefault(path_key, []).extend(
            [path_entry_script, browse_button_script])

        if script_idx < len(script_keys_list) - 1:
            sep = ttk.Separator(scripts_main_lf, orient='horizontal')
            sep.grid(row=current_script_row_internal + 1, column=0,
                     columnspan=3, sticky='ew', pady=10, padx=5)
        current_script_row_internal += 2

        script_toggle_func = make_toggle_dependent_fields_func(
            enabled_key, [name_key, path_key],
            associated_labels_keys=script_specific_associated_labels
        )
        script_check.config(command=script_toggle_func)
        script_toggle_func()

    result = {"saved": False, "log_level_changed": False}

    def save_config():
        nonlocal result
        config_data = {}
        has_errors = False

        for key_widget in ALL_USER_CONFIG_KEYS:
            if key_widget not in entries_vars:

                continue
            var = entries_vars[key_widget]
            definition = CONFIG_FIELD_DEFINITIONS.get(key_widget, {})
            value = None
            if isinstance(var, tk.BooleanVar):
                value = var.get()
                config_data[key_widget] = value
            else:
                value_str = var.get().strip()
                config_data[key_widget] = value_str
                is_required = definition.get("required", False)

                is_enabled_dependency_key = definition.get("depends_on")
                is_required_if_enabled_key = definition.get(
                    "required_if_enabled")

                field_is_active_for_validation = True
                if is_enabled_dependency_key and is_enabled_dependency_key in entries_vars and isinstance(entries_vars.get(is_enabled_dependency_key), tk.BooleanVar):
                    field_is_active_for_validation = entries_vars[is_enabled_dependency_key].get(
                    )
                elif is_required_if_enabled_key and is_required_if_enabled_key in entries_vars and isinstance(entries_vars.get(is_required_if_enabled_key), tk.BooleanVar):
                    field_is_active_for_validation = entries_vars[is_required_if_enabled_key].get(
                    )

                if (is_required or (is_required_if_enabled_key and field_is_active_for_validation)) and not value_str:
                    messagebox.showerror(
                        "Error", f"'{definition['label']}' cannot be empty.", parent=root)
                    has_errors = True
                    break
                if key_widget == "CHAT_ID" and value_str and not value_str.lstrip('-').isdigit():
                    messagebox.showerror(
                        "Error", f"'{definition['label']}' must be a numerical ID.", parent=root)
                    has_errors = True
                    break
                if key_widget in ["ADD_MEDIA_MAX_SEARCH_RESULTS", "ADD_MEDIA_ITEMS_PER_PAGE", "ABDM_PORT"]:
                    if value_str and not value_str.isdigit():
                        messagebox.showerror(
                            "Error", f"'{definition['label']}' must be a number.", parent=root)
                        has_errors = True
                        break

                    if value_str and int(value_str) <= 0:
                        if not (key_widget == "ABDM_PORT" and not entries_vars["ABDM_ENABLED"].get()):
                            messagebox.showerror(
                                "Error", f"'{definition['label']}' must be > 0.", parent=root)
                            has_errors = True
                            break
            if has_errors:
                break
        if has_errors:
            return

        current_selected_log_level = config_data.get("LOG_LEVEL", "INFO")
        if current_selected_log_level != initial_log_level_on_ui_open:
            result["log_level_changed"] = True
            logger_ui.info(
                f"Log level changed from '{initial_log_level_on_ui_open}' to '{current_selected_log_level}'. Restart will be advised.")

        try:

            config_dir = os.path.dirname(config_file_to_write_path)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
                logger_ui.info(
                    f"Created directory for config file: {config_dir}")

            with open(config_file_to_write_path, "w", encoding="utf-8") as f:

                f.write("# config.py - Automatically generated by Media Bot UI\n")
                f.write("\n# --- General Settings ---\n")
                f.write(
                    f'TELEGRAM_BOT_TOKEN = "{config_data.get("TELEGRAM_BOT_TOKEN", "")}"\n')
                f.write(f'CHAT_ID = "{config_data.get("CHAT_ID", "")}"\n\n')
                f.write("# --- API Service Configurations ---\n")
                f.write(
                    f'PLEX_ENABLED = {config_data.get("PLEX_ENABLED", False)}\n')
                f.write(f'PLEX_URL = "{config_data.get("PLEX_URL", "")}"\n')
                f.write(
                    f'PLEX_TOKEN = "{config_data.get("PLEX_TOKEN", "")}"\n\n')
                f.write(
                    f'RADARR_ENABLED = {config_data.get("RADARR_ENABLED", False)}\n')
                f.write(
                    f'RADARR_API_URL = "{config_data.get("RADARR_API_URL", "")}"\n')
                f.write(
                    f'RADARR_API_KEY = "{config_data.get("RADARR_API_KEY", "")}"\n\n')
                f.write(
                    f'SONARR_ENABLED = {config_data.get("SONARR_ENABLED", False)}\n')
                f.write(
                    f'SONARR_API_URL = "{config_data.get("SONARR_API_URL", "")}"\n')
                f.write(
                    f'SONARR_API_KEY = "{config_data.get("SONARR_API_KEY", "")}"\n\n')
                f.write(
                    f'ABDM_ENABLED = {config_data.get("ABDM_ENABLED", False)}\n')

                abdm_port_val_str = config_data.get("ABDM_PORT", "15151")
                abdm_port_val_int = 15151
                if abdm_port_val_str.isdigit():
                    abdm_port_val_int = int(abdm_port_val_str)

                elif config_data.get("ABDM_ENABLED"):
                    logger_ui.warning(
                        "ABDM enabled but port is invalid, using default 15151.")
                f.write(
                    f'ABDM_PORT = {abdm_port_val_int}\n\n')

                f.write("# --- General Settings (Logging, UI & PC Control) ---\n")
                f.write(
                    f'LOG_LEVEL = "{config_data.get("LOG_LEVEL", "INFO")}"\n')
                pc_control_key_val = CONFIG_KEYS_PC_CONTROL[0]
                f.write(
                    f'{pc_control_key_val} = {config_data.get(pc_control_key_val, False)}\n')
                f.write(
                    f'ADD_MEDIA_MAX_SEARCH_RESULTS = {config_data.get("ADD_MEDIA_MAX_SEARCH_RESULTS", 30)}\n')
                f.write(
                    f'ADD_MEDIA_ITEMS_PER_PAGE = {config_data.get("ADD_MEDIA_ITEMS_PER_PAGE", 5)}\n\n')
                f.write("# --- Application Launcher Configurations ---\n")
                launcher_key_groups = [CONFIG_KEYS_PLEX_LAUNCHER, CONFIG_KEYS_SONARR_LAUNCHER,
                                       CONFIG_KEYS_RADARR_LAUNCHER, CONFIG_KEYS_PROWLARR_LAUNCHER, CONFIG_KEYS_TORRENT_LAUNCHER,
                                       CONFIG_KEYS_ABDM_LAUNCHER]
                for launcher_key_group in launcher_key_groups:
                    enabled_k, name_k, path_k = launcher_key_group
                    f.write(
                        f'{enabled_k} = {config_data.get(enabled_k, False)}\n')
                    f.write(f'{name_k} = "{config_data.get(name_k, "")}"\n')
                    f.write(f'{path_k} = r"{config_data.get(path_k, "")}"\n\n')
                f.write("# --- Custom Script Configurations ---\n")
                for i in range(1, 4):
                    f.write(
                        f'SCRIPT_{i}_ENABLED = {config_data.get(f"SCRIPT_{i}_ENABLED", False)}\n')
                    f.write(
                        f'SCRIPT_{i}_NAME = "{config_data.get(f"SCRIPT_{i}_NAME", "")}"\n')
                    f.write(
                        f'SCRIPT_{i}_PATH = r"{config_data.get(f"SCRIPT_{i}_PATH", "")}"\n')
                    if i < 3:
                        f.write("\n")

            success_message = "Configuration saved!\nThe bot will attempt to reload settings if running."
            if result["log_level_changed"]:
                success_message += "\n\nIMPORTANT: Log level changed. Please restart the bot for this setting to take full effect."
            messagebox.showinfo("Success", success_message, parent=root)
            result["saved"] = True
            root.destroy()
        except IOError as e:
            messagebox.showerror(
                "Error", f"Failed to save configuration to '{config_file_to_write_path}':\n{e}", parent=root)
            result["saved"] = False
            result["log_level_changed"] = False

    button_frame = ttk.Frame(main_frame)
    button_frame.grid(row=current_main_row, column=0,
                      columnspan=2, pady=15, sticky="ew")
    button_frame.grid_columnconfigure(0, weight=1)
    button_frame.grid_columnconfigure(1, weight=1)
    save_button = ttk.Button(
        button_frame, text="Save Configuration", command=save_config)
    save_button.grid(row=0, column=0, padx=5, sticky="e")
    cancel_button = ttk.Button(
        button_frame, text="Cancel", command=root.destroy)
    cancel_button.grid(row=0, column=1, padx=5, sticky="w")
    root.update_idletasks()
    initial_width = 900
    initial_height = 800
    root.geometry(f'{initial_width}x{initial_height}')
    root.minsize(850, 650)
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x_pos = (root.winfo_screenwidth() // 2) - (width // 2)
    y_pos = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x_pos}+{y_pos}')
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()
    return result


if __name__ == '__main__':

    if not logging.getLogger().hasHandlers():
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    test_data_dir = "data_test_ui"
    if not os.path.exists(test_data_dir):
        os.makedirs(test_data_dir)
    test_config_path = os.path.join(test_data_dir, "test_config_generated.py")

    mock_initial_values = {
        "TELEGRAM_BOT_TOKEN": "test_token_123", "CHAT_ID": "123456789",
        "PLEX_ENABLED": True, "PLEX_URL": "http://localhost:32400", "PLEX_TOKEN": "plex_token",
        CONFIG_KEYS_PC_CONTROL[0]: True,
        "ADD_MEDIA_MAX_SEARCH_RESULTS": "25", "ADD_MEDIA_ITEMS_PER_PAGE": "7",
        "PLEX_LAUNCHER_ENABLED": True, "PLEX_LAUNCHER_NAME": "Start Plex Server", "PLEX_LAUNCHER_PATH": "C:/Plex/Plex Media Server.exe",
        "ABDM_ENABLED": True, "ABDM_PORT": "15152",
        "ABDM_LAUNCHER_ENABLED": True, "ABDM_LAUNCHER_NAME": "Launch AB Test", "ABDM_LAUNCHER_PATH": "C:/path/to/ABTest.exe",
        "LOG_LEVEL": "DEBUG"
    }
    ui_result = run_config_ui(test_config_path, mock_initial_values)
    print(f"UI Result: {ui_result}")
    if ui_result["saved"]:
        print(f"Config (mock) saved to {test_config_path}")
    if ui_result.get("log_level_changed"):
        print("Log level was changed during UI session.")
