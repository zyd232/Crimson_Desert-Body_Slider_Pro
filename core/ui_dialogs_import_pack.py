# -*- coding: utf-8 -*-
"""
Import Pack Dialogs for Body Slider Pro.

All dialogs related to character pack import are extracted here.
"""

import os
import json
import hashlib
import re
from typing import Dict, List, Optional, Set, Tuple

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QPushButton, QScrollArea, QFrame, QButtonGroup, QRadioButton,
    QLineEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from core.ui_components import (
    DialogBase, PackDialogStyledCheckBox,
    PackDialogRadioButton, show_warning, show_critical,
    SmoothHoverButton,
)
from core.ui_dialogs import CustomTitleBar
from core.ui_constants import (
    QSS_STYLESHEET,
    DIALOG_CONTENT_BG,
    DIALOG_TEXT_LABEL_STYLE,
    COLOR_BG_PANEL, COLOR_BG_INPUT,
    COLOR_ACCENT, COLOR_ACCENT_LIGHT,
    COLOR_TEXT, COLOR_TEXT_BRIGHT, COLOR_TEXT_DIM, COLOR_TEXT_MUTED,
    COLOR_BORDER, COLOR_BORDER_ACCENT,
    COLOR_ERROR,
    # Import pack dialog styles
    PACK_DIALOG_INFO_LABEL_STYLE,
    PACK_DIALOG_SCROLL_STYLE,
    PACK_DIALOG_TAG_EXISTING_STYLE,
    PACK_DIALOG_TAG_OUTFIT_STYLE,
    PACK_DIALOG_SECTION_STYLE,
    PACK_DIALOG_SECTION_BORDER_STYLE,
    PACK_DIALOG_SECTION_TITLE_STYLE,
    PACK_DIALOG_SECTION_HEADER_STYLE,
    PACK_DIALOG_COUNT_LABEL_STYLE,
    PACK_DIALOG_ERROR_LABEL_STYLE,
    PACK_DIALOG_INPUT_STYLE,
    PACK_DIALOG_HINT_LABEL_STYLE,
)


# ==========================================
# 1. CharacterPackLoadDialog
# ==========================================

