# -*- coding: utf-8 -*-
"""
Dialog classes extracted from ui_components.py.
Contains all custom QDialog-based dialogs and related helpers.
"""

import os
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSlider,
    QVBoxLayout,
    QWidget,
    QAbstractSpinBox,
    QComboBox,
    QGroupBox,
    QFormLayout,
    QCheckBox,
    QScrollArea,
)
from PyQt6.QtCore import (
    Qt,
    QEvent,
    QTimer,
    QPropertyAnimation,
    QElapsedTimer,
    QPointF,
    QRectF,
    QRect,
    QPoint,
)
from PyQt6.QtGui import (
    QMouseEvent,
    QPalette,
    QColor,
    QPainter,
    QPen,
    QFontMetrics,
    QTextOption,
    QCursor,
)

from core.ui_constants import (
    T,
    QSS_STYLESHEET,
    DIALOG_CONTENT_BG,
    DIALOG_INPUT_STYLE,
    DIALOG_INPUT_READONLY_STYLE,
    DIALOG_TEXT_LABEL_STYLE,
    TITLE_BAR_TITLE_LABEL_STYLE,
    TITLE_BAR_BUTTON_STYLE,
    TITLE_BAR_BUTTON_SMALL_STYLE,
    TITLE_BAR_CLOSE_BUTTON_STYLE,
    TITLE_BAR_WIDGET_STYLE,
    DARK_MESSAGEBOX_TEXT_LABEL_STYLE,
    DARK_MESSAGEBOX_ICON_LABEL_STYLE,
    DARK_MESSAGEBOX_ICON_LABEL_WARNING_STYLE,
    DARK_MESSAGEBOX_CONTENT_WIDGET_STYLE,
    SORT_ROW_WIDGET_STYLE,
    SORT_ROW_NAME_LABEL_STYLE,
    SORT_ROW_ID_LABEL_STYLE,
    BORDERED_SCROLL_STYLE,
    COLOR_ACCENT_HOT,
    COLOR_ACCENT_LIGHT,
    PACK_RADIO_INDICATOR_SIZE,
    PACK_RADIO_BORDER_UNCHECKED,
    PACK_RADIO_FILL_UNCHECKED,
    PACK_RADIO_FILL_CHECKED,
    PACK_RADIO_BORDER_CHECKED,
    PACK_RADIO_CHECKMARK_COLOR,
    PACK_RADIO_TEXT_COLOR,
    PACK_RADIO_TEXT_COLOR_DISABLED,
)
from core.ui_window_manager import FramelessDialogMixin, SimpleDragDialogMixin


# ==========================================
# Dialog base class
# ==========================================

class DialogBase(QDialog, FramelessDialogMixin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setProperty("isDialog", True)

        # Initialize frameless dialog behavior from mixin
        self.init_frameless_dialog(resizable=True, resize_margin=8)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        FramelessDialogMixin.mousePressEvent(self, event)
        super(QDialog, self).mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        FramelessDialogMixin.mouseMoveEvent(self, event)
        super(QDialog, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        FramelessDialogMixin.mouseReleaseEvent(self, event)
        super(QDialog, self).mouseReleaseEvent(event)

    def register_widgets_for_resize(self, widgets: list):
        # For timer-based resize, per-widget tracking is not strictly required,
        # but we keep this hook so child dialogs can still mark widgets if needed.
        for w in widgets:
            if w:
                w.setMouseTracking(True)


# ==========================================
# Custom widgets used by dialogs
# ==========================================

from PyQt6.QtWidgets import QGraphicsOpacityEffect
from PyQt6.QtCore import QEasingCurve


class SmoothHoverButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(1.0)
        self.setGraphicsEffect(self._effect)
        self._anim = QPropertyAnimation(self._effect, b"opacity")
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._normal_opacity = 1.0
        self._hover_opacity = 0.92
        self._pressed_opacity = 0.85

    def _animate_to(self, target_opacity: float) -> None:
        if self._anim:
            self._anim.stop()
            self._anim.setEndValue(target_opacity)
            self._anim.start(QPropertyAnimation.DeletionPolicy.KeepWhenStopped)

    def mousePressEvent(self, event):
        self._animate_to(self._pressed_opacity)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        target = self._hover_opacity if self.underMouse() else self._normal_opacity
        self._animate_to(target)
        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        self._animate_to(self._hover_opacity)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate_to(self._normal_opacity)
        super().leaveEvent(event)


class CustomTitleBar(QWidget):
    BACKGROUND_COLOR = QColor("#c56d43")

    def __init__(self, title: str = "", show_minimize: bool = False,
                 show_maximize: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("customTitleBar")
        self.setFixedHeight(32)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 6, 0)
        layout.setSpacing(6)
        self.title_label = QLabel(title)
        self.title_label.setAutoFillBackground(False)
        self.title_label.setStyleSheet(TITLE_BAR_TITLE_LABEL_STYLE)
        layout.addWidget(self.title_label)
        layout.addStretch()
        btn_style = TITLE_BAR_BUTTON_STYLE
        close_style = TITLE_BAR_CLOSE_BUTTON_STYLE
        if show_minimize:
            btn_min = QPushButton("\u2500")
            btn_min.setFixedSize(36, 26)
            btn_min.setStyleSheet(btn_style)
            btn_min.clicked.connect(self._show_minimized)
            layout.addWidget(btn_min)
        if show_maximize:
            self.btn_max = QPushButton("\u25A1")
            self.btn_max.setFixedSize(36, 26)
            self.btn_max.setStyleSheet(btn_style.replace("font-size: 14px;", "font-size: 12px;"))
            self.btn_max.clicked.connect(self._toggle_maximize)
            layout.addWidget(self.btn_max)
        btn_close = QPushButton("\u2715")
        btn_close.setFixedSize(36, 26)
        btn_close.setStyleSheet(close_style)
        btn_close.clicked.connect(self._close)
        layout.addWidget(btn_close)
        self.setStyleSheet(TITLE_BAR_WIDGET_STYLE)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.BACKGROUND_COLOR)
        painter.end()
        super().paintEvent(event)

    def _show_minimized(self):
        win = self.window()
        if win:
            win.showMinimized()

    def _toggle_maximize(self):
        win = self.window()
        if not win:
            return
        if win.isMaximized():
            win.showNormal()
            self.btn_max.setText("\u25A1")
        else:
            win.showMaximized()
            self.btn_max.setText("\u276F")

    def _close(self):
        win = self.window()
        if win:
            win.close()


# ==========================================
# 1. DarkMessageBox
# ==========================================

class DarkMessageBox(QDialog, SimpleDragDialogMixin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setMinimumWidth(360)
        self.setProperty("isDarkMessageBox", True)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setStyleSheet(QSS_STYLESHEET)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.title_bar = CustomTitleBar("", show_minimize=False, show_maximize=False)
        main_layout.addWidget(self.title_bar)
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(16, 14, 16, 10)
        content_layout.setSpacing(8)
        self.icon_label = QLabel()
        self.icon_label.setFixedWidth(28)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        icon_content_layout = QHBoxLayout()
        icon_content_layout.setSpacing(10)
        icon_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        icon_content_layout.addWidget(self.icon_label)
        self.text_label = QLabel()
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet(DARK_MESSAGEBOX_TEXT_LABEL_STYLE)
        icon_content_layout.addWidget(self.text_label, stretch=1)
        content_layout.addLayout(icon_content_layout)
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(16, 4, 16, 12)
        button_layout.addStretch()
        self.button_box = QHBoxLayout()
        self.button_box.setSpacing(8)
        button_layout.addLayout(self.button_box)
        content_layout.addLayout(button_layout)
        content_widget = QWidget()
        content_widget.setStyleSheet(DARK_MESSAGEBOX_CONTENT_WIDGET_STYLE)
        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget)
        self._drag_pos = None

    def setWindowTitle(self, title: str) -> None:
        super().setWindowTitle(title)
        self.title_bar.title_label.setText(title)

    def setText(self, text: str) -> None:
        self.text_label.setText(text)

    def setIcon(self, icon) -> None:
        icon_map = {
            QMessageBox.Icon.Information: "ℹ",
            QMessageBox.Icon.Warning: "⚠",
            QMessageBox.Icon.Critical: "✖",
            QMessageBox.Icon.Question: "❓",
        }
        symbol = icon_map.get(icon, "")
        if symbol:
            self.icon_label.setText(symbol)
            color = {
                QMessageBox.Icon.Information: "#f4ddc4",
                QMessageBox.Icon.Warning: "#f07b61",
                QMessageBox.Icon.Critical: "#f07b61",
                QMessageBox.Icon.Question: "#f4ddc4",
            }.get(icon, "#f4ddc4")
            self.icon_label.setStyleSheet(
                DARK_MESSAGEBOX_ICON_LABEL_WARNING_STYLE
                if color in ("#f07b61",)
                else DARK_MESSAGEBOX_ICON_LABEL_STYLE
            )
        else:
            self.icon_label.setText("")

    def addButton(self, text: str, role: QMessageBox.ButtonRole = QMessageBox.ButtonRole.ActionRole) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("btn_dialog_primary")
        btn.setFixedSize(110, 32)
        result_id = len(self.button_box)
        
        def make_clicked_callback(button_ref):
            def on_clicked(checked=False):
                self._clicked_button = button_ref
            return on_clicked
        
        btn.clicked.connect(make_clicked_callback(btn))
        btn.clicked.connect(lambda checked=False, r=result_id: self.done(r))
        self.button_box.addWidget(btn)
        return btn

    def clickedButton(self) -> Optional[QPushButton]:
        return getattr(self, "_clicked_button", None)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        SimpleDragDialogMixin.mousePressEvent(self, event)
        super(QDialog, self).mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        SimpleDragDialogMixin.mouseMoveEvent(self, event)
        super(QDialog, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        SimpleDragDialogMixin.mouseReleaseEvent(self, event)
        super(QDialog, self).mouseReleaseEvent(event)


# ==========================================
# 2. ModRenameDialog
# ==========================================

CHAR_ID_PATTERN = __import__("re", fromlist=["compile"]).compile(r"[A-Za-z0-9_]+$")
SLIDER_NAME_MAX_LEN = 64
CHAR_NAME_MAX_LEN = 64

class ModRenameDialog(DialogBase):
    def __init__(self, T: "TranslationProxy", parent=None, title: str = "", prompt: str = "", text: str = ""):
        super().__init__(parent)
        self.T = T
        self.setWindowTitle(title)
        self.setMinimumWidth(380)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(title, show_minimize=False, show_maximize=False)
        main_layout.addWidget(self.title_bar)

        content = QWidget()
        content.setStyleSheet(DIALOG_CONTENT_BG)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 14, 16, 10)
        content_layout.setSpacing(8)

        if prompt:
            prompt_label = QLabel(prompt)
            prompt_label.setWordWrap(True)
            prompt_label.setStyleSheet(DIALOG_TEXT_LABEL_STYLE)
            content_layout.addWidget(prompt_label)

        self.text_input = QLineEdit()
        self.text_input.setObjectName("dialog_input")
        self.text_input.setStyleSheet(DIALOG_INPUT_STYLE)
        self.text_input.setText(text)
        self.text_input.returnPressed.connect(lambda: self.done(QDialog.DialogCode.Accepted))
        content_layout.addWidget(self.text_input)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        def make_btn(btn_text, result_code):
            b = SmoothHoverButton(btn_text)
            b.setObjectName("btn_base_secondary")
            b.setFixedSize(90, 28)
            b.clicked.connect(lambda: self.done(result_code))
            return b

        btn_layout.addWidget(make_btn(self.T["btn_ok"], QDialog.DialogCode.Accepted))
        btn_layout.addWidget(make_btn(self.T["btn_cancel"], QDialog.DialogCode.Rejected))
        content_layout.addLayout(btn_layout)

        main_layout.addWidget(content)

    def text(self) -> str:
        return self.text_input.text().strip()


# ==========================================
# 3. RangeInputDialog
# ==========================================

class RangeInputDialog(DialogBase):
    def __init__(self, T: "TranslationProxy", parent=None, title: str = "", label: str = "", text: str = ""):
        super().__init__(parent)
        self.T = T
        self.setWindowTitle(title)
        self.setMinimumWidth(360)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.title_bar = CustomTitleBar(title, show_minimize=False, show_maximize=False)
        main_layout.addWidget(self.title_bar)
        content = QWidget()
        content.setStyleSheet(DIALOG_CONTENT_BG)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 14, 16, 10)
        content_layout.setSpacing(8)
        if label:
            content_layout.addWidget(QLabel(label))
        self.text_input = QLineEdit()
        self.text_input.setObjectName("dialog_input")
        self.text_input.setStyleSheet(DIALOG_INPUT_STYLE)
        self.text_input.setText(text)
        self.text_input.returnPressed.connect(lambda: self.done(QDialog.DialogCode.Accepted))
        content_layout.addWidget(self.text_input)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        def make_btn(text, result_code):
            b = SmoothHoverButton(text)
            b.setObjectName("btn_base_secondary")
            b.setFixedSize(90, 28)
            b.clicked.connect(lambda: self.done(result_code))
            return b
        btn_layout.addWidget(make_btn(self.T["btn_ok"], QDialog.DialogCode.Accepted))
        btn_layout.addWidget(make_btn(self.T["btn_cancel"], QDialog.DialogCode.Rejected))
        content_layout.addLayout(btn_layout)
        main_layout.addWidget(content)

    def text(self) -> str:
        return self.text_input.text().strip()

    def get_range(self) -> tuple:
        raw = self.text_input.text().strip()
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) != 2:
            raise ValueError("Invalid range format. Expected: min,max")
        return float(parts[0]), float(parts[1])


