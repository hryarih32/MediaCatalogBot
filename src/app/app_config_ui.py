
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import logging
import json
import datetime
import uuid

from src.config.config_definitions import (
    CONFIG_KEYS_CORE, CONFIG_KEYS_PLEX, CONFIG_KEYS_RADARR, CONFIG_KEYS_SONARR,
    CONFIG_KEYS_PC_CONTROL, CONFIG_KEYS_UI_BEHAVIOR, CONFIG_KEYS_LOGGING,
    ALL_USER_CONFIG_KEYS, CONFIG_FIELD_DEFINITIONS, CONFIG_KEYS_ABDM, LOG_LEVEL_OPTIONS
)
from src.app.app_config_holder import ROLE_ADMIN, ROLE_STANDARD_USER
from .app_file_utils import get_ico_file_path, get_bot_state_file_path, load_json_data, save_json_data
import src.app.user_manager as user_manager
from src.app.user_manager import DEFAULT_BOT_STATE

logger_ui = logging.getLogger(__name__ + "_ui")


def run_config_ui(config_file_to_write_path, initial_values=None):
    if initial_values is None:
        initial_values = {}

    initial_log_level_on_ui_open = initial_values.get(
        "LOG_LEVEL", CONFIG_FIELD_DEFINITIONS.get("LOG_LEVEL", {}).get("default", "INFO"))

    bot_state_path = get_bot_state_file_path()
    loaded_bot_state = load_json_data(bot_state_path)

    initial_user_data_on_gui_open = {}
    initial_dynamic_launchers_on_gui_open = []
    static_launchers_already_migrated = False
    other_bot_state_parts_on_gui_open = DEFAULT_BOT_STATE.copy()

    if loaded_bot_state is None:
        logger_ui.info(
            f"{bot_state_path} not found/invalid, starting with default structure.")
        initial_user_data_on_gui_open = DEFAULT_BOT_STATE['users'].copy()
        initial_dynamic_launchers_on_gui_open = DEFAULT_BOT_STATE['dynamic_launchers'].copy(
        )

        del other_bot_state_parts_on_gui_open['users']

        del other_bot_state_parts_on_gui_open['dynamic_launchers']
    else:
        initial_user_data_on_gui_open = loaded_bot_state.get(
            "users", DEFAULT_BOT_STATE['users'].copy())
        initial_dynamic_launchers_on_gui_open = loaded_bot_state.get(
            "dynamic_launchers", DEFAULT_BOT_STATE['dynamic_launchers'].copy())
        static_launchers_already_migrated = loaded_bot_state.get(
            "bot_info", {}).get("static_launchers_migrated", False)
        for key, value in loaded_bot_state.items():
            if key not in ['users', 'dynamic_launchers']:
                other_bot_state_parts_on_gui_open[key] = value

    gui_user_data_state = {k: v.copy()
                           for k, v in initial_user_data_on_gui_open.items()}
    gui_dynamic_launchers_state = [
        launcher.copy() for launcher in initial_dynamic_launchers_on_gui_open]
    static_launchers_migrated_this_session = False

    primary_admin_chat_id_loaded = initial_values.get("CHAT_ID", "")

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

    main_canvas = tk.Canvas(root)
    scrollbar = ttk.Scrollbar(root, orient="vertical",
                              command=main_canvas.yview)
    scrollable_frame_for_notebook = ttk.Frame(main_canvas)
    scrollable_frame_for_notebook.bind("<Configure>", lambda e: main_canvas.configure(
        scrollregion=main_canvas.bbox("all")))
    main_canvas_frame_id = main_canvas.create_window(
        (0, 0), window=scrollable_frame_for_notebook, anchor="nw")
    main_canvas.configure(yscrollcommand=scrollbar.set)

    def on_main_canvas_configure(event): main_canvas.itemconfig(
        main_canvas_frame_id, width=event.width)
    main_canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    main_canvas.bind("<Configure>", on_main_canvas_configure)

    def _on_mousewheel(event):
        delta = 0
        if event.num == 4:
            delta = -1
        elif event.num == 5:
            delta = 1
        else:
            delta = int(-1 * (event.delta / 120))
        main_canvas.yview_scroll(delta, "units")

    for widget_to_bind_scroll in [main_canvas, scrollable_frame_for_notebook, root]:
        widget_to_bind_scroll.bind_all("<MouseWheel>", _on_mousewheel)
        widget_to_bind_scroll.bind_all("<Button-4>", _on_mousewheel)
        widget_to_bind_scroll.bind_all("<Button-5>", _on_mousewheel)

    notebook = ttk.Notebook(scrollable_frame_for_notebook)
    notebook.pack(expand=True, fill="both", padx=10, pady=10)

    tab_core_general = ttk.Frame(notebook, padding="10")
    tab_api_services = ttk.Frame(notebook, padding="10")
    tab_launcher_management = ttk.Frame(notebook, padding="10")
    tab_user_management = ttk.Frame(notebook, padding="10")

    notebook.add(tab_core_general, text='Core & General')
    notebook.add(tab_api_services, text='API Services')
    notebook.add(tab_launcher_management, text='Launcher Management')
    notebook.add(tab_user_management, text='User Management')

    entries_vars = {}
    widgets_map = {}
    label_widgets_map = {}

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
                        if isinstance(widget, (ttk.Entry, ttk.Button, ttk.Combobox, ttk.Checkbutton)):
                            widget.config(state=widget_state)
                        elif isinstance(widget, tk.Frame):
                            for child_widget in widget.winfo_children():
                                if isinstance(child_widget, (ttk.Entry, ttk.Button)):
                                    child_widget.config(state=widget_state)
            for label_key in associated_labels_keys:
                if label_key in label_widgets_map:
                    label_widgets_map[label_key].config(
                        foreground=label_fg_color)
        return toggle_fields

    def create_field(parent_frame, key, definition, row_num, initial_val, col_span=1):
        item_label_widget = ttk.Label(parent_frame, text=definition["label"])
        item_label_widget.grid(row=row_num, column=0, sticky=tk.W, pady=(
            5, 0) if definition["type"] != "checkbutton" else (2, 0), padx=5)
        label_widgets_map[key] = item_label_widget
        actual_initial_val = initial_val
        current_widgets = []
        if definition["type"] == "entry":
            entry_var = tk.StringVar(value=actual_initial_val)
            entry = ttk.Entry(parent_frame, width=definition.get(
                "width", 40), textvariable=entry_var)
            entry.grid(row=row_num, column=1, sticky=(tk.W, tk.E), pady=(
                5, 5) if definition["type"] != "checkbutton" else (2, 2), padx=5, columnspan=col_span)
            entries_vars[key] = entry_var
            current_widgets.append(entry)
        elif definition["type"] == "combobox":
            combo_var = tk.StringVar(value=actual_initial_val)
            combobox = ttk.Combobox(parent_frame, textvariable=combo_var,
                                    values=definition["options"], state="readonly", width=definition.get("width", 15)-2)
            combobox.grid(row=row_num, column=1, sticky=tk.W,
                          pady=(5, 5), padx=5, columnspan=col_span)
            entries_vars[key] = combo_var
            current_widgets.append(combobox)

        widgets_map.setdefault(key, []).extend(current_widgets)

    core_general_lf = ttk.LabelFrame(
        tab_core_general, text="Bot Core & General Configuration", padding="10")
    core_general_lf.pack(fill="x", expand=True, padx=5, pady=5)
    core_general_lf.grid_columnconfigure(1, weight=1)
    cg_row = 0
    for key in CONFIG_KEYS_CORE:
        create_field(core_general_lf, key, CONFIG_FIELD_DEFINITIONS[key], cg_row, initial_values.get(
            key, CONFIG_FIELD_DEFINITIONS[key].get("default", "")))
        cg_row += 1
    ttk.Separator(core_general_lf, orient='horizontal').grid(
        row=cg_row, column=0, columnspan=3, sticky='ew', pady=10, padx=5)
    cg_row += 1
    for key in CONFIG_KEYS_LOGGING + CONFIG_KEYS_UI_BEHAVIOR:
        create_field(core_general_lf, key, CONFIG_FIELD_DEFINITIONS[key], cg_row, initial_values.get(
            key, CONFIG_FIELD_DEFINITIONS[key].get("default", "")))
        cg_row += 1
    pc_control_key = CONFIG_KEYS_PC_CONTROL[0]
    pc_control_def = CONFIG_FIELD_DEFINITIONS[pc_control_key]
    pc_control_var = tk.BooleanVar(value=initial_values.get(
        pc_control_key, pc_control_def.get("default", False)))
    entries_vars[pc_control_key] = pc_control_var
    pc_check = ttk.Checkbutton(
        core_general_lf, text=pc_control_def["label"], variable=pc_control_var)
    pc_check.grid(row=cg_row, column=0, columnspan=2,
                  sticky=tk.W, pady=(10, 5), padx=5)
    widgets_map[pc_control_key] = [pc_check]
    cg_row += 1

    api_services_data_phase_a = [
        {"title": "Plex API", "enable_key": "PLEX_ENABLED",
            "api_keys": CONFIG_KEYS_PLEX[1:]},
        {"title": "Radarr API", "enable_key": "RADARR_ENABLED",
            "api_keys": CONFIG_KEYS_RADARR[1:]},
        {"title": "Sonarr API", "enable_key": "SONARR_ENABLED",
            "api_keys": CONFIG_KEYS_SONARR[1:]},
        {"title": "ABDM API", "enable_key": "ABDM_ENABLED",
            "api_keys": CONFIG_KEYS_ABDM[1:]},
    ]
    for service_data in api_services_data_phase_a:
        service_lf = ttk.LabelFrame(
            tab_api_services, text=service_data["title"], padding="10")
        service_lf.pack(fill="x", expand=True, padx=5, pady=5)
        service_lf.grid_columnconfigure(1, weight=1)
        s_row = 0
        enable_key = service_data["enable_key"]
        enable_def = CONFIG_FIELD_DEFINITIONS[enable_key]
        enabled_var = tk.BooleanVar(value=initial_values.get(
            enable_key, enable_def.get("default", False)))
        entries_vars[enable_key] = enabled_var
        enable_check_api = ttk.Checkbutton(
            service_lf, text=enable_def["label"], variable=enabled_var)
        enable_check_api.grid(row=s_row, column=0,
                              columnspan=2, sticky=tk.W, pady=(0, 5), padx=5)
        widgets_map.setdefault(enable_key, []).append(enable_check_api)
        s_row += 1
        dependent_api_fields = []
        associated_api_labels = []
        for key in service_data["api_keys"]:
            create_field(service_lf, key, CONFIG_FIELD_DEFINITIONS[key], s_row, initial_values.get(
                key, CONFIG_FIELD_DEFINITIONS[key].get("default", "")), col_span=1)
            dependent_api_fields.append(key)
            associated_api_labels.append(key)
            s_row += 1
        toggle_api_func = make_toggle_dependent_fields_func(
            enable_key, dependent_api_fields, associated_api_labels)
        enable_check_api.config(command=toggle_api_func)
        toggle_api_func()

    launcher_management_lf = ttk.LabelFrame(
        tab_launcher_management, text="Dynamic Launcher Configuration", padding="10")
    launcher_management_lf.pack(fill="both", expand=True, padx=5, pady=5)
    launcher_management_lf.grid_columnconfigure(0, weight=1)
    launcher_management_lf.grid_rowconfigure(1, weight=1)

    migration_frame = ttk.Frame(launcher_management_lf)
    migration_frame.grid(row=0, column=0, columnspan=3,
                         sticky="ew", pady=(0, 10))
    migration_button = ttk.Button(
        migration_frame, text="Import Static Launchers/Scripts from old config.py settings")

    def do_migration():
        nonlocal static_launchers_migrated_this_session
        migrated_count = 0

        static_item_definitions = [
            ("PLEX_LAUNCHER", "Plex App",
             "Services"), ("SONARR_LAUNCHER", "Sonarr UI", "Services"),
            ("RADARR_LAUNCHER", "Radarr UI",
             "Services"), ("ABDM_LAUNCHER", "ABDM UI", "Services"),
            ("PROWLARR_LAUNCHER", "Prowlarr UI",
             "Services"), ("TORRENT_LAUNCHER", "Torrent Client", "Services"),
            ("SCRIPT_1", "Custom Script 1",
             "Scripts"), ("SCRIPT_2", "Custom Script 2", "Scripts"),
            ("SCRIPT_3", "Custom Script 3", "Scripts")
        ]
        for key_prefix, default_name, default_subgroup in static_item_definitions:

            enabled_val = initial_values.get(f"{key_prefix}_ENABLED", False)
            if enabled_val:
                name_val = initial_values.get(
                    f"{key_prefix}_NAME", default_name)
                path_val = initial_values.get(f"{key_prefix}_PATH", "")
                if name_val and path_val:
                    exists = any(l['name'] == name_val and l['path']
                                 == path_val for l in gui_dynamic_launchers_state)
                    if not exists:
                        new_id = uuid.uuid4().hex
                        gui_dynamic_launchers_state.append(
                            {"id": new_id, "name": name_val, "path": path_val, "subgroup": default_subgroup})
                        migrated_count += 1
        if migrated_count > 0:
            populate_launcher_tree()
            static_launchers_migrated_this_session = True
            messagebox.showinfo(
                "Migration", f"{migrated_count} static launchers/scripts imported. Review & save.", parent=root)
        else:
            messagebox.showinfo(
                "Migration", "No new static launchers/scripts found in old config values to import.", parent=root)
        migration_button.config(state=tk.DISABLED)

    migration_button.configure(command=do_migration)
    if static_launchers_already_migrated:
        migration_button.pack_forget()
    else:
        migration_button.pack(pady=5)

    launcher_tree_frame = ttk.Frame(launcher_management_lf)
    launcher_tree_frame.grid(
        row=1, column=0, columnspan=3, sticky="nsew", pady=(0, 10))
    launcher_tree_frame.grid_columnconfigure(0, weight=1)
    launcher_tree_frame.grid_rowconfigure(0, weight=1)
    launcher_tree_cols = ("name", "path", "subgroup")
    launcher_tree = ttk.Treeview(
        launcher_tree_frame, columns=launcher_tree_cols, show="headings", height=10)
    launcher_tree.heading("name", text="Launcher Name")
    launcher_tree.heading("path", text="Executable Path")
    launcher_tree.heading("subgroup", text="Subgroup")
    launcher_tree.column("name", width=200, anchor=tk.W)
    launcher_tree.column("path", width=350, anchor=tk.W)
    launcher_tree.column("subgroup", width=150, anchor=tk.W)
    launcher_tree_scrollbar_y = ttk.Scrollbar(
        launcher_tree_frame, orient="vertical", command=launcher_tree.yview)
    launcher_tree.configure(yscrollcommand=launcher_tree_scrollbar_y.set)
    launcher_tree.pack(side=tk.LEFT, fill="both", expand=True)
    launcher_tree_scrollbar_y.pack(side=tk.RIGHT, fill="y")

    launcher_controls_frame = ttk.Frame(launcher_management_lf)
    launcher_controls_frame.grid(
        row=2, column=0, columnspan=3, sticky="ew", pady=(5, 0))
    launcher_form_lf = ttk.LabelFrame(
        launcher_controls_frame, text="Add/Edit Launcher", padding="5")
    launcher_form_lf.pack(fill="x", expand=True)
    launcher_form_lf.grid_columnconfigure(1, weight=1)

    ttk.Label(launcher_form_lf, text="Name:").grid(
        row=0, column=0, sticky=tk.W, padx=2, pady=2)
    add_launcher_name_var = tk.StringVar()
    add_launcher_name_entry = ttk.Entry(
        launcher_form_lf, textvariable=add_launcher_name_var, width=40)
    add_launcher_name_entry.grid(
        row=0, column=1, columnspan=2, sticky=tk.EW, padx=2, pady=2)
    ttk.Label(launcher_form_lf, text="Path:").grid(
        row=1, column=0, sticky=tk.W, padx=2, pady=2)
    add_launcher_path_var = tk.StringVar()
    add_launcher_path_entry_frame = ttk.Frame(launcher_form_lf)
    add_launcher_path_entry_frame.grid(
        row=1, column=1, columnspan=2, sticky=tk.EW, padx=2, pady=2)
    add_launcher_path_entry_frame.grid_columnconfigure(0, weight=1)
    add_launcher_path_entry = ttk.Entry(
        add_launcher_path_entry_frame, textvariable=add_launcher_path_var)
    add_launcher_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def browse_launcher_path_gui(e_var=add_launcher_path_var):
        current_path_val = e_var.get()
        filetypes_list = [("All files", "*.*"), ("Executable files", "*.exe"), ("Batch files",
                                                                                "*.bat;*.cmd"), ("Shell scripts", "*.sh"), ("Shortcut files", "*.lnk")]
        initial_dir_val = os.path.dirname(current_path_val) if current_path_val and os.path.exists(
            os.path.dirname(current_path_val)) else os.path.expanduser("~")
        filepath = filedialog.askopenfilename(
            title="Select Executable/Script", filetypes=filetypes_list, initialdir=initial_dir_val, parent=root)
        if filepath:
            e_var.set(filepath)
    ttk.Button(add_launcher_path_entry_frame, text="Browse...", command=lambda: browse_launcher_path_gui(
        add_launcher_path_var)).pack(side=tk.LEFT, padx=(2, 0))

    ttk.Label(launcher_form_lf, text="Subgroup:").grid(
        row=2, column=0, sticky=tk.W, padx=2, pady=2)
    add_launcher_subgroup_var = tk.StringVar()

    launcher_subgroup_form_combo = ttk.Combobox(
        launcher_form_lf, textvariable=add_launcher_subgroup_var, width=37)
    launcher_subgroup_form_combo.grid(
        row=2, column=1, columnspan=2, sticky=tk.EW, padx=2, pady=2)

    current_dynamic_launchers_subgroups = set()

    def populate_launcher_tree():
        nonlocal current_dynamic_launchers_subgroups
        current_dynamic_launchers_subgroups.clear()
        for item in launcher_tree.get_children():
            launcher_tree.delete(item)
        sorted_launchers = sorted(gui_dynamic_launchers_state, key=lambda x: (
            str(x.get("subgroup") or "").lower(), str(x.get("name") or "").lower()))
        for launcher in sorted_launchers:
            launcher_tree.insert("", tk.END, values=(launcher.get("name"), launcher.get(
                "path"), launcher.get("subgroup") or ""), iid=launcher.get("id"))
            if launcher.get("subgroup"):
                current_dynamic_launchers_subgroups.add(
                    launcher.get("subgroup"))
        sorted_subgroups = sorted(
            list(current_dynamic_launchers_subgroups), key=str.lower)

        launcher_subgroup_form_combo['values'] = sorted_subgroups
    populate_launcher_tree()

    selected_launcher_id_for_edit = tk.StringVar(value=None)

    def clear_launcher_form():
        add_launcher_name_var.set("")
        add_launcher_path_var.set("")
        add_launcher_subgroup_var.set("")
        selected_launcher_id_for_edit.set("")
        add_launcher_name_entry.focus()
        if launcher_tree.selection():
            launcher_tree.selection_remove(launcher_tree.selection())

    def on_launcher_tree_select(event):
        selected_items = launcher_tree.selection()
        if selected_items:
            launcher_id = selected_items[0]
            selected_launcher = next(
                (l for l in gui_dynamic_launchers_state if l["id"] == launcher_id), None)
            if selected_launcher:
                add_launcher_name_var.set(selected_launcher.get("name", ""))
                add_launcher_path_var.set(selected_launcher.get("path", ""))
                add_launcher_subgroup_var.set(
                    selected_launcher.get("subgroup", ""))
                selected_launcher_id_for_edit.set(launcher_id)
        else:
            clear_launcher_form()
    launcher_tree.bind("<<TreeviewSelect>>", on_launcher_tree_select)

    def add_or_update_launcher_action():
        name = add_launcher_name_var.get().strip()
        path = add_launcher_path_var.get().strip()
        subgroup = add_launcher_subgroup_var.get().strip() or None
        if not name or not path:
            messagebox.showerror(
                "Error", "Launcher Name and Path are required.", parent=root)
            return
        edit_id = selected_launcher_id_for_edit.get()
        if edit_id:
            for i, launcher in enumerate(gui_dynamic_launchers_state):
                if launcher["id"] == edit_id:
                    gui_dynamic_launchers_state[i] = {
                        "id": edit_id, "name": name, "path": path, "subgroup": subgroup}
                    break
            logger_ui.info(f"Launcher '{name}' (ID: {edit_id}) updated.")
        else:
            new_id = uuid.uuid4().hex
            gui_dynamic_launchers_state.append(
                {"id": new_id, "name": name, "path": path, "subgroup": subgroup})
            logger_ui.info(f"Launcher '{name}' (ID: {new_id}) added.")
        populate_launcher_tree()
        clear_launcher_form()

    def delete_launcher_action():
        edit_id = selected_launcher_id_for_edit.get()
        if not edit_id:
            messagebox.showerror(
                "Error", "No launcher selected to delete.", parent=root)
            return
        if messagebox.askyesno("Confirm Delete", f"Delete launcher '{add_launcher_name_var.get()}'?", parent=root):
            gui_dynamic_launchers_state[:] = [
                l for l in gui_dynamic_launchers_state if l["id"] != edit_id]
            populate_launcher_tree()
            clear_launcher_form()
            logger_ui.info(f"Launcher ID {edit_id} removed.")
    launcher_form_buttons_frame = ttk.Frame(launcher_form_lf)
    launcher_form_buttons_frame.grid(row=3, column=0, columnspan=3, pady=5)
    ttk.Button(launcher_form_buttons_frame, text="Save/Add Launcher",
               command=add_or_update_launcher_action).pack(side=tk.LEFT, padx=5)
    ttk.Button(launcher_form_buttons_frame, text="Delete Selected",
               command=delete_launcher_action).pack(side=tk.LEFT, padx=5)
    ttk.Button(launcher_form_buttons_frame, text="Clear Form / Deselect",
               command=clear_launcher_form).pack(side=tk.LEFT, padx=5)

    user_management_lf = ttk.LabelFrame(
        tab_user_management, text="Manage Users", padding="10")
    user_management_lf.pack(fill="both", expand=True, padx=5, pady=5)
    user_management_lf.grid_columnconfigure(0, weight=1)
    user_management_lf.grid_rowconfigure(0, weight=1)
    user_tree_frame = ttk.Frame(user_management_lf)
    user_tree_frame.grid(row=0, column=0, columnspan=3,
                         sticky="nsew", pady=(0, 10))
    user_tree_frame.grid_columnconfigure(0, weight=1)
    user_tree_frame.grid_rowconfigure(0, weight=1)
    user_tree_cols = ("chat_id", "username", "role")
    user_tree = ttk.Treeview(
        user_tree_frame, columns=user_tree_cols, show="headings", height=8)
    user_tree.heading("chat_id", text="Chat ID")
    user_tree.heading("username", text="Username")
    user_tree.heading("role", text="Role")
    user_tree.column("chat_id", width=150, anchor=tk.W)
    user_tree.column("username", width=200, anchor=tk.W)
    user_tree.column("role", width=100, anchor=tk.W)
    user_tree_scrollbar_y = ttk.Scrollbar(
        user_tree_frame, orient="vertical", command=user_tree.yview)
    user_tree.configure(yscrollcommand=user_tree_scrollbar_y.set)
    user_tree.pack(side=tk.LEFT, fill="both", expand=True)
    user_tree_scrollbar_y.pack(side=tk.RIGHT, fill="y")

    def populate_user_tree():
        for item in user_tree.get_children():
            user_tree.delete(item)
        sorted_chat_ids = sorted(
            gui_user_data_state.keys(), key=lambda x: int(str(x).lstrip('-')))
        for chat_id_str_key in sorted_chat_ids:
            user_tree.insert("", tk.END, values=(chat_id_str_key, gui_user_data_state[chat_id_str_key].get(
                "username", "N/A"), gui_user_data_state[chat_id_str_key].get("role", "UNKNOWN")))
    populate_user_tree()
    user_controls_frame = ttk.Frame(user_management_lf)
    user_controls_frame.grid(
        row=1, column=0, columnspan=3, sticky="ew", pady=(5, 0))
    add_user_lf = ttk.LabelFrame(
        user_controls_frame, text="Add New User", padding="5")
    add_user_lf.pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 5))
    ttk.Label(add_user_lf, text="Chat ID:").grid(
        row=0, column=0, sticky=tk.W, padx=2, pady=2)
    add_chat_id_var = tk.StringVar()
    add_chat_id_entry = ttk.Entry(
        add_user_lf, textvariable=add_chat_id_var, width=15)
    add_chat_id_entry.grid(row=0, column=1, sticky=tk.EW, padx=2, pady=2)
    ttk.Label(add_user_lf, text="Role:").grid(
        row=1, column=0, sticky=tk.W, padx=2, pady=2)
    add_role_var = tk.StringVar()
    add_role_combo_user_tab = ttk.Combobox(add_user_lf, textvariable=add_role_var, values=[
                                           ROLE_ADMIN, ROLE_STANDARD_USER], state="readonly", width=13)
    add_role_combo_user_tab.grid(row=1, column=1, sticky=tk.EW, padx=2, pady=2)
    add_role_combo_user_tab.set(ROLE_STANDARD_USER)

    def add_user_action():
        chat_id_to_add = add_chat_id_var.get().strip()
        role_to_add = add_role_var.get()
        if not chat_id_to_add or not chat_id_to_add.lstrip('-').isdigit():
            messagebox.showerror(
                "Error", "Valid numerical Chat ID required.", parent=root)
            return
        if chat_id_to_add == primary_admin_chat_id_loaded:
            messagebox.showerror(
                "Error", "Primary Admin cannot be re-added.", parent=root)
            return
        if chat_id_to_add in gui_user_data_state:
            messagebox.showerror(
                "Error", f"User {chat_id_to_add} already exists.", parent=root)
            return
        if not role_to_add:
            messagebox.showerror("Error", "Select a role.", parent=root)
            return
        gui_user_data_state[chat_id_to_add] = {
            "username": f"User_{chat_id_to_add}", "role": role_to_add}
        populate_user_tree()
        add_chat_id_var.set("")
        add_role_combo_user_tab.set(ROLE_STANDARD_USER)
    ttk.Button(add_user_lf, text="Add User", command=add_user_action).grid(
        row=2, column=0, columnspan=2, pady=5)
    edit_user_lf = ttk.LabelFrame(
        user_controls_frame, text="Edit Selected User", padding="5")
    edit_user_lf.pack(side=tk.LEFT, fill="x", expand=True, padx=(5, 0))
    selected_user_chat_id_label_var = tk.StringVar(value="Selected: None")
    ttk.Label(edit_user_lf, textvariable=selected_user_chat_id_label_var).grid(
        row=0, column=0, columnspan=2, sticky=tk.W, padx=2, pady=2)
    ttk.Label(edit_user_lf, text="New Role:").grid(
        row=1, column=0, sticky=tk.W, padx=2, pady=2)
    edit_role_var = tk.StringVar()
    edit_role_combo_user_tab_edit = ttk.Combobox(edit_user_lf, textvariable=edit_role_var, values=[
                                                 ROLE_ADMIN, ROLE_STANDARD_USER], state="readonly", width=13)
    edit_role_combo_user_tab_edit.grid(
        row=1, column=1, sticky=tk.EW, padx=2, pady=2)

    def on_user_tree_select(event):
        selected_items = user_tree.selection()
        is_primary_selected = False
        if selected_items:
            values = user_tree.item(selected_items[0], "values")
            if values:
                sel_chat_id = values[0]
                selected_user_chat_id_label_var.set(f"Selected: {sel_chat_id}")
                edit_role_var.set(values[2])
                is_primary_selected = (
                    str(sel_chat_id) == primary_admin_chat_id_loaded)
        else:
            selected_user_chat_id_label_var.set("Selected: None")
            edit_role_var.set("")
        edit_role_combo_user_tab_edit.config(
            state=tk.DISABLED if is_primary_selected or not selected_items else tk.NORMAL)
        modify_user_button.config(
            state=tk.DISABLED if is_primary_selected or not selected_items else tk.NORMAL)
        remove_user_button.config(
            state=tk.DISABLED if is_primary_selected or not selected_items else tk.NORMAL)
    user_tree.bind("<<TreeviewSelect>>", on_user_tree_select)

    def modify_user_role_action():
        selected_items = user_tree.selection()
        if not selected_items:
            messagebox.showerror("Error", "No user selected.", parent=root)
            return
        chat_id_to_edit = user_tree.item(selected_items[0], "values")[0]
        new_role = edit_role_var.get()
        if str(chat_id_to_edit) == primary_admin_chat_id_loaded:
            messagebox.showerror(
                "Error", "Primary Admin's role cannot be changed here.", parent=root)
            return
        if not new_role:
            messagebox.showerror("Error", "Select a new role.", parent=root)
            return
        if chat_id_to_edit in gui_user_data_state:
            gui_user_data_state[chat_id_to_edit]["role"] = new_role
            populate_user_tree()
            logger_ui.info(
                f"User {chat_id_to_edit} role updated to {new_role} in GUI.")
        else:
            messagebox.showerror(
                "Error", "Selected user not found in data.", parent=root)
    modify_user_button = ttk.Button(
        edit_user_lf, text="Update Role", command=modify_user_role_action, state=tk.DISABLED)
    modify_user_button.grid(row=2, column=0, sticky=tk.EW, padx=2, pady=(5, 2))

    def remove_user_action():
        selected_items = user_tree.selection()
        if not selected_items:
            messagebox.showerror("Error", "No user selected.", parent=root)
            return
        chat_id_to_remove = user_tree.item(selected_items[0], "values")[0]
        if str(chat_id_to_remove) == primary_admin_chat_id_loaded:
            messagebox.showerror(
                "Error", "Primary Admin cannot be removed.", parent=root)
            return
        if messagebox.askyesno("Confirm Delete", f"Remove user {chat_id_to_remove}?", parent=root):
            if chat_id_to_remove in gui_user_data_state:
                del gui_user_data_state[chat_id_to_remove]
                populate_user_tree()
                on_user_tree_select(None)
                logger_ui.info(
                    f"User {chat_id_to_remove} removed from GUI list.")
            else:
                messagebox.showerror(
                    "Error", "Selected user not found for removal.", parent=root)
    remove_user_button = ttk.Button(
        edit_user_lf, text="Remove User", command=remove_user_action, state=tk.DISABLED)
    remove_user_button.grid(row=2, column=1, sticky=tk.EW, padx=2, pady=(5, 2))
    on_user_tree_select(None)

    result = {"saved": False, "log_level_changed": False,
              "user_data_changed": False, "affected_users_for_refresh": []}

    def save_all_configurations():
        nonlocal result, static_launchers_migrated_this_session
        config_data_for_py_file = {}
        has_errors_config_py = False

        for key_widget in ALL_USER_CONFIG_KEYS:
            if key_widget not in entries_vars:
                continue
            var = entries_vars[key_widget]
            definition = CONFIG_FIELD_DEFINITIONS.get(key_widget, {})
            if isinstance(var, tk.BooleanVar):
                config_data_for_py_file[key_widget] = var.get()
            else:
                value_str = var.get().strip()
                config_data_for_py_file[key_widget] = value_str
                is_required = definition.get("required", False)
                is_required_if_enabled_key = definition.get(
                    "required_if_enabled")
                field_is_active_for_validation = True
                if is_required_if_enabled_key and is_required_if_enabled_key in entries_vars and isinstance(entries_vars.get(is_required_if_enabled_key), tk.BooleanVar):
                    field_is_active_for_validation = entries_vars[is_required_if_enabled_key].get(
                    )
                if (is_required or (is_required_if_enabled_key and field_is_active_for_validation)) and not value_str:
                    messagebox.showerror(
                        "Error", f"'{definition.get('label', key_widget)}' cannot be empty.", parent=root)
                    has_errors_config_py = True
                    break
                if key_widget == "CHAT_ID" and value_str and not value_str.lstrip('-').isdigit():
                    messagebox.showerror(
                        "Error", f"'{definition.get('label', key_widget)}' must be a numerical ID.", parent=root)
                    has_errors_config_py = True
                    break
                numeric_fields_positive = [
                    "ADD_MEDIA_MAX_SEARCH_RESULTS", "ADD_MEDIA_ITEMS_PER_PAGE"]
                if key_widget == "ABDM_PORT":
                    abdm_enabled_for_port_check = entries_vars.get(
                        "ABDM_ENABLED", tk.BooleanVar(value=False)).get()
                    if value_str and not value_str.isdigit():
                        messagebox.showerror(
                            "Error", f"'{definition.get('label', key_widget)}' must be a number.", parent=root)
                        has_errors_config_py = True
                        break
                    if abdm_enabled_for_port_check and value_str and int(value_str) <= 0:
                        messagebox.showerror(
                            "Error", f"'{definition.get('label', key_widget)}' must be > 0 when ABDM is enabled.", parent=root)
                        has_errors_config_py = True
                        break
                elif key_widget in numeric_fields_positive:
                    if value_str and not value_str.isdigit():
                        messagebox.showerror(
                            "Error", f"'{definition.get('label', key_widget)}' must be a number.", parent=root)
                        has_errors_config_py = True
                        break
                    if value_str and int(value_str) <= 0:
                        messagebox.showerror(
                            "Error", f"'{definition.get('label', key_widget)}' must be > 0.", parent=root)
                        has_errors_config_py = True
                        break
            if has_errors_config_py:
                break
        if has_errors_config_py:
            return
        current_selected_log_level = config_data_for_py_file.get(
            "LOG_LEVEL", "INFO")
        if current_selected_log_level != initial_log_level_on_ui_open:
            result["log_level_changed"] = True

        try:
            config_dir = os.path.dirname(config_file_to_write_path)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
            with open(config_file_to_write_path, "w", encoding="utf-8") as f:
                f.write(
                    f"# config.py - Automatically generated by Media Bot UI\n# Last saved: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("# --- Core Settings ---\n")
                f.write(
                    f'TELEGRAM_BOT_TOKEN = "{config_data_for_py_file.get("TELEGRAM_BOT_TOKEN", "")}"\n')
                f.write(
                    f'CHAT_ID = "{config_data_for_py_file.get("CHAT_ID", "")}"\n\n')
                f.write("# --- General Settings ---\n")
                f.write(
                    f'LOG_LEVEL = "{config_data_for_py_file.get("LOG_LEVEL", "INFO")}"\n')
                f.write(
                    f'{CONFIG_KEYS_PC_CONTROL[0]} = {config_data_for_py_file.get(CONFIG_KEYS_PC_CONTROL[0], False)}\n')
                amsr_val = config_data_for_py_file.get(
                    "ADD_MEDIA_MAX_SEARCH_RESULTS", "30")
                f.write(
                    f'ADD_MEDIA_MAX_SEARCH_RESULTS = {int(amsr_val) if amsr_val.isdigit() else 30}\n')
                amip_val = config_data_for_py_file.get(
                    "ADD_MEDIA_ITEMS_PER_PAGE", "5")
                f.write(
                    f'ADD_MEDIA_ITEMS_PER_PAGE = {int(amip_val) if amip_val.isdigit() else 5}\n\n')

                f.write("# --- API Service Configurations ---\n")
                api_services_keys = {"PLEX": CONFIG_KEYS_PLEX, "RADARR": CONFIG_KEYS_RADARR,
                                     "SONARR": CONFIG_KEYS_SONARR, "ABDM": CONFIG_KEYS_ABDM}
                for service_prefix, service_keys_list in api_services_keys.items():

                    f.write(
                        f'{service_keys_list[0]} = {config_data_for_py_file.get(service_keys_list[0], False)}\n')
                    f.write(

                        f'{service_keys_list[1]} = "{config_data_for_py_file.get(service_keys_list[1], "")}"\n')
                    if len(service_keys_list) > 2:
                        if service_keys_list[2] == "ABDM_PORT":
                            port_val_str = config_data_for_py_file.get(
                                service_keys_list[2], CONFIG_FIELD_DEFINITIONS.get("ABDM_PORT", {}).get("default", "15151"))
                            f.write(
                                f'{service_keys_list[2]} = {int(port_val_str) if port_val_str.isdigit() else 15151}\n')
                        else:
                            f.write(
                                f'{service_keys_list[2]} = "{config_data_for_py_file.get(service_keys_list[2], "")}"\n')
                    f.write("\n")
                f.write(
                    "# End of automatically generated config.py settings.\n")
            logger_ui.info(
                f"Bot configuration (config.py) saved to {config_file_to_write_path}")
        except Exception as e:
            messagebox.showerror(
                "Error", f"Failed to save bot configuration to '{config_file_to_write_path}':\n{e}", parent=root)
            return

        affected_user_ids = set()
        new_primary_admin_id_from_config_py = config_data_for_py_file.get(
            "CHAT_ID", "")
        all_ids_ever = set(initial_user_data_on_gui_open.keys()) | set(
            gui_user_data_state.keys())
        for user_id_str_key in all_ids_ever:
            initial_user = initial_user_data_on_gui_open.get(user_id_str_key)
            current_gui_user = gui_user_data_state.get(user_id_str_key)
            if (initial_user and not current_gui_user) or \
               (not initial_user and current_gui_user) or \
               (initial_user and current_gui_user and initial_user.get("role") != current_gui_user.get("role")):
                affected_user_ids.add(user_id_str_key)
        result["affected_users_for_refresh"] = list(affected_user_ids)
        if new_primary_admin_id_from_config_py and new_primary_admin_id_from_config_py.lstrip('-').isdigit():
            current_pa_info = gui_user_data_state.get(
                new_primary_admin_id_from_config_py)
            pa_role_needs_update = not (
                current_pa_info and current_pa_info.get("role") == ROLE_ADMIN)
            if pa_role_needs_update:
                gui_user_data_state[new_primary_admin_id_from_config_py] = {"username": current_pa_info.get(
                    "username") if current_pa_info else f"PrimaryAdmin_{new_primary_admin_id_from_config_py}", "role": ROLE_ADMIN}
                if new_primary_admin_id_from_config_py not in affected_user_ids:
                    result["affected_users_for_refresh"].append(
                        new_primary_admin_id_from_config_py)

        full_bot_state_to_save = other_bot_state_parts_on_gui_open.copy()
        full_bot_state_to_save["users"] = gui_user_data_state
        full_bot_state_to_save["dynamic_launchers"] = gui_dynamic_launchers_state
        if "bot_info" not in full_bot_state_to_save or not isinstance(full_bot_state_to_save["bot_info"], dict):
            full_bot_state_to_save["bot_info"] = DEFAULT_BOT_STATE["bot_info"].copy(
            )
        if static_launchers_migrated_this_session:
            full_bot_state_to_save["bot_info"]["static_launchers_migrated"] = True
            logger_ui.info(
                "Static launchers migration flag set to True in bot_state.")

        if save_json_data(bot_state_path, full_bot_state_to_save):
            logger_ui.info(
                f"User data and dynamic launchers (bot_state.json) saved to {bot_state_path}")
            user_data_content_changed = (
                initial_user_data_on_gui_open != gui_user_data_state)
            launcher_data_content_changed = (
                initial_dynamic_launchers_on_gui_open != gui_dynamic_launchers_state)
            result["user_data_changed"] = user_data_content_changed or launcher_data_content_changed or static_launchers_migrated_this_session
        else:
            messagebox.showerror(
                "Error", f"Failed to save user data/launchers to '{bot_state_path}'. Bot config was saved, but other data was not.", parent=root)

        success_message = "Configuration saved!"
        if result["log_level_changed"] or result["user_data_changed"]:
            success_message += "\nSome changes may require a bot restart or user re-interaction to take full effect."

        messagebox.showinfo("Success", success_message, parent=root)
        result["saved"] = True
        root.destroy()

    button_frame = ttk.Frame(scrollable_frame_for_notebook)
    button_frame.pack(pady=15, fill='x')
    center_button_subframe = ttk.Frame(button_frame)
    center_button_subframe.pack()
    save_button = ttk.Button(
        center_button_subframe, text="Save All Configuration", command=save_all_configurations)
    save_button.pack(side=tk.LEFT, padx=5)
    cancel_button = ttk.Button(
        center_button_subframe, text="Cancel", command=root.destroy)
    cancel_button.pack(side=tk.LEFT, padx=5)
    root.update_idletasks()
    initial_width = 950
    initial_height = 850
    root.geometry(f'{initial_width}x{initial_height}')
    root.minsize(900, 700)
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
    import json
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(
            level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    mock_data_dir = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..', '..', 'data_test_ui_phase_a_v2'))
    if not os.path.exists(mock_data_dir):
        os.makedirs(mock_data_dir)
    mock_config_path = os.path.join(
        mock_data_dir, "test_config_generated_phase_a_v2.py")
    mock_bot_state_path_val = os.path.join(
        mock_data_dir, "bot_state_phase_a_v2.json")
    mock_initial_config_values_phase_a = {
        "TELEGRAM_BOT_TOKEN": "test_token_phase_a_v2", "CHAT_ID": "123456", "LOG_LEVEL": "DEBUG",
        "PC_CONTROL_ENABLED": True, "ADD_MEDIA_MAX_SEARCH_RESULTS": "40", "ADD_MEDIA_ITEMS_PER_PAGE": "8",
        "PLEX_ENABLED": True, "PLEX_URL": "http://plex.example.com", "PLEX_TOKEN": "plex_token_example",
        "RADARR_ENABLED": True, "RADARR_API_URL": "http://radarr.example.com", "RADARR_API_KEY": "radarr_key_example",
        "SONARR_ENABLED": False,
        "ABDM_ENABLED": True, "ABDM_PORT": "15151",

        "PLEX_LAUNCHER_ENABLED": True, "PLEX_LAUNCHER_NAME": "Old Plex Static", "PLEX_LAUNCHER_PATH": "C:/Plex/plex.exe",
        "SCRIPT_1_ENABLED": True, "SCRIPT_1_NAME": "My Backup Script", "SCRIPT_1_PATH": "/opt/backup.sh",
    }
    initial_test_bot_state = DEFAULT_BOT_STATE.copy()
    initial_test_bot_state["users"] = {"123456": {
        "username": "PrimaryAdmin_123456", "role": ROLE_ADMIN}}
    initial_test_bot_state["dynamic_launchers"] = [
        {"id": "preexisting1", "name": "Pre-existing Dyn Launcher", "path": "/usr/local/bin/tool", "subgroup": "Tools"}]
    initial_test_bot_state["bot_info"]["static_launchers_migrated"] = False
    with open(mock_bot_state_path_val, "w") as f_state:
        json.dump(initial_test_bot_state, f_state, indent=4)
    import src.app.app_file_utils as app_file_utils_module
    original_get_bot_state_file_path_real = app_file_utils_module.get_bot_state_file_path
    def mock_get_bot_state_file_path_for_test(): return mock_bot_state_path_val
    app_file_utils_module.get_bot_state_file_path = mock_get_bot_state_file_path_for_test
    try:
        ui_result = run_config_ui(
            mock_config_path, mock_initial_config_values_phase_a)
        print(f"UI Result (Phase A v2 test): {ui_result}")
        if ui_result["saved"]:
            print(f"Bot config (mock) saved to {mock_config_path}")
            if os.path.exists(mock_config_path):
                with open(mock_config_path, "r") as f_conf_check:
                    print(
                        f"\n--- Generated config.py ---\n{f_conf_check.read()}")
            if os.path.exists(mock_bot_state_path_val):
                with open(mock_bot_state_path_val, "r") as f_state_check:
                    print(
                        f"\n--- Generated bot_state.json ---\n{f_state_check.read()}")
        if ui_result.get("affected_users_for_refresh"):
            print(
                f"Affected users for refresh: {ui_result['affected_users_for_refresh']}")
    finally:
        app_file_utils_module.get_bot_state_file_path = original_get_bot_state_file_path_real