class CharacterPackLoadDialog(DialogBase):
    def __init__(self, characters: List[Dict], existing_ids: Set[str], pack_has_outfit_ids: Set[str], T, parent=None):
        super().__init__(parent)
        self.T = T
        self.characters = characters
        self.existing_ids = existing_ids
        self.pack_has_outfit_ids = pack_has_outfit_ids
        self._checkboxes: Dict[str, PackDialogStyledCheckBox] = {}
        self.setStyleSheet(QSS_STYLESHEET)
        self.setMinimumWidth(400)
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.title_bar = CustomTitleBar(
            self.T.get("pack_load_select_title", "Select Characters to Import"),
            show_minimize=False, show_maximize=False
        )
        main_layout.addWidget(self.title_bar)
        content = QWidget()
        content.setStyleSheet(DIALOG_CONTENT_BG)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 10, 14, 10)
        content_layout.setSpacing(8)
        info = QLabel(self.T.get("pack_load_select_msg", "Select one or more characters from this pack to import."))
        info.setWordWrap(True)
        info.setStyleSheet(PACK_DIALOG_INFO_LABEL_STYLE)
        content_layout.addWidget(info)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(PACK_DIALOG_SCROLL_STYLE)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        for char in self.characters:
            cid = char["char_id"]
            name = char.get("name", cid)
            is_existing = cid in self.existing_ids
            has_outfit = cid in self.pack_has_outfit_ids
            row = QHBoxLayout()
            row.setSpacing(8)
            cb = PackDialogStyledCheckBox(name)
            row.addWidget(cb, stretch=1)
            self._checkboxes[cid] = cb
            tags = QHBoxLayout()
            tags.setSpacing(4)
            if is_existing:
                tag = QLabel(self.T.get("pack_load_existing", "will overwrite"))
                tag.setStyleSheet(PACK_DIALOG_TAG_EXISTING_STYLE)
                tags.addWidget(tag)
            if has_outfit:
                tag = QLabel("\U0001f457 Outfit")
                tag.setStyleSheet(PACK_DIALOG_TAG_OUTFIT_STYLE)
                tags.addWidget(tag)
            row.addLayout(tags)
            layout.addLayout(row)
        select_row = QHBoxLayout()
        select_row.setContentsMargins(0, 4, 0, 0)
        select_row.setSpacing(6)
        select_row.addStretch()
        btn_select_all = QPushButton(self.T.get("pack_select_all", "Select All"))
        btn_select_all.setObjectName("PackDialogCancelButton")
        btn_select_all.setMinimumSize(90, 24)
        btn_select_all.clicked.connect(lambda: [cb.setChecked(True) for cb in self._checkboxes.values()])
        select_row.addWidget(btn_select_all)
        btn_select_none = QPushButton(self.T.get("pack_select_none", "Select None"))
        btn_select_none.setObjectName("PackDialogCancelButton")
        btn_select_none.setMinimumSize(90, 24)
        btn_select_none.clicked.connect(lambda: [cb.setChecked(False) for cb in self._checkboxes.values()])
        select_row.addWidget(btn_select_none)
        content_layout.addLayout(select_row)
        scroll.setWidget(widget)
        content_layout.addWidget(scroll)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()
        btn_ok = SmoothHoverButton(self.T.get("pack_load_ok", "Import"))
        btn_ok.setObjectName("btn_base_secondary")
        btn_ok.setFixedSize(90, 28)
        btn_ok.clicked.connect(self.accept)
        btn_cancel = SmoothHoverButton(self.T.get("pack_cancel", "Cancel"))
        btn_cancel.setObjectName("btn_base_secondary")
        btn_cancel.setFixedSize(90, 28)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        content_layout.addLayout(btn_row)
        main_layout.addWidget(content, stretch=1)

    def get_selected_ids(self) -> Set[str]:
        return {cid for cid, cb in self._checkboxes.items() if cb.isChecked()}


# ==========================================
# 2. ImportOverwriteSelectDialog
# ==========================================