# ==========================================
# 4. AddSliderDialog
# ==========================================

class AddSliderDialog(DialogBase):
    def __init__(self, T: "TranslationProxy", existing_ids: List[str], char_id: str, parent=None):
        super().__init__(parent)
        self.T = T
        self.char_id = char_id
        self._existing_local_ids: Set[str] = {
            sid.split(".", 1)[-1] for sid in existing_ids if "." in sid
        }
        self._result: Optional[Tuple[str, str, str, float, float]] = None

        self.setWindowTitle(T.get("dlg_add_slider_title", "Add Custom Slider"))
        self.setMinimumWidth(440)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(
            T.get("dlg_add_slider_title", "Add Custom Slider"),
            show_minimize=False, show_maximize=False
        )
        main_layout.addWidget(self.title_bar)

        content = QWidget()
        content.setStyleSheet(DIALOG_CONTENT_BG)
        form_layout = QFormLayout(content)
        form_layout.setContentsMargins(16, 14, 16, 10)
        form_layout.setSpacing(8)

        self.name_edit = QLineEdit()
        self.name_edit.setObjectName("dialog_input")
        self.name_edit.setStyleSheet(DIALOG_INPUT_STYLE)
        self.name_edit.setMaxLength(SLIDER_NAME_MAX_LEN)
        self.name_edit.setPlaceholderText(T.get("dlg_slider_name_placeholder", "Enter slider name..."))
        self.name_edit.returnPressed.connect(self._on_accept)
        form_layout.addRow(T.get("label_slider_name", "Name:"), self.name_edit)

        self.id_edit = QLineEdit()
        self.id_edit.setObjectName("dialog_input")
        self.id_edit.setStyleSheet(DIALOG_INPUT_STYLE)
        self.id_edit.setMaxLength(CHAR_NAME_MAX_LEN)
        self.id_edit.setPlaceholderText(T.get("placeholder_slider_id", "Letters, numbers, underscore only (e.g. breast_size)"))
        self.id_edit.returnPressed.connect(self._on_accept)
        form_layout.addRow(T.get("label_id", "ID:"), self.id_edit)

        self.mesh_edit = QLineEdit()
        self.mesh_edit.setObjectName("dialog_input")
        self.mesh_edit.setStyleSheet(DIALOG_INPUT_STYLE)
        self.mesh_edit.setPlaceholderText(T.get("placeholder_slider_mesh", "Select a target mesh file (.obj or .pac)"))
        self.mesh_edit.returnPressed.connect(self._on_accept)
        btn_browse_mesh = SmoothHoverButton(T.get("btn_browse", "Browse..."))
        btn_browse_mesh.setObjectName("btn_base_secondary")
        btn_browse_mesh.setFixedHeight(28)
        btn_browse_mesh.clicked.connect(self._browse_mesh)
        mesh_row = QHBoxLayout()
        mesh_row.addWidget(self.mesh_edit, stretch=1)
        mesh_row.addWidget(btn_browse_mesh)
        form_layout.addRow(T.get("label_slider_mesh", "Target Mesh:"), mesh_row)

        self.range_edit = QLineEdit()
        self.range_edit.setObjectName("dialog_input")
        self.range_edit.setStyleSheet(DIALOG_INPUT_STYLE)
        self.range_edit.setPlaceholderText(T.get("placeholder_slider_range", "Format: min,max (e.g. -50,150)"))
        self.range_edit.setText("-50,150")
        self.range_edit.returnPressed.connect(self._on_accept)
        form_layout.addRow(T.get("label_slider_range", "Range:"), self.range_edit)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        def make_btn(text, result_code):
            b = SmoothHoverButton(text)
            b.setObjectName("btn_base_secondary")
            b.setFixedSize(90, 28)
            if result_code == QDialog.DialogCode.Accepted:
                b.clicked.connect(self._on_accept)
            else:
                b.clicked.connect(lambda: self.done(result_code))
            return b
        btn_layout.addWidget(make_btn(self.T["btn_ok"], QDialog.DialogCode.Accepted))
        btn_layout.addWidget(make_btn(self.T["btn_cancel"], QDialog.DialogCode.Rejected))
        form_layout.addRow(btn_layout)
        main_layout.addWidget(content)

    def _browse_mesh(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.T.get("dlg_add_slider_select_title", "Select Target Mesh for Slider"),
            "",
            "Mesh Files (*.obj *.pac);;OBJ Files (*.obj);;PAC Files (*.pac)",
        )
        if path:
            self.mesh_edit.setText(path)

    def _on_accept(self):
        try:
            name = self.name_edit.text().strip()
            slider_id = self.id_edit.text().strip()
            mesh_path = self.mesh_edit.text().strip()
            range_text = self.range_edit.text().strip()

            if not name:
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("dlg_slider_name_required", "Slider name is required."))
                return
            if not slider_id:
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("dlg_slider_id_required", "Slider ID is required."))
                return
            if not CHAR_ID_PATTERN.fullmatch(slider_id):
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("dlg_slider_id_invalid", "ID can only contain letters, numbers, and underscores."))
                return
            if slider_id in self._existing_local_ids:
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("char_id_duplicate", "This ID is already in use. Please choose another."))
                return
            if not mesh_path:
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("dlg_slider_mesh_required", "Target mesh file is required."))
                return
            if not os.path.exists(mesh_path):
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("dlg_slider_mesh_not_found", "The specified file does not exist."))
                return
            try:
                parts = [p.strip() for p in range_text.split(",")]
                if len(parts) != 2:
                    raise ValueError()
                vmin, vmax = float(parts[0]), float(parts[1])
                if vmin >= vmax:
                    show_warning(self, self.T.get("msg_error", "Error"), self.T.get("dlg_slider_range_invalid", "Min must be less than max."))
                    return
            except (ValueError, IndexError):
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("dlg_slider_range_format", "Invalid range format. Use: min,max (e.g. -50,150)"))
                return

            full_id = f"{self.char_id}.{slider_id}"
            self._result = (name, full_id, mesh_path, vmin, vmax)
            self.done(QDialog.DialogCode.Accepted)
        except Exception:
            try:
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("msg_error", "An error occurred. Please check your input."))
            except Exception:
                pass

    def get_result(self) -> Optional[Tuple[str, str, str, float, float]]:
        return self._result


# ==========================================
# 5. EditSliderDialog
# ==========================================

