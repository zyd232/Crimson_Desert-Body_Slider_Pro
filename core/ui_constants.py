# -*- coding: utf-8 -*-
"""
Centralized UI constants and styles for Body Slider Pro.
All color tokens, component styles, and global stylesheet live here.
"""

# ==========================================
# 1. Default Language
# ==========================================
DEFAULT_LANG = "en"

# ==========================================
# 2. Font Family
# ==========================================
FONT_FAMILY = "Microsoft YaHei, Segoe UI, sans-serif"

# ==========================================
# 3. Color Tokens
# ==========================================

# 3D mesh preview colors
#
# Rendering rules (controlled by MeshViewer + MainWindow):
#
# - No Outfits panel:
#   - wireframe ON:  all meshes -> orange (accent)
#   - wireframe OFF: character base -> white (clay)
#
# - With Outfits panel:
#   - wireframe ON:
#       - character base -> white
#       - outfit mesh (activated item) -> orange (accent)
#   - wireframe OFF:
#       - character base -> white (clay)
#       - outfit mesh (activated item) -> orange (accent, lit)
#
MESH_COLOR_BEIGE_RGB = (0.96, 0.87, 0.70)
MESH_COLOR_WHITE_RGB = (1.0, 1.0, 1.0)
MESH_COLOR_ACCENT_RGB = (224.0 / 255.0, 122.0 / 255.0, 54.0 / 255.0)  # orange

# Backgrounds
COLOR_BG_MAIN = "#211814"
COLOR_BG_PANEL = "#2a1d18"
COLOR_BG_SURFACE = "#35241c"
COLOR_BG_HOVER = "#443025"
COLOR_BG_HOVER_SOFT = "#4e362b"
COLOR_BG_ELEVATED = "#3e2a20"
COLOR_BG_INPUT = "#1b130f"
COLOR_BG_PRESS = "#2b1d17"

# Accents
COLOR_ACCENT = "#c56d43"
COLOR_ACCENT_LIGHT = "#d98a4f"
COLOR_ACCENT_HOT = "#f07b61"
COLOR_ACCENT_FOCUS = "#e07a36"

# Borders
COLOR_BORDER = "#513929"
COLOR_BORDER_ACCENT = "#6b4932"

# Text
COLOR_TEXT = "#d9c0aa"
COLOR_TEXT_BRIGHT = "#f4ddc4"
COLOR_TEXT_DIM = "#a98c77"
COLOR_TEXT_MUTED = "#7a6a5a"
COLOR_TEXT_SEPIA = "#6b5b50"
COLOR_TEXT_WHITE = "#ffffff"

# Semantic
COLOR_ERROR = "#ff6b6b"
COLOR_CLOSE_HOT = "#c53e2c"
COLOR_CLOSE_HOVER = "#e04b3e"

# ==========================================
# 4. Translation Dictionary T
# ==========================================
T = {
    "lang_name": "English",
    "app_title": "Body Slider Pro",
    "btn_ok": "OK",
    "btn_cancel": "Cancel",
    "btn_browse": "Browse...",
    "btn_text_reset": "Reset",
    "btn_text_edit": "Edit",
    "btn_text_del": "Del",
    "btn_reset_all": "Reset All",
    "btn_reset_all_tip": "Reset all sliders to default (0)",
    "btn_save_pack": "Save Pack",
    "btn_load_pack": "Load Pack",
    "btn_edit_char": "Edit",
    "no_custom": "No custom sliders.",
    "slider_missing_file": "Missing mesh file.",
    "tooltip_slider_missing": "Click to reselect the target mesh file.",
    "char_label_prefix": "Character",
    "char_missing_pac": "Missing PAC file.",
    "tooltip_pac_missing": "Click to select a new PAC file.",
    "label_language": "Language:",
    "label_name": "Name:",
    "label_id": "ID:",
    "label_slider_name": "Name:",
    "label_slider_mesh": "Target Mesh:",
    "label_slider_range": "Range:",
    "label_pac_file": "Original PAC:",
    "label_mod_path": "Mod Path:",
    "placeholder_slider_id": "Letters, numbers, underscore only (e.g. breast_size)",
    "placeholder_slider_mesh": "Select a target mesh file (.obj or .pac)",
    "placeholder_slider_range": "Format: min,max (e.g. -50,150)",
    "placeholder_char_id": "Letters, numbers, underscore only (e.g. char_01)",
    "placeholder_pac_path": "Enter PAC file path or click Browse...",
    "placeholder_mod_path": "Example: character\\model\\1_pc\\2_phw\\nude",
    "char_id_label": "Character ID (English letters, numbers, underscore only):",
    "char_add_title": "Add Character",
    "char_edit_title": "Edit Character",
    "char_id_invalid": "ID can only contain letters, numbers, and underscores.",
    "char_id_duplicate": "This ID is already in use. Please choose another.",
    "pac_required": "PAC file path is required.",
    "pac_not_found": "The specified PAC file does not exist. Please check the path.",
    "pac_is_directory": "The specified path is a directory, not a PAC file. Please select a PAC file.",
    "mod_path_required": "Mod path is required and cannot be empty.",
    "dlg_add_slider_title": "Add Custom Slider",
    "dlg_edit_slider_title": "Edit Slider",
    "dlg_slider_name_placeholder": "Enter slider name...",
    "dlg_slider_name_required": "Slider name is required.",
    "dlg_slider_id_required": "Slider ID is required.",
    "dlg_slider_id_invalid": "ID can only contain letters, numbers, and underscores.",
    "dlg_slider_mesh_required": "Target mesh file is required.",
    "dlg_slider_mesh_not_found": "The specified file does not exist.",
    "dlg_slider_range_invalid": "Min must be less than max.",
    "dlg_slider_range_format": "Invalid range format. Use: min,max (e.g. -50,150)",
    "dlg_sort_chars_title": "Sort Characters",
    "dlg_sort_chars_hint": "Drag to reorder characters",
    "file_dialog_pac_title": "Select Original PAC",
    "msg_error": "Error",
    "pack_load_title": "Load Character Pack",
    "pack_load_select_title": "Select Characters to Load",
    "pack_load_select_msg": "Select one or more characters from the pack to import.",
    "pack_load_existing": "will overwrite",
    "pack_load_ok": "Load",
    "pack_save_title": "Save/Share Character Pack",
    "pack_multi_select_title": "Select Characters to Pack",
    "pack_multi_select_msg": "Select one or more characters to include in the pack.",
    "pack_select_all": "Select All",
    "pack_select_none": "Select None",
    "pack_ok": "OK",
    "pack_cancel": "Cancel",
    "pack_conflict_title": "Resolve Conflicts",
    "pack_conflict_msg": "Some characters share the same in-game identity (same PAC file and Mod Path). For each group, select exactly one character to include in the MOD.",
    "pack_conflict_group": "Conflict Group",
    "tooltip_edit_char": "Edit settings for character: {name}",

    # Outfits
    "tab_outfits": "Outfits",
    "btn_unload_all_outfits": "Unload All Outfits",
    "unload_all_outfits_confirm": "Are you sure you want to unload all Outfits for this character?\nThis will delete all contents under:\noriginal_outfit/{char_id}\nexported_outfit/{char_id}",
    "msg_outfits_unloaded": "All Outfits for this character have been unloaded.",
    "msg_outfits_delete_error": "Failed to delete some outfit files.",

    # Outfits toggle
    "btn_toggle_outfits_show": "Show Outfits Panel",
    "btn_toggle_outfits_hide": "Hide Outfits Panel",

    # Outfit Sliders panels
    "group_outfit_default": "Outfit Default Sliders",
    "group_outfit_custom": "Outfit Custom Sliders",
    "no_outfit_sliders": "No outfit sliders available.",

    # File tree toolbar tooltips
    "tooltip_tree_expand_all": "Expand All",
    "tooltip_tree_collapse_all": "Collapse All",
    "tooltip_tree_refresh": "Refresh",
    "label_no_outfit_data": "No outfit data",
}