class ImportOverwriteSelectDialog(DialogBase):
    def __init__(self, duplicate_chars: List[Dict], T, parent=None):
        super().__init__(parent)
        self.T = T
        self.duplicate_chars = duplicate_chars
        self._checkboxes: Dict[str, PackDialogStyledCheckBox] = {}
        self.setStyleSheet(QSS_STYLESHEET)
        self.setMinimumWidth(420)
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.title_bar = CustomTitleBar(
            self.T.get("import_overwrite_title", "Overwrite or Merge Characters"),
            show_minimize=False, show_maximize=False
        )
        main_layout.addWidget(self.title_bar)
        content = QWidget()
        content.setStyleSheet(DIALOG_CONTENT_BG)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 10, 14, 10)
        content_layout.setSpacing(8)
        info = QLabel(self.T.get("import_overwrite_msg", "For each character that already exists, choose whether to fully overwrite it\n(existing data will be lost) or merge sliders later.\n\n- Checked: fully overwrite this character.\n- Unchecked: merge sliders (you will choose which ones to keep)."))
        info.setWordWrap(True)
        info.setStyleSheet(PACK_DIALOG_INFO_LABEL_STYLE)
        content_layout.addWidget(info)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(PACK_DIALOG_SCROLL_STYLE)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        for item in self.duplicate_chars:
            char_id = item["char_id"]
            pack_name = item.get("pack_name", char_id)
            existing_name = item.get("existing_name", char_id)
            label = f"{existing_name} ({char_id})"
            hint = pack_name
            if hint and hint not in label:
                label += f" <- {hint}"
            row = QHBoxLayout()
            row.setSpacing(8)
            cb = PackDialogStyledCheckBox(label)
            cb.setToolTip(self.T.get("import_overwrite_cb", "Fully overwrite this character (existing data will be lost)"))
            row.addWidget(cb, stretch=1)
            self._checkboxes[char_id] = cb
            layout.addLayout(row)
        select_row = QHBoxLayout()
        select_row.setContentsMargins(0, 4, 0, 0)
        select_row.setSpacing(6)
        select_row.addStretch()
        btn_merge_all = QPushButton(self.T.get("import_merge_all", "Merge All"))
        btn_merge_all.setObjectName("PackDialogCancelButton")
        btn_merge_all.setMinimumSize(90, 24)
        btn_merge_all.clicked.connect(lambda: [cb.setChecked(False) for cb in self._checkboxes.values()])
        select_row.addWidget(btn_merge_all)
        btn_overwrite_all = QPushButton(self.T.get("import_overwrite_all", "Overwrite All"))
        btn_overwrite_all.setObjectName("PackDialogCancelButton")
        btn_overwrite_all.setMinimumSize(90, 24)
        btn_overwrite_all.clicked.connect(lambda: [cb.setChecked(True) for cb in self._checkboxes.values()])
        select_row.addWidget(btn_overwrite_all)
        content_layout.addLayout(select_row)
        scroll.setWidget(widget)
        content_layout.addWidget(scroll)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()
        btn_ok = SmoothHoverButton(self.T.get("pack_ok", "OK"))
        btn_ok.setObjectName("btn_base_secondary")
        btn_ok.setFixedSize(90, 28)
        btn_ok.clicked.connect(self.accept)
        btn_cancel = SmoothHoverButton(self.T.get("pack_cancel", "Cancel"))
        btn_cancel.setObjectName("btn_base_secondary")
        btn_cancel.setFixedSize(90, 28)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        content_layout.addLayout(btn_row)
        main_layout.addWidget(content, stretch=1)

    def get_overwrite_ids(self) -> Set[str]:
        return {cid for cid, cb in self._checkboxes.items() if cb.isChecked()}


# ==========================================
# 3. ImportRenameCharDialog
# ==========================================

class ImportRenameCharDialog(DialogBase):
    def __init__(self, original_id: str, existing_ids: Set[str], T, parent=None):
        super().__init__(parent)
        self.T = T
        self.original_id = original_id
        self.existing_ids = existing_ids
        self.setStyleSheet(QSS_STYLESHEET)
        self.setMinimumWidth(340)
        self._chosen_id: Optional[str] = None
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.title_bar = CustomTitleBar(
            self.T.get("import_rename_title", "Incompatible Mesh - Rename Character"),
            show_minimize=False, show_maximize=False
        )
        main_layout.addWidget(self.title_bar)
        content = QWidget()
        content.setStyleSheet(DIALOG_CONTENT_BG)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 10, 14, 10)
        content_layout.setSpacing(8)
        info = QLabel(self.T.get("import_rename_msg", "The original mesh of this character is incompatible with the existing one.\nIt must be imported as a new character with a different ID."))
        info.setWordWrap(True)
        info.setStyleSheet(PACK_DIALOG_INFO_LABEL_STYLE)
        content_layout.addWidget(info)
        id_row = QHBoxLayout()
        id_row.setSpacing(6)
        id_row.addWidget(QLabel(self.T.get("import_rename_id_label", "New character ID:")))
        self.line_id = QLineEdit()
        self.line_id.setPlaceholderText(self.T.get("import_rename_id_hint", "Enter a unique character ID"))
        self.line_id.setStyleSheet(PACK_DIALOG_INPUT_STYLE)
        id_row.addWidget(self.line_id)
        content_layout.addLayout(id_row)
        self.error_label = QLabel()
        self.error_label.setStyleSheet(PACK_DIALOG_ERROR_LABEL_STYLE)
        self.error_label.setVisible(False)
        content_layout.addWidget(self.error_label)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()
        btn_ok = SmoothHoverButton(self.T.get("btn_ok", "OK"))
        btn_ok.setObjectName("btn_base_secondary")
        btn_ok.setFixedSize(90, 28)
        btn_ok.clicked.connect(self._accept)
        btn_cancel = SmoothHoverButton(self.T.get("btn_cancel", "Cancel"))
        btn_cancel.setObjectName("btn_base_secondary")
        btn_cancel.setFixedSize(90, 28)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        content_layout.addLayout(btn_row)
        main_layout.addWidget(content, stretch=1)

    def _accept(self):
        raw = self.line_id.text().strip()
        if not raw:
            self._show_error(self.T.get("import_rename_err_empty", "ID cannot be empty."))
            return
        if not re.fullmatch(r"[A-Za-z0-9_]+", raw):
            self._show_error(self.T.get("import_rename_err_invalid", "ID can only contain letters, numbers, and underscores."))
            return
        if raw in self.existing_ids:
            self._show_error(self.T.get("import_rename_err_exists", "This ID is already in use. Please choose another."))
            return
        self._chosen_id = raw
        self.accept()

    def _show_error(self, msg: str):
        self.error_label.setText(msg)
        self.error_label.setVisible(True)

    def chosen_id(self) -> Optional[str]:
        return self._chosen_id