class EditSliderDialog(DialogBase):
    def __init__(self, T: "TranslationProxy", existing_ids: List[str], char_id: str,
                 current_name: str, current_id: str, current_mesh: str,
                 current_min: float, current_max: float, parent=None):
        super().__init__(parent)
        self.T = T
        self.char_id = char_id
        current_local = current_id.split(".", 1)[-1] if "." in current_id else current_id
        self._existing_local_ids: Set[str] = {
            sid.split(".", 1)[-1] for sid in existing_ids
            if "." in sid and sid.split(".", 1)[-1] != current_local
        }
        self._result: Optional[Tuple[str, str, str, float, float]] = None

        self.setWindowTitle(T.get("dlg_edit_slider_title", "Edit Slider"))
        self.setMinimumWidth(440)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(
            T.get("dlg_edit_slider_title", "Edit Slider"),
            show_minimize=False, show_maximize=False
        )
        main_layout.addWidget(self.title_bar)

        content = QWidget()
        content.setStyleSheet(DIALOG_CONTENT_BG)
        form_layout = QFormLayout(content)
        form_layout.setContentsMargins(16, 14, 16, 10)
        form_layout.setSpacing(8)

        self.name_edit = QLineEdit(current_name)
        self.name_edit.setObjectName("dialog_input")
        self.name_edit.setStyleSheet(DIALOG_INPUT_STYLE)
        self.name_edit.setMaxLength(SLIDER_NAME_MAX_LEN)
        self.name_edit.setPlaceholderText(T.get("dlg_slider_name_placeholder", "Enter slider name..."))
        self.name_edit.returnPressed.connect(self._on_accept)
        form_layout.addRow(T.get("label_slider_name", "Name:"), self.name_edit)

        self.id_edit = QLineEdit(current_local)
        self.id_edit.setObjectName("dialog_input")
        self.id_edit.setStyleSheet(DIALOG_INPUT_STYLE)
        self.id_edit.setMaxLength(CHAR_NAME_MAX_LEN)
        self.id_edit.setPlaceholderText(T.get("placeholder_slider_id", "Letters, numbers, underscore only (e.g. breast_size)"))
        self.id_edit.returnPressed.connect(self._on_accept)
        form_layout.addRow(T.get("label_id", "ID:"), self.id_edit)

        self.mesh_edit = QLineEdit(current_mesh)
        self.mesh_edit.setObjectName("dialog_input")
        self.mesh_edit.setReadOnly(True)
        self.mesh_edit.setStyleSheet(DIALOG_INPUT_READONLY_STYLE)
        form_layout.addRow(T.get("label_slider_mesh", "Target Mesh:"), self.mesh_edit)

        self.range_edit = QLineEdit(f"{int(current_min)},{int(current_max)}")
        self.range_edit.setObjectName("dialog_input")
        self.range_edit.setStyleSheet(DIALOG_INPUT_STYLE)
        self.range_edit.setPlaceholderText(T.get("placeholder_slider_range", "Format: min,max (e.g. -50,150)"))
        self.range_edit.returnPressed.connect(self._on_accept)
        form_layout.addRow(T.get("label_slider_range", "Range:"), self.range_edit)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        def make_btn(text, result_code):
            b = SmoothHoverButton(text)
            b.setObjectName("btn_base_secondary")
            b.setFixedSize(90, 28)
            if result_code == QDialog.DialogCode.Accepted:
                b.clicked.connect(self._on_accept)
            else:
                b.clicked.connect(lambda: self.done(result_code))
            return b
        btn_layout.addWidget(make_btn(self.T["btn_ok"], QDialog.DialogCode.Accepted))
        btn_layout.addWidget(make_btn(self.T["btn_cancel"], QDialog.DialogCode.Rejected))
        form_layout.addRow(btn_layout)
        main_layout.addWidget(content)

    def _on_accept(self):
        try:
            name = self.name_edit.text().strip()
            slider_id = self.id_edit.text().strip()
            mesh_path = self.mesh_edit.text().strip()
            range_text = self.range_edit.text().strip()

            if not name:
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("dlg_slider_name_required", "Slider name is required."))
                return
            if not slider_id:
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("dlg_slider_id_required", "Slider ID is required."))
                return
            if not CHAR_ID_PATTERN.fullmatch(slider_id):
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("dlg_slider_id_invalid", "ID can only contain letters, numbers, and underscores."))
                return
            if slider_id in self._existing_local_ids:
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("char_id_duplicate", "This ID is already in use. Please choose another."))
                return
            if not mesh_path:
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("dlg_slider_mesh_required", "Target mesh file is required."))
                return
            if not os.path.exists(mesh_path):
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("dlg_slider_mesh_not_found", "The specified file does not exist."))
                return
            try:
                parts = [p.strip() for p in range_text.split(",")]
                if len(parts) != 2:
                    raise ValueError()
                vmin, vmax = float(parts[0]), float(parts[1])
                if vmin >= vmax:
                    show_warning(self, self.T.get("msg_error", "Error"), self.T.get("dlg_slider_range_invalid", "Min must be less than max."))
                    return
            except (ValueError, IndexError):
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("dlg_slider_range_format", "Invalid range format. Use: min,max (e.g. -50,150)"))
                return

            full_id = f"{self.char_id}.{slider_id}"
            self._result = (name, full_id, mesh_path, vmin, vmax)
            self.done(QDialog.DialogCode.Accepted)
        except Exception:
            try:
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("msg_error", "An error occurred. Please check your input."))
            except Exception:
                pass

    def get_result(self) -> Optional[Tuple[str, str, str, float, float]]:
        return self._result


# ==========================================
# 6. AddCharacterDialog
# ==========================================

class AddCharacterDialog(DialogBase):
    def __init__(self, T: "TranslationProxy", existing_ids: List[str], parent=None):
        super().__init__(parent)
        self.T = T
        self.existing_ids = existing_ids
        self._result: Optional[Tuple[str, str, str, str]] = None

        self.setWindowTitle(T.get("char_add_title", "Add Character"))
        self.setMinimumWidth(420)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(
            T.get("char_add_title", "Add Character"),
            show_minimize=False, show_maximize=False
        )
        main_layout.addWidget(self.title_bar)

        content = QWidget()
        content.setStyleSheet(DIALOG_CONTENT_BG)
        form_layout = QFormLayout(content)
        form_layout.setContentsMargins(16, 14, 16, 10)
        form_layout.setSpacing(8)

        self.name_edit = QLineEdit()
        self.name_edit.setObjectName("dialog_input")
        self.name_edit.setStyleSheet(DIALOG_INPUT_STYLE)
        self.name_edit.setMaxLength(CHAR_NAME_MAX_LEN)
        self.name_edit.returnPressed.connect(self._on_accept)
        form_layout.addRow(self.T["label_name"], self.name_edit)

        self.id_edit = QLineEdit()
        self.id_edit.setObjectName("dialog_input")
        self.id_edit.setStyleSheet(DIALOG_INPUT_STYLE)
        self.id_edit.setMaxLength(CHAR_NAME_MAX_LEN)
        self.id_edit.setPlaceholderText(self.T.get("placeholder_char_id", "Letters, numbers, underscore only (e.g. char_01)"))
        self.id_edit.returnPressed.connect(self._on_accept)
        form_layout.addRow(self.T["label_id"], self.id_edit)

        self.pac_edit = QLineEdit()
        self.pac_edit.setObjectName("dialog_input")
        self.pac_edit.setStyleSheet(DIALOG_INPUT_STYLE)
        self.pac_edit.setPlaceholderText(self.T.get("placeholder_pac_path", "Enter PAC file path or click Browse..."))
        self.pac_edit.returnPressed.connect(self._on_accept)
        btn_browse_pac = SmoothHoverButton(self.T["btn_browse"])
        btn_browse_pac.setObjectName("btn_base_secondary")
        btn_browse_pac.setFixedHeight(28)
        btn_browse_pac.clicked.connect(self._browse_pac)
        pac_row = QHBoxLayout()
        pac_row.addWidget(self.pac_edit, stretch=1)
        pac_row.addWidget(btn_browse_pac)
        form_layout.addRow(self.T["label_pac_file"], pac_row)

        self.mod_edit = QLineEdit()
        self.mod_edit.setObjectName("dialog_input")
        self.mod_edit.setStyleSheet(DIALOG_INPUT_STYLE)
        self.mod_edit.setPlaceholderText(self.T.get("placeholder_mod_path", "Example: character\\model\\1_pc\\2_phw\\nude"))
        self.mod_edit.returnPressed.connect(self._on_accept)
        form_layout.addRow(self.T["label_mod_path"], self.mod_edit)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        def make_btn(text, result_code):
            b = SmoothHoverButton(text)
            b.setObjectName("btn_base_secondary")
            b.setFixedSize(90, 28)
            if result_code == QDialog.DialogCode.Accepted:
                b.clicked.connect(self._on_accept)
            else:
                b.clicked.connect(lambda: self.done(result_code))
            return b
        btn_layout.addWidget(make_btn(self.T["btn_ok"], QDialog.DialogCode.Accepted))
        btn_layout.addWidget(make_btn(self.T["btn_cancel"], QDialog.DialogCode.Rejected))
        form_layout.addRow(btn_layout)
        main_layout.addWidget(content)

    def _browse_pac(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.T.get("file_dialog_pac_title", "Select Original PAC"),
            "",
            "PAC Files (*.pac)"
        )
        if path:
            self.pac_edit.setText(path)

    def _on_accept(self):
        try:
            name = self.name_edit.text().strip()
            char_id = self.id_edit.text().strip()
            pac_path = self.pac_edit.text().strip()
            mod_path = self.mod_edit.text().strip()

            if not name or not char_id:
                return
            if not CHAR_ID_PATTERN.fullmatch(char_id):
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("char_id_invalid", "ID can only contain letters, numbers, and underscores."))
                return
            if char_id in self.existing_ids:
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("char_id_duplicate", "This ID is already in use. Please choose another."))
                return
            if not pac_path:
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("pac_required", "PAC file path is required."))
                return
            if not os.path.exists(pac_path):
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("pac_not_found", "The specified PAC file does not exist. Please check the path."))
                return
            if os.path.isdir(pac_path):
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("pac_is_directory", "The specified path is a directory, not a PAC file. Please select a PAC file."))
                return
            if not mod_path:
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("mod_path_required", "Mod path is required and cannot be empty."))
                return

            self._result = (name, char_id, pac_path, mod_path)
            self.done(QDialog.DialogCode.Accepted)
        except Exception:
            try:
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("mod_path_required", "An error occurred while validating input."))
            except Exception:
                pass

    def get_result(self) -> Optional[Tuple[str, str, str, str]]:
        return self._result


# ==========================================
# 7. EditCharacterDialog
# ==========================================

