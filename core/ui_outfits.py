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
from core.ui_components import NoWheelSlider, NoWheelSpinBox
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
    The companion _OutfitSlidersManager handles data distribution and signals.
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
        layout.setContentsMargins(0, 0, 0, OUTFIT_PANEL_BOTTOM_MARGIN)
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
        group_layout.addWidget(scroll)
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
    """

    outfitSliderValueChanged = pyqtSignal(str, float, object)

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

    def clear_sliders(self):
        """Remove all outfit slider widgets."""
        self._clear_layout(self.default_scroll_layout, self.default_scroll_content)
        self._clear_layout(self.custom_scroll_layout, self.custom_scroll_content)
        self._slider_widgets.clear()
        # Hide both panels when empty
        self.default_panel.hide()
        self.custom_panel.hide()

    def load_sliders(self, outfit_sliders_info: Dict[str, Dict[str, Any]]):
        """
        Load outfit sliders from discovered info.
        outfit_sliders_info: dict mapping outfit_key -> slider_info
        """
        self.clear_sliders()

        if not outfit_sliders_info:
            return

        # Separate into default and custom
        default_sliders: List[Tuple[str, Dict[str, Any]]] = []
        custom_sliders: List[Tuple[str, Dict[str, Any]]] = []

        for key, info in sorted(outfit_sliders_info.items()):
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
        def_v = float(info.get("current_value", 0))
        char_slider_id = info.get("char_slider_id")

        row_widget = QWidget()
        row_main_layout = QVBoxLayout(row_widget)
        row_main_layout.setContentsMargins(5, 5, 5, 10)
        row_main_layout.setSpacing(6)

        # Name label
        from core.ui_components import ForceWrapLabel
        name_lbl = ForceWrapLabel(label_text)
        name_lbl.setObjectName("slider_name")
        row_main_layout.addWidget(name_lbl)

        # Tools layout: slider + spinbox
        tools_layout = QHBoxLayout()
        tools_layout.setSpacing(8)
        tools_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        spin = NoWheelSpinBox()
        spin.setRange(float(min_v), float(max_v))
        spin.setDecimals(2)
        spin.setValue(float(def_v))
        spin.setFixedWidth(60)

        tools_layout.addStretch()
        tools_layout.addWidget(spin)
        tools_layout.addWidget(QLabel("%"))
        row_main_layout.addLayout(tools_layout)

        slider = NoWheelSlider(Qt.Orientation.Horizontal)
        slider.setRange(int(min_v * 100), int(max_v * 100))
        slider.setValue(int(def_v * 100))
        row_main_layout.addWidget(slider)

        # Value change handler
        def update_logic(v: float, ok=True):
            try:
                # Update our internal info
                info["current_value"] = v
                # Emit signal for synchronization with character sliders
                self.outfitSliderValueChanged.emit(outfit_key, v, char_slider_id)
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
        }

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