# ==========================================
# 4. SliderMergeDialog
# ==========================================

class SliderMergeDialog(DialogBase):
    def __init__(self, existing_sliders: List[Dict], new_sliders: List[Dict], char_name: str, T, parent=None):
        super().__init__(parent)
        self.T = T
        self.existing_sliders = existing_sliders
        self.new_sliders = new_sliders
        self.char_name = char_name
        self._conflict_buttons: Dict[str, QButtonGroup] = {}
        self._new_checkboxes: Dict[str, PackDialogStyledCheckBox] = {}
        self.setStyleSheet(QSS_STYLESHEET)
        self.setMinimumWidth(420)
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.title_bar = CustomTitleBar(
            self.T.get("slider_merge_title", "Merge Sliders"),
            show_minimize=False, show_maximize=False
        )
        main_layout.addWidget(self.title_bar)
        content = QWidget()
        content.setStyleSheet(DIALOG_CONTENT_BG)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 10, 14, 10)
        content_layout.setSpacing(8)
        existing_ids = {s["id"] for s in self.existing_sliders}
        new_ids = {s["id"] for s in self.new_sliders}
        conflict_ids = existing_ids & new_ids
        new_only_ids = new_ids - existing_ids
        existing_map = {s["id"]: s for s in self.existing_sliders}
        new_map = {s["id"]: s for s in self.new_sliders}
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(PACK_DIALOG_SCROLL_STYLE)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        for sid in sorted(conflict_ids):
            ex = existing_map[sid]
            nw = new_map[sid]
            section = QWidget()
            section.setStyleSheet(PACK_DIALOG_SECTION_STYLE)
            sl = QVBoxLayout(section)
            sl.setContentsMargins(8, 6, 8, 6)
            sl.setSpacing(4)
            title = QLabel(f"{self.T.get('slider_merge_conflict', 'Conflict: ')}{sid}")
            title.setStyleSheet(PACK_DIALOG_SECTION_TITLE_STYLE)
            sl.addWidget(title)
            group = QButtonGroup()
            self._conflict_buttons[sid] = group
            rb_existing = PackDialogRadioButton(self.T.get("slider_merge_keep_existing", "Keep current: {name}").format(name=ex["name"]))
            rb_existing.setChecked(True)
            group.addButton(rb_existing, 0)
            sl.addWidget(rb_existing)
            rb_new = PackDialogRadioButton(self.T.get("slider_merge_keep_new", "Keep new: {name}").format(name=nw["name"]))
            group.addButton(rb_new, 1)
            sl.addWidget(rb_new)
            layout.addWidget(section)
        if new_only_ids:
            hdr = QLabel(self.T.get("slider_merge_new_only", "New sliders (only in imported pack)"))
            hdr.setStyleSheet(PACK_DIALOG_SECTION_HEADER_STYLE)
            layout.addWidget(hdr)
            for sid in sorted(new_only_ids):
                nw = new_map[sid]
                row = QHBoxLayout()
                row.setSpacing(8)
                cb = PackDialogStyledCheckBox(nw["name"])
                cb.setChecked(True)
                row.addWidget(cb, stretch=1)
                self._new_checkboxes[sid] = cb
                layout.addLayout(row)
        select_row = QHBoxLayout()
        select_row.setContentsMargins(0, 4, 0, 0)
        select_row.setSpacing(6)
        select_row.addStretch()
        btn_all_existing = QPushButton(self.T.get("slider_merge_all_existing", "Keep Only Original"))
        btn_all_existing.setObjectName("PackDialogCancelButton")
        btn_all_existing.setMinimumSize(120, 24)
        btn_all_existing.clicked.connect(lambda: [self._conflict_buttons[sid].button(0).setChecked(True) for sid in conflict_ids])
        select_row.addWidget(btn_all_existing)
        btn_all_new = QPushButton(self.T.get("slider_merge_all_new", "Fully Overwrite with New"))
        btn_all_new.setObjectName("PackDialogCancelButton")
        btn_all_new.setMinimumSize(120, 24)
        btn_all_new.clicked.connect(lambda: [self._conflict_buttons[sid].button(1).setChecked(True) for sid in conflict_ids])
        select_row.addWidget(btn_all_new)
        content_layout.addLayout(select_row)
        scroll.setWidget(widget)
        content_layout.addWidget(scroll)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()
        btn_ok = SmoothHoverButton(self.T.get("pack_ok", "OK"))
        btn_ok.setObjectName("btn_base_secondary")
        btn_ok.setFixedSize(90, 28)
        btn_ok.clicked.connect(self.accept)
        btn_cancel = SmoothHoverButton(self.T.get("pack_cancel", "Cancel"))
        btn_cancel.setObjectName("btn_base_secondary")
        btn_cancel.setFixedSize(90, 28)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        content_layout.addLayout(btn_row)
        main_layout.addWidget(content, stretch=1)

    def get_result(self) -> Dict:
        existing_map = {s["id"]: s for s in self.existing_sliders}
        new_map = {s["id"]: s for s in self.new_sliders}
        conflict_ids = set(existing_map.keys()) & set(new_map.keys())
        keep_existing = set()
        keep_new = set()
        for sid in conflict_ids:
            group = self._conflict_buttons[sid]
            chosen = group.checkedId()
            if chosen == 0:
                keep_existing.add(sid)
            else:
                keep_new.add(sid)
        new_only_checked = {sid for sid, cb in self._new_checkboxes.items() if cb.isChecked()}
        return {"keep_existing": keep_existing, "keep_new": keep_new | new_only_checked}