class EditCharacterDialog(DialogBase):
    def __init__(self, T: "TranslationProxy", char_info: Dict[str, Any],
                 existing_ids: List[str], root_dir: str, parent=None):
        super().__init__(parent)
        self.T = T
        self.char_info = char_info
        self.existing_ids = [x for x in existing_ids if x != char_info.get("id")]
        self.root_dir = root_dir
        self._result: Optional[Tuple[str, str, str, str]] = None

        self.setWindowTitle(T.get("char_edit_title", "Edit Character"))
        self.setMinimumWidth(420)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(
            T.get("char_edit_title", "Edit Character"),
            show_minimize=False, show_maximize=False
        )
        main_layout.addWidget(self.title_bar)

        content = QWidget()
        content.setStyleSheet(DIALOG_CONTENT_BG)
        form_layout = QFormLayout(content)
        form_layout.setContentsMargins(16, 14, 16, 10)
        form_layout.setSpacing(8)

        self.name_edit = QLineEdit(char_info.get("name", ""))
        self.name_edit.setObjectName("dialog_input")
        self.name_edit.setStyleSheet(DIALOG_INPUT_STYLE)
        self.name_edit.setMaxLength(CHAR_NAME_MAX_LEN)
        self.name_edit.returnPressed.connect(self._on_accept)
        form_layout.addRow(self.T["label_name"], self.name_edit)

        self.id_edit = QLineEdit(char_info.get("id", ""))
        self.id_edit.setObjectName("dialog_input")
        self.id_edit.setMaxLength(CHAR_NAME_MAX_LEN)
        self.id_edit.setPlaceholderText(self.T.get("placeholder_char_id", "Letters, numbers, underscore only (e.g. char_01)"))
        self.id_edit.setToolTip(self.T.get("char_id_label", "Character ID (English letters, numbers, underscore only):"))
        is_default = char_info.get("is_default", False)
        if not is_default:
            self.id_edit.returnPressed.connect(self._on_accept)
        if is_default:
            self.id_edit.setReadOnly(True)
        self.id_edit.setStyleSheet(
            DIALOG_INPUT_READONLY_STYLE if self.id_edit.isReadOnly() else DIALOG_INPUT_STYLE
        )
        form_layout.addRow(self.T["label_id"], self.id_edit)

        self.pac_edit = QLineEdit(char_info.get("original_pac_path", ""))
        self.pac_edit.setObjectName("dialog_input")
        self.pac_edit.setStyleSheet(DIALOG_INPUT_STYLE)
        self.pac_edit.setPlaceholderText(self.T.get("placeholder_pac_path", "Enter PAC file path or click Browse..."))
        self.pac_edit.returnPressed.connect(self._on_accept)
        btn_browse_pac = SmoothHoverButton(self.T["btn_browse"])
        btn_browse_pac.setObjectName("btn_base_secondary")
        btn_browse_pac.setFixedHeight(28)
        btn_browse_pac.clicked.connect(self._browse_pac)
        pac_row = QHBoxLayout()
        pac_row.addWidget(self.pac_edit, stretch=1)
        pac_row.addWidget(btn_browse_pac)
        form_layout.addRow(self.T["label_pac_file"], pac_row)

        self.mod_edit = QLineEdit(char_info.get("mod_path", "character\\model\\1_pc\\2_phw\\nude"))
        self.mod_edit.setObjectName("dialog_input")
        self.mod_edit.setStyleSheet(DIALOG_INPUT_STYLE)
        self.mod_edit.setPlaceholderText(self.T.get("placeholder_mod_path", "Example: character\\model\\1_pc\\2_phw\\nude"))
        self.mod_edit.returnPressed.connect(self._on_accept)
        form_layout.addRow(self.T["label_mod_path"], self.mod_edit)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        def make_btn(text, result_code):
            b = SmoothHoverButton(text)
            b.setObjectName("btn_base_secondary")
            b.setFixedSize(90, 28)
            if result_code == QDialog.DialogCode.Accepted:
                b.clicked.connect(self._on_accept)
            else:
                b.clicked.connect(lambda: self.done(result_code))
            return b
        btn_layout.addWidget(make_btn(self.T["btn_ok"], QDialog.DialogCode.Accepted))
        btn_layout.addWidget(make_btn(self.T["btn_cancel"], QDialog.DialogCode.Rejected))
        form_layout.addRow(btn_layout)
        main_layout.addWidget(content)

    def _browse_pac(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.T.get("file_dialog_pac_title", "Select Original PAC"),
            "",
            "PAC Files (*.pac)"
        )
        if path:
            self.pac_edit.setText(path)

    def _on_accept(self):
        try:
            name = self.name_edit.text().strip()
            char_id = self.id_edit.text().strip()
            pac_path = self.pac_edit.text().strip()
            mod_path = self.mod_edit.text().strip()

            if not name or not char_id:
                return
            if not CHAR_ID_PATTERN.fullmatch(char_id):
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("char_id_invalid", "ID can only contain letters, numbers, and underscores."))
                return
            if char_id in self.existing_ids:
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("char_id_duplicate", "This ID is already in use. Please choose another."))
                return
            if not pac_path:
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("pac_required", "PAC file path is required."))
                return
            if not os.path.exists(pac_path):
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("pac_not_found", "The specified PAC file does not exist."))
                return
            if os.path.isdir(pac_path):
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("pac_is_directory", "The specified path is a directory, not a PAC file."))
                return
            if not mod_path:
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("mod_path_required", "Mod path is required and cannot be empty."))
                return

            self._result = (name, char_id, pac_path, mod_path)
            self.done(QDialog.DialogCode.Accepted)
        except Exception:
            try:
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("mod_path_required", "An error occurred."))
            except Exception:
                pass

    def get_result(self) -> Optional[Tuple[str, str, str, str]]:
        return self._result


# ==========================================
# 8. UnloadAllOutfitsDialog
# ==========================================

