"""
Main window UI construction and management for Body Slider Pro.

Responsible for:
- Main layout initialization (init_ui)
- Character bar / tabs creation
- Character page creation (viewer, splitter, slider panel, outfits panel)
- Slider UI building and refreshing
- Splitter size initialization
- Viewer-related UI helpers (camera, wireframe, refresh)
- Event filter and resize behavior for main UI widgets

Designed to be used as a mixin with the BodySlider class.
"""

import os
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np
import trimesh

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QWidget,
    QPushButton,
    QLabel,
    QSlider,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QStackedWidget,
    QDoubleSpinBox,
    QGroupBox,
    QSizePolicy,
    QDialog,
)
from PyQt6.QtCore import (
    Qt,
    QTimer,
    QEvent,
)

from core.mesh_viewer import MeshViewer
from core.ui_components import (
    SmoothHoverButton,
    WireframeButton,
    ForceWrapLabel,
    NoWheelSlider,
    NoWheelSpinBox,
    TabHoverEventFilter,
    apply_tab_styles,
    ui_init_main_splitter_sizes,
    ui_init_slider_splitter_sizes,
    ui_ensure_tab_scroll_widget_size,
    create_char_info_row,
)
from core.ui_constants import (
    TAB_SCROLL_STYLE,
    TAB_INACTIVE_CONTAINER_STYLE,
    TAB_INACTIVE_HOVER_CONTAINER_STYLE,
    TAB_INACTIVE_LABEL_STYLE,
    TAB_INACTIVE_HOVER_LABEL_STYLE,
    TAB_DELETE_BUTTON_STYLE,
    VIEWER_BOTTOM_BAR_STYLE,
    BTN_RESET_CAM_STYLE,
    OUTFIT_PANEL_MIN_WIDTH,
    OUTFIT_PANEL_MAX_WIDTH,
    SLIDERS_PANEL_MIN_WIDTH,
    BTN_EXPORT_ROW_MARGINS,
    BTN_EXPORT_ROW_SPACING,
    BTN_EXPORT_TWO_ROW_MARGINS,
    BTN_EXPORT_TWO_ROW_SPACING,
)

from core.ui_dialogs import (
    AddOutfitSliderDialog,
    EditOutfitSliderDialog,
    show_warning,
    show_critical,
    show_question,
)