# ==========================================
# 5. OutfitSelectDialog (export)
# ==========================================

class OutfitSelectDialog(DialogBase):
    def __init__(self, chars_with_outfits: List[Dict], T, parent=None):
        super().__init__(parent)
        self.T = T
        self.chars_with_outfits = chars_with_outfits
        self._checkboxes: Dict[str, PackDialogStyledCheckBox] = {}
        self.setStyleSheet(QSS_STYLESHEET)
        self.setMinimumWidth(360)
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.title_bar = CustomTitleBar(
            self.T.get("outfit_select_title", "Select Characters to Export Outfits"),
            show_minimize=False, show_maximize=False
        )
        main_layout.addWidget(self.title_bar)
        content = QWidget()
        content.setStyleSheet(DIALOG_CONTENT_BG)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 10, 14, 10)
        content_layout.setSpacing(8)
        info = QLabel(self.T.get("outfit_select_msg", "The following characters have outfit data. Check the characters whose outfits you want to include in the pack."))
        info.setWordWrap(True)
        info.setStyleSheet(PACK_DIALOG_INFO_LABEL_STYLE)
        content_layout.addWidget(info)
        for ch in self.chars_with_outfits:
            cid = ch["char_id"]
            name = ch.get("name", cid)
            row = QHBoxLayout()
            row.setSpacing(8)
            cb = PackDialogStyledCheckBox(name)
            cb.setChecked(True)
            row.addWidget(cb, stretch=1)
            self._checkboxes[cid] = cb
            count_label = QLabel(f"{ch.get('outfit_count', '?')} outfits")
            count_label.setStyleSheet(PACK_DIALOG_COUNT_LABEL_STYLE)
            row.addWidget(count_label)
            content_layout.addLayout(row)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()
        btn_ok = SmoothHoverButton(self.T.get("pack_ok", "OK"))
        btn_ok.setObjectName("btn_base_secondary")
        btn_ok.setFixedSize(90, 28)
        btn_ok.clicked.connect(self.accept)
        btn_cancel = SmoothHoverButton(self.T.get("pack_cancel", "Cancel"))
        btn_cancel.setObjectName("btn_base_secondary")
        btn_cancel.setFixedSize(90, 28)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        content_layout.addLayout(btn_row)
        main_layout.addWidget(content, stretch=1)

    def get_selected_ids(self) -> Set[str]:
        return {cid for cid, cb in self._checkboxes.items() if cb.isChecked()}