class UnloadAllOutfitsDialog(QDialog, SimpleDragDialogMixin):
    """
    Confirmation dialog for 'Unload All Outfits'.
    Uses the same visual style as DarkMessageBox.
    """

    def __init__(self, T, char_id: str, parent=None):
        super().__init__(parent)
        self.T = T
        self.char_id = char_id
        self._confirmed = False

        self.setModal(True)
        self.setMinimumWidth(360)
        self.setProperty("isDarkMessageBox", True)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setStyleSheet(QSS_STYLESHEET)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title bar
        self.title_bar = CustomTitleBar(
            self._tr("btn_unload_all_outfits", "Unload All Outfits"),
            show_minimize=False,
            show_maximize=False,
        )
        main_layout.addWidget(self.title_bar)

        # Content
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(16, 14, 16, 10)
        content_layout.setSpacing(8)

        # Icon
        self.icon_label = QLabel("⚠")
        self.icon_label.setFixedWidth(28)
        self.icon_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.icon_label.setStyleSheet(DARK_MESSAGEBOX_ICON_LABEL_WARNING_STYLE)

        # Text
        self.text_label = QLabel()
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet(DARK_MESSAGEBOX_TEXT_LABEL_STYLE)

        icon_content_layout = QHBoxLayout()
        icon_content_layout.setSpacing(10)
        icon_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        icon_content_layout.addWidget(self.icon_label)
        icon_content_layout.addWidget(self.text_label, stretch=1)

        content_layout.addLayout(icon_content_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(16, 4, 16, 12)
        btn_layout.addStretch()

        self.btn_yes = SmoothHoverButton(self._tr("btn_yes", "Yes"))
        self.btn_yes.setObjectName("btn_dialog_primary")
        self.btn_yes.setFixedSize(110, 32)
        self.btn_yes.clicked.connect(self._on_yes)

        self.btn_no = SmoothHoverButton(self._tr("btn_no", "No"))
        self.btn_no.setObjectName("btn_dialog_secondary")
        self.btn_no.setFixedSize(110, 32)
        self.btn_no.clicked.connect(lambda: self.done(QDialog.DialogCode.Rejected))

        btn_layout.addWidget(self.btn_yes)
        btn_layout.addWidget(self.btn_no)
        content_layout.addLayout(btn_layout)

        content_widget = QWidget()
        content_widget.setStyleSheet(DARK_MESSAGEBOX_CONTENT_WIDGET_STYLE)
        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget)

        # Set message text
        msg = self._tr(
            "unload_all_outfits_confirm",
            "Are you sure you want to unload all Outfits for this character?\n"
            "This will delete all contents under:\n"
            "original_outfit/{char_id}\n"
            "exported_outfit/{char_id}",
        ).format(char_id=self.char_id)

        self.text_label.setText(msg)

        self.setWindowTitle(self._tr("btn_unload_all_outfits", "Unload All Outfits"))

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

    def _on_yes(self):
        self._confirmed = True
        self.done(QDialog.DialogCode.Accepted)

    def is_confirmed(self) -> bool:
        return self._confirmed

    # Drag support
    def mousePressEvent(self, event: QMouseEvent) -> None:
        SimpleDragDialogMixin.mousePressEvent(self, event)
        super(QDialog, self).mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        SimpleDragDialogMixin.mouseMoveEvent(self, event)
        super(QDialog, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        SimpleDragDialogMixin.mouseReleaseEvent(self, event)
        super(QDialog, self).mouseReleaseEvent(event)


# ==========================================
# 9. CharacterSortDialog
# ==========================================

class CharacterSortRow(QWidget):
    def __init__(self, T: "TranslationProxy", name: str, char_id: str, parent=None):
        super().__init__(parent)
        self.T = T
        self.char_id = char_id
        self.setMinimumHeight(32)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(8)

        self.lbl_name = QLabel(name)
        self.lbl_name.setStyleSheet(SORT_ROW_NAME_LABEL_STYLE)
        self.setStyleSheet(SORT_ROW_WIDGET_STYLE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_name.setToolTip(name)

        self.lbl_id = QLabel(char_id)
        self.lbl_id.setStyleSheet(SORT_ROW_ID_LABEL_STYLE)
        self.lbl_id.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        self.lbl_id.setToolTip(char_id)

        layout.addWidget(self.lbl_name, stretch=1)
        layout.addWidget(self.lbl_id, stretch=0)

        self._scroll_timer: Optional[QTimer] = None
        self._scroll_pos = 0
        self._scroll_dir = 1
        self.installEventFilter(self)

    def eventFilter(self, obj, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Enter:
            self._start_scroll_if_needed()
        elif event.type() == QEvent.Type.Leave:
            self._stop_scroll()
        return super().eventFilter(obj, event)

    def _start_scroll_if_needed(self):
        self._stop_scroll()
        if not self.lbl_name:
            return
        fm = QFontMetrics(self.lbl_name.font())
        text = self.lbl_name.text() or ""
        if fm.horizontalAdvance(text) <= self.lbl_name.width():
            return
        self._scroll_timer = QTimer(self)
        self._scroll_timer.timeout.connect(self._on_scroll_tick)
        self._scroll_timer.start(30)

    def _on_scroll_tick(self):
        if not self.lbl_name:
            self._stop_scroll()
            return
        text = (self.lbl_name.property("_fullText") or self.lbl_name.text() or "")
        if not text:
            self._stop_scroll()
            return
        if not self.lbl_name.property("_fullText"):
            self.lbl_name.setProperty("_fullText", text)
        fm = QFontMetrics(self.lbl_name.font())
        w = self.lbl_name.width()
        start = self._scroll_pos
        end = start + w
        total = fm.horizontalAdvance(text)
        if end >= total:
            self._scroll_dir = -1
        if start <= 0:
            self._scroll_dir = 1
        self._scroll_pos += self._scroll_dir * 2
        self._scroll_pos = max(0, min(self._scroll_pos, max(0, total - 4)))
        offset_chars = int(self._scroll_pos * len(text) / max(1, total))
        offset_chars = offset_chars % max(1, len(text))
        rotated = text[offset_chars:] + "..." + text[:offset_chars]
        self.lbl_name.setText(fm.elidedText(rotated, QTextOption.ElideRight, w))
        self.lbl_name.setToolTip(text)

    def _stop_scroll(self):
        if self._scroll_timer:
            self._scroll_timer.stop()
            self._scroll_timer = None
        full = self.lbl_name.property("_fullText")
        if full:
            fm = QFontMetrics(self.lbl_name.font())
            self.lbl_name.setText(fm.elidedText(full, QTextOption.ElideMiddle, self.lbl_name.width()))


class CharacterSortDialog(DialogBase):
    def __init__(self, T: "TranslationProxy",
                 char_items: List[Dict[str, str]],
                 parent=None):
        super().__init__(parent)
        self.T = T
        self.char_items = list(char_items)
        self._result: Optional[List[str]] = None

        self.setWindowTitle(self.T.get("dlg_sort_chars_title", "Sort Characters"))
        self.setMinimumSize(360, 260)
        self.resize(420, 380)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.title_bar = CustomTitleBar(
            self.T.get("dlg_sort_chars_title", "Sort Characters"),
            show_minimize=False,
            show_maximize=False
        )
        root.addWidget(self.title_bar)

        content = QWidget()
        content.setStyleSheet("QWidget { background-color: #2a1d18; }")
        lay = QVBoxLayout(content)
        lay.setContentsMargins(10, 8, 10, 10)
        lay.setSpacing(6)

        hint = QLabel(self.T.get("dlg_sort_chars_hint", "Drag to reorder characters"))
        hint.setStyleSheet(
            "QLabel { color: #a98c77; font-size: 12px; padding: 0; margin: 0; }"
        )
        lay.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(BORDERED_SCROLL_STYLE)

        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("QWidget { background: transparent; }")
        self.rows_layout = QVBoxLayout(scroll_widget)
        self.rows_layout.setContentsMargins(2, 2, 2, 2)
        self.rows_layout.setSpacing(2)
        scroll.setWidget(scroll_widget)
        lay.addWidget(scroll, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        def make_btn(text, role):
            b = SmoothHoverButton(text)
            b.setObjectName("btn_base_secondary")
            b.setFixedSize(90, 28)
            if role == QDialog.DialogCode.Accepted:
                b.clicked.connect(self._on_accept)
            else:
                b.clicked.connect(lambda: self.done(QDialog.DialogCode.Rejected))
            return b

        btn_ok = make_btn(self.T["btn_ok"], QDialog.DialogCode.Accepted)
        btn_cancel = make_btn(self.T["btn_cancel"], QDialog.DialogCode.Rejected)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        lay.addLayout(btn_row)

        root.addWidget(content)

        self.rows: List[CharacterSortRow] = []
        for item in self.char_items:
            row = CharacterSortRow(self.T, item["name"], item["id"])
            self.rows_layout.addWidget(row)
            self.rows.append(row)

        self._drag_start_pos: Optional[QPoint] = None
        self._drag_row: Optional[CharacterSortRow] = None
        self._drag_index: int = -1
        self._dragging = False
        self._scroll_timer = QTimer(self)
        self._scroll_timer.setInterval(20)
        self._scroll_timer.timeout.connect(self._auto_scroll_while_drag)

        scroll_widget.installEventFilter(self)
        self.register_widgets_for_resize([content, self.title_bar, scroll, scroll_widget])

    def eventFilter(self, obj, event: QEvent) -> bool:
        if hasattr(self, "rows_layout") and self.rows_layout is not None:
            scroll_widget = self.rows_layout.parentWidget()
            if obj is scroll_widget and event.type() in (QEvent.Type.MouseMove, QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
                if self._handle_mouse_event(obj, event):
                    return True
        return super().eventFilter(obj, event)

    def _handle_mouse_event(self, obj, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() != Qt.MouseButton.LeftButton:
                return False
            pos = event.pos()
            idx = self._index_at(pos)
            if idx is not None:
                self._drag_start_pos = pos
                self._drag_index = idx
                self._drag_row = self.rows[idx]
                self._dragging = False
            return True

        if event.type() == QEvent.Type.MouseMove:
            if self._drag_start_pos is None:
                return False
            pos = event.pos()
            if not self._dragging:
                dx = pos.x() - self._drag_start_pos.x()
                dy = pos.y() - self._drag_start_pos.y()
                if (dx * dx + dy * dy) > 9:
                    self._dragging = True
                    self._drag_start_pos = pos
                    self._scroll_timer.start()
            if self._dragging and self._drag_row is not None:
                target_idx = self._index_at(pos)
                if target_idx is not None and target_idx != self._drag_index:
                    self.move_row(self._drag_index, target_idx)
            return True

        if event.type() == QEvent.Type.MouseButtonRelease:
            if event.button() == Qt.MouseButton.LeftButton:
                self._scroll_timer.stop()
                self._dragging = False
                self._drag_row = None
                self._drag_index = -1
                self._drag_start_pos = None
            return True

        return False

    def _auto_scroll_while_drag(self):
        if not self._dragging or self._drag_start_pos is None:
            return
        scroll_area = self.findChild(QScrollArea)
        if not scroll_area:
            return
        viewport = scroll_area.viewport()
        global_pos = self.mapToGlobal(self._drag_start_pos)
        vp_pos = viewport.mapFromGlobal(global_pos)
        h = viewport.height()
        bar = scroll_area.verticalScrollBar()
        val = bar.value()
        margin = 20
        step = 8
        if vp_pos.y() <= margin:
            bar.setValue(val - step)
        elif vp_pos.y() >= h - margin:
            bar.setValue(val + step)

    def _index_at(self, pos: QPoint) -> int:
        for i, row in enumerate(self.rows):
            rect = row.geometry()
            if rect.contains(pos):
                return i
        return -1

    def move_row(self, from_idx: int, to_idx: int):
        if from_idx < 0 or to_idx < 0 or from_idx == to_idx:
            return
        if to_idx >= len(self.rows):
            to_idx = len(self.rows) - 1
        row = self.rows.pop(from_idx)
        item = self.char_items.pop(from_idx)
        self.rows.insert(to_idx, row)
        self.char_items.insert(to_idx, item)
        while self.rows_layout.count():
            self.rows_layout.takeAt(0)
        for r in self.rows:
            self.rows_layout.addWidget(r)
        self._drag_index = to_idx

    def _on_accept(self):
        self._result = [item["id"] for item in self.char_items]
        self.done(QDialog.DialogCode.Accepted)

    def get_result(self) -> Optional[List[str]]:
        return self._result

    def get_order(self) -> Optional[List[str]]:
        return self._result


# ==========================================
# 9. Pack Dialogs
# ==========================================

class PackDialogRadioButton(QRadioButton):
    """Styled radio button with custom-drawn circular indicator for pack dialogs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setObjectName("PackDialogRadioButton")

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QPen, QBrush
        from PyQt6.QtCore import QRect

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        p.save()
        rect = self.rect()
        indicator_size = PACK_RADIO_INDICATOR_SIZE
        text_rect = rect.adjusted(indicator_size + 6, 0, 0, 0)
        if self.isEnabled():
            p.setPen(QColor(PACK_RADIO_TEXT_COLOR))
        else:
            p.setPen(QColor(PACK_RADIO_TEXT_COLOR_DISABLED))
        p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, self.text())
        p.restore()

        ind_rect = QRect(
            rect.left() + 2,
            rect.center().y() - indicator_size // 2,
            indicator_size,
            indicator_size,
        )

        checked = self.isChecked()

        # Outer ring
        if checked:
            p.setBrush(QBrush(QColor(PACK_RADIO_FILL_CHECKED)))
            p.setPen(QPen(QColor(PACK_RADIO_BORDER_CHECKED), 1))
        else:
            p.setBrush(QBrush(QColor(PACK_RADIO_FILL_UNCHECKED)))
            p.setPen(QPen(QColor(PACK_RADIO_BORDER_UNCHECKED), 1))

        p.drawEllipse(ind_rect)

        # Inner dot when checked
        if checked:
            dot_size = indicator_size - 6
            dot_rect = QRect(
                ind_rect.center().x() - dot_size // 2,
                ind_rect.center().y() - dot_size // 2,
                dot_size,
                dot_size,
            )
            p.setBrush(QBrush(QColor(PACK_RADIO_CHECKMARK_COLOR)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(dot_rect)

        p.end()


class PackDialogStyledCheckBox(QCheckBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setObjectName("PackDialogCheckBox")

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QPen, QBrush
        from PyQt6.QtCore import QRect

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        p.save()
        rect = self.rect()
        indicator_size = 14
        text_rect = rect.adjusted(indicator_size + 6, 0, 0, 0)
        if self.isEnabled():
            p.setPen(QColor("#d9c0aa"))
        else:
            p.setPen(QColor("#6b5b50"))
        p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, self.text())
        p.restore()

        ind_rect = QRect(
            rect.left() + 2,
            rect.center().y() - indicator_size // 2,
            indicator_size,
            indicator_size,
        )

        checked = self.isChecked()

        if checked:
            p.setBrush(QBrush(QColor("#c56d43")))
            p.setPen(QPen(QColor("#c56d43"), 1))
        else:
            p.setBrush(QBrush(QColor("#1b130f")))
            p.setPen(QPen(QColor("#6b4932"), 1))

        p.drawRoundedRect(ind_rect, 3, 3)

        if checked:
            p.setPen(QPen(QColor("#ffffff"), 2, Qt.PenStyle.SolidLine))
            tl = ind_rect.topLeft()
            br = ind_rect.bottomRight()
            cx, cy = ind_rect.center().x(), ind_rect.center().y()
            p.drawLine(tl.x() + 3, cy, cx - 1, br.y() - 3)
            p.drawLine(cx - 1, br.y() - 3, br.x() - 2, tl.y() + 2)

        p.end()


class ImportOverwriteSelectDialog(DialogBase):
    """
    Step 2: For duplicate character IDs, let user choose which to fully overwrite.
    Unchecked characters will go into Merge flow.
    """
    def __init__(
        self,
        duplicate_chars: List[Dict[str, str]],
        T: "TranslationProxy",
        parent=None,
    ):
        """
        :param duplicate_chars: list of {char_id, pack_name, existing_name}
        """
        super().__init__(parent)
        self.T = T
        self.duplicate_chars = duplicate_chars
        self._drag_pos = None
        self._checkboxes: Dict[str, QCheckBox] = {}

        self.setStyleSheet(QSS_STYLESHEET)
        self.setMinimumWidth(360)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title bar
        title_bar = QWidget()
        title_bar.setObjectName("PackDialogTitleBar")
        title_bar.setFixedHeight(32)

        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 0, 4, 0)
        title_layout.setSpacing(6)

        title_label = QLabel(self.T.get("import_overwrite_title", "Overwrite or Merge Characters"))
        title_label.setObjectName("PackDialogTitleLabel")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(22, 22)
        btn_close.setObjectName("PackDialogCloseButton")
        btn_close.clicked.connect(self.reject)
        title_layout.addWidget(btn_close)

        main_layout.addWidget(title_bar)

        # Content
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 10, 14, 10)
        content_layout.setSpacing(6)

        info_label = QLabel(
            self.T.get(
                "import_overwrite_msg",
                "For each character that already exists, choose whether to fully overwrite it "
                "(all existing data will be lost) or merge sliders later.\n\n"
                "- Checked: fully overwrite this character.\n"
                "- Unchecked: merge sliders (you will choose which ones to keep)."
            )
        )
        info_label.setObjectName("PackDialogInfoLabel")
        info_label.setWordWrap(True)
        content_layout.addWidget(info_label)

        scroll = QScrollArea()
        scroll.setObjectName("PackDialogScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        for item in self.duplicate_chars:
            char_id = item["char_id"]
            pack_name = item.get("pack_name", char_id)
            existing_name = item.get("existing_name", char_id)

            # Show character names + ID so user can identify each row
            label = f"{existing_name} ({char_id})"
            hint = pack_name
            if hint and hint not in label:
                label += f" <- {hint}"

            row = QHBoxLayout()
            row.setSpacing(8)

            text = self.T.get(
                "import_overwrite_cb",
                "Fully overwrite this character (existing data will be lost)"
            )
            cb = PackDialogStyledCheckBox(label)
            cb.setToolTip(text)
            row.addWidget(cb, stretch=1)

            self._checkboxes[char_id] = cb
            layout.addLayout(row)

        # Overwrite / Merge buttons (above list, right-aligned)
        select_row = QHBoxLayout()
        select_row.setContentsMargins(0, 4, 0, 0)
        select_row.setSpacing(6)
        select_row.addStretch()

        btn_merge_all = QPushButton(self.T.get("import_merge_all", "Merge All"))
        btn_merge_all.setObjectName("PackDialogCancelButton")
        btn_merge_all.setMinimumSize(90, 24)
        btn_merge_all.clicked.connect(
            lambda: [cb.setChecked(False) for cb in self._checkboxes.values()]
        )
        select_row.addWidget(btn_merge_all)

        btn_overwrite_all = QPushButton(self.T.get("import_overwrite_all", "Overwrite All"))
        btn_overwrite_all.setObjectName("PackDialogCancelButton")
        btn_overwrite_all.setMinimumSize(90, 24)
        btn_overwrite_all.clicked.connect(
            lambda: [cb.setChecked(True) for cb in self._checkboxes.values()]
        )
        select_row.addWidget(btn_overwrite_all)
        content_layout.addLayout(select_row)

        scroll.setWidget(widget)
        content_layout.addWidget(scroll)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 4, 0, 0)
        btn_row.setSpacing(8)
        btn_row.addStretch()

        btn_ok = QPushButton(self.T.get("pack_ok", "OK"))
        btn_ok.setObjectName("PackDialogExportButton")
        btn_ok.setMinimumSize(80, 28)
        btn_ok.clicked.connect(self.accept)

        btn_cancel = QPushButton(self.T.get("pack_cancel", "Cancel"))
        btn_cancel.setObjectName("PackDialogCancelButton")
        btn_cancel.setMinimumSize(80, 28)
        btn_cancel.clicked.connect(self.reject)

        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        content_layout.addLayout(btn_row)

        main_layout.addWidget(content, stretch=1)

    def get_overwrite_ids(self) -> Set[str]:
        return {cid for cid, cb in self._checkboxes.items() if cb.isChecked()}


class ImportRenameCharDialog(DialogBase):
    """
    Step 3: When PAC topology is incompatible, require user to choose a new character ID.
    """
    def __init__(
        self,
        original_id: str,
        existing_ids: Set[str],
        T: "TranslationProxy",
        parent=None,
    ):
        super().__init__(parent)
        self.T = T
        self.original_id = original_id
        self.existing_ids = existing_ids
        self.setStyleSheet(QSS_STYLESHEET)
        self.setMinimumWidth(340)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title bar
        title_bar = QWidget()
        title_bar.setObjectName("PackDialogTitleBar")
        title_bar.setFixedHeight(32)

        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 0, 4, 0)
        title_layout.setSpacing(6)

        title_label = QLabel(self.T.get("import_rename_title", "Incompatible Mesh - Rename Character"))
        title_label.setObjectName("PackDialogTitleLabel")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(22, 22)
        btn_close.setObjectName("PackDialogCloseButton")
        btn_close.clicked.connect(self.reject)
        title_layout.addWidget(btn_close)

        main_layout.addWidget(title_bar)

        # Content
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 10, 14, 10)
        content_layout.setSpacing(8)

        info_label = QLabel(
            self.T.get(
                "import_rename_msg",
                "The original mesh of this character is incompatible with the existing one.\n"
                "It must be imported as a new character with a different ID."
            )
        )
        info_label.setObjectName("PackDialogInfoLabel")
        info_label.setWordWrap(True)
        content_layout.addWidget(info_label)

        id_row = QHBoxLayout()
        id_row.setSpacing(6)
        id_label = QLabel(self.T.get("import_rename_id_label", "New character ID:"))
        id_row.addWidget(id_label)

        self.line_id = QLineEdit()
        self.line_id.setPlaceholderText(self.T.get("import_rename_id_hint", "Enter a unique character ID"))
        suggested = original_id + "_import"
        self.line_id.setText(suggested)
        id_row.addWidget(self.line_id)
        content_layout.addLayout(id_row)

        error_label = QLabel("")
        error_label.setObjectName("PackDialogErrorLabel")
        error_label.setStyleSheet("color: #ff6b6b; font-size: 12px;")
        content_layout.addWidget(error_label)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 4, 0, 0)
        btn_row.setSpacing(8)
        btn_row.addStretch()

        btn_ok = QPushButton(self.T.get("pack_ok", "OK"))
        btn_ok.setObjectName("PackDialogExportButton")
        btn_ok.setMinimumSize(80, 28)
        btn_cancel = QPushButton(self.T.get("pack_cancel", "Cancel"))
        btn_cancel.setObjectName("PackDialogCancelButton")
        btn_cancel.setMinimumSize(80, 28)

        def validate():
            new_id = self.line_id.text().strip()
            ok = True
            msg = ""
            if not new_id:
                ok = False
                msg = self.T.get("import_rename_err_empty", "ID cannot be empty.")
            elif not all(c.isalnum() or c == "_" for c in new_id):
                ok = False
                msg = self.T.get(
                    "import_rename_err_invalid",
                    "ID can only contain letters, numbers, and underscores.",
                )
            elif new_id in self.existing_ids:
                ok = False
                msg = self.T.get(
                    "import_rename_err_exists",
                    "This ID is already in use. Please choose another.",
                )
            btn_ok.setEnabled(ok)
            error_label.setText(msg)

        self.line_id.textChanged.connect(validate)

        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        content_layout.addLayout(btn_row)

        main_layout.addWidget(content, stretch=1)

        validate()

    def get_new_id(self) -> str:
        return self.line_id.text().strip()


class SliderMergeDialog(DialogBase):
    """
    Step 4: For characters to be merged, let user choose:
    - For each conflicting slider: keep existing / keep new / keep none
    - For new-only sliders: choose which to import (default all).
    """
    def __init__(
        self,
        merge_chars: List[Dict[str, Any]],
        T: "TranslationProxy",
        parent=None,
    ):
        """
        :param merge_chars: list of:
          {
            char_id: str,
            char_name: str,
            conflict_groups: [
              {
                slider_local_id: str,
                existing_slider: {name, ...},
                new_slider: {name, ...}
              }
            ],
            new_only_sliders: [
              {slider_local_id: str, name: str, ...}
            ]
          }
        """
        super().__init__(parent)
        self.T = T
        self.merge_chars = merge_chars
        self._drag_pos = None

        # Selection storage
        self._conflict_radios: Dict[str, Dict[str, Dict[str, QCheckBox]]] = {}
        self._new_only_checkboxes: Dict[str, Dict[str, QCheckBox]] = {}

        self.setStyleSheet(QSS_STYLESHEET)
        self.setMinimumWidth(420)
        self.setMinimumHeight(300)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title bar
        title_bar = QWidget()
        title_bar.setObjectName("PackDialogTitleBar")
        title_bar.setFixedHeight(32)

        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 0, 4, 0)
        title_layout.setSpacing(6)

        title_label = QLabel(self.T.get("slider_merge_title", "Merge Sliders"))
        title_label.setObjectName("PackDialogTitleLabel")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(22, 22)
        btn_close.setObjectName("PackDialogCloseButton")
        btn_close.clicked.connect(self.reject)
        title_layout.addWidget(btn_close)

        main_layout.addWidget(title_bar)

        # Content
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 10, 14, 10)
        content_layout.setSpacing(6)

        info_label = QLabel(
            self.T.get(
                "slider_merge_msg",
                "For each slider conflict, you can keep the existing one, the new one, or neither.\n"
                "Below that are sliders only in the new pack; choose which to import (default: all)."
            )
        )
        info_label.setObjectName("PackDialogInfoLabel")
        info_label.setWordWrap(True)
        content_layout.addWidget(info_label)

        # Helper: select all conflicts in a given direction ("existing" or "new")
        # "existing": keep only original sliders (uncheck all new-only)
        # "new": fully overwrite with new sliders (check all new-only)
        def select_all_conflicts(choice: str):
            for char_id, conflicts in self._conflict_radios.items():
                for local_id, radios in conflicts.items():
                    for key, rb in radios.items():
                        rb.setChecked(key == choice)
            if choice == "existing":
                # "只保留原有滑块": uncheck all new-only sliders
                for char_id, cbs in self._new_only_checkboxes.items():
                    for cb in cbs.values():
                        cb.setChecked(False)
            elif choice == "new":
                # "全部用新滑块覆盖": check all new-only sliders
                for char_id, cbs in self._new_only_checkboxes.items():
                    for cb in cbs.values():
                        cb.setChecked(True)

        # "只保留原有滑块 / 全部用新滑块覆盖" buttons (top-right, above list)
        helper_row = QHBoxLayout()
        helper_row.setContentsMargins(0, 0, 0, 0)
        helper_row.setSpacing(6)
        helper_row.addStretch()

        btn_all_existing = QPushButton(self.T.get("slider_merge_all_existing", "Keep Only Original"))
        btn_all_existing.setObjectName("PackDialogCancelButton")
        btn_all_existing.setMinimumSize(110, 24)
        btn_all_existing.clicked.connect(lambda: select_all_conflicts("existing"))

        btn_all_new = QPushButton(self.T.get("slider_merge_all_new", "Fully Overwrite with New"))
        btn_all_new.setObjectName("PackDialogCancelButton")
        btn_all_new.setMinimumSize(110, 24)
        btn_all_new.clicked.connect(lambda: select_all_conflicts("new"))

        helper_row.addWidget(btn_all_existing)
        helper_row.addWidget(btn_all_new)
        content_layout.addLayout(helper_row)

        scroll = QScrollArea()
        scroll.setObjectName("PackDialogScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        for ch in merge_chars:
            char_id = ch["char_id"]
            char_name = ch.get("char_name", char_id)

            char_group = QGroupBox(f"{char_name} ({char_id})")
            char_group.setObjectName("PackDialogGroupBox")
            char_layout = QVBoxLayout(char_group)
            char_layout.setContentsMargins(8, 6, 8, 6)
            char_layout.setSpacing(6)

            self._conflict_radios[char_id] = {}
            self._new_only_checkboxes[char_id] = {}

            # Conflict groups
            for cg in ch.get("conflict_groups", []):
                local_id = cg["slider_local_id"]
                ex = cg.get("existing_slider", {})
                nw = cg.get("new_slider", {})

                group = QGroupBox(
                    self.T.get("slider_merge_conflict", "Conflict: ") + local_id
                )
                group.setObjectName("PackDialogGroupBox")
                group_layout = QVBoxLayout(group)
                group_layout.setContentsMargins(6, 4, 6, 4)
                group_layout.setSpacing(2)

                radios: Dict[str, QCheckBox] = {}

                ex_name = ex.get("name", local_id)
                cb_ex = PackDialogStyledCheckBox(
                    self.T.get("slider_merge_keep_existing", "Keep current: {name}").format(name=ex_name)
                )
                cb_ex.setChecked(True)  # default: keep existing
                group_layout.addWidget(cb_ex)
                radios["existing"] = cb_ex

                nw_name = nw.get("name", local_id)
                cb_nw = PackDialogStyledCheckBox(
                    self.T.get("slider_merge_keep_new", "Keep new: {name}").format(name=nw_name)
                )
                group_layout.addWidget(cb_nw)
                radios["new"] = cb_nw

                self._conflict_radios[char_id][local_id] = radios

                # Radio-like behavior: exactly one must be selected
                for src in radios.values():
                    (lambda r: r.toggled.connect(
                        lambda checked, rr=radios, s=r: (
                            [oo.setChecked(False) for oo in rr.values() if oo is not s]
                        ) if checked else (
                            # If this one is unchecked, ensure another is checked
                            (lambda others=[oo for oo in rr.values() if oo is not s]:
                               None if any(oo.isChecked() for oo in others)
                               else others[0].setChecked(True)
                            )()
                        )
                    ))(src)

                # Ensure at least one is checked by default
                if not any(rb.isChecked() for rb in radios.values()):
                    radios["existing"].setChecked(True)

                char_layout.addWidget(group)

            # New-only sliders
            new_only = ch.get("new_only_sliders", [])
            if new_only:
                no_group = QGroupBox(
                    self.T.get("slider_merge_new_only", "New sliders (only in imported pack)")
                )
                no_group.setObjectName("PackDialogGroupBox")
                no_layout = QVBoxLayout(no_group)
                no_layout.setContentsMargins(6, 4, 6, 4)
                no_layout.setSpacing(2)

                for ns in new_only:
                    local_id = ns["slider_local_id"]
                    name = ns.get("name", local_id)
                    cb = PackDialogStyledCheckBox(name)
                    cb.setChecked(True)
                    no_layout.addWidget(cb)
                    self._new_only_checkboxes[char_id][local_id] = cb

                char_layout.addWidget(no_group)

            layout.addWidget(char_group)

        scroll.setWidget(widget)
        content_layout.addWidget(scroll)

        # OK / Cancel buttons
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 4, 0, 0)
        btn_row.setSpacing(8)
        btn_row.addStretch()

        btn_ok = QPushButton(self.T.get("pack_ok", "OK"))
        btn_ok.setObjectName("PackDialogExportButton")
        btn_ok.setMinimumSize(80, 28)
        btn_ok.clicked.connect(self.accept)

        btn_cancel = QPushButton(self.T.get("pack_cancel", "Cancel"))
        btn_cancel.setObjectName("PackDialogCancelButton")
        btn_cancel.setMinimumSize(80, 28)
        btn_cancel.clicked.connect(self.reject)

        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        content_layout.addLayout(btn_row)

        main_layout.addWidget(content, stretch=1)

    def get_merge_choices(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns:
          {
            char_id: {
              conflicts: {slider_local_id: "existing" | "new" | None},
              new_only: {slider_local_id: bool}
            }
          }
        """
        result: Dict[str, Dict[str, Any]] = {}
        for char_id, conflicts in self._conflict_radios.items():
            char_result: Dict[str, Any] = {"conflicts": {}, "new_only": {}}

            for local_id, radios in conflicts.items():
                chosen = None
                for key, rb in radios.items():
                    if rb.isChecked():
                        chosen = key
                        break
                char_result["conflicts"][local_id] = chosen

            for local_id, cb in self._new_only_checkboxes.get(char_id, {}).items():
                char_result["new_only"][local_id] = cb.isChecked()

            result[char_id] = char_result
        return result


class CharacterPackLoadDialog(DialogBase):
    def __init__(
        self,
        pack_char_ids: List[str],
        pack_char_names: Dict[str, str],
        existing_char_ids: Set[str],
        T: "TranslationProxy",
        parent=None,
        pack_outfit_char_ids: Optional[Set[str]] = None,
    ):
        super().__init__(parent)
        self.T = T
        self.pack_char_ids = pack_char_ids
        self.pack_char_names = pack_char_names or {}
        self.existing_char_ids = existing_char_ids or set()
        self.pack_outfit_char_ids = pack_outfit_char_ids or set()
        self._checkboxes: Dict[str, "PackDialogStyledCheckBox"] = {}

        self.setStyleSheet(QSS_STYLESHEET)
        self.setMinimumWidth(400)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        title_bar = QWidget()
        title_bar.setObjectName("PackDialogTitleBar")
        title_bar.setFixedHeight(32)

        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 0, 4, 0)
        title_layout.setSpacing(6)

        title_label = QLabel(self.T.get("pack_load_select_title", "Select Characters to Load"))
        title_label.setObjectName("PackDialogTitleLabel")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(22, 22)
        btn_close.setObjectName("PackDialogCloseButton")
        btn_close.clicked.connect(self.reject)
        title_layout.addWidget(btn_close)

        main_layout.addWidget(title_bar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 10, 14, 10)
        content_layout.setSpacing(6)

        info_label = QLabel(
            self.T.get("pack_load_select_msg",
                       "Select one or more characters from the pack to import.")
        )
        info_label.setObjectName("PackDialogInfoLabel")
        info_label.setWordWrap(True)
        content_layout.addWidget(info_label)

        select_all_row = QHBoxLayout()
        select_all_row.setContentsMargins(0, 0, 0, 0)
        select_all_row.setSpacing(4)
        select_all_row.addStretch()

        btn_select_none = QPushButton(self.T.get("pack_select_none", "Select None"))
        btn_select_none.setObjectName("PackDialogCancelButton")
        btn_select_none.setMinimumSize(80, 24)
        btn_select_none.clicked.connect(
            lambda: [cb.setChecked(False) for cb in self._checkboxes.values()]
        )
        select_all_row.addWidget(btn_select_none)

        btn_select_all = QPushButton(self.T.get("pack_select_all", "Select All"))
        btn_select_all.setObjectName("PackDialogCancelButton")
        btn_select_all.setMinimumSize(80, 24)
        btn_select_all.clicked.connect(
            lambda: [cb.setChecked(True) for cb in self._checkboxes.values()]
        )
        select_all_row.addWidget(btn_select_all)
        content_layout.addLayout(select_all_row)

        check_scroll = QScrollArea()
        check_scroll.setObjectName("PackDialogScrollArea")
        check_scroll.setWidgetResizable(True)
        check_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        check_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        check_widget = QWidget()
        check_layout = QVBoxLayout(check_widget)
        check_layout.setContentsMargins(8, 6, 8, 6)
        check_layout.setSpacing(3)
        check_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        for cid in self.pack_char_ids:
            name = (self.pack_char_names or {}).get(cid, cid)
            is_existing = cid in self.existing_char_ids
            has_outfit = cid in self.pack_outfit_char_ids

            row = QHBoxLayout()
            row.setSpacing(8)

            cb = PackDialogStyledCheckBox(name)
            cb.setChecked(True)
            self._checkboxes[cid] = cb
            row.addWidget(cb, stretch=1)

            # Show tags for existing/outfit
            if is_existing or has_outfit:
                tags_layout = QHBoxLayout()
                tags_layout.setSpacing(4)

                if is_existing:
                    tag = QLabel(self.T.get("pack_load_existing", "will overwrite"))
                    tag.setStyleSheet(
                        f"QLabel {{ color: {COLOR_ACCENT_HOT}; font-size: 11px; font-weight: bold; "
                        f"background: rgba(240,123,97,0.12); padding: 2px 6px; border-radius: 3px; "
                        f"border: 1px solid rgba(240,123,97,0.3); }}"
                    )
                    tags_layout.addWidget(tag)

                if has_outfit:
                    tag = QLabel("\U0001f455 Outfit")
                    tag.setStyleSheet(
                        f"QLabel {{ color: {COLOR_ACCENT_LIGHT}; font-size: 11px; font-weight: bold; "
                        f"background: rgba(217,138,79,0.12); padding: 2px 6px; border-radius: 3px; "
                        f"border: 1px solid rgba(217,138,79,0.3); }}"
                    )
                    tags_layout.addWidget(tag)

                row.addLayout(tags_layout)

            check_layout.addLayout(row)

        check_scroll.setWidget(check_widget)
        content_layout.addWidget(check_scroll)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 4, 0, 0)
        btn_row.setSpacing(8)
        btn_row.addStretch()

        btn_ok = QPushButton(self.T.get("pack_load_ok", "Load"))
        btn_ok.setObjectName("PackDialogExportButton")
        btn_ok.setMinimumSize(80, 28)

        btn_cancel = QPushButton(self.T.get("pack_cancel", "Cancel"))
        btn_cancel.setObjectName("PackDialogCancelButton")
        btn_cancel.setMinimumSize(80, 28)

        def update_ok():
            any_checked = any(cb.isChecked() for cb in self._checkboxes.values())
            btn_ok.setEnabled(any_checked)

        for cb in self._checkboxes.values():
            cb.toggled.connect(update_ok)

        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        content_layout.addLayout(btn_row)

        main_layout.addWidget(content, stretch=1)

        update_ok()

    def get_selected_ids(self) -> List[str]:
        return [cid for cid, cb in self._checkboxes.items() if cb.isChecked()]


class PackConflictResolveDialog(DialogBase):
    def __init__(
        self,
        conflict_groups: Dict[str, List[Tuple[str, str]]],
        T: "TranslationProxy",
        parent=None,
    ):
        super().__init__(parent)
        self.T = T
        self.conflict_groups = conflict_groups
        self._drag_pos = None
        self._radio_buttons: Dict[str, Dict[str, QCheckBox]] = {}
        self._selected: Dict[str, str] = {}

        self.setStyleSheet(QSS_STYLESHEET)
        self.setMinimumWidth(360)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        title_bar = QWidget()
        title_bar.setObjectName("PackDialogTitleBar")
        title_bar.setFixedHeight(32)

        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 0, 4, 0)
        title_layout.setSpacing(6)

        title_label = QLabel(self.T.get("pack_conflict_title", "Resolve Conflicts"))
        title_label.setObjectName("PackDialogTitleLabel")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(22, 22)
        btn_close.setObjectName("PackDialogCloseButton")
        btn_close.clicked.connect(self.reject)
        title_layout.addWidget(btn_close)

        main_layout.addWidget(title_bar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 10, 14, 10)
        content_layout.setSpacing(6)

        info_label = QLabel(
            self.T.get(
                "pack_conflict_msg",
                "Some characters share the same in-game identity (same PAC file and Mod Path). "
                "For each group, select exactly one character to include in the MOD."
            )
        )
        info_label.setObjectName("PackDialogInfoLabel")
        info_label.setWordWrap(True)
        content_layout.addWidget(info_label)

        check_scroll = QScrollArea()
        check_scroll.setObjectName("PackDialogScrollArea")
        check_scroll.setWidgetResizable(True)
        check_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        check_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        check_widget = QWidget()
        check_layout = QVBoxLayout(check_widget)
        check_layout.setContentsMargins(8, 6, 8, 6)
        check_layout.setSpacing(8)
        check_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        for key, chars in self.conflict_groups.items():
            group = QGroupBox(self.T.get("pack_conflict_group", "Conflict Group"))
            group.setObjectName("PackDialogGroupBox")
            group_layout = QVBoxLayout(group)
            group_layout.setContentsMargins(8, 6, 8, 6)
            group_layout.setSpacing(3)

            radios: Dict[str, QCheckBox] = {}
            for char_id, char_name in chars:
                rb = PackDialogStyledCheckBox(char_name)
                group_layout.addWidget(rb)
                radios[char_id] = rb

            self._radio_buttons[key] = radios

            for char_id, rb in radios.items():
                (lambda cid, r: r.toggled.connect(
                    lambda checked, c=cid, rr=radios:
                    [rr[oid].setChecked(False) for oid in rr if oid != c and rr[oid].isChecked()]
                    if checked else None
                ))(char_id, rb)

            check_layout.addWidget(group)

        check_scroll.setWidget(check_widget)
        content_layout.addWidget(check_scroll)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 4, 0, 0)
        btn_row.setSpacing(8)
        btn_row.addStretch()

        btn_ok = QPushButton(self.T.get("pack_ok", "OK"))
        btn_ok.setObjectName("PackDialogExportButton")
        btn_ok.setMinimumSize(80, 28)

        btn_cancel = QPushButton(self.T.get("pack_cancel", "Cancel"))
        btn_cancel.setObjectName("PackDialogCancelButton")
        btn_cancel.setMinimumSize(80, 28)

        def update_ok():
            all_resolved = True
            for key, radios in self._radio_buttons.items():
                any_checked = any(r.isChecked() for r in radios.values())
                if not any_checked:
                    all_resolved = False
                    break
            btn_ok.setEnabled(all_resolved)

        for radios in self._radio_buttons.values():
            for rb in radios.values():
                rb.toggled.connect(update_ok)

        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        content_layout.addLayout(btn_row)

        main_layout.addWidget(content, stretch=1)

        update_ok()

    def get_selection(self) -> Dict[str, str]:
        result = {}
        for key, radios in self._radio_buttons.items():
            for char_id, rb in radios.items():
                if rb.isChecked():
                    result[key] = char_id
                    break
        return result


class OutfitSelectDialog(DialogBase):
    """
    Dialog for selecting which characters should have their outfit data exported.
    Similar structure to CharacterPackSelectDialog.
    Only shows characters that have outfit data (original_outfit/{char_id} exists).
    """
    def __init__(
        self,
        characters_with_outfit: List[str],
        T: "TranslationProxy",
        root_dir: str,
        parent=None,
    ):
        super().__init__(parent)
        self.T = T
        self.characters_with_outfit = characters_with_outfit
        self.root_dir = root_dir
        self._checkboxes: Dict[str, "PackDialogStyledCheckBox"] = {}

        self.setStyleSheet(QSS_STYLESHEET)
        self.setMinimumWidth(320)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        title_bar = QWidget()
        title_bar.setObjectName("PackDialogTitleBar")
        title_bar.setFixedHeight(32)

        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 0, 4, 0)
        title_layout.setSpacing(6)

        title_label = QLabel(self.T.get("outfit_select_title", "Select Characters to Export Outfits"))
        title_label.setObjectName("PackDialogTitleLabel")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(22, 22)
        btn_close.setObjectName("PackDialogCloseButton")
        btn_close.clicked.connect(self.reject)
        title_layout.addWidget(btn_close)

        main_layout.addWidget(title_bar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 10, 14, 10)
        content_layout.setSpacing(6)

        info_label = QLabel(
            self.T.get("outfit_select_msg",
                       "The following characters have outfit data. Check the characters whose outfits you want to include in the pack.")
        )
        info_label.setObjectName("PackDialogInfoLabel")
        info_label.setWordWrap(True)
        content_layout.addWidget(info_label)

        select_all_row = QHBoxLayout()
        select_all_row.setContentsMargins(0, 0, 0, 0)
        select_all_row.setSpacing(4)
        select_all_row.addStretch()

        btn_select_none = QPushButton(self.T.get("pack_select_none", "Select None"))
        btn_select_none.setObjectName("PackDialogCancelButton")
        btn_select_none.setMinimumSize(80, 24)
        btn_select_none.clicked.connect(
            lambda: [cb.setChecked(False) for cb in self._checkboxes.values()]
        )
        select_all_row.addWidget(btn_select_none)

        btn_select_all = QPushButton(self.T.get("pack_select_all", "Select All"))
        btn_select_all.setObjectName("PackDialogCancelButton")
        btn_select_all.setMinimumSize(80, 24)
        btn_select_all.clicked.connect(
            lambda: [cb.setChecked(True) for cb in self._checkboxes.values()]
        )
        select_all_row.addWidget(btn_select_all)
        content_layout.addLayout(select_all_row)

        check_scroll = QScrollArea()
        check_scroll.setObjectName("PackDialogScrollArea")
        check_scroll.setWidgetResizable(True)
        check_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        check_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        check_widget = QWidget()
        check_layout = QVBoxLayout(check_widget)
        check_layout.setContentsMargins(8, 6, 8, 6)
        check_layout.setSpacing(3)
        check_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        for cid in self.characters_with_outfit:
            # Get character name from the directory name or display the char_id
            name = self.T.get("char_id_display_" + cid, cid)
            cb = PackDialogStyledCheckBox(name)
            cb.setChecked(True)  # Default to checked
            self._checkboxes[cid] = cb
            check_layout.addWidget(cb)

        check_scroll.setWidget(check_widget)
        content_layout.addWidget(check_scroll)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 4, 0, 0)
        btn_row.setSpacing(8)
        btn_row.addStretch()

        btn_ok = QPushButton(self.T.get("pack_ok", "OK"))
        btn_ok.setObjectName("PackDialogExportButton")
        btn_ok.setMinimumSize(80, 28)

        btn_cancel = QPushButton(self.T.get("pack_cancel", "Cancel"))
        btn_cancel.setObjectName("PackDialogCancelButton")
        btn_cancel.setMinimumSize(80, 28)

        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        content_layout.addLayout(btn_row)

        main_layout.addWidget(content, stretch=1)

    def get_selected_ids(self) -> List[str]:
        return [cid for cid, cb in self._checkboxes.items() if cb.isChecked()]


