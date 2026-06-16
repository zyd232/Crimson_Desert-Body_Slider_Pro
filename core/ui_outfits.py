"""
Outfits panel for Body Slider Pro.

Provides:
- File tree of outfit meshes for the current character.
- Single outfit activation/deactivation via signals.
- "Unload All Outfits" button that deletes outfit directories after confirmation.
"""

import os
from typing import Optional

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QGroupBox,
    QPushButton,
    QDialog,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.ui_file_tree import OutfitFileTree
from core.ui_dialogs import UnloadAllOutfitsDialog
from core.ui_constants import OUTFIT_PANEL_MIN_WIDTH, OUTFIT_PANEL_MAX_WIDTH, OUTFIT_PANEL_BOTTOM_MARGIN


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