# ==========================================
# 6. OutfitMergeDialog (NEW)
# ==========================================

class OutfitMergeDialog(DialogBase):
    """
    For each group of duplicate outfit files, user selects which one to keep.

    IMPROVED: Only original_outfit duplicates are displayed to the user.
    Exported_outfit duplicates are automatically resolved based on the user's
    choices for original_outfit files.
    """

    def __init__(self, duplicate_groups: List[Dict], T, parent=None):
        super().__init__(parent)
        self.T = T
        self.duplicate_groups = duplicate_groups
        self._button_groups: Dict[str, QButtonGroup] = {}
        self._original_groups: List[Dict] = [
            g for g in duplicate_groups if g.get("source_type") == "original"
        ]
        self._exported_groups: List[Dict] = [
            g for g in duplicate_groups if g.get("source_type") == "exported"
        ]
        self.setStyleSheet(QSS_STYLESHEET)
        self.setMinimumWidth(480)
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.title_bar = CustomTitleBar(
            self.T.get("outfit_merge_title", "Merge Outfit Files"),
            show_minimize=False, show_maximize=False
        )
        main_layout.addWidget(self.title_bar)
        content = QWidget()
        content.setStyleSheet(DIALOG_CONTENT_BG)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 10, 14, 10)
        content_layout.setSpacing(8)
        info = QLabel(self.T.get(
            "outfit_merge_msg",
            "The following outfit files exist in both the imported pack and your existing data.\n"
            "For each file, select which version to keep.\n\n"
            "Note: exported outfit files will be automatically resolved based on your choices here."
        ))
        info.setWordWrap(True)
        info.setStyleSheet(PACK_DIALOG_INFO_LABEL_STYLE)
        content_layout.addWidget(info)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(PACK_DIALOG_SCROLL_STYLE)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        for group in self._original_groups:
            rel_path = group["rel_path"]
            section = QWidget()
            section.setStyleSheet(PACK_DIALOG_SECTION_BORDER_STYLE)
            sl = QVBoxLayout(section)
            sl.setContentsMargins(8, 6, 8, 6)
            sl.setSpacing(4)
            path_label = QLabel(rel_path)
            path_label.setStyleSheet(PACK_DIALOG_SECTION_TITLE_STYLE)
            sl.addWidget(path_label)
            group_btn = QButtonGroup()
            self._button_groups[rel_path] = group_btn
            for idx, opt in enumerate(group["options"]):
                rb = PackDialogRadioButton(opt["label"])
                if idx == 0:
                    rb.setChecked(True)
                group_btn.addButton(rb, idx)
                sl.addWidget(rb)
            layout.addWidget(section)

        if self._exported_groups:
            hint = QLabel(
                f"\U0001f4c5 {len(self._exported_groups)} exported outfit file(s) will be automatically resolved."
            )
            hint.setStyleSheet(PACK_DIALOG_HINT_LABEL_STYLE)
            layout.addWidget(hint)

        scroll.setWidget(widget)

        # --- Batch action buttons (uniform style with SliderMergeDialog) ---
        select_row = QHBoxLayout()
        select_row.setContentsMargins(0, 4, 0, 0)
        select_row.setSpacing(6)
        select_row.addStretch()
        btn_all_existing = QPushButton(self.T.get("outfit_merge_all_existing", "Keep All Existing"))
        btn_all_existing.setObjectName("PackDialogCancelButton")
        btn_all_existing.setMinimumSize(120, 24)
        btn_all_existing.clicked.connect(
            lambda: [self._button_groups[rel].button(0).setChecked(True) for rel in self._button_groups]
        )
        select_row.addWidget(btn_all_existing)
        btn_all_new = QPushButton(self.T.get("outfit_merge_all_new", "Overwrite All with Imported"))
        btn_all_new.setObjectName("PackDialogCancelButton")
        btn_all_new.setMinimumSize(120, 24)
        btn_all_new.clicked.connect(
            lambda: [self._button_groups[rel].button(1).setChecked(True) for rel in self._button_groups]
        )
        select_row.addWidget(btn_all_new)
        content_layout.addLayout(select_row)

        content_layout.addWidget(scroll)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()
        btn_ok = SmoothHoverButton(self.T.get("pack_ok", "OK"))
        btn_ok.setObjectName("btn_base_secondary")
        btn_ok.setFixedSize(90, 28)
        btn_ok.clicked.connect(self.accept)
        btn_cancel = SmoothHoverButton(self.T.get("pack_cancel", "Cancel"))
        btn_cancel.setObjectName("btn_base_secondary")
        btn_cancel.setFixedSize(90, 28)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        content_layout.addLayout(btn_row)
        main_layout.addWidget(content, stretch=1)

    def get_choices(self) -> Dict[str, str]:
        """
        Return {rel_path: source} mapping.

        For original_outfit files: uses the user's direct choice.
        For exported_outfit files: automatically infers the choice based on
        the corresponding original_outfit file's choice.
        """
        result = {}

        original_choices: Dict[str, str] = {}
        for rel_path, group in self._button_groups.items():
            chosen_idx = group.checkedId()
            group_data = next(g for g in self._original_groups if g["rel_path"] == rel_path)
            source = group_data["options"][chosen_idx]["source"]
            result[rel_path] = source
            original_choices[group_data["original_key"]] = source

        for group in self._exported_groups:
            rel_path = group["rel_path"]
            original_key = group.get("original_key", "")
            inferred_source = original_choices.get(original_key, "existing")
            result[rel_path] = inferred_source

        return result