class CharacterPackSelectDialog(DialogBase):
    def __init__(
        self,
        characters: Dict[str, Dict[str, Any]],
        active_char_id: Optional[str],
        T: "TranslationProxy",
        parent=None,
    ):
        super().__init__(parent)
        self.T = T
        self.characters = characters
        self.active_char_id = active_char_id
        self._checkboxes: Dict[str, "PackDialogStyledCheckBox"] = {}

        self.setStyleSheet(QSS_STYLESHEET)
        self.setMinimumWidth(320)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        title_bar = QWidget()
        title_bar.setObjectName("PackDialogTitleBar")
        title_bar.setFixedHeight(32)

        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 0, 4, 0)
        title_layout.setSpacing(6)

        title_label = QLabel(self.T.get("pack_multi_select_title", "Select Characters to Pack"))
        title_label.setObjectName("PackDialogTitleLabel")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(22, 22)
        btn_close.setObjectName("PackDialogCloseButton")
        btn_close.clicked.connect(self.reject)
        title_layout.addWidget(btn_close)

        main_layout.addWidget(title_bar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 10, 14, 10)
        content_layout.setSpacing(6)

        info_label = QLabel(
            self.T.get("pack_multi_select_msg",
                       "Select one or more characters to include in the pack.")
        )
        info_label.setObjectName("PackDialogInfoLabel")
        info_label.setWordWrap(True)
        content_layout.addWidget(info_label)

        select_all_row = QHBoxLayout()
        select_all_row.setContentsMargins(0, 0, 0, 0)
        select_all_row.setSpacing(4)
        select_all_row.addStretch()

        btn_select_none = QPushButton(self.T.get("pack_select_none", "Select None"))
        btn_select_none.setObjectName("PackDialogCancelButton")
        btn_select_none.setMinimumSize(80, 24)
        btn_select_none.clicked.connect(
            lambda: [cb.setChecked(False) for cb in self._checkboxes.values()]
        )
        select_all_row.addWidget(btn_select_none)

        btn_select_all = QPushButton(self.T.get("pack_select_all", "Select All"))
        btn_select_all.setObjectName("PackDialogCancelButton")
        btn_select_all.setMinimumSize(80, 24)
        btn_select_all.clicked.connect(
            lambda: [cb.setChecked(True) for cb in self._checkboxes.values()]
        )
        select_all_row.addWidget(btn_select_all)
        content_layout.addLayout(select_all_row)

        check_scroll = QScrollArea()
        check_scroll.setObjectName("PackDialogScrollArea")
        check_scroll.setWidgetResizable(True)
        check_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        check_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        check_widget = QWidget()
        check_layout = QVBoxLayout(check_widget)
        check_layout.setContentsMargins(8, 6, 8, 6)
        check_layout.setSpacing(3)
        check_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        for cid, c in self.characters.items():
            name = c.get("name", cid)
            cb = PackDialogStyledCheckBox(name)
            cb.setChecked(cid == self.active_char_id)
            self._checkboxes[cid] = cb
            check_layout.addWidget(cb)

        check_scroll.setWidget(check_widget)
        content_layout.addWidget(check_scroll)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 4, 0, 0)
        btn_row.setSpacing(8)
        btn_row.addStretch()

        btn_ok = QPushButton(self.T.get("pack_export_ok", "Export"))
        btn_ok.setObjectName("PackDialogExportButton")
        btn_ok.setMinimumSize(80, 28)

        btn_cancel = QPushButton(self.T.get("pack_cancel", "Cancel"))
        btn_cancel.setObjectName("PackDialogCancelButton")
        btn_cancel.setMinimumSize(80, 28)

        def update_ok():
            any_checked = any(cb.isChecked() for cb in self._checkboxes.values())
            btn_ok.setEnabled(any_checked)

        for cb in self._checkboxes.values():
            cb.toggled.connect(update_ok)

        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        content_layout.addLayout(btn_row)

        main_layout.addWidget(content, stretch=1)

        update_ok()

    def get_selected_ids(self) -> List[str]:
        return [cid for cid, cb in self._checkboxes.items() if cb.isChecked()]