# ==========================================
# 5. Component Styles (reusable fragments)
# ==========================================

# -- Dialog base --

DIALOG_CONTENT_BG = f"QWidget {{ background-color: {COLOR_BG_SURFACE}; }}"

DIALOG_INPUT_STYLE = f"""
    QLineEdit {{
        background: {COLOR_BG_INPUT};
        color: {COLOR_TEXT};
        border: 1px solid {COLOR_BORDER_ACCENT};
        border-radius: 4px;
        padding: 0 4px;
    }}
"""

DIALOG_INPUT_READONLY_STYLE = f"""
    QLineEdit {{
        background: rgba(27, 19, 15, 0.45);
        color: {COLOR_TEXT_MUTED};
        border: 1px solid rgba(107, 73, 50, 0.5);
        border-radius: 4px;
        padding: 0 4px;
    }}
"""

DIALOG_TEXT_LABEL_STYLE = f"QLabel {{ color: {COLOR_TEXT}; font-size: 13px; padding: 0; margin: 0; }}"

# -- Title bar (main window) --

TITLE_BAR_BG = f"QWidget {{ background-color: {COLOR_BG_MAIN}; }}"

TITLE_LABEL_STYLE = f"QLabel {{ color: {COLOR_TEXT_BRIGHT}; font-size: 14px; font-weight: bold; padding: 0px; }}"

TITLE_SEP_STYLE = f"QLabel {{ color: {COLOR_TEXT_SEPIA}; font-size: 13px; padding: 0px; }}"

TITLE_SUB_STYLE = f"QLabel {{ color: {COLOR_TEXT_SEPIA}; font-size: 13px; padding: 0px; }}"

LANG_LABEL_STYLE = f"QLabel {{ color: {COLOR_TEXT_DIM}; font-size: 12px; padding: 0px 2px; }}"

WINDOW_CONTROL_STYLE = f"""
    QPushButton {{
        background-color: {COLOR_BG_SURFACE};
        color: {COLOR_TEXT_BRIGHT};
        border: 1px solid {COLOR_BORDER};
        border-radius: 4px;
        font-size: 14px;
        font-weight: bold;
        padding: 0px;
    }}
    QPushButton:hover {{
        background-color: {COLOR_BG_HOVER};
        border-color: {COLOR_ACCENT};
    }}
"""

WINDOW_CONTROL_SMALL_STYLE = WINDOW_CONTROL_STYLE.replace("font-size: 14px;", "font-size: 12px;")

WINDOW_CLOSE_STYLE = f"""
    QPushButton {{
        background-color: {COLOR_BG_SURFACE};
        color: {COLOR_TEXT_BRIGHT};
        border: 1px solid {COLOR_BORDER};
        border-radius: 4px;
        font-size: 14px;
        font-weight: bold;
        padding: 0px;
    }}
    QPushButton:hover {{
        background-color: {COLOR_CLOSE_HOT};
        border-color: {COLOR_ACCENT_HOT};
        color: {COLOR_TEXT_WHITE};
    }}
"""

# -- CustomTitleBar (dialogs) --

TITLE_BAR_TITLE_LABEL_STYLE = f"""
    QLabel {{
        color: {COLOR_TEXT_WHITE};
        font-size: 13px;
        font-weight: bold;
        padding: 0; margin: 0;
        background: transparent;
    }}
"""

TITLE_BAR_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {COLOR_BG_ELEVATED};
        color: {COLOR_TEXT_BRIGHT};
        border: 1px solid {COLOR_BORDER};
        border-radius: 4px;
        font-size: 14px;
        font-weight: bold;
        padding: 0px;
    }}
    QPushButton:hover {{
        background-color: {COLOR_BG_HOVER_SOFT};
        border-color: {COLOR_ACCENT};
    }}
"""

TITLE_BAR_BUTTON_SMALL_STYLE = TITLE_BAR_BUTTON_STYLE.replace("font-size: 14px;", "font-size: 12px;")

TITLE_BAR_CLOSE_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {COLOR_BG_ELEVATED};
        color: {COLOR_TEXT_BRIGHT};
        border: 1px solid {COLOR_BORDER};
        border-radius: 4px;
        font-size: 14px;
        font-weight: bold;
        padding: 0px;
    }}
    QPushButton:hover {{
        background-color: {COLOR_CLOSE_HOT};
        color: {COLOR_TEXT_WHITE};
        border-color: {COLOR_ACCENT_HOT};
    }}
"""

TITLE_BAR_WIDGET_STYLE = f"QWidget#customTitleBar {{ background-color: {COLOR_ACCENT}; }}"


# -- DarkMessageBox internals --

DARK_MESSAGEBOX_TEXT_LABEL_STYLE = f"""
    QLabel {{ color: {COLOR_TEXT}; font-size: 13px; padding: 0; margin: 0; }}
"""

DARK_MESSAGEBOX_ICON_LABEL_STYLE = f"""
    QLabel {{ color: {COLOR_TEXT_BRIGHT}; font-size: 16px; padding-top: 2px; }}
"""

DARK_MESSAGEBOX_ICON_LABEL_WARNING_STYLE = f"""
    QLabel {{ color: {COLOR_ACCENT_HOT}; font-size: 16px; padding-top: 2px; }}
"""

DARK_MESSAGEBOX_CONTENT_WIDGET_STYLE = f"QWidget {{ background-color: {COLOR_BG_SURFACE}; }}"


# -- Tab buttons (character bar) --

TAB_INACTIVE_CONTAINER_STYLE = f"""
    QWidget {{
        background-color: {COLOR_BG_SURFACE};
        color: {COLOR_TEXT_DIM};
        border: 1px solid {COLOR_BORDER};
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }}
"""

TAB_INACTIVE_HOVER_CONTAINER_STYLE = f"""
    QWidget {{
        background-color: {COLOR_BG_HOVER};
        color: {COLOR_TEXT_BRIGHT};
        border: 1px solid {COLOR_ACCENT};
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }}
"""

TAB_ACTIVE_CONTAINER_STYLE = f"""
    QWidget {{
        background-color: {COLOR_BG_PANEL};
        color: {COLOR_TEXT_BRIGHT};
        border: 1px solid {COLOR_BORDER_ACCENT};
        border-bottom: 2px solid {COLOR_BG_PANEL};
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }}
"""

TAB_INACTIVE_LABEL_STYLE = f"""
    QLabel {{
        font-size: 14px;
        background: transparent;
        border: none;
        padding: 4px 8px;
        margin: 0px;
        color: {COLOR_TEXT_DIM};
    }}
"""

TAB_INACTIVE_HOVER_LABEL_STYLE = f"""
    QLabel {{
        font-size: 14px;
        background: transparent;
        border: none;
        padding: 4px 8px;
        margin: 0px;
        color: {COLOR_TEXT_BRIGHT};
    }}
"""

TAB_ACTIVE_LABEL_STYLE = f"""
    QLabel {{
        font-size: 14px;
        font-weight: bold;
        background: transparent;
        border: none;
        padding: 4px 8px;
        margin: 0px;
        color: {COLOR_TEXT_BRIGHT};
    }}
"""

# -- Delete button in tab --

TAB_DELETE_BUTTON_STYLE = f"""
    QPushButton {{
        background: transparent;
        border: none;
        color: {COLOR_TEXT_DIM};
        font-size: 14px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        color: {COLOR_ACCENT_HOT};
    }}
"""

# -- Bottom bar / viewer controls --

VIEWER_BOTTOM_BAR_STYLE = "QWidget { background: transparent; border: none; }"

# -- Reset Camera / Wireframe buttons --

BTN_RESET_CAM_STYLE = f"""
    QPushButton#btn_reset_cam {{
        color: {COLOR_TEXT_BRIGHT};
        border-radius: 4px;
        border: 1px solid rgba(107,73,50,180);
        padding: 0 8px;
        height: 36px;
        font-size: 12px;
        background-color: rgba(35,25,18,220);
    }}
    QPushButton#btn_reset_cam:hover {{
        background-color: rgba(68,48,37,240);
    }}
"""

BTN_WIREFRAME_STYLE = f"""
    QPushButton#btn_wireframe {{
        color: {COLOR_TEXT_BRIGHT};
        border-radius: 4px;
        border: 1px solid rgba(107,73,50,180);
        padding: 0 8px 0 22px;
        height: 36px;
        font-size: 12px;
        background-color: rgba(35,25,18,220);
    }}
    QPushButton#btn_wireframe:hover {{
        background-color: rgba(68,48,37,240);
    }}
"""

# -- Loading overlay --

LOADING_OVERLAY_ROOT_STYLE = (
    "QWidget#LoadingOverlayRoot { "
    "background-color: rgba(33,24,20,255); "
    "border: none; }"
)

LOADING_LABEL_STYLE = f"""
    QLabel {{
        color: {COLOR_TEXT_BRIGHT};
        font-size: 16px;
        font-weight: bold;
        background-color: transparent;
    }}
"""

# -- SpinBox --

SPINBOX_STYLE = f"""
    QDoubleSpinBox {{
        border: 1px solid {COLOR_BORDER_ACCENT};
        border-radius: 4px;
        background: {COLOR_BG_INPUT};
        color: {COLOR_TEXT};
        padding: 0 6px;
        height: 28px;
    }}
    QDoubleSpinBox::up-button,
    QDoubleSpinBox::down-button {{
        width: 0;
        subcontrol-position: top right;
    }}
"""

# -- Warning label --

WARNING_LABEL_STYLE = f"""
    color: {COLOR_ACCENT_HOT};
    font-size: 12px;
    font-weight: bold;
    background: rgba(240,123,97,0.08);
    border-radius: 4px;
    padding: 4px 6px;
    border: 1px solid {COLOR_BORDER_ACCENT};
"""

WARNING_LABEL_SMALL_STYLE = f"""
    color: {COLOR_ACCENT_HOT};
    font-size: 12px;
    font-weight: bold;
    background: rgba(240,123,97,0.08);
    border-radius: 3px;
    padding: 2px 4px;
    border: 1px solid {COLOR_BORDER_ACCENT};
"""

# -- Character info row --

CHAR_LABEL_STYLE = f"font-weight: bold; font-size: 14px; color: {COLOR_TEXT_BRIGHT};"

# -- Unified ScrollBar style fragment (vertical + horizontal) --
# Used across all scroll areas in the application for consistent appearance.
# - Background: COLOR_BG_INPUT (dark)
# - Handle default: COLOR_BORDER_ACCENT (subtle sepia)
# - Handle hover: COLOR_ACCENT (orange accent)
# - Size: 8px width/height, 4px border-radius
# - No arrow buttons (add-line/sub-line hidden)

SCROLL_BAR_STYLE = f"""
    QScrollBar:vertical {{
        background-color: {COLOR_BG_INPUT};
        width: 8px;
        border: none;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {COLOR_BORDER_ACCENT};
        border-radius: 4px;
        min-height: 20px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {COLOR_ACCENT};
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        background-color: {COLOR_BG_INPUT};
        height: 8px;
        border: none;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal {{
        background-color: {COLOR_BORDER_ACCENT};
        border-radius: 4px;
        min-width: 20px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background-color: {COLOR_ACCENT};
    }}
    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
"""

# -- Scroll area with transparent background (Outfits panel, Tab scroll) --

TRANSPARENT_SCROLL_STYLE = (
    f"QScrollArea {{ background: transparent; border: none; }}"
    f"QScrollArea QWidget {{ background: transparent; }}"
    + SCROLL_BAR_STYLE
)

# -- Scroll area with bordered background (Sort dialog, etc.) --

BORDERED_SCROLL_STYLE = (
    f"QScrollArea {{ background: {COLOR_BG_INPUT}; border: 1px solid {COLOR_BORDER}; border-radius: 4px; }}"
    + SCROLL_BAR_STYLE
)

# -- Legacy aliases for backward compatibility --

# Tab scroll area
TAB_SCROLL_STYLE = TRANSPARENT_SCROLL_STYLE

# Outfits panel width constants
OUTFIT_PANEL_MIN_WIDTH = 180
OUTFIT_PANEL_MAX_WIDTH = 400

# Outfit Sliders panel width constants
OUTFIT_SLIDERS_PANEL_MIN_WIDTH = 200
OUTFIT_SLIDERS_PANEL_MAX_WIDTH = 420

# Outfits panel scroll style
OUTFIT_SCROLL_STYLE = TRANSPARENT_SCROLL_STYLE

# -- File tree toolbar button styles --

BTN_TREE_CONTROL_STYLE = f"""
    QPushButton#btn_tree_control {{
        color: {COLOR_TEXT};
        border-radius: 3px;
        border: 1px solid {COLOR_BORDER_ACCENT};
        padding: 0;
        background-color: {COLOR_BG_SURFACE};
        font-size: 10px;
        min-width: 18px;
        max-width: 18px;
        min-height: 18px;
        max-height: 18px;
    }}
    QPushButton#btn_tree_control:hover {{
        background-color: {COLOR_BG_HOVER};
        border-color: {COLOR_ACCENT};
    }}
    QPushButton#btn_tree_control:pressed {{
        background-color: {COLOR_BG_PRESS};
    }}
"""

BTN_REFRESH_STYLE = f"""
    QPushButton#btn_refresh {{
        color: {COLOR_TEXT};
        border-radius: 3px;
        border: 1px solid {COLOR_BORDER_ACCENT};
        padding: 0;
        background-color: {COLOR_BG_SURFACE};
        font-size: 10px;
        min-width: 18px;
        max-width: 18px;
        min-height: 18px;
        max-height: 18px;
    }}
    QPushButton#btn_refresh:hover {{
        background-color: {COLOR_BG_HOVER};
        border-color: {COLOR_ACCENT};
    }}
    QPushButton#btn_refresh:pressed {{
        background-color: {COLOR_BG_PRESS};
    }}
"""

BTN_SELECT_ALL_STYLE = f"""
    QPushButton#btn_select_all {{
        color: {COLOR_TEXT};
        border-radius: 3px;
        border: 1px solid {COLOR_BORDER_ACCENT};
        padding: 0 6px;
        background-color: {COLOR_BG_SURFACE};
        font-size: 10px;
        min-height: 18px;
        max-height: 18px;
    }}
    QPushButton#btn_select_all:hover {{
        background-color: {COLOR_BG_HOVER};
        border-color: {COLOR_ACCENT};
    }}
    QPushButton#btn_select_all:pressed {{
        background-color: {COLOR_BG_PRESS};
    }}
"""

BTN_DESELECT_ALL_STYLE = f"""
    QPushButton#btn_deselect_all {{
        color: {COLOR_TEXT};
        border-radius: 3px;
        border: 1px solid {COLOR_BORDER_ACCENT};
        padding: 0 6px;
        background-color: {COLOR_BG_SURFACE};
        font-size: 10px;
        min-height: 18px;
        max-height: 18px;
    }}
    QPushButton#btn_deselect_all:hover {{
        background-color: {COLOR_BG_HOVER};
        border-color: {COLOR_ACCENT};
    }}
    QPushButton#btn_deselect_all:pressed {{
        background-color: {COLOR_BG_PRESS};
    }}
"""

# -- File tree refresh overlay (semi-transparent, covers only the tree) --
TREE_REFRESH_OVERLAY_STYLE = (
    "QWidget#TreeRefreshOverlay {"
    "background-color: rgba(20,14,10,180);"
    "border: 1px solid rgba(107,73,50,180);"
    "border-radius: 4px;"
    "}"
)

TREE_REFRESH_LABEL_STYLE = f"""
    QLabel#TreeRefreshLabel {{
        color: {COLOR_TEXT_BRIGHT};
        font-size: 14px;
        font-weight: bold;
        background: transparent;
    }}
"""

# -- Sliders panel minimum width (prevents splitter from collapsing) --
SLIDERS_PANEL_MIN_WIDTH = 200

# -- Bottom export buttons row layout --
BTN_EXPORT_ROW_MARGINS = (0, 4, 0, 8)  # (left, top, right, bottom) - bottom=8 to align with viewer bottom bar
BTN_EXPORT_ROW_SPACING = 6

# -- Two-row export buttons layout (Row1: Add Custom + Export OBJ, Row2: Export MOD) --
BTN_EXPORT_TWO_ROW_MARGINS = (0, 4, 0, 8)  # (left, top, right, bottom)
BTN_EXPORT_TWO_ROW_SPACING = 6              # spacing within each row and between rows

# -- Outfits panel bottom margin (matches button row bottom margin so Outfits bottom aligns with buttons bottom) --
OUTFIT_PANEL_BOTTOM_MARGIN = 8

# -- Outfit Sliders panel button row layout --
OUTFIT_SLIDERS_BTN_ROW_MARGINS = (0, 4, 0, 8)  # (left, top, right, bottom)
OUTFIT_SLIDERS_BTN_ROW_SPACING = 6

# -- Sort dialog scroll area (uses bordered scroll style defined above) --
SORT_SCROLL_STYLE = BORDERED_SCROLL_STYLE

# -- Sort dialog content --

SORT_CONTENT_BG = "QWidget { background: transparent; }"

# ==========================================
# Export Progress Dialog Styles
# ==========================================

EXPORT_PROGRESS_DIALOG_MIN_WIDTH = 480
EXPORT_PROGRESS_DIALOG_MIN_HEIGHT = 180

EXPORT_PROGRESS_TITLE_BAR_STYLE = f"QWidget#exportProgressTitleBar {{ background-color: {COLOR_ACCENT}; }}"

EXPORT_PROGRESS_TITLE_LABEL_STYLE = f"""
    QLabel {{
        color: {COLOR_TEXT_WHITE};
        font-size: 13px;
        font-weight: bold;
        padding: 0; margin: 0;
        background: transparent;
    }}
"""

EXPORT_PROGRESS_CLOSE_BUTTON_STYLE = f"""
    QPushButton {{
        background: transparent;
        border: none;
        color: {COLOR_TEXT_WHITE};
        font-size: 12px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: {COLOR_CLOSE_HOVER};
        border-radius: 3px;
    }}
"""

EXPORT_PROGRESS_STATUS_LABEL_STYLE = f"""
    QLabel {{
        color: {COLOR_TEXT};
        font-size: 12px;
        padding: 0; margin: 0;
    }}
"""

EXPORT_PROGRESS_FILENAME_LABEL_STYLE = f"""
    QLabel {{
        color: {COLOR_TEXT_MUTED};
        font-size: 11px;
        padding: 0; margin: 0;
    }}
"""

EXPORT_PROGRESS_BAR_STYLE = f"""
    QProgressBar {{
        background: {COLOR_BG_INPUT};
        border: 1px solid {COLOR_BORDER};
        border-radius: 4px;
        text-align: center;
        height: 18px;
    }}
    QProgressBar::chunk {{
        background-color: {COLOR_ACCENT};
        border-radius: 3px;
    }}
"""

EXPORT_PROGRESS_CANCEL_BUTTON_STYLE = f"""
    QPushButton#exportProgressCancelButton {{
        color: {COLOR_TEXT};
        border-radius: 4px;
        border: 1px solid {COLOR_BORDER_ACCENT};
        padding: 0 16px;
        background-color: {COLOR_BG_ELEVATED};
        font-size: 12px;
        height: 28px;
    }}
    QPushButton#exportProgressCancelButton:hover {{
        background-color: {COLOR_BG_HOVER_SOFT};
        border-color: {COLOR_ACCENT};
    }}
"""

EXPORT_PROGRESS_DONE_BUTTON_STYLE = f"""
    QPushButton#exportProgressDoneButton {{
        color: {COLOR_TEXT_WHITE};
        font-weight: bold;
        border-radius: 4px;
        border: none;
        padding: 0 16px;
        background-color: {COLOR_ACCENT};
        font-size: 12px;
        height: 28px;
    }}
    QPushButton#exportProgressDoneButton:hover {{
        background-color: {COLOR_ACCENT_LIGHT};
    }}
"""

SORT_HINT_STYLE = f"""
    QLabel {{ color: {COLOR_TEXT_DIM}; font-size: 12px; padding: 0; margin: 0; }}
"""

SORT_ROW_WIDGET_STYLE = f"""
    QWidget {{
        background-color: {COLOR_BG_PANEL};
        border-bottom: 1px solid {COLOR_BORDER};
    }}
"""

SORT_ROW_NAME_LABEL_STYLE = f"""
    QLabel {{ color: {COLOR_TEXT_BRIGHT}; font-size: 13px; font-weight: bold; background: transparent; }}
"""

SORT_ROW_ID_LABEL_STYLE = f"""
    QLabel {{ color: {COLOR_TEXT_DIM}; font-size: 12px; background: transparent; }}
"""

# -- Pack dialog row --

PACK_ROW_STYLE = f"""
    QWidget {{
        background-color: {COLOR_BG_PANEL};
        border-bottom: 1px solid {COLOR_BORDER};
    }}
"""

PACK_ROW_NAME_STYLE = f"""
    QLabel {{ color: {COLOR_TEXT_BRIGHT}; font-size: 13px; font-weight: bold; background: transparent; }}
"""

PACK_ROW_ID_STYLE = f"""
    QLabel {{ color: {COLOR_TEXT_DIM}; font-size: 12px; background: transparent; }}
"""

# -- Pack dialog error label --

PACK_ERROR_LABEL_STYLE = f"color: {COLOR_ERROR}; font-size: 12px;"

# ==========================================
# Import Pack Dialog Styles (ui_dialogs_import_pack.py)
# ==========================================

# -- Info label (dim text, small font) --

PACK_DIALOG_INFO_LABEL_STYLE = f"QLabel {{ color: {COLOR_TEXT_DIM}; font-size: 12px; }}"

# -- Scroll area (uniform across all pack dialogs) --
PACK_DIALOG_SCROLL_STYLE = TRANSPARENT_SCROLL_STYLE

# -- "Already exists" tag (grey, small badge) --

PACK_DIALOG_TAG_EXISTING_STYLE = (
    f"QLabel {{ color: {COLOR_TEXT_DIM}; font-size: 11px; "
    f"background: rgba(137,150,166,0.12); padding: 2px 6px; border-radius: 3px; "
    f"border: 1px solid rgba(137,150,166,0.3); }}"
)

# -- "Outfit" tag (accent, small badge) --

PACK_DIALOG_TAG_OUTFIT_STYLE = (
    f"QLabel {{ color: {COLOR_ACCENT_LIGHT}; font-size: 11px; font-weight: bold; "
    f"background: rgba(217,138,79,0.12); padding: 2px 6px; border-radius: 3px; "
    f"border: 1px solid rgba(217,138,79,0.3); }}"
)

# -- Section widget (slider merge conflict section, no border) --

PACK_DIALOG_SECTION_STYLE = f"QWidget {{ background-color: {COLOR_BG_PANEL}; border-radius: 4px; }}"

# -- Section widget with border (outfit merge section) --

PACK_DIALOG_SECTION_BORDER_STYLE = (
    f"QWidget {{ background-color: {COLOR_BG_PANEL}; "
    f"border: 1px solid {COLOR_BORDER}; border-radius: 4px; }}"
)

# -- Section title label (bold bright text) --

PACK_DIALOG_SECTION_TITLE_STYLE = f"QLabel {{ color: {COLOR_TEXT_BRIGHT}; font-size: 12px; font-weight: bold; }}"

# -- Section header (e.g. "New sliders" divider header) --

PACK_DIALOG_SECTION_HEADER_STYLE = (
    f"QLabel {{ color: {COLOR_TEXT_BRIGHT}; font-size: 13px; font-weight: bold; "
    f"padding: 4px 0; border-bottom: 1px solid {COLOR_BORDER}; }}"
)

# -- Count label (e.g. outfit count) --

PACK_DIALOG_COUNT_LABEL_STYLE = f"QLabel {{ color: {COLOR_TEXT_MUTED}; font-size: 11px; }}"

# -- Error label --

PACK_DIALOG_ERROR_LABEL_STYLE = f"QLabel {{ color: {COLOR_ERROR}; font-size: 12px; }}"

# -- Input field (QLineEdit) --

PACK_DIALOG_INPUT_STYLE = (
    f"QLineEdit {{ background: {COLOR_BG_INPUT}; color: {COLOR_TEXT}; "
    f"border: 1px solid {COLOR_BORDER_ACCENT}; border-radius: 4px; padding: 0 4px; }}"
)

# -- Hint label (italic muted text) --

PACK_DIALOG_HINT_LABEL_STYLE = f"QLabel {{ color: {COLOR_TEXT_MUTED}; font-size: 11px; font-style: italic; }}"

# ==========================================
# Pack Dialog Radio Button / CheckBox Styles (unified)
# ==========================================

# Colors for styled radio buttons and checkboxes in pack dialogs
PACK_RADIO_INDICATOR_SIZE = 14
PACK_RADIO_BORDER_UNCHECKED = COLOR_BORDER_ACCENT  # #6b4932 - visible border when unchecked
PACK_RADIO_FILL_UNCHECKED = COLOR_BG_INPUT  # #1b130f - dark fill when unchecked
PACK_RADIO_FILL_CHECKED = COLOR_ACCENT  # #c56d43 - orange fill when checked
PACK_RADIO_BORDER_CHECKED = COLOR_ACCENT  # #c56d43 - orange border when checked
PACK_RADIO_CHECKMARK_COLOR = COLOR_TEXT_WHITE  # #ffffff - white checkmark/dot
PACK_RADIO_TEXT_COLOR = COLOR_TEXT  # #d9c0aa - normal text
PACK_RADIO_TEXT_COLOR_DISABLED = COLOR_TEXT_SEPIA  # #6b5b50 - disabled text
PACK_RADIO_TEXT_SIZE = "13px"

# ==========================================
# 6. Global Stylesheet QSS_STYLESHEET
# ==========================================
QSS_STYLESHEET = f"""
/* Crimson Desert theme */
QMainWindow {{ background-color: {COLOR_BG_MAIN}; }}
QWidget {{ background-color: {COLOR_BG_MAIN}; color: {COLOR_TEXT}; }}
QLabel {{ color: {COLOR_TEXT}; }}
QGroupBox {{
    font-weight: bold; font-size: 14px;
    border: 1px solid {COLOR_BORDER};
    border-radius: 5px;
    margin-top: 15px; padding-top: 15px;
    background-color: {COLOR_BG_PANEL};
    color: {COLOR_TEXT_BRIGHT};
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; color: {COLOR_TEXT_BRIGHT}; }}

/* Tooltip */
QToolTip {{
    background-color: {COLOR_BG_SURFACE};
    color: {COLOR_TEXT_BRIGHT};
    border: 1px solid {COLOR_BORDER_ACCENT};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}}

QScrollArea {{ border: none; background-color: {COLOR_BG_PANEL}; }}
QScrollArea > QWidget {{ background-color: {COLOR_BG_PANEL}; }}
QScrollArea QWidget {{ background-color: {COLOR_BG_PANEL}; }}

/* Dialogs */
QDialog[isDialog="true"], QDialog[isDarkMessageBox="true"] {{
    background-color: {COLOR_BG_PANEL};
    color: {COLOR_TEXT};
}}
QDialog[isDialog="true"] QWidget,
QDialog[isDarkMessageBox="true"] QWidget {{
    background-color: {COLOR_BG_PANEL};
}}

/* Custom title bar for dialogs (orange header) */
QWidget#customTitleBar {{
    background-color: {COLOR_ACCENT} !important;
}}
QDialog[isDialog="true"] QWidget#customTitleBar,
QDialog[isDarkMessageBox="true"] QWidget#customTitleBar {{
    background-color: {COLOR_ACCENT} !important;
}}

/* Inputs */
QLineEdit {{
    border: 1px solid {COLOR_BORDER_ACCENT};
    border-radius: 4px;
    background: {COLOR_BG_INPUT};
    color: {COLOR_TEXT};
    padding: 0 4px;
}}
QLineEdit#dialog_input {{
    background: {COLOR_BG_INPUT};
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_BORDER_ACCENT};
    border-radius: 4px;
    padding: 0 4px;
}}

/* ComboBox */
QComboBox {{
    border: 1px solid {COLOR_BORDER_ACCENT};
    border-radius: 4px;
    background: {COLOR_BG_INPUT};
    color: {COLOR_TEXT};
    padding: 0 4px;
}}
QComboBox::drop-down {{ border: none; width: 0px; }}
QComboBox QAbstractItemView {{
    background-color: {COLOR_BG_INPUT};
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_BORDER_ACCENT};
    outline: none;
    selection-background-color: transparent;
    selection-color: {COLOR_TEXT_BRIGHT};
}}
QComboBox QAbstractItemView::item {{ padding: 4px 6px; }}
QComboBox QAbstractItemView::item:selected {{
    background-color: transparent;
    color: {COLOR_TEXT_BRIGHT};
    border-left: 2px solid {COLOR_ACCENT};
    padding-left: 4px;
}}
QComboBox QAbstractItemView::item:hover {{
    background-color: rgba(197,109,67,140);
    color: {COLOR_TEXT_BRIGHT};
}}

/* Dialog buttons */
QDialogButtonBox QPushButton {{
    border: 1px solid {COLOR_BORDER_ACCENT};
    border-radius: 4px;
    background-color: {COLOR_BG_ELEVATED};
    color: {COLOR_TEXT};
    padding: 4px 12px;
}}
QDialogButtonBox QPushButton:hover {{
    background-color: {COLOR_BG_HOVER_SOFT};
    border-color: {COLOR_ACCENT};
}}

QInputDialog QLabel {{ color: {COLOR_TEXT}; }}
QMessageBox QLabel {{ color: {COLOR_TEXT}; }}

/* Slider name label */
QLabel#slider_name {{
    color: {COLOR_TEXT};
    font-size: 14px;
    font-weight: normal;
    margin-bottom: 2px;
}}
QGroupBox QLabel#slider_name {{ font-weight: normal; }}

/* Primary button (main window) */
QPushButton#btn_base_primary {{
    color: {COLOR_TEXT_BRIGHT};
    font-weight: bold;
    border-radius: 4px;
    border: 1px solid {COLOR_BORDER_ACCENT};
    padding: 0 10px;
    background-color: {COLOR_BG_SURFACE};
    font-size: 14px;
    height: 36px;
    min-height: 36px;
}}
QPushButton#btn_base_primary:hover {{
    background-color: {COLOR_BG_HOVER};
    border-color: {COLOR_ACCENT};
}}
QPushButton#btn_base_primary:pressed {{
    background-color: {COLOR_BG_PRESS};
}}
QPushButton#btn_base_primary:disabled {{
    color: {COLOR_TEXT_SEPIA};
    background-color: rgba(53,36,28,100);
    border-color: rgba(81,57,41,100);
}}

/* Primary green button */
QPushButton#btn_base_primary_green {{
    color: {COLOR_TEXT_BRIGHT};
    font-weight: bold;
    border-radius: 4px;
    border: 1px solid {COLOR_BORDER_ACCENT};
    padding: 0 10px;
    background-color: #543322;
    font-size: 14px;
    height: 36px;
    min-height: 36px;
}}
QPushButton#btn_base_primary_green:hover {{
    background-color: {COLOR_ACCENT};
    border-color: {COLOR_ACCENT};
}}
QPushButton#btn_base_primary_green:pressed {{
    background-color: {COLOR_BG_PRESS};
}}

/* Secondary button (main window) */
QPushButton#btn_base_secondary {{
    color: {COLOR_TEXT};
    border-radius: 4px;
    border: 1px solid {COLOR_BORDER_ACCENT};
    padding: 0 8px;
    background-color: {COLOR_BG_SURFACE};
    font-size: 12px;
    height: 28px;
    min-height: 28px;
    max-height: 28px;
}}
QPushButton#btn_base_secondary:hover {{
    background-color: {COLOR_BG_HOVER};
    border-color: {COLOR_ACCENT};
}}
QPushButton#btn_base_secondary:pressed {{
    background-color: {COLOR_BG_PRESS};
}}

/* Dialog primary button */
QPushButton#btn_dialog_primary {{
    color: {COLOR_TEXT_BRIGHT};
    font-weight: bold;
    border-radius: 4px;
    border: 1px solid {COLOR_BORDER_ACCENT};
    padding: 0 10px;
    background-color: {COLOR_BG_ELEVATED};
    font-size: 13px;
    height: 32px;
    min-height: 32px;
}}
QPushButton#btn_dialog_primary:hover {{
    background-color: {COLOR_BG_HOVER_SOFT};
    border-color: {COLOR_ACCENT};
}}
QPushButton#btn_dialog_primary:pressed {{
    background-color: {COLOR_BG_PANEL};
}}

/* Dialog secondary button */
QPushButton#btn_dialog_secondary {{
    color: {COLOR_TEXT};
    border-radius: 4px;
    border: 1px solid {COLOR_BORDER_ACCENT};
    padding: 0 8px;
    background-color: {COLOR_BG_ELEVATED};
    font-size: 12px;
    height: 28px;
    min-height: 28px;
    max-height: 28px;
}}
QPushButton#btn_dialog_secondary:hover {{
    background-color: {COLOR_BG_HOVER_SOFT};
    border-color: {COLOR_ACCENT};
}}
QPushButton#btn_dialog_secondary:pressed {{
    background-color: {COLOR_BG_PANEL};
}}

/* Reset button (default) */
QPushButton#btn_default_reset {{
    color: {COLOR_TEXT};
    border-radius: 4px;
    border: 1px solid {COLOR_BORDER_ACCENT};
    padding: 0 8px;
    background-color: {COLOR_BG_SURFACE};
    font-size: 12px;
    height: 28px;
    min-height: 28px;
    max-height: 28px;
}}
QPushButton#btn_default_reset:hover {{
    background-color: {COLOR_BG_HOVER};
    border-color: {COLOR_ACCENT};
}}
QPushButton#btn_default_reset:pressed {{
    background-color: {COLOR_BG_PRESS};
}}

/* Delete button */
QPushButton#btn_del_base {{
    color: {COLOR_TEXT_BRIGHT};
    border-radius: 4px;
    border: 1px solid {COLOR_BORDER_ACCENT};
    padding: 0 8px;
    background-color: #543322;
    font-size: 12px;
    height: 28px;
    min-height: 28px;
    max-height: 28px;
}}
QPushButton#btn_del_base:hover {{
    background-color: {COLOR_ACCENT_HOT};
    border-color: {COLOR_ACCENT_HOT};
}}
QPushButton#btn_del_base:pressed {{
    background-color: {COLOR_BG_PRESS};
}}

/* Reset Camera button */
QPushButton#btn_reset_cam {{
    color: {COLOR_TEXT_BRIGHT};
    border-radius: 4px;
    border: 1px solid rgba(107,73,50,180);
    padding: 0 8px;
    height: 36px;
    font-size: 12px;
    background-color: rgba(35,25,18,220);
}}
QPushButton#btn_reset_cam:hover {{
    background-color: rgba(68,48,37,240);
}}

/* Wireframe button */
QPushButton#btn_wireframe {{
    color: {COLOR_TEXT_BRIGHT};
    border-radius: 4px;
    border: 1px solid rgba(107,73,50,180);
    padding: 0 8px;
    height: 36px;
    font-size: 12px;
    background-color: rgba(35,25,18,220);
}}
QPushButton#btn_wireframe:hover {{
    background-color: rgba(68,48,37,240);
}}

/* SpinBox */
QDoubleSpinBox {{
    border: 1px solid {COLOR_BORDER_ACCENT};
    border-radius: 4px;
    background: {COLOR_BG_INPUT};
    color: {COLOR_TEXT};
    padding: 0 4px;
    height: 28px;
}}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0; }}

/* Tabs */
QTabBar::tab {{
    background-color: {COLOR_BG_SURFACE};
    color: {COLOR_TEXT_DIM};
    border: 1px solid {COLOR_BORDER};
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 6px 14px;
    margin-right: 2px;
    font-size: 12px;
}}
QTabBar::tab:selected {{
    background-color: {COLOR_BG_PANEL};
    color: {COLOR_TEXT_BRIGHT};
    font-weight: bold;
    border-color: {COLOR_BORDER_ACCENT};
    border-bottom: 1px solid {COLOR_BG_PANEL};
}}
QTabBar::tab:hover:!selected {{
    background-color: {COLOR_BG_HOVER};
    color: {COLOR_TEXT_BRIGHT};
}}

/* Selection - 仅对文本编辑器生效，避免污染 QTreeWidget */
QLineEdit, QTextEdit, QTextBrowser {{ selection-background-color: {COLOR_ACCENT}; selection-color: {COLOR_TEXT_BRIGHT}; }}

/* Slider */
QSlider::groove:horizontal {{
    background: {COLOR_BG_INPUT};
    border: 1px solid {COLOR_BORDER};
    height: 6px;
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {COLOR_ACCENT};
    border: 3px solid {COLOR_TEXT_BRIGHT};
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{ background: {COLOR_ACCENT_HOT}; }}

/* ScrollBar - unified style (vertical + horizontal) */
QScrollBar:vertical {{
    background-color: {COLOR_BG_INPUT};
    width: 8px;
    border: none;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background-color: {COLOR_BORDER_ACCENT};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {COLOR_ACCENT};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

QScrollBar:horizontal {{
    background-color: {COLOR_BG_INPUT};
    height: 8px;
    border: none;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background-color: {COLOR_BORDER_ACCENT};
    border-radius: 4px;
    min-width: 20px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {COLOR_ACCENT};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}

/* Character pack select / load / conflict dialogs */
QWidget#PackDialogTitleBar,
QWidget#PackConflictDialogTitleBar {{
    background-color: {COLOR_ACCENT};
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}}

QLabel#PackDialogTitleLabel {{
    color: {COLOR_TEXT_WHITE};
    font-size: 13px;
    font-weight: bold;
    padding: 0px;
    background: transparent;
    background-color: transparent;
}}

QPushButton#PackDialogCloseButton {{
    background: transparent;
    border: none;
    color: {COLOR_TEXT_WHITE};
    font-size: 12px;
    font-weight: bold;
}}
QPushButton#PackDialogCloseButton:hover {{
    background-color: {COLOR_CLOSE_HOVER};
    border-radius: 3px;
}}

QLabel#PackDialogInfoLabel {{
    color: {COLOR_TEXT};
    font-size: 12px;
}}

QScrollArea#PackDialogScrollArea {{
    background-color: {COLOR_BG_PANEL};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
}}
QScrollArea#PackDialogScrollArea QScrollBar:vertical {{
    background-color: {COLOR_BG_INPUT};
    width: 8px;
    border-radius: 4px;
    border: none;
}}
QScrollArea#PackDialogScrollArea QScrollBar::handle:vertical {{
    background-color: {COLOR_BORDER_ACCENT};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollArea#PackDialogScrollArea QScrollBar::handle:vertical:hover {{
    background-color: {COLOR_ACCENT};
}}

QCheckBox#PackDialogCheckBox {{
    color: {COLOR_TEXT};
    font-size: 12px;
    spacing: 6px;
    padding: 2px 4px;
}}
QCheckBox#PackDialogCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border-radius: 3px;
    border: 1px solid {COLOR_BORDER_ACCENT};
    background-color: {COLOR_BG_INPUT};
}}
QCheckBox#PackDialogCheckBox::indicator:hover {{
    border-color: {COLOR_ACCENT};
}}
    QCheckBox#PackDialogCheckBox::indicator:checked {{
        background-color: {COLOR_ACCENT};
        border-color: {COLOR_ACCENT};
        image: none;
    }}

/* Outfits Panel */
QWidget#OutfitsPanel {{
    background-color: {COLOR_BG_PANEL};
    border-left: 1px solid {COLOR_BORDER};
}}

/* Outfits Toggle Button (right edge) */
QPushButton#btn_outfits_toggle {{
    color: {COLOR_TEXT_BRIGHT};
    border-radius: 0;
    border: none;
    border-left: 1px solid {COLOR_BORDER};
    padding: 0;
    background-color: {COLOR_ACCENT};
    font-size: 10px;
    min-width: 16px;
    min-height: 24px;
}}
QPushButton#btn_outfits_toggle:hover {{
    background-color: {COLOR_ACCENT_HOT};
    color: {COLOR_TEXT_WHITE};
}}

QPushButton#PackDialogExportButton {{
    background-color: {COLOR_ACCENT};
    color: {COLOR_TEXT_WHITE};
    border: none;
    border-radius: 4px;
    font-size: 12px;
    font-weight: bold;
    padding: 0 8px;
}}
QPushButton#PackDialogExportButton:hover {{
    background-color: {COLOR_ACCENT_LIGHT};
}}
QPushButton#PackDialogExportButton:disabled {{
    background-color: {COLOR_BORDER};
    color: {COLOR_TEXT_DIM};
}}

QPushButton#PackDialogCancelButton {{
    background-color: {COLOR_BG_SURFACE};
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    font-size: 12px;
    padding: 0 8px;
}}
QPushButton#PackDialogCancelButton:hover {{
    background-color: {COLOR_BG_HOVER};
    border-color: {COLOR_ACCENT};
}}

/* ============================================================ */
/* QTreeWidget — Outfits file tree                              */
/* ============================================================ */
QTreeWidget {{
    background-color: {COLOR_BG_INPUT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 4px;
    font-size: 12px;
    color: {COLOR_TEXT};
    outline: none;
    selection-background-color: transparent;
    show-decoration-selected: 0;
}}

QTreeWidget::item {{
    background-color: {COLOR_BG_PANEL};
    border: 1px solid {COLOR_BG_ELEVATED};
    border-radius: 4px;
    margin: 2px 0px;
    padding: 4px 8px;
    color: {COLOR_TEXT};
    outline: none;
}}

QTreeWidget::item:hover {{
    background-color: {COLOR_BG_HOVER};
    border: 1px solid {COLOR_ACCENT};
    outline: none;
}}

QTreeWidget::item:selected {{
    background-color: rgba(197,109,67,50);
    border: 1px solid {COLOR_ACCENT};
    color: {COLOR_TEXT_BRIGHT};
    outline: none;
}}

QTreeWidget::branch {{
    background: transparent;
    border-image: none;
}}

QTreeWidget::branch:has-siblings:!adjoins-item {{
    border-right: 1px solid {COLOR_BORDER_ACCENT};
    margin-right: 8px;
}}

QTreeWidget::branch:has-siblings:adjoins-item {{
    border-right: 1px solid {COLOR_BORDER_ACCENT};
    border-bottom: 1px solid {COLOR_BORDER_ACCENT};
    border-radius: 0 0 0 4px;
    margin-right: 8px;
}}

QTreeWidget::branch:!has-children:!has-siblings:adjoins-item {{
    border-right: 1px solid {COLOR_BORDER_ACCENT};
    border-bottom: 1px solid {COLOR_BORDER_ACCENT};
    border-radius: 0 0 0 4px;
    margin-right: 8px;
}}

QTreeWidget::branch:has-children:!has-siblings:closed,
QTreeWidget::branch:closed:has-children:has-siblings {{
    border-image: none;
    background: transparent;
}}

QTreeWidget::branch:open:has-children:!has-siblings,
QTreeWidget::branch:open:has-children:has-siblings {{
    border-image: none;
    background: transparent;
}}

QTreeWidget::branch:selected {{
    background-color: transparent;
    border: none;
}}

QTreeWidget::branch:selected:!has-children:!has-siblings:adjoins-item,
QTreeWidget::branch:selected:has-siblings:!adjoins-item,
QTreeWidget::branch:selected:has-siblings:adjoins-item {{
    background: transparent;
    border: none;
}}

/* ============================================================ */
/* Tree control toolbar buttons (expand / collapse / refresh)   */
/* ============================================================ */
QPushButton#btn_tree_expand {{
    color: {COLOR_TEXT};
    border-radius: 3px;
    border: 1px solid {COLOR_BORDER_ACCENT};
    padding: 0;
    background-color: {COLOR_BG_SURFACE};
    font-size: 10px;
    min-width: 18px;
    max-width: 18px;
    min-height: 18px;
    max-height: 18px;
}}
QPushButton#btn_tree_expand:hover {{
    background-color: {COLOR_BG_HOVER};
    border-color: {COLOR_ACCENT};
}}
QPushButton#btn_tree_expand:pressed {{
    background-color: {COLOR_BG_PRESS};
}}

QPushButton#btn_tree_collapse {{
    color: {COLOR_TEXT};
    border-radius: 3px;
    border: 1px solid {COLOR_BORDER_ACCENT};
    padding: 0;
    background-color: {COLOR_BG_SURFACE};
    font-size: 10px;
    min-width: 18px;
    max-width: 18px;
    min-height: 18px;
    max-height: 18px;
}}
QPushButton#btn_tree_collapse:hover {{
    background-color: {COLOR_BG_HOVER};
    border-color: {COLOR_ACCENT};
}}
QPushButton#btn_tree_collapse:pressed {{
    background-color: {COLOR_BG_PRESS};
}}

QPushButton#btn_tree_refresh {{
    color: {COLOR_TEXT};
    border-radius: 3px;
    border: 1px solid {COLOR_BORDER_ACCENT};
    padding: 0;
    background-color: {COLOR_BG_SURFACE};
    font-size: 10px;
    min-width: 18px;
    max-width: 18px;
    min-height: 18px;
    max-height: 18px;
}}
QPushButton#btn_tree_refresh:hover {{
    background-color: {COLOR_BG_HOVER};
    border-color: {COLOR_ACCENT};
}}
QPushButton#btn_tree_refresh:pressed {{
    background-color: {COLOR_BG_PRESS};
}}

/* ============================================================ */
/* Tree select/deselect all buttons                              */
/* ============================================================ */
QPushButton#btn_select_all {{
    color: {COLOR_TEXT};
    border-radius: 3px;
    border: 1px solid {COLOR_BORDER_ACCENT};
    padding: 0 6px;
    background-color: {COLOR_BG_SURFACE};
    font-size: 10px;
    min-height: 18px;
    max-height: 18px;
}}
QPushButton#btn_select_all:hover {{
    background-color: {COLOR_BG_HOVER};
    border-color: {COLOR_ACCENT};
}}
QPushButton#btn_select_all:pressed {{
    background-color: {COLOR_BG_PRESS};
}}

QPushButton#btn_deselect_all {{
    color: {COLOR_TEXT};
    border-radius: 3px;
    border: 1px solid {COLOR_BORDER_ACCENT};
    padding: 0 6px;
    background-color: {COLOR_BG_SURFACE};
    font-size: 10px;
    min-height: 18px;
    max-height: 18px;
}}
QPushButton#btn_deselect_all:hover {{
    background-color: {COLOR_BG_HOVER};
    border-color: {COLOR_ACCENT};
}}
QPushButton#btn_deselect_all:pressed {{
    background-color: {COLOR_BG_PRESS};
}}

/* Outfit link toggle button (circular) */
QPushButton#outfit_link_toggle {{
    background: transparent;
    border: 1px solid {COLOR_BORDER};
    border-radius: 14px;
    color: {COLOR_TEXT_BRIGHT};
    font-size: 12px;
    padding: 0px;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
}}
QPushButton#outfit_link_toggle:hover {{
    background-color: {COLOR_ACCENT};
    border-color: {COLOR_ACCENT};
}}
"""