# ==========================================
# 7. OutfitImportChoiceDialog (NEW)
# ==========================================

class OutfitImportChoiceDialog(DialogBase):
    """
    When both pack and existing char have outfit data and meshes match,
    ask user to choose: Overwrite or Merge outfit data.
    """

    CHOICE_OVERWRITE = "overwrite"
    CHOICE_MERGE = "merge"

    def __init__(self, char_name: str, T, parent=None):
        super().__init__(parent)
        self.T = T
        self.char_name = char_name
        self._choice = self.CHOICE_OVERWRITE
        self._choice_group: Optional[QButtonGroup] = None
        self.setStyleSheet(QSS_STYLESHEET)
        self.setMinimumWidth(380)
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.title_bar = CustomTitleBar(
            self.T.get("outfit_import_choice_title", "Import Outfit Data"),
            show_minimize=False, show_maximize=False
        )
        main_layout.addWidget(self.title_bar)
        content = QWidget()
        content.setStyleSheet(DIALOG_CONTENT_BG)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 10, 14, 10)
        content_layout.setSpacing(8)
        info = QLabel(self.T.get("outfit_import_choice_msg", "The imported pack contains outfit data for this character, and you already have outfit data.\nChoose how to handle the outfit data:"))
        info.setWordWrap(True)
        info.setStyleSheet(DIALOG_TEXT_LABEL_STYLE)
        content_layout.addWidget(info)
        self._choice_group = QButtonGroup()
        rb_overwrite = PackDialogRadioButton(
            self.T.get("outfit_import_overwrite", "Overwrite - Replace all existing outfit data with the imported data")
        )
        rb_overwrite.setChecked(True)
        self._choice_group.addButton(rb_overwrite, 0)
        content_layout.addWidget(rb_overwrite)
        rb_merge = PackDialogRadioButton(
            self.T.get("outfit_import_merge", "Merge - Combine outfit data, resolving conflicts for duplicate files")
        )
        self._choice_group.addButton(rb_merge, 1)
        content_layout.addWidget(rb_merge)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()
        btn_ok = SmoothHoverButton(self.T.get("pack_ok", "OK"))
        btn_ok.setObjectName("btn_base_secondary")
        btn_ok.setFixedSize(90, 28)
        btn_ok.clicked.connect(self._accept)
        btn_cancel = SmoothHoverButton(self.T.get("pack_cancel", "Cancel"))
        btn_cancel.setObjectName("btn_base_secondary")
        btn_cancel.setFixedSize(90, 28)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        content_layout.addLayout(btn_row)
        main_layout.addWidget(content, stretch=1)

    def _accept(self):
        chosen_id = self._choice_group.checkedId()
        self._choice = self.CHOICE_MERGE if chosen_id == 1 else self.CHOICE_OVERWRITE
        self.accept()

    def choice(self) -> str:
        return self._choice