# ==========================================
# 10. Dialog helper functions (show_*)
# ==========================================

def show_info(parent, title: str, message: str, T=None) -> None:
    ok_text = T["btn_ok"] if T else "OK"
    dlg = DarkMessageBox(parent)
    dlg.setWindowTitle(title)
    dlg.setText(message)
    dlg.setIcon(QMessageBox.Icon.Information)
    dlg.addButton(ok_text, QMessageBox.ButtonRole.AcceptRole)
    dlg.exec()


def show_warning(parent, title: str, message: str, T=None) -> None:
    ok_text = T["btn_ok"] if T else "OK"
    dlg = DarkMessageBox(parent)
    dlg.setWindowTitle(title)
    dlg.setText(message)
    dlg.setIcon(QMessageBox.Icon.Warning)
    dlg.addButton(ok_text, QMessageBox.ButtonRole.AcceptRole)
    dlg.exec()


def show_critical(parent, title: str, message: str, T=None) -> None:
    ok_text = T["btn_ok"] if T else "OK"
    dlg = DarkMessageBox(parent)
    dlg.setWindowTitle(title)
    dlg.setText(message)
    dlg.setIcon(QMessageBox.Icon.Critical)
    dlg.addButton(ok_text, QMessageBox.ButtonRole.AcceptRole)
    dlg.exec()


def show_question(parent, title: str, message: str,
                  yes_text: str = "Yes", no_text: str = "No") -> bool:
    dlg = DarkMessageBox(parent)
    dlg.setWindowTitle(title)
    dlg.setText(message)
    dlg.setIcon(QMessageBox.Icon.Question)
    yes_btn = dlg.addButton(yes_text, QMessageBox.ButtonRole.AcceptRole)
    dlg.addButton(no_text, QMessageBox.ButtonRole.RejectRole)
    dlg.exec()
    return dlg.clickedButton() is yes_btn


def show_choice(parent, title: str, message: str,
                choices: List[str]) -> str | None:
    if not choices:
        return None

    dlg = DarkMessageBox(parent)
    dlg.setWindowTitle(title)
    dlg.setText(message)
    dlg.setIcon(QMessageBox.Icon.Question)

    btn_map = {}
    for i, text in enumerate(choices):
        btn = dlg.addButton(text, QMessageBox.ButtonRole.ActionRole)
        btn_map[btn] = text

    dlg.exec()
    clicked = dlg.clickedButton()
    return btn_map.get(clicked, None)