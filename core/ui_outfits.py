"""
Outfits panel for Body Slider Pro.

Provides:
- File tree of outfit meshes for the current character.
- Single outfit activation/deactivation via signals.
- "Unload All Outfits" button that deletes outfit directories after confirmation.
- Outfit Sliders panels (Outfit Default Sliders + Outfit Custom Sliders).
"""

import os
from typing import Any, Dict, List, Optional, Tuple

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QGroupBox,
    QPushButton,
    QDialog,
    QSizePolicy,
    QScrollArea,
    QLabel,
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.ui_file_tree import OutfitFileTree
from core.ui_dialogs import UnloadAllOutfitsDialog
from core.ui_components import NoWheelSlider, NoWheelSpinBox, SmoothHoverButton
from core.ui_constants import (
    OUTFIT_PANEL_MIN_WIDTH,
    OUTFIT_PANEL_MAX_WIDTH,
    OUTFIT_PANEL_BOTTOM_MARGIN,
    OUTFIT_SLIDERS_PANEL_MIN_WIDTH,
    OUTFIT_SLIDERS_PANEL_MAX_WIDTH,
)


class OutfitsPanel(QWidget):
    """
    Outfits panel shown on the far right when outfit data exists for the active character.

    Signals:
        outfitActivated(original_path: str, mod_path: str)
        outfitDeactivated(original_path: str)
        outfitChecked(original_path: str, checked: bool)
            Emitted when an outfit file's checkbox state changes.
        checkedOutfitsChanged(checked_count: int, total_files: int)
            Emitted when the set of checked outfit files changes.
        unloadAllRequested()
    """

    outfitActivated = pyqtSignal(str, str)
    outfitDeactivated = pyqtSignal(str)
    outfitChecked = pyqtSignal(str, bool)
    checkedOutfitsChanged = pyqtSignal(int, int)
    unloadAllRequested = pyqtSignal()

    def __init__(
        self,
        body_slider,
        char_id: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("OutfitsPanel")
        self.main = body_slider
        self.root_dir = body_slider.root_dir
        self.char_id = char_id
        self.T = body_slider.T

        # Size constraints so the splitter cannot collapse the panel
        # to an unusable width, and so it does not grow beyond a
        # reasonable limit.
        self.setMinimumWidth(OUTFIT_PANEL_MIN_WIDTH)
        self.setMaximumWidth(OUTFIT_PANEL_MAX_WIDTH)

        # SizePolicy: prefer the minimum width, but allow the splitter
        # to expand up to maximumWidth.  This keeps the panel stable
        # while still allowing free dragging.
        self.setSizePolicy(
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Expanding,
        )

        # Connect signals to main window handlers
        self.outfitActivated.connect(self.main._on_outfit_activated)
        self.outfitDeactivated.connect(self.main._on_outfit_deactivated)
        self.unloadAllRequested.connect(self.main._on_outfits_unload_all)

        self.original_outfit_root = os.path.join(
            self.root_dir, "original_outfit", self.char_id
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, OUTFIT_PANEL_BOTTOM_MARGIN)
        layout.setSpacing(0)

        # Outfits group box (same style as Default/Custom Sliders panels)
        group = QGroupBox(self._tr("tab_outfits"))
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(5, 5, 5, 5)
        group_layout.setSpacing(4)

        # "Unload All Outfits" button inside group
        btn_unload = QPushButton(self._tr("btn_unload_all_outfits"))
        btn_unload.setObjectName("btn_base_secondary")
        btn_unload.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_unload.clicked.connect(self._on_unload_all)
        group_layout.addWidget(btn_unload)

        # File tree with toolbar, path indicator, icons
        self.file_tree = OutfitFileTree(
            root_dir=self.original_outfit_root,
            allowed_extensions=(".pac", ".obj"),
            T=self.T,
        )

        self.file_tree.itemActivated.connect(self._on_item_activated)
        self.file_tree.itemDeactivated.connect(self._on_item_deactivated)
        self.file_tree.itemChecked.connect(self._on_item_checked)
        self.file_tree.checkedFilesChanged.connect(
            self.checkedOutfitsChanged.emit
        )

        group_layout.addWidget(self.file_tree, stretch=1)
        layout.addWidget(group, stretch=1)

    # ------------ translation helper ------------

    def _tr(self, key: str, fallback: str = "") -> str:
        if not self.T:
            return fallback or key
        try:
            if hasattr(self.T, "get"):
                return self.T.get(key, fallback or key)
            if isinstance(self.T, dict):
                return self.T.get(key, fallback or key)
        except Exception:
            pass
        return fallback or key

    # ------------ file tree signals ------------

    def _on_item_activated(self, file_path: str):
        if not file_path:
            return
        try:
            mod_path = os.path.relpath(file_path, self.original_outfit_root)
        except Exception:
            mod_path = file_path
        self.outfitActivated.emit(file_path, mod_path)

    def _on_item_deactivated(self, file_path: str):
        if not file_path:
            return
        self.outfitDeactivated.emit(file_path)

    def _on_item_checked(self, file_path: str, checked: bool):
        if not file_path:
            return
        self.outfitChecked.emit(file_path, checked)

    # ------------ unload all button ------------

    def _on_unload_all(self):
        dlg = UnloadAllOutfitsDialog(self.T, self.char_id, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.unloadAllRequested.emit()

    # ------------ public helpers ------------

    def reload_for_character(self, char_id: str):
        self.char_id = char_id
        self.original_outfit_root = os.path.join(
            self.root_dir, "original_outfit", self.char_id
        )
        if os.path.isdir(self.original_outfit_root):
            self.file_tree.set_root_dir(self.original_outfit_root)
        else:
            self.file_tree.set_root_dir(os.path.join(self.root_dir, "original_outfit"))

    def get_char_id(self) -> str:
        return self.char_id

    def refresh_file_tree(self):
        """Refresh the file tree from disk asynchronously (non-blocking)."""
        if hasattr(self.file_tree, "refresh_async"):
            self.file_tree.refresh_async()


class _OutfitSingleSlidersPanel(QWidget):
    """
    Single-column outfit slider panel (either Default or Custom).
    Used as a standalone widget added directly to the outer splitter
    for six-panel equal-width layout.

    This class holds the QGroupBox + QScrollArea structure for one column.
    The companion OutfitSlidersPanel handles data distribution and signals.
    """

    def __init__(
        self,
        title: str,
        manager: "OutfitSlidersPanel",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._manager = manager
        self.setMinimumWidth(OUTFIT_SLIDERS_PANEL_MIN_WIDTH)
        self.setMaximumWidth(OUTFIT_SLIDERS_PANEL_MAX_WIDTH)
        self.setSizePolicy(
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Expanding,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        group = QGroupBox(title)
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(5, 5, 5, 5)
        group_layout.setSpacing(4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(scroll_content)
        group_layout.addWidget(scroll, stretch=1)
        layout.addWidget(group, stretch=1)

        # Expose for manager
        self.scroll_content = scroll_content
        self.scroll_layout = scroll_layout


class OutfitSlidersPanel(QWidget):
    """
    Manager for Outfit Default Sliders and Outfit Custom Sliders panels.

    Unlike the old design where this was a single QWidget with an internal
    splitter, this class now manages TWO independent _OutfitSingleSlidersPanel
    instances that are added directly to the outer splitter for six-panel layout.

    Signals:
        outfitSliderValueChanged(outfit_key: str, value: float, char_slider_id: str or None)
            Emitted when an outfit slider's value changes.
        outfitAddSliderRequested()
            Emitted when the "+ Add Outfit Slider" button is clicked.
        outfitExportObjRequested()
            Emitted when the "Export Outfit Model (.obj)" button is clicked.
    """

    outfitSliderValueChanged = pyqtSignal(str, float, object)
    outfitAddSliderRequested = pyqtSignal()
    outfitExportObjRequested = pyqtSignal()

    def __init__(
        self,
        body_slider,
        char_id: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("OutfitSlidersPanel")
        self.main = body_slider
        self.root_dir = body_slider.root_dir
        self.char_id = char_id
        self.T = body_slider.T

        # Store slider widget references for synchronization
        # key -> {"slider": QSlider, "spin": NoWheelSpinBox, "info": dict}
        self._slider_widgets: Dict[str, Dict[str, Any]] = {}

        # Current outfit mod_path for config persistence
        self._outfit_mod_path: str = ""

        # Create the two independent panels (not added to self layout)
        self.default_panel = _OutfitSingleSlidersPanel(
            self._tr("group_outfit_default"), self
        )
        self.custom_panel = _OutfitSingleSlidersPanel(
            self._tr("group_outfit_custom"), self
        )

    def _tr(self, key: str, fallback: str = "") -> str:
        if not self.T:
            return fallback or key
        try:
            if hasattr(self.T, "get"):
                return self.T.get(key, fallback or key)
            if isinstance(self.T, dict):
                return self.T.get(key, fallback or key)
        except Exception:
            pass
        return fallback or key

    # ---------- legacy properties for backward compatibility ----------

    @property
    def default_scroll_content(self):
        return self.default_panel.scroll_content

    @property
    def default_scroll_layout(self):
        return self.default_panel.scroll_layout

    @property
    def custom_scroll_content(self):
        return self.custom_panel.scroll_content

    @property
    def custom_scroll_layout(self):
        return self.custom_panel.scroll_layout

    # ---------- slider management ----------

    def _clear_layout(self, layout: QVBoxLayout, scroll_content: QWidget):
        """Clear all widgets from a scroll layout."""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def clear_sliders(self, show_empty: bool = False):
        """
        Remove all outfit slider widgets.

        Args:
            show_empty: If True, show "no sliders" placeholder labels and keep
                panels visible. Used when deactivating an outfit so the panels
                do not disappear. If False (default), only clears the widgets
                without adding placeholders. Used internally by load_sliders().
        """
        self._clear_layout(self.default_scroll_layout, self.default_scroll_content)
        self._clear_layout(self.custom_scroll_layout, self.custom_scroll_content)
        self._slider_widgets.clear()
        if show_empty:
            # Show "no sliders" placeholder labels
            self.default_scroll_layout.addWidget(
                QLabel(self._tr("no_outfit_sliders"))
            )
            self.custom_scroll_layout.addWidget(
                QLabel(self._tr("no_outfit_sliders"))
            )
            # Keep both panels visible even when no outfit is activated
            self.default_panel.show()
            self.custom_panel.show()

    def load_sliders(
        self,
        outfit_sliders_info: Dict[str, Dict[str, Any]],
        outfit_mod_path: str = "",
    ):
        """
        Load outfit sliders from discovered info.

        Args:
            outfit_sliders_info: dict mapping outfit_key -> slider_info
            outfit_mod_path: the mod_path of the currently active outfit file
                (used as top-level key in outfit_config JSON)
        """
        self.clear_sliders()
        self._outfit_mod_path = outfit_mod_path

        if not outfit_sliders_info:
            return

        # Clean up old outfit's link states (remove keys not in new outfit)
        old_keys = set(self.main.outfit_link_states.keys())
        new_keys = set(outfit_sliders_info.keys())
        for key in old_keys - new_keys:
            self.main.outfit_link_states.pop(key, None)
            self.main.outfit_slider_values.pop(key, None)
            self.main.outfit_slider_mapping.pop(key, None)

        # Initialize link states and slider values for each outfit key.
        # Default is linked. Only when JSON has explicit record with is_linked=false,
        # the slider is unlinked and uses the JSON values.
        for key, info in outfit_sliders_info.items():
            saved = self._load_saved_slider_config(info)
            # Only treat as unlinked when JSON has record AND is_linked is explicitly false
            if saved and not saved.get("is_linked", True):
                is_linked = False
            else:
                is_linked = True

            self.main.outfit_link_states[key] = is_linked

            if not is_linked and saved:
                # Unlinked: use saved current_value from JSON
                self.main.outfit_slider_values[key] = saved.get(
                    "current_value", info.get("current_value", 0.0)
                )
            else:
                # Linked: use character slider value
                self.main.outfit_slider_values[key] = info.get("current_value", 0.0)

            self.main.outfit_slider_mapping[key] = info.get("char_slider_id")

        # Separate into default and custom
        default_sliders: List[Tuple[str, Dict[str, Any]]] = []
        custom_sliders: List[Tuple[str, Dict[str, Any]]] = []

        for key, info in outfit_sliders_info.items():
            if info.get("is_custom", False):
                custom_sliders.append((key, info))
            else:
                default_sliders.append((key, info))

        # Build UI rows
        for key, info in default_sliders:
            self._add_slider_row(key, info, self.default_scroll_layout)

        for key, info in custom_sliders:
            self._add_slider_row(key, info, self.custom_scroll_layout)

        # Show "no sliders" labels if empty
        if not default_sliders:
            self.default_scroll_layout.addWidget(
                QLabel(self._tr("no_outfit_sliders"))
            )
        if not custom_sliders:
            self.custom_scroll_layout.addWidget(
                QLabel(self._tr("no_outfit_sliders"))
            )

        # Show both panels
        self.default_panel.show()
        self.custom_panel.show()

    def _add_slider_row(
        self,
        outfit_key: str,
        info: Dict[str, Any],
        target_layout: QVBoxLayout,
    ):
        """Add a single slider row to the given layout."""
        label_text = info.get("name", outfit_key)
        min_v = float(info.get("min", -50))
        max_v = float(info.get("max", 150))
        char_slider_id = info.get("char_slider_id")

        # Determine link state and default value from saved config
        linked = self.main.outfit_link_states.get(outfit_key, True)
        saved = self._load_saved_slider_config(info)

        if linked:
            # Linked: use character slider value
            def_v = float(info.get("current_value", 0))
        else:
            # Unlinked: use saved current_value from JSON
            def_v = float(
                saved.get("current_value", info.get("current_value", 0))
            ) if saved else float(info.get("current_value", 0))

        row_widget = QWidget()
        row_main_layout = QVBoxLayout(row_widget)
        row_main_layout.setContentsMargins(5, 5, 5, 10)
        row_main_layout.setSpacing(6)

        # Name row: [link toggle button] [name label]
        name_row = QHBoxLayout()
        name_row.setSpacing(6)

        # Link toggle button (only when there is a matched character slider)
        link_btn = None
        if char_slider_id:
            link_btn = QPushButton()
            link_btn.setObjectName("outfit_link_toggle")
            link_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if linked:
                link_btn.setText("🔗")
                link_btn.setToolTip(self._tr("tooltip_outfit_link_linked"))
            else:
                link_btn.setText("⛓️‍💥")
                link_btn.setToolTip(self._tr("tooltip_outfit_link_unlinked"))
            # Capture outfit_key for the closure
            ok_key = outfit_key
            link_btn.clicked.connect(
                lambda _: self._toggle_outfit_link(ok_key, info, link_btn)
            )
            name_row.addWidget(link_btn)

        from core.ui_components import ForceWrapLabel
        name_lbl = ForceWrapLabel(label_text)
        name_lbl.setObjectName("slider_name")
        name_row.addWidget(name_lbl, stretch=1)
        row_main_layout.addLayout(name_row)

        # Slider widget (created first so reset button can reference it)
        slider = NoWheelSlider(Qt.Orientation.Horizontal)
        slider.setRange(int(min_v * 100), int(max_v * 100))
        slider.setValue(int(def_v * 100))

        # Tools layout: reset button + spinbox + %
        tools_layout = QHBoxLayout()
        tools_layout.setSpacing(8)
        tools_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        spin = NoWheelSpinBox()
        spin.setRange(float(min_v), float(max_v))
        spin.setDecimals(2)
        spin.setValue(float(def_v))
        spin.setFixedWidth(60)

        # Reset button — same style as Default/Custom Sliders reset button
        reset_btn = SmoothHoverButton(self._tr("btn_text_reset", "Reset"))
        reset_btn.setObjectName("btn_base_secondary")
        # Capture variables for closure
        ok_key = outfit_key
        ok_info = info
        ok_char_sid = char_slider_id
        reset_btn.clicked.connect(
            lambda _: self._reset_slider_to_default(ok_key, ok_info, ok_char_sid, slider, spin)
        )

        tools_layout.addWidget(reset_btn)
        tools_layout.addStretch()
        tools_layout.addWidget(spin)
        tools_layout.addWidget(QLabel("%"))
        row_main_layout.addLayout(tools_layout)
        row_main_layout.addWidget(slider)

        # Value change handler
        def update_logic(v: float, ok=True):
            try:
                # Update our internal info
                info["current_value"] = v
                # Emit signal for synchronization with character sliders
                self.outfitSliderValueChanged.emit(outfit_key, v, char_slider_id)
                # Save current_value to outfit_config (only when unlinked)
                current_linked = self.main.outfit_link_states.get(outfit_key, True)
                if not current_linked:
                    self._save_slider_config(info, v)
            except Exception:
                pass

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

        target_layout.addWidget(row_widget)

        # Store widget references for external synchronization
        self._slider_widgets[outfit_key] = {
            "slider": slider,
            "spin": spin,
            "info": info,
            "link_btn": link_btn,
        }

    def _toggle_outfit_link(self, outfit_key: str, info: Dict[str, Any], link_btn: QPushButton):
        """
        Toggle the link/unlink state for an outfit slider.

        Business rules:
        - Default state is linked (follow character slider).
        - When unlinked -> linked: delete JSON record, use character slider value.
        - When linked -> unlinked: use current character slider value as initial value,
          save to JSON with is_linked=false.
        """
        currently_linked = self.main.outfit_link_states.get(outfit_key, True)
        new_linked = not currently_linked
        self.main.outfit_link_states[outfit_key] = new_linked

        char_slider_id = info.get("char_slider_id")

        if new_linked:
            # Unlinked -> Linked: delete JSON record, follow character slider
            link_btn.setText("🔗")
            link_btn.setToolTip(self._tr("tooltip_outfit_link_linked"))

            # Delete the slider record from outfit_config JSON
            ocm = getattr(self.main, "outfit_config_mgr", None)
            if ocm and self._outfit_mod_path:
                short_id = info.get("short_id", "")
                ocm.delete_slider(self.char_id, self._outfit_mod_path, short_id)

            # Use character slider value
            if char_slider_id and char_slider_id in self.main.sliders_info:
                char_val = self.main.sliders_info[char_slider_id].get("current_value", 0.0)
                info["current_value"] = char_val
                self.main.outfit_slider_values[outfit_key] = char_val
                # Update UI without emitting signals (avoid circular trigger)
                widgets = self._slider_widgets.get(outfit_key)
                if widgets:
                    slider = widgets["slider"]
                    spin = widgets["spin"]
                    slider.blockSignals(True)
                    spin.blockSignals(True)
                    slider.setValue(int(char_val * 100))
                    spin.setValue(char_val)
                    slider.blockSignals(False)
                    spin.blockSignals(False)
                # Emit signal to update outfit mesh
                self.outfitSliderValueChanged.emit(outfit_key, char_val, char_slider_id)
        else:
            # Linked -> Unlinked: use current character slider value as initial value
            link_btn.setText("⛓️‍💥")
            link_btn.setToolTip(self._tr("tooltip_outfit_link_unlinked"))

            # Get current character slider value as the starting point
            char_val = float(info.get("current_value", 0.0))
            if char_slider_id and char_slider_id in self.main.sliders_info:
                char_val = self.main.sliders_info[char_slider_id].get("current_value", 0.0)

            info["current_value"] = char_val
            self.main.outfit_slider_values[outfit_key] = char_val

            # Update UI widgets
            widgets = self._slider_widgets.get(outfit_key)
            if widgets:
                slider = widgets["slider"]
                spin = widgets["spin"]
                slider.blockSignals(True)
                spin.blockSignals(True)
                slider.setValue(int(char_val * 100))
                spin.setValue(char_val)
                slider.blockSignals(False)
                spin.blockSignals(False)

            # Emit signal to update outfit mesh
            self.outfitSliderValueChanged.emit(outfit_key, char_val, char_slider_id)

            # Save to outfit_config JSON with is_linked=false
            self._save_slider_config(info, char_val)

    def _reset_slider_to_default(
        self,
        outfit_key: str,
        info: Dict[str, Any],
        char_slider_id: Optional[str],
        slider: "NoWheelSlider",
        spin: "NoWheelSpinBox",
    ):
        """Reset a single outfit slider to its default value (0.00)."""
        default_value = 0.0
        info["current_value"] = default_value
        self.main.outfit_slider_values[outfit_key] = default_value

        # Update UI without emitting signals (avoid circular trigger)
        slider.blockSignals(True)
        spin.blockSignals(True)
        slider.setValue(int(default_value * 100))
        spin.setValue(default_value)
        slider.blockSignals(False)
        spin.blockSignals(False)

        # Emit signal to update outfit mesh
        self.outfitSliderValueChanged.emit(outfit_key, default_value, char_slider_id)

        # Save reset value to outfit_config if unlinked
        linked = self.main.outfit_link_states.get(outfit_key, True)
        if not linked:
            self._save_slider_config(info, default_value)

    def update_slider_value(self, outfit_key: str, value: float):
        """
        Update a specific outfit slider's display value (called from character slider sync).
        Uses blockSignals to prevent circular triggers.
        """
        widgets = self._slider_widgets.get(outfit_key)
        if not widgets:
            return
        slider = widgets["slider"]
        spin = widgets["spin"]
        info = widgets["info"]
        info["current_value"] = value
        slider.blockSignals(True)
        spin.blockSignals(True)
        slider.setValue(int(value * 100))
        spin.setValue(value)
        slider.blockSignals(False)
        spin.blockSignals(False)

    def reload_for_character(self, char_id: str):
        """Update character ID reference."""
        self.char_id = char_id

    # ---------- outfit_config helpers ----------

    def _load_saved_slider_config(
        self, info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Load saved slider config from outfit_config/{char_id}.json.
        Returns slider_info dict or None.
        """
        ocm = getattr(self.main, "outfit_config_mgr", None)
        if not ocm or not self._outfit_mod_path:
            return None
        short_id = info.get("short_id", "")
        result = ocm.get_slider(self.char_id, self._outfit_mod_path, short_id)
        if result is None and short_id.startswith("custom/"):
            # Backward compat: old JSON stored custom slider short_id without prefix
            result = ocm.get_slider(
                self.char_id,
                self._outfit_mod_path,
                short_id[len("custom/"):],
            )
        return result

    def _save_slider_config(
        self, info: Dict[str, Any], current_value: float
    ) -> None:
        """
        Save slider's current_value to outfit_config JSON.
        Only called when is_linked is False.
        """
        ocm = getattr(self.main, "outfit_config_mgr", None)
        if not ocm or not self._outfit_mod_path:
            return
        short_id = info.get("short_id", "")
        slider_data: Dict[str, Any] = {
            "name": info.get("name", short_id),
            "min": float(info.get("min", -50)),
            "max": float(info.get("max", 150)),
            "current_value": current_value,
            "is_linked": False,
        }
        ocm.save_slider(self.char_id, self._outfit_mod_path, short_id, slider_data)

    def _save_slider_link_state(
        self, info: Dict[str, Any], is_linked: bool, preserve_values: bool = False
    ) -> None:
        """
        Save is_linked state change to outfit_config JSON.

        Args:
            info: slider info dict
            is_linked: new link state
            preserve_values: If True, only update is_linked and keep existing
                min/max/current_value from JSON. Used when switching to linked
                so that the saved independent values are preserved for future
                unlinked use.
        """
        ocm = getattr(self.main, "outfit_config_mgr", None)
        if not ocm or not self._outfit_mod_path:
            return
        short_id = info.get("short_id", "")

        if preserve_values:
            # Only update is_linked, keep existing min/max/current_value from JSON
            saved = self._load_saved_slider_config(info)
            if saved:
                slider_data: Dict[str, Any] = {
                    "name": saved.get("name", info.get("name", short_id)),
                    "min": float(saved.get("min", info.get("min", -50))),
                    "max": float(saved.get("max", info.get("max", 150))),
                    "current_value": float(saved.get("current_value", 0.0)),
                    "is_linked": is_linked,
                }
            else:
                # No existing saved data — write defaults
                slider_data = {
                    "name": info.get("name", short_id),
                    "min": float(info.get("min", -50)),
                    "max": float(info.get("max", 150)),
                    "current_value": float(info.get("current_value", 0.0)),
                    "is_linked": is_linked,
                }
        else:
            slider_data = {
                "name": info.get("name", short_id),
                "min": float(info.get("min", -50)),
                "max": float(info.get("max", 150)),
                "current_value": float(info.get("current_value", 0.0)),
                "is_linked": is_linked,
            }
        ocm.save_slider(self.char_id, self._outfit_mod_path, short_id, slider_data)