# ==========================================
# 8. MeshMismatchDialog (NEW)
# ==========================================

class MeshMismatchDialog(DialogBase):
    """Warn user when model files differ between pack and existing data."""

    def __init__(self, char_name: str, diff_summary: str, T, parent=None):
        super().__init__(parent)
        self.T = T
        self.char_name = char_name
        self.diff_summary = diff_summary
        self.setStyleSheet(QSS_STYLESHEET)
        self.setMinimumWidth(420)
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.title_bar = CustomTitleBar(
            self.T.get("mesh_mismatch_title", "Model Mismatch Detected"),
            show_minimize=False, show_maximize=False
        )
        main_layout.addWidget(self.title_bar)
        content = QWidget()
        content.setStyleSheet(DIALOG_CONTENT_BG)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 10, 14, 10)
        content_layout.setSpacing(8)
        info = QLabel(
            self.T.get("mesh_mismatch_msg",
                       "The character model files in the imported pack differ from your existing model files.\n\n"
                       "{details}\n\n"
                       "You must delete the existing character data before importing the new character data.")
            .format(details=self.diff_summary)
        )
        info.setWordWrap(True)
        info.setStyleSheet(DIALOG_TEXT_LABEL_STYLE)
        content_layout.addWidget(info)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()
        btn_delete_import = SmoothHoverButton(self.T.get("mesh_mismatch_delete_import", "Delete Existing & Import"))
        btn_delete_import.setObjectName("btn_base_secondary")
        btn_delete_import.setMinimumSize(160, 28)
        btn_delete_import.clicked.connect(self._accept_delete)
        btn_cancel = SmoothHoverButton(self.T.get("pack_cancel", "Cancel"))
        btn_cancel.setObjectName("btn_base_secondary")
        btn_cancel.setFixedSize(90, 28)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_delete_import)
        btn_row.addWidget(btn_cancel)
        content_layout.addLayout(btn_row)
        main_layout.addWidget(content, stretch=1)

    def _accept_delete(self):
        self.accept()