class MainWindowUIMixin:
    """
    Mixin that provides main window UI construction and management
    for the BodySlider class.

    Expected attributes on host class:
    - self.T: translation proxy
    - self.characters: Dict[str, Dict]
    - self.character_sliders: Dict[str, Dict]
    - self.sliders_info: Dict[str, Dict]
    - self.morph_data: Dict[str, Dict]
    - self.original_points: Dict[str, np.ndarray]
    - self.original_faces: Dict[str, np.ndarray]
    - self.mesh_viewer_data: Dict[str, Dict]
    - self.scene_base: Optional[trimesh.Scene]
    - self.active_char_id: Optional[str]
    - self.pac_mesh
    - self.cm: ConfigManager
    - self.outfit_mgr: OutfitManager
    - self._splitter_timers: List[QTimer]
    """

    # ========== init_ui ==========

    def init_ui(self) -> None:
        """
        Initialize main UI after data is ready.
        Called from startup pipeline.
        """
        central = self.central
        main_layout = self.main_layout

        self._create_custom_title_bar(main_layout, self.languages, self.current_lang, self.on_lang_changed)
        self._create_char_bar(main_layout)
        self.refresh_char_tabs()
        self._refresh_active_page_plotter()
        self.refresh_slider_ui()

        plotter = self._plotter
        if plotter:
            plotter.show()
        QTimer.singleShot(150, lambda: self.update_all_morphs())

    # ========== char bar ==========

    def _create_char_bar(self, main_layout: QVBoxLayout):
        """
        Create character tab bar (scrollable tabs + stacked pages).
        """
        self.char_bar_widget = QWidget()
        char_bar_layout = QHBoxLayout(self.char_bar_widget)
        char_bar_layout.setContentsMargins(8, 2, 8, 0)
        char_bar_layout.setSpacing(0)
        char_bar_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.char_tab_widget = QTabWidget()
        self.char_tab_widget.setDocumentMode(True)
        self.char_tab_widget.tabsClosable = False

        self.tab_scroll = QScrollArea()
        self.tab_scroll.setWidgetResizable(False)
        self.tab_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tab_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tab_scroll.setStyleSheet(TAB_SCROLL_STYLE)

        self.tab_scroll_widget = QWidget()
        self.tab_button_layout = QHBoxLayout(self.tab_scroll_widget)
        self.tab_button_layout.setContentsMargins(0, 0, 0, 0)
        self.tab_button_layout.setSpacing(2)
        self.tab_button_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.btn_add_char = SmoothHoverButton("+")
        self.btn_add_char.setObjectName("btn_base_secondary")
        self.btn_add_char.setFixedSize(28, 28)
        self.btn_add_char.setToolTip(self.T.get("btn_add_char", "+ Add Character"))
        self.btn_add_char.clicked.connect(self.add_character)
        self.tab_button_layout.addWidget(self.btn_add_char)

        self.btn_sort_chars = SmoothHoverButton("⇋")
        self.btn_sort_chars.setObjectName("btn_base_secondary")
        self.btn_sort_chars.setFixedSize(28, 28)
        self.btn_sort_chars.setToolTip(self.T.get("btn_sort_chars", "Sort Characters"))
        self.btn_sort_chars.clicked.connect(self.sort_characters)
        self.tab_button_layout.addWidget(self.btn_sort_chars)

        self.tab_scroll.setWidget(self.tab_scroll_widget)
        self.tab_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        char_bar_layout.addWidget(self.tab_scroll, stretch=1)

        self.char_stack = QStackedWidget()

        main_layout.addWidget(self.char_bar_widget)
        main_layout.addWidget(self.char_stack, stretch=1)

        QTimer.singleShot(200, self._ensure_tab_scroll_widget_size)

    def _ensure_tab_scroll_widget_size(self):
        if not hasattr(self, "tab_scroll"):
            return
        ui_ensure_tab_scroll_widget_size(self.tab_scroll_widget)

    # ========== refresh_char_tabs ==========

    def refresh_char_tabs(self):
        """
        Rebuild character tabs and pages.
        """
        self._save_current_wireframe_state()
        self._cancel_splitter_timers()
        self.mesh_viewer_data = {}

        if hasattr(self, "centralWidget"):
            root = self.centralWidget()
            if root:
                try:
                    root.removeEventFilter(self)
                except Exception:
                    pass

        while self.char_stack.count():
            w = self.char_stack.widget(0)
            self.char_stack.removeWidget(w)
            viewer = getattr(w, "plotter", None)
            plotter_container = getattr(w, "plotter_container", None)
            for obj in (viewer, plotter_container):
                if obj is not None:
                    try:
                        obj.removeEventFilter(self)
                    except Exception:
                        pass
            if viewer:
                self._close_plotter(viewer)
            w.deleteLater()

        while self.tab_button_layout.count():
            item = self.tab_button_layout.takeAt(0)
            w = item.widget()
            if w and w is not self.btn_add_char and w is not self.btn_sort_chars:
                w.deleteLater()

        char_list = list(self.characters.items())
        active_index = 0
        self._tab_buttons: List[Dict[str, Any]] = []

        for i, (cid, c) in enumerate(char_list):
            active_index = self._build_char_tab(cid, c, i, char_list, active_index)

        self.tab_button_layout.addWidget(self.btn_add_char)
        self.tab_button_layout.addWidget(self.btn_sort_chars)

        self.char_stack.setCurrentIndex(active_index)
        self._set_active_tab(active_index)

        # 立即强制更新标签栏布局几何信息，防止标签堆叠在左侧
        self.tab_scroll_widget.updateGeometry()
        self._ensure_tab_scroll_widget_size()
        self.tab_scroll.updateGeometry()

        active_page = self.char_stack.widget(active_index)
        if active_page:
            active_page.updateGeometry()
            active_page.adjustSize()
            if hasattr(active_page, "splitter"):
                active_page.splitter.updateGeometry()
                active_page.splitter.adjustSize()

        QTimer.singleShot(150, self._ensure_tab_scroll_widget_size)

    def _build_char_tab(self, cid: str, c: Dict[str, Any], i: int, char_list: List, active_index: int) -> int:
        """
        Build a single character tab button and its page.
        Returns the active_index (updated if this is the active character).
        """
        is_default_char = c.get("is_default", False)
        has_delete = not is_default_char and len(self.characters) > 1

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 0, 8, 0)
        layout.setSpacing(2)

        container.setStyleSheet(TAB_INACTIVE_CONTAINER_STYLE)
        container.setCursor(Qt.CursorShape.ArrowCursor)
        container._inactive_style = TAB_INACTIVE_CONTAINER_STYLE
        container._inactive_hover_style = TAB_INACTIVE_HOVER_CONTAINER_STYLE

        name_lbl = QLabel(c["name"])
        name_lbl.setCursor(Qt.CursorShape.ArrowCursor)
        name_lbl.setStyleSheet(TAB_INACTIVE_LABEL_STYLE)
        name_lbl._inactive_style = TAB_INACTIVE_LABEL_STYLE
        name_lbl._inactive_hover_style = TAB_INACTIVE_HOVER_LABEL_STYLE

        char_id = cid
        name_lbl.mousePressEvent = lambda e, x=char_id: self._switch_to_character_by_id(x)

        tab_index = i
        hover_filter = TabHoverEventFilter(container, name_lbl, self.char_stack, tab_index)
        container.installEventFilter(hover_filter)
        layout.addWidget(name_lbl)

        if has_delete:
            btn_del = QPushButton("×")
            btn_del.setFixedSize(16, 16)
            btn_del.setStyleSheet(TAB_DELETE_BUTTON_STYLE)
            btn_del.setToolTip(self.T.get("char_del_title", "Delete Character") + ": " + c["name"])
            char_id = cid
            btn_del.clicked.connect(lambda _, x=char_id: self.delete_character(x))
            layout.addWidget(btn_del)

        self.tab_button_layout.addWidget(container, stretch=0)

        self._tab_buttons.append({
            "container": container,
            "name_lbl": name_lbl,
        })

        page = self._create_character_page(cid)
        self.char_stack.addWidget(page)

        if cid == self.active_char_id:
            active_index = i

        return active_index

    def _set_active_tab(self, index: int):
        if not hasattr(self, "_tab_buttons"):
            return
        apply_tab_styles(self._tab_buttons, index)

    # ========== create_character_page ==========

    def _create_character_page(self, char_id: str) -> QWidget:
        """
        Create a character page with:
        - MeshViewer (left)
        - Right wrapper: [Sliders Panel] [Outfits Toggle]
        """
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        plotter_container = QWidget()
        plotter_layout = QVBoxLayout(plotter_container)
        plotter_layout.setContentsMargins(8, 0, 0, 8)

        viewer = MeshViewer()

        if hasattr(self, "scene_base") and self.scene_base:
            for name, geom in self.scene_base.geometry.items():
                if not isinstance(geom, trimesh.Trimesh):
                    continue
                verts = geom.vertices
                faces = geom.faces
                viewer.add_mesh(verts, faces, color="beige", name=name)
                self.mesh_viewer_data[name] = {
                    "vertices": verts.copy(),
                    "faces": faces.copy(),
                }

        # Set has_outfits_panel on viewer so color logic is correct
        if hasattr(self, "outfit_mgr"):
            viewer.set_has_outfits_panel(self.outfit_mgr.has_outfits_for_char(char_id))
        else:
            viewer.set_has_outfits_panel(False)

        viewer.installEventFilter(self)
        plotter_container.installEventFilter(self)

        inner_layout = QVBoxLayout()
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)

        inner_layout.addWidget(viewer, stretch=1)

        bottom_bar = QWidget()
        bottom_bar.setStyleSheet(VIEWER_BOTTOM_BAR_STYLE)
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(8, 0, 0, 0)
        bottom_layout.setSpacing(4)
        bottom_layout.addStretch(1)

        btn_reset_cam = SmoothHoverButton(self.T["btn_reset_cam"])
        btn_reset_cam.setObjectName("btn_reset_cam")
        btn_reset_cam.clicked.connect(self.reset_camera_view)
        btn_reset_cam.setStyleSheet(BTN_RESET_CAM_STYLE)

        btn_wireframe = WireframeButton(self.T["btn_wireframe_toggle"])
        btn_wireframe.set_wireframe_on(viewer._wireframe_enabled)
        btn_wireframe.clicked.connect(lambda: self._toggle_wireframe(viewer, btn_wireframe))

        bottom_layout.addWidget(btn_wireframe)
        bottom_layout.addWidget(btn_reset_cam)

        inner_layout.addWidget(bottom_bar)

        plotter_layout.addLayout(inner_layout)

        right_wrapper = QWidget()
        right_wrapper_layout = QVBoxLayout(right_wrapper)
        right_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        right_wrapper_layout.setSpacing(0)

        # Top area: [sliders+outfits splitter] [toggle button]
        right_top = QWidget()
        right_top_layout = QHBoxLayout(right_top)
        right_top_layout.setContentsMargins(0, 0, 0, 0)
        right_top_layout.setSpacing(0)

        sliders_container_widget = QWidget()
        sliders_container_widget.setMinimumWidth(380)
        v_layout = QVBoxLayout(sliders_container_widget)
        v_layout.setContentsMargins(0, 0, 10, 0)
        v_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        btn_outfits_toggle = QPushButton("▶")
        btn_outfits_toggle.setObjectName("btn_outfits_toggle")
        btn_outfits_toggle.setFixedSize(16, 24)
        btn_outfits_toggle.setToolTip(self.T.get("btn_toggle_outfits_show", "Show Outfits Panel"))
        btn_outfits_toggle.setCursor(Qt.CursorShape.PointingHandCursor)

        def _on_outfits_toggle():
            outfits_panel = getattr(page, "outfits_panel", None)
            outfit_default_panel = getattr(page, "outfit_default_sliders_panel", None)
            outfit_custom_panel = getattr(page, "outfit_custom_sliders_panel", None)
            if outfits_panel is None:
                return
            will_show = not outfits_panel.isVisible()
            self.outfit_mgr.adjust_window_width(will_show)
            if will_show:
                outfits_panel.show()
                if outfit_default_panel is not None:
                    outfit_default_panel.show()
                if outfit_custom_panel is not None:
                    outfit_custom_panel.show()
                btn_outfits_toggle.setText("◀")
                btn_outfits_toggle.setToolTip(self.T.get("btn_toggle_outfits_hide", "Hide Outfits Panel"))
            else:
                outfits_panel.hide()
                if outfit_default_panel is not None:
                    outfit_default_panel.hide()
                if outfit_custom_panel is not None:
                    outfit_custom_panel.hide()
                btn_outfits_toggle.setText("▶")
                btn_outfits_toggle.setToolTip(self.T.get("btn_toggle_outfits_show", "Show Outfits Panel"))

        btn_outfits_toggle.clicked.connect(_on_outfits_toggle)

        right_top_layout.addWidget(sliders_container_widget, stretch=1)
        right_top_layout.addWidget(btn_outfits_toggle, stretch=0)

        right_wrapper_layout.addWidget(right_top, stretch=1)

        page.btn_outfits_toggle = btn_outfits_toggle

        splitter.addWidget(plotter_container)
        splitter.addWidget(right_wrapper)

        is_default_char = self.characters.get(char_id, {}).get("is_default", False)
        if is_default_char:
            splitter.setStretchFactor(0, 1)
            splitter.setStretchFactor(1, 2)
        else:
            splitter.setStretchFactor(0, 1)
            splitter.setStretchFactor(1, 1)

        page_layout.addWidget(splitter, stretch=1)

        has_outfits = False
        if hasattr(self, "outfit_mgr"):
            has_outfits = self.outfit_mgr.has_outfits_for_char(char_id)

        if has_outfits:
            btn_outfits_toggle.setText("◀")
            btn_outfits_toggle.setToolTip(self.T.get("btn_toggle_outfits_hide", "Hide Outfits Panel"))
        else:
            btn_outfits_toggle.hide()

        is_default_char = self.characters.get(char_id, {}).get("is_default", False)
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(
            lambda: self._init_main_splitter_sizes_safe(splitter, is_default_char, has_outfits)
        )
        timer.start(150)
        self._splitter_timers.append(timer)

        page.splitter = splitter
        page.plotter = viewer
        page.plotter_container = plotter_container
        page.plotter_layout = plotter_layout
        page.panel = sliders_container_widget
        page.v_layout = v_layout
        page.btn_reset_cam = btn_reset_cam
        page.btn_wireframe = btn_wireframe

        return page

    # ========== refresh_slider_ui ==========

    def refresh_slider_ui(self) -> None:
        """
        Rebuild the right-side slider panel for the active character page.
        """
        page = self._current_page()
        if not page or not hasattr(page, "v_layout"):
            return

        v_layout = page.v_layout
        # Clear existing widgets
        while v_layout.count():
            item = v_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        char_id = self.active_char_id
        if not char_id or char_id not in self.characters:
            return

        char = self.characters[char_id]

        # Character info row
        self._add_char_info_row(v_layout, char)

        # Categorize sliders
        default_sliders, custom_sliders = self._categorize_sliders()

        is_default_char = char.get("is_default", False)

        # Create outer splitter: [Sliders Container] | [Outfits Panel]
        outer_splitter = QSplitter(Qt.Orientation.Horizontal)
        outer_splitter.setChildrenCollapsible(False)

        # Sliders container
        sliders_container = QWidget()
        sliders_container.setMinimumWidth(SLIDERS_PANEL_MIN_WIDTH)
        sliders_layout = QVBoxLayout(sliders_container)
        sliders_layout.setContentsMargins(0, 0, 0, 0)
        sliders_layout.setSpacing(4)

        # Inner splitter: Default | Custom sliders
        sliders_h_splitter = QSplitter(Qt.Orientation.Horizontal)
        sliders_h_splitter.setChildrenCollapsible(False)

        # Default sliders panel
        default_panel = QWidget()
        default_panel_layout = QVBoxLayout(default_panel)
        default_panel_layout.setContentsMargins(0, 0, 0, 0)
        default_panel_layout.setSpacing(0)

        if default_sliders:
            self._add_default_sliders_group(default_panel_layout, default_sliders)

        # Custom sliders panel
        custom_panel = QWidget()
        custom_panel_layout = QVBoxLayout(custom_panel)
        custom_panel_layout.setContentsMargins(0, 0, 0, 0)
        custom_panel_layout.setSpacing(0)

        self._add_custom_sliders_group(custom_panel_layout, custom_sliders, default_sliders)

        # Add panels to inner splitter
        if is_default_char:
            sliders_h_splitter.addWidget(default_panel)
            sliders_h_splitter.addWidget(custom_panel)
            sliders_h_splitter.setStretchFactor(0, 1)
            sliders_h_splitter.setStretchFactor(1, 1)
        else:
            sliders_h_splitter.addWidget(custom_panel)

        sliders_layout.addWidget(sliders_h_splitter, stretch=1)

        outer_splitter.addWidget(sliders_container)

        # Outfits panel
        outfits_panel = None
        if hasattr(self, "outfit_mgr"):
            outfits_panel = self.outfit_mgr.create_outfits_panel(self)

        has_outfits = outfits_panel is not None

        if has_outfits:
            outer_splitter.addWidget(outfits_panel)
            page.outfits_panel = outfits_panel
            self.outfits_panel = outfits_panel

            # Outfit Sliders panels (added as independent children for six-panel layout)
            from core.ui_outfits import OutfitSlidersPanel
            outfit_sliders_panel = OutfitSlidersPanel(self, char_id)
            outfit_sliders_panel.outfitSliderValueChanged.connect(
                self._on_outfit_slider_value_changed
            )
            outfit_sliders_panel.outfitAddSliderRequested.connect(
                self._on_outfit_add_slider
            )
            outfit_sliders_panel.outfitExportObjRequested.connect(
                self._on_outfit_export_obj
            )
            outfit_sliders_panel.outfitCustomEditRequested.connect(
                self._edit_outfit_custom_slider
            )
            outfit_sliders_panel.outfitCustomDeleteRequested.connect(
                self._delete_outfit_custom_slider
            )

            # Wrapper container for outfit sliders + buttons at the bottom
            outfit_sliders_container = QWidget()
            outfit_sliders_container_layout = QVBoxLayout(outfit_sliders_container)
            outfit_sliders_container_layout.setContentsMargins(0, 0, 0, 0)
            outfit_sliders_container_layout.setSpacing(4)

            # Horizontal splitter for the two outfit slider panels
            outfit_h_splitter = QSplitter(Qt.Orientation.Horizontal)
            outfit_h_splitter.setChildrenCollapsible(False)
            outfit_h_splitter.addWidget(outfit_sliders_panel.default_panel)
            outfit_h_splitter.addWidget(outfit_sliders_panel.custom_panel)
            outfit_h_splitter.setStretchFactor(0, 1)
            outfit_h_splitter.setStretchFactor(1, 1)
            outfit_sliders_container_layout.addWidget(outfit_h_splitter, stretch=1)

            # Button row: Export Outfit Model (.obj) | + Add Outfit Custom Slider
            outfit_btns_row = QHBoxLayout()
            outfit_btns_row.setSpacing(BTN_EXPORT_ROW_SPACING)
            outfit_btns_row.setContentsMargins(*BTN_EXPORT_ROW_MARGINS)

            outfit_btn_add = SmoothHoverButton(
                self.T.get("btn_outfit_add_slider", "+ Add Outfit Custom Slider")
            )
            outfit_btn_add.setObjectName("btn_base_primary")
            outfit_btn_add.setEnabled(False)
            outfit_btn_add.clicked.connect(self._on_outfit_add_slider)

            outfit_btn_obj = SmoothHoverButton(
                self.T.get("btn_outfit_export_obj", "Export Outfit Model (.obj)")
            )
            outfit_btn_obj.setObjectName("btn_base_primary")
            outfit_btn_obj.setEnabled(False)
            outfit_btn_obj.clicked.connect(self._on_outfit_export_obj)

            outfit_btns_row.addWidget(outfit_btn_obj, stretch=1)
            outfit_btns_row.addWidget(outfit_btn_add, stretch=1)
            outfit_sliders_container_layout.addLayout(outfit_btns_row)

            outer_splitter.addWidget(outfit_sliders_container)

            page.outfit_sliders_panel = outfit_sliders_panel
            page.outfit_default_sliders_panel = outfit_sliders_panel.default_panel
            page.outfit_custom_sliders_panel = outfit_sliders_panel.custom_panel
            page.outfit_sliders_container = outfit_sliders_container
            page.outfit_btn_add = outfit_btn_add
            page.outfit_btn_obj = outfit_btn_obj
            self.outfit_sliders_panel = outfit_sliders_panel

            # Default shown together with Outfits panel

        # Sync viewer has_outfits_panel after outfits_panel is (not) created
        try:
            viewer = self._plotter
            if viewer is not None:
                viewer.set_has_outfits_panel(bool(has_outfits))
        except Exception:
            pass

        # outer_splitter takes up the main space (stretch=1)
        v_layout.addWidget(outer_splitter, stretch=1)

        # Bottom buttons: two-row layout
        #   Row 1: Export Model (.obj) | + Add Custom Slider
        #   Row 2: Export as MOD Folder (full width)
        btns_outer = QVBoxLayout()
        btns_outer.setSpacing(BTN_EXPORT_TWO_ROW_SPACING)
        btns_outer.setContentsMargins(*BTN_EXPORT_TWO_ROW_MARGINS)

        btn_add_custom = SmoothHoverButton(self.T.get("btn_add_custom_slider", "+ Add Custom Slider"))
        btn_add_custom.setObjectName("btn_base_primary")
        btn_add_custom.clicked.connect(self.guide_add_slider)

        btn_obj = SmoothHoverButton(self.T.get("btn_export_obj", "Export Model (.obj)"))
        btn_obj.setObjectName("btn_base_primary")
        btn_obj.clicked.connect(self.save_model_obj)

        btn_mod = SmoothHoverButton(self.T.get("btn_export_mod_folder", "Export as MOD Folder"))
        btn_mod.setObjectName("btn_base_primary_green")
        btn_mod.clicked.connect(self.package_and_export_mod)

        # Row 1: Add Custom Slider + Export OBJ (equal width)
        btns_row1 = QHBoxLayout()
        btns_row1.setSpacing(BTN_EXPORT_TWO_ROW_SPACING)
        btns_row1.addWidget(btn_obj, stretch=1)
        btns_row1.addWidget(btn_add_custom, stretch=1)
        btns_outer.addLayout(btns_row1)

        # Row 2: Export MOD Folder (full width)
        btns_row2 = QHBoxLayout()
        btns_row2.setSpacing(BTN_EXPORT_TWO_ROW_SPACING)
        btns_row2.addWidget(btn_mod, stretch=1)
        btns_outer.addLayout(btns_row2)

        sliders_layout.addLayout(btns_outer)

        page.btn_add_custom = btn_add_custom
        page.btn_obj = btn_obj
        page.btn_mod = btn_mod

        # Save splitter references for resize handling
        page.outer_splitter = outer_splitter
        page.sliders_h_splitter = sliders_h_splitter

        # Initialize splitter sizes
        self._init_sliders_splitter_sizes(outer_splitter, sliders_h_splitter, is_default_char, has_outfits)

    def _categorize_sliders(self) -> Tuple[List[Tuple[str, Dict]], List[Tuple[str, Dict]]]:
        default_sliders: List[Tuple[str, Dict[str, Any]]] = []
        custom_sliders: List[Tuple[str, Dict[str, Any]]] = []
        for sid, info in self.sliders_info.items():
            if info.get("is_default", False):
                default_sliders.append((sid, info))
            else:
                custom_sliders.append((sid, info))
        return default_sliders, custom_sliders

    # ========== helper UI methods ==========

    def _add_char_info_row(self, v_layout: QVBoxLayout, char: Dict[str, Any]):
        pac_path = char.get("original_pac_path", "")
        has_pac_warning = not pac_path or not os.path.exists(pac_path)

        char_id = self.active_char_id

        def on_edit():
            if char_id is not None:
                self.edit_character(char_id)

        def on_reselect():
            if char_id is not None:
                self._reselect_pac_for_character(char_id)

        is_default = char.get("is_default", False)

        create_char_info_row(
            v_layout,
            char["name"],
            self.T,
            on_edit=on_edit,
            has_pac_warning=has_pac_warning,
            on_reselect_pac=on_reselect if has_pac_warning else None,
            on_save_pack=self.export_character_pack,
            on_load_pack=self.import_character_pack,
            on_reset_all=self.reset_all_sliders if is_default else None,
        )

    def _add_default_sliders_group(self, target_layout: QVBoxLayout, default_sliders: List[Tuple[str, Dict]]):
        def_group = QGroupBox(self.T["group_default"])
        def_main = QVBoxLayout(def_group)
        def_scroll = QScrollArea()
        def_scroll.setWidgetResizable(True)
        def_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        def_scroll_content = QWidget()
        def_layout = QVBoxLayout(def_scroll_content)
        def_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        for sid, info in default_sliders:
            path = info.get("path", "")
            missing = not path or not os.path.exists(path)
            slider_name = info.get("name") or sid or "Unnamed Slider"
            slider_min = float(info.get("min", 0.0))
            slider_max = float(info.get("max", 100.0))
            slider_value = float(info.get("current_value", 0.0))
            self.add_ui_row(slider_name, slider_min, slider_max, slider_value, def_layout, "slider", sid, missing=missing)

        def_scroll.setWidget(def_scroll_content)
        def_main.addWidget(def_scroll)
        target_layout.addWidget(def_group)

    def _add_custom_sliders_group(self, target_layout: QVBoxLayout, custom_sliders: List[Tuple[str, Dict]], default_sliders: List[Tuple[str, Dict]]):
        cust_group = QGroupBox(self.T["group_custom"])
        cg_main = QVBoxLayout(cust_group)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_content = QWidget()
        cg_layout = QVBoxLayout(scroll_content)
        cg_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        if not custom_sliders and not default_sliders:
            cg_layout.addWidget(QLabel(self.T["no_custom"]))
        else:
            for sid, info in custom_sliders:
                path = info.get("path", "")
                missing = not path or not os.path.exists(path)
                slider_name = info.get("name") or sid or "Unnamed Slider"
                slider_min = float(info.get("min", -50.0))
                slider_max = float(info.get("max", 150.0))
                slider_value = float(info.get("current_value", 0.0))
                self.add_ui_row(slider_name, slider_min, slider_max, slider_value, cg_layout, "slider", sid, missing=missing)

        scroll.setWidget(scroll_content)
        cg_main.addWidget(scroll)
        target_layout.addWidget(cust_group)

    # ========== slider UI row ==========

    def add_ui_row(self, label_text, min_v, max_v, def_v, target_layout, mode, sid=None, missing=False):
        row_widget = QWidget()
        row_main_layout = QVBoxLayout(row_widget)
        row_main_layout.setContentsMargins(5, 5, 5, 10)
        row_main_layout.setSpacing(6)

        name_lbl = ForceWrapLabel(label_text)
        name_lbl.setObjectName("slider_name")
        row_main_layout.addWidget(name_lbl)

        tools_layout = QHBoxLayout()
        tools_layout.setSpacing(8)
        tools_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        spin = NoWheelSpinBox()
        spin.setRange(float(min_v), float(max_v))
        spin.setDecimals(2)
        spin.setValue(float(def_v))
        spin.setFixedWidth(60)

        btn_reset = SmoothHoverButton(self.T["btn_text_reset"])
        btn_reset.setObjectName("btn_base_secondary")
        btn_reset.clicked.connect(lambda: spin.setValue(0.0))
        tools_layout.addWidget(btn_reset)

        if mode == "slider":
            info = self.sliders_info.get(sid, {})
            is_default_slider = info.get("is_default", False)

            if not is_default_slider:
                btn_edit = SmoothHoverButton(self.T["btn_text_edit"])
                btn_edit.setObjectName("btn_base_secondary")
                btn_edit.clicked.connect(lambda: self.edit_slider(sid))
                tools_layout.addWidget(btn_edit)

                btn_del = SmoothHoverButton(self.T["btn_text_del"])
                btn_del.setObjectName("btn_del_base")
                btn_del.clicked.connect(lambda: self.remove_slider(sid))
                tools_layout.addWidget(btn_del)

        tools_layout.addStretch()
        tools_layout.addWidget(spin)
        tools_layout.addWidget(QLabel("%"))
        row_main_layout.addLayout(tools_layout)

        slider = NoWheelSlider(Qt.Orientation.Horizontal)
        slider.setRange(int(min_v * 100), int(max_v * 100))
        slider.setValue(int(def_v * 100))
        row_main_layout.addWidget(slider)

        # Track character slider widgets for outfit sync
        if sid and not hasattr(self, "_char_slider_widgets"):
            self._char_slider_widgets: Dict[str, Dict[str, Any]] = {}

        def update_logic(v: float):
            try:
                if sid and sid in self.sliders_info:
                    self.sliders_info[sid]["current_value"] = v
                self.save_config()
                self.update_all_morphs()
            except Exception as e:
                import traceback
                print(f"[Slider Update Error] {e}")
                traceback.print_exc()

        slider.valueChanged.connect(
            lambda v: (
                spin.blockSignals(True),
                spin.setValue(v / 100.0),
                spin.blockSignals(False),
                update_logic(v / 100.0),
            )
        )
        spin.valueChanged.connect(
            lambda v: (
                slider.blockSignals(True),
                slider.setValue(int(v * 100)),
                slider.blockSignals(False),
                update_logic(v),
            )
        )

        # Register widget references for outfit slider sync
        if sid:
            if not hasattr(self, "_char_slider_widgets"):
                self._char_slider_widgets = {}
            self._char_slider_widgets[sid] = {"slider": slider, "spin": spin}

        if missing:
            warn = self._create_clickable_warning(
                self.T["slider_missing_file"],
                self.T.get("slider_reselect_hint", "Click to reselect the target mesh file."),
                lambda s=sid: self._reselect_slider_file(s),
            )
            warn.setStyleSheet(
                "color: #f07b61; font-size: 12px; font-weight: bold; "
                "background: rgba(240,123,97,0.08); border-radius: 3px; padding: 2px 4px; "
                "border: 1px solid #6b4932;"
            )
            row_main_layout.addWidget(warn)

        target_layout.addWidget(row_widget)

    # ========== splitter size init ==========

    def _init_main_splitter_sizes(self, splitter: QSplitter, is_default_char: bool = False, has_outfits: bool = False):
        ui_init_main_splitter_sizes(splitter, is_default_char, has_outfits)

    def _init_main_splitter_sizes_safe(self, splitter: QSplitter, is_default_char: bool = False, has_outfits: bool = False):
        try:
            if splitter is None or splitter.parent() is None:
                return
            splitter.window()
            self._init_main_splitter_sizes(splitter, is_default_char, has_outfits)
        except (RuntimeError, SystemError):
            return
        except Exception:
            return

    def _init_splitter_by_index(self, index: int, is_default_char: bool = False, has_outfits: bool = False):
        try:
            if not hasattr(self, "char_stack"):
                return
            if index < 0 or index >= self.char_stack.count():
                return
            page = self.char_stack.widget(index)
            if not page or not hasattr(page, "splitter"):
                return
            splitter = page.splitter
            if splitter is None or splitter.parent() is None:
                return
            splitter.window()
            self._init_main_splitter_sizes(splitter, is_default_char, has_outfits)
        except (RuntimeError, SystemError):
            return
        except Exception:
            return

    def _init_inner_splitter_sizes(self, sliders_h_splitter: QSplitter):
        """
        Set initial sizes for inner Default|Custom splitter.
        """
        try:
            if sliders_h_splitter is None or sliders_h_splitter.parent() is None:
                return
            sliders_h_splitter.window()
            inner_total = sliders_h_splitter.size().width()
            if inner_total <= 0 or sliders_h_splitter.count() < 2:
                return
            half = inner_total // 2
            sliders_h_splitter.setSizes([half, inner_total - half])
        except (RuntimeError, SystemError):
            pass
        except Exception:
            pass

    def _init_sliders_splitter_sizes(self, outer_splitter: QSplitter, sliders_h_splitter: QSplitter, is_default_char: bool, has_outfits: bool):
        """
        Set initial sizes for both splitters with correct proportions.

        Rules:
        - Default Character + Outfits: 3 equal panels → outer 2:1, inner 1:1
        - Default Character no Outfits: 2 equal panels → outer sliders full, inner 1:1
        - Custom Character + Outfits: 2 equal panels → outer 1:1
        - Custom Character no Outfits: sliders fill

        Using QTimer to run after layout is ready.
        """
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(
            lambda: self._apply_sliders_splitter_sizes(outer_splitter, sliders_h_splitter, is_default_char, has_outfits)
        )
        timer.start(100)
        self._splitter_timers.append(timer)

    def _apply_sliders_splitter_sizes(self, outer_splitter: QSplitter, sliders_h_splitter: QSplitter, is_default_char: bool, has_outfits: bool):
        try:
            if outer_splitter is None or outer_splitter.parent() is None:
                return
            outer_splitter.window()

            total = outer_splitter.size().width()
            if total <= 0:
                return

            # Outer splitter layout:
            #   has_outfits=True: [Sliders Container] [Outfits] [Outfit Sliders Container] = 3 children
            #     Sliders Container contains 2 panels (Default+Custom) via inner splitter
            #     Outfit Sliders Container contains 2 panels (Outfit Default+Custom) via inner splitter
            #     So 3 children represent 5 equal panels
            #   has_outfits=False: [Sliders Container] = 1 child
            if has_outfits and outer_splitter.count() >= 3:
                # Five equal panels within outer_splitter (each = total/5)
                # Sliders container = 2 panels = 2/5 of outer_splitter width
                # Outfits panel = 1 panel = 1/5
                # Outfit Sliders container = 2 panels = 2/5
                panel_w = total // 5
                sliders_w = panel_w * 2
                outfits_w = panel_w
                outfit_sliders_w = panel_w * 2
                sizes = [sliders_w, outfits_w, outfit_sliders_w]
                # Adjust last element to account for rounding
                sizes[-1] = total - sum(sizes[:-1])
                outer_splitter.setSizes(sizes)
            elif has_outfits:
                # Fallback for backward compatibility
                if is_default_char:
                    sliders_w = int(total * 2 / 3)
                    outfits_w = total - sliders_w
                else:
                    sliders_w = total // 2
                    outfits_w = total - sliders_w
                outer_splitter.setSizes([sliders_w, outfits_w])
            # else: only sliders container, no need to set sizes

            # Inner splitter: Default | Custom
            if sliders_h_splitter is None or sliders_h_splitter.parent() is None:
                return
            sliders_h_splitter.window()

            inner_total = sliders_h_splitter.size().width()
            if inner_total <= 0 or sliders_h_splitter.count() < 2:
                return

            if is_default_char:
                # Equal split: Default 1/2, Custom 1/2
                half = inner_total // 2
                sliders_h_splitter.setSizes([half, inner_total - half])
            # else: only custom panel, no need to set sizes

        except (RuntimeError, SystemError):
            pass
        except Exception:
            pass

    # ========== viewer-related UI helpers ==========

    def _current_page(self) -> Optional[QWidget]:
        try:
            if not hasattr(self, "char_stack"):
                return None
            idx = self.char_stack.currentIndex()
            if idx < 0:
                return None
            return self.char_stack.widget(idx)
        except RuntimeError:
            return None
        except Exception:
            return None

    @property
    def _plotter(self) -> Optional[MeshViewer]:
        try:
            if not hasattr(self, "char_stack"):
                return None
            page = self._current_page()
            return page.plotter if page else None
        except RuntimeError:
            return None
        except Exception:
            return None

    def _refresh_active_page_plotter(self):
        """
        Rebuild meshes in the active page's viewer.
        """
        page = self._current_page()
        if not page or not page.plotter:
            return

        viewer = page.plotter
        viewer.clear()

        if hasattr(self, "scene_base") and self.scene_base:
            for name, geom in self.scene_base.geometry.items():
                if not isinstance(geom, trimesh.Trimesh):
                    continue
                verts = geom.vertices
                faces = geom.faces
                self.mesh_viewer_data[name] = {
                    "vertices": verts.copy(),
                    "faces": faces.copy(),
                }
                viewer.add_mesh(verts, faces, color="beige", name=name)

        global_cam = self.camera_positions.get("global")

        if global_cam:
            viewer.set_camera_position(global_cam)
        else:
            self._apply_default_camera(viewer)

        self._apply_wireframe_state(viewer)

    def _apply_default_camera(self, viewer):
        if not viewer:
            return

        if hasattr(self, "min_b") and hasattr(self, "max_b"):
            cx = float((self.min_b[0] + self.max_b[0]) / 2.0)
            cy = float((self.min_b[1] + self.max_b[1]) / 2.0)
            cz = float((self.min_b[2] + self.max_b[2]) / 2.0)
            viewer.set_view_target([cx, cy, cz])
            viewer.set_distance(2.5)
        viewer.view_vector((0, 0, -1), (0, 1, 0))

    def reset_camera_view(self):
        plotter = self._plotter
        if not plotter:
            return

        if hasattr(self, "min_b") and hasattr(self, "max_b"):
            cx = float((self.min_b[0] + self.max_b[0]) / 2.0)
            cy = float((self.min_b[1] + self.max_b[1]) / 2.0)
            cz = float((self.min_b[2] + self.max_b[2]) / 2.0)
            plotter.set_view_target([cx, cy, cz])
            plotter.set_distance(2.5)
        plotter.view_vector((0, 0, -1), (0, 1, 0))

    def _save_current_wireframe_state(self):
        viewer = self._plotter
        if viewer is not None:
            self.wireframe_enabled = bool(getattr(viewer, "_wireframe_enabled", False))

    def _apply_wireframe_state(self, viewer: "MeshViewer"):
        if not viewer:
            return
        on = bool(getattr(self, "wireframe_enabled", False))
        viewer.set_wireframe(on)
        self._sync_wireframe_button(on)

    def _sync_wireframe_button(self, on: bool):
        page = self._current_page()
        if not page:
            return
        btn = getattr(page, "btn_wireframe", None)
        if btn is not None:
            btn.set_wireframe_on(on)

    def _toggle_wireframe(self, viewer: MeshViewer, btn: "WireframeButton"):
        if not viewer:
            return
        on = not viewer._wireframe_enabled
        viewer.set_wireframe(on)
        if btn is not None:
            btn.set_wireframe_on(on)

    def eventFilter(self, obj, event):
        try:
            try:
                is_widget = isinstance(obj, QWidget)
            except (RuntimeError, SystemError, TypeError):
                return False

            et = event.type()
            if et == QEvent.Type.Resize and is_widget:
                try:
                    if obj.testAttribute(Qt.WidgetAttribute.WA_Closing):
                        return False

                    parent = obj
                    page = None
                    while parent is not None:
                        try:
                            pw = parent.window()
                            if pw is self and hasattr(parent, "plotter") and hasattr(parent, "splitter"):
                                page = parent
                                break
                        except (RuntimeError, SystemError):
                            break
                        except Exception:
                            break
                        try:
                            parent = parent.parent()
                        except (RuntimeError, SystemError):
                            break

                    if page is not None:
                        if not getattr(self, "_splitter_resizing", False):
                            self._splitter_resizing = True
                        self._splitter_resize_timer.start()

                except (RuntimeError, SystemError):
                    pass
                except Exception:
                    pass

            try:
                return super(MainWindowUIMixin, self).eventFilter(obj, event)  # type: ignore[misc]
            except (RuntimeError, SystemError):
                return False
            except Exception:
                return False

        except (RuntimeError, SystemError):
            return False
        except Exception:
            return False

    def _on_splitter_resize_stable(self):
        self._splitter_resizing = False

        # Re-apply splitter proportions after resize stabilizes
        self._reapply_splitter_proportions()

    def _reapply_splitter_proportions(self):
        """
        Re-apply the correct splitter proportions to the current page's splitter.
        Called after resize stabilizes to maintain consistent 3D preview width.
        """
        try:
            page = self._current_page()
            if page is None:
                return
            splitter = getattr(page, "splitter", None)
            if splitter is None or splitter.parent() is None:
                return
            splitter.window()

            # Determine character type and outfits state
            char_id = self.active_char_id
            is_default_char = self.characters.get(char_id, {}).get("is_default", False) if char_id else False
            has_outfits = hasattr(page, "outfits_panel") and page.outfits_panel is not None

            # Re-apply main splitter sizes
            self._init_main_splitter_sizes(splitter, is_default_char, has_outfits)

            # Re-apply sliders splitter sizes if outer_splitter exists
            outer_splitter = getattr(page, "outer_splitter", None)
            sliders_h_splitter = getattr(page, "sliders_h_splitter", None)
            if outer_splitter is not None and sliders_h_splitter is not None:
                self._apply_sliders_splitter_sizes(
                    outer_splitter, sliders_h_splitter, is_default_char, has_outfits
                )
        except (RuntimeError, SystemError):
            pass
        except Exception:
            pass

    def _cancel_splitter_timers(self):
        if not hasattr(self, "_splitter_timers"):
            return
        for t in self._splitter_timers:
            try:
                t.stop()
            except Exception:
                pass
            try:
                t.deleteLater()
            except Exception:
                pass
        self._splitter_timers.clear()

    @staticmethod
    def _close_plotter(viewer: Optional[MeshViewer]):
        # Intentionally empty; kept for compatibility.
        pass

    # ========== outfits panel sync ==========

    def _sync_outfits_panel_for_char(self, char_id: str):
        page = self._current_page()
        if not page:
            return
        btn = getattr(page, "btn_outfits_toggle", None)
        if btn is None:
            return

        original_outfit_dir = os.path.join(self.root_dir, "original_outfit", char_id)
        has_outfits = False
        if os.path.isdir(original_outfit_dir):
            try:
                for root, _, files in os.walk(original_outfit_dir):
                    if files:
                        has_outfits = True
                        break
            except OSError:
                has_outfits = False

        if has_outfits:
            btn.show()
            btn.setText("◀")
            btn.setToolTip(self.T.get("btn_toggle_outfits_hide", "Hide Outfits Panel"))
        else:
            btn.hide()

    # ========== _create_clickable_warning (UI helper) ==========

    def _create_clickable_warning(self, text: str, tooltip: str, on_click: Callable[[], None]) -> QLabel:
        """
        Create a clickable warning label (used in slider rows).
        Delegates to ui_components if available, else falls back.
        """
        from core.ui_components import create_clickable_warning as ui_create_clickable_warning
        return ui_create_clickable_warning(text, tooltip, on_click)

    # ========== Outfit Slider sync ==========

    def _on_outfit_slider_value_changed(
        self, outfit_key: str, value: float, char_slider_id: Optional[str]
    ):
        """
        Called when an outfit slider value changes.
        If linked: sync the value to the corresponding character slider.
        If unlinked: only update the outfit mesh independently.
        """
        linked = self.outfit_link_states.get(outfit_key, True)

        if linked and char_slider_id and char_slider_id in self.sliders_info:
            # Linked state: two-way sync (existing behavior)
            self.sliders_info[char_slider_id]["current_value"] = value
            self.outfit_slider_values[outfit_key] = value
            # Update character slider UI widgets (sync display)
            widgets = getattr(self, "_char_slider_widgets", {})
            char_widgets = widgets.get(char_slider_id)
            if char_widgets:
                char_slider = char_widgets["slider"]
                char_spin = char_widgets["spin"]
                char_slider.blockSignals(True)
                char_spin.blockSignals(True)
                char_slider.setValue(int(value * 100))
                char_spin.setValue(value)
                char_slider.blockSignals(False)
                char_spin.blockSignals(False)
            # Save config (only character slider data)
            self.save_config()
            # Update morphs (this will also update outfit mesh)
            self.update_all_morphs()
        else:
            # Unlinked state: only update outfit mesh
            self.outfit_slider_values[outfit_key] = value
            if hasattr(self, "outfit_mgr") and self.outfit_mgr:
                self.outfit_mgr.update_outfit_morphs()

    def _on_outfit_add_slider(self):
        """Handle "+ Add Outfit Custom Slider" button click."""
        char_id = self.active_char_id
        if not char_id:
            return
        # Require an active outfit
        if not self.active_outfit_path or not self.active_outfit_mod_path:
            show_warning(
                self,
                self.T.get("msg_error", "Error"),
                self.T.get("outfit_add_need_active", "Activate an outfit first."),
            )
            return

        # Build existing-id set (global): character sliders + outfit-custom ids
        existing_ids = list(self.sliders_info.keys())
        ocm = getattr(self, "outfit_config_mgr", None)
        if ocm:
            existing_ids.extend(ocm.list_outfit_slider_ids(char_id))

        dlg = AddOutfitSliderDialog(self.T, existing_ids, char_id, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        result = dlg.get_result()
        if not result:
            return

        slider_name, slider_id, mesh_path, vmin, vmax = result

        # Validate Target Mesh against the active outfit signature
        outfit_sig = [
            (name, int(len(verts)))
            for name, verts in (self.outfit_original_points or {}).items()
        ]
        from core.mesh_validator import validate_target_mesh_against_original
        error_msg = validate_target_mesh_against_original(
            mesh_path,
            outfit_sig,
            translation_fn=lambda key, fallback: self.T.get(key, fallback),
        )
        if error_msg:
            show_warning(
                self,
                self.T.get("mesh_validation_title", "Target Mesh Incompatible"),
                error_msg,
            )
            return

        # Deploy mesh + compute morph delta via OutfitManager
        new_sid, err = self.outfit_mgr.add_outfit_custom_slider(
            char_id=char_id,
            slider_id=slider_id,
            slider_name=slider_name,
            min_v=vmin,
            max_v=vmax,
            src_mesh_path=mesh_path,
            outfit_original_path=self.active_outfit_path,
            outfit_mod_path=self.active_outfit_mod_path,
        )
        if not new_sid or err:
            show_critical(self, self.T.get("msg_error", "Error"), err or "Failed to add outfit slider.")
            return

        # Resolve deployed target path (relative) for persistence
        deployed_abs = self.outfit_mgr.get_deployed_target_path(
            char_id, slider_id, self.active_outfit_path, self.active_outfit_mod_path
        )
        rel_path = self._norm_path(
            os.path.relpath(deployed_abs, self.root_dir)
        ) if deployed_abs else ""

        # Persist to outfit_config JSON
        if ocm and self.active_outfit_mod_path:
            ocm.save_outfit_slider(
                char_id, self.active_outfit_mod_path, slider_id,
                {
                    "name": slider_name,
                    "min": float(vmin),
                    "max": float(vmax),
                    "current_value": 0.0,
                    "path": rel_path,
                },
            )

        # Refresh UI + 3D preview
        self._load_outfit_sliders(self.active_outfit_mod_path)
        self.outfit_mgr.update_outfit_morphs()

    def _edit_outfit_custom_slider(self, slider_id: str):
        """Edit an outfit-custom slider (Edit button)."""
        char_id = self.active_char_id
        if not char_id or not slider_id:
            return
        if not self.active_outfit_path or not self.active_outfit_mod_path:
            return
        ocm = getattr(self, "outfit_config_mgr", None)
        if not ocm:
            return
        rec = ocm.get_outfit_slider(char_id, self.active_outfit_mod_path, slider_id)
        if not rec:
            return

        # Build existing-id set excluding current
        existing_ids = list(self.sliders_info.keys())
        existing_ids.extend(ocm.list_outfit_slider_ids(char_id))

        # Current deployed mesh path (absolute)
        current_mesh = self.outfit_mgr.get_deployed_target_path(
            char_id, slider_id, self.active_outfit_path, self.active_outfit_mod_path
        )

        dlg = EditOutfitSliderDialog(
            self.T,
            existing_ids,
            char_id,
            rec.get("name", slider_id),
            slider_id,
            current_mesh,
            float(rec.get("min", -50)),
            float(rec.get("max", 150)),
            self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        result = dlg.get_result()
        if not result:
            return

        new_name, new_id, new_mesh_path, new_min, new_max = result

        # Validate new mesh if changed against outfit signature
        outfit_sig = [
            (name, int(len(verts)))
            for name, verts in (self.outfit_original_points or {}).items()
        ]
        from core.mesh_validator import validate_target_mesh_against_original
        error_msg = validate_target_mesh_against_original(
            new_mesh_path,
            outfit_sig,
            translation_fn=lambda key, fallback: self.T.get(key, fallback),
        )
        if error_msg:
            show_warning(
                self,
                self.T.get("mesh_validation_title", "Target Mesh Incompatible"),
                error_msg,
            )
            return

        # OutfitManager handles dir rename + morph key update + mesh overwrite
        ok_sid, err = self.outfit_mgr.edit_outfit_custom_slider(
            char_id=char_id,
            old_slider_id=slider_id,
            new_slider_id=new_id,
            new_src_mesh_path=new_mesh_path if new_mesh_path != current_mesh else "",
            outfit_original_path=self.active_outfit_path,
            outfit_mod_path=self.active_outfit_mod_path,
        )
        if not ok_sid or err:
            show_critical(self, self.T.get("msg_error", "Error"), err or "Failed to edit outfit slider.")
            return

        # Update JSON: rename + update fields + path
        # Resolve new deployed path
        new_deployed = self.outfit_mgr.get_deployed_target_path(
            char_id, new_id, self.active_outfit_path, self.active_outfit_mod_path
        )
        new_rel = self._norm_path(
            os.path.relpath(new_deployed, self.root_dir)
        ) if new_deployed else ""
        if slider_id != new_id:
            ocm.rename_outfit_slider(
                char_id, self.active_outfit_mod_path, slider_id, new_id
            )
        ocm.save_outfit_slider(
            char_id, self.active_outfit_mod_path, new_id,
            {
                "name": new_name,
                "min": float(new_min),
                "max": float(new_max),
                "current_value": float(rec.get("current_value", 0.0)),
                "path": new_rel,
            },
        )

        # Refresh UI + 3D preview
        self._load_outfit_sliders(self.active_outfit_mod_path)
        self.outfit_mgr.update_outfit_morphs()

    def _delete_outfit_custom_slider(self, slider_id: str):
        """Delete an outfit-custom slider (× button)."""
        char_id = self.active_char_id
        if not char_id or not slider_id:
            return
        if not self.active_outfit_path or not self.active_outfit_mod_path:
            return

        reply = show_question(
            self,
            self.T.get("outfit_custom_del_title", "Delete Outfit Custom Slider"),
            self.T.get(
                "outfit_custom_del_msg",
                'Delete outfit custom slider "{name}"?\nThis removes its deployed mesh, morph data, and config record.',
            ).format(name=slider_id),
            yes_text=self.T.get("btn_yes", "Yes"),
            no_text=self.T.get("btn_no", "No"),
        )
        if not reply:
            return

        ocm = getattr(self, "outfit_config_mgr", None)
        if ocm and self.active_outfit_mod_path:
            ocm.delete_outfit_slider(char_id, self.active_outfit_mod_path, slider_id)

        # Remove deployed dir + morph data
        self.outfit_mgr.delete_outfit_custom_slider(char_id, slider_id)

        # Refresh UI + 3D preview
        self._load_outfit_sliders(self.active_outfit_mod_path)
        self.outfit_mgr.update_outfit_morphs()

    def _on_outfit_export_obj(self):
        """Handle outfit export OBJ button click."""
        self.save_outfit_obj()