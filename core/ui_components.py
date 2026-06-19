"""
UI Components for Body Slider Pro.
Contains custom widgets, data classes, and UI layout helper functions.
No functional/backend logic.

- Translations (T) and QSS stylesheet (QSS_STYLESHEET) are defined in core.ui_constants.
- Dialog classes are in core.ui_dialogs.
"""

import os
import re
import json
import shutil
from dataclasses import dataclass, field
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
    QSlider,
    QVBoxLayout,
    QWidget,
    QAbstractSpinBox,
    QComboBox,
    QGraphicsOpacityEffect,
    QSizePolicy,
    QTabBar,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QGroupBox,
    QFormLayout,
    QCheckBox,
    QProgressBar,
)
from PyQt6.QtCore import (
    Qt,
    QEvent,
    QPropertyAnimation,
    QEasingCurve,
    QObject,
    QTimer,
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

import core.ui_constants as ui_constants
# Imported constants (extracted to ui_constants.py)
from core.ui_constants import (
    T,
    QSS_STYLESHEET,
    DEFAULT_LANG,
    FONT_FAMILY,
    BTN_WIREFRAME_STYLE,
    LOADING_OVERLAY_ROOT_STYLE,
    LOADING_LABEL_STYLE,
    SPINBOX_STYLE,
    TAB_INACTIVE_CONTAINER_STYLE,
    TAB_INACTIVE_HOVER_CONTAINER_STYLE,
    TAB_ACTIVE_CONTAINER_STYLE,
    TAB_INACTIVE_LABEL_STYLE,
    TAB_INACTIVE_HOVER_LABEL_STYLE,
    TAB_ACTIVE_LABEL_STYLE,
    TAB_DELETE_BUTTON_STYLE,
    CHAR_LABEL_STYLE,
    WARNING_LABEL_STYLE,
    WARNING_LABEL_SMALL_STYLE,
    VIEWER_BOTTOM_BAR_STYLE,
    BTN_RESET_CAM_STYLE,
    TAB_SCROLL_STYLE,
    SORT_SCROLL_STYLE,
    SORT_CONTENT_BG,
    SORT_HINT_STYLE,
    PACK_ROW_STYLE,
    PACK_ROW_NAME_STYLE,
    PACK_ROW_ID_STYLE,
    PACK_ERROR_LABEL_STYLE,
    EXPORT_PROGRESS_DIALOG_MIN_WIDTH,
    EXPORT_PROGRESS_DIALOG_MIN_HEIGHT,
    EXPORT_PROGRESS_TITLE_BAR_STYLE,
    EXPORT_PROGRESS_TITLE_LABEL_STYLE,
    EXPORT_PROGRESS_CLOSE_BUTTON_STYLE,
    EXPORT_PROGRESS_STATUS_LABEL_STYLE,
    EXPORT_PROGRESS_FILENAME_LABEL_STYLE,
    EXPORT_PROGRESS_BAR_STYLE,
    EXPORT_PROGRESS_CANCEL_BUTTON_STYLE,
    EXPORT_PROGRESS_DONE_BUTTON_STYLE,
    COLOR_BG_SURFACE,
)

from core.ui_window_manager import FramelessDialogMixin

# Import dialog classes from ui_dialogs for backward compatibility
from core.ui_dialogs import (
    CharacterPackSelectDialog,
    CharacterPackLoadDialog,
    PackConflictResolveDialog,
    ModRenameDialog,
    DarkMessageBox,
    DialogBase,
    CustomTitleBar,
    AddSliderDialog,
    EditSliderDialog,
    AddCharacterDialog,
    EditCharacterDialog,
    CharacterSortDialog,
    RangeInputDialog,
    PackDialogStyledCheckBox,
    PackDialogRadioButton,
    CharacterSortRow,
    SmoothHoverButton,
    ImportOverwriteSelectDialog,
    ImportRenameCharDialog,
    SliderMergeDialog,
    show_info,
    show_warning,
    show_critical,
    show_question,
    show_choice,
)


# ==========================================
# 1. Constants
# ==========================================

HOVER_ANIM_DURATION = 200
CLICK_DRAG_THRESHOLD = 9

SINGLE_SLIDER_ROW_HEIGHT = 90

DEFAULT_MOD_PATH = "character\\model\\1_pc\\2_phw\\nude"
DEFAULT_PAC_NAME = "cd_phw_00_nude_00_0001_damian.pac"
DEFAULT_CHAR_ID = "damiane"
DEFAULT_CHAR_NAME = "Damiane"

OBJ_FILE_FILTER = "OBJ Files (*.obj)"
PAC_FILE_FILTER = "PAC Files (*.pac)"
MESH_FILE_FILTER = "Mesh Files (*.obj *.pac)"

SLIDER_NAME_MAX_LEN = 64
CHAR_NAME_MAX_LEN = 64
CHAR_ID_PATTERN = re.compile(r"[A-Za-z0-9_]+$")


# ==========================================
# 1b. Default Sliders
# ==========================================

DEFAULT_SLIDERS: Dict[str, Dict[str, Any]] = {
    "damiane.breast_size_type_01": {
        "name_key": "slider_breast_size_type_01",
        "filename": "breast_size_type_01.obj",
        "min": 0.0,
        "max": 100.0,
    },
    "damiane.breast_size_type_02": {
        "name_key": "slider_breast_size_type_02",
        "filename": "breast_size_type_02.obj",
        "min": 0.0,
        "max": 100.0,
    },
    "damiane.breast_height": {
        "name_key": "slider_breast_height",
        "filename": "breast_height.obj",
        "min": -150.0,
        "max": 100.0,
    },
    "damiane.breast_space": {
        "name_key": "slider_breast_space",
        "filename": "breast_space.obj",
        "min": -100.0,
        "max": 100.0,
    },
    "damiane.nipple_erect": {
        "name_key": "slider_nipple_erect",
        "filename": "nipple_erect.obj",
        "min": 0.0,
        "max": 100.0,
    },
    "damiane.nipple_size": {
        "name_key": "slider_nipple_size",
        "filename": "nipple_size.obj",
        "min": -50.0,
        "max": 100.0,
    },
    "damiane.areola_puffy": {
        "name_key": "slider_areola_puffy",
        "filename": "areola_puffy.obj",
        "min": 0.0,
        "max": 100.0,
    },
    "damiane.waist_size": {
        "name_key": "slider_waist_size",
        "filename": "waist_size.obj",
        "min": -100.0,
        "max": 100.0,
    },
    "damiane.hip_width": {
        "name_key": "slider_hip_width",
        "filename": "hip_width.obj",
        "min": -100.0,
        "max": 100.0,
    },
    "damiane.buttock_size": {
        "name_key": "slider_buttock_size",
        "filename": "buttock_size.obj",
        "min": -100.0,
        "max": 100.0,
    },
    "damiane.thigh_size": {
        "name_key": "slider_thigh_size",
        "filename": "thigh_size.obj",
        "min": -100.0,
        "max": 100.0,
    },
    "damiane.calf_size": {
        "name_key": "slider_calf_size",
        "filename": "calf_size.obj",
        "min": -100.0,
        "max": 100.0,
    },
    "damiane.camel_toe": {
        "name_key": "slider_camel_toe",
        "filename": "camel_toe.obj",
        "min": 0.0,
        "max": 150.0,
    },
}


# ==========================================
# 2. Data classes
# ==========================================

@dataclass
class SliderInfo:
    name: str
    min: float
    max: float
    path: str
    current_value: float = 0.0
    is_default: bool = False


@dataclass
class CharacterInfo:
    name: str
    id: str
    is_default: bool = False
    original_pac_path: str = ""
    mod_path: str = DEFAULT_MOD_PATH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "id": self.id,
            "is_default": self.is_default,
            "original_pac_path": self.original_pac_path,
            "mod_path": self.mod_path,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CharacterInfo":
        return cls(
            name=data.get("name", data.get("id", "")),
            id=data.get("id", ""),
            is_default=data.get("is_default", False),
            original_pac_path=data.get("original_pac_path", ""),
            mod_path=data.get("mod_path", DEFAULT_MOD_PATH),
        )


# ==========================================
# 3. Custom widgets (non-dialog)
# ==========================================

class WireframeButton(QPushButton):
    def __init__(self, text: str, parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self._wireframe_on = True
        self.setObjectName("btn_wireframe")
        self.setStyleSheet(BTN_WIREFRAME_STYLE)

    def set_wireframe_on(self, on: bool):
        self._wireframe_on = bool(on)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        cy = rect.center().y()
        cx = rect.left() + 12
        r = 4
        color = QColor("#e07a36")
        if self._wireframe_on:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(QPointF(cx, cy), r, r)
        else:
            painter.setPen(QPen(color, 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), r, r)
        painter.end()


class LoadingAnimationWidget(QWidget):
    def __init__(self, parent=None, transparent: bool = False):
        super().__init__(parent)
        self.setFixedSize(256, 10)
        self.loop_duration = 1400
        self._transparent = transparent
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(4)
        self._elapsed = QElapsedTimer()
        self._elapsed.start()
        self._phase_offset = int(self._elapsed.elapsed())

    def _now(self):
        return int(self._elapsed.elapsed())

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainterPath
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        outer = QRectF(0.0, 0.0, float(w), float(h))
        clip = QPainterPath()
        clip.addRoundedRect(outer, float(h) * 0.5, float(h) * 0.5)
        painter.setClipPath(clip)
        if not self._transparent:
            painter.fillRect(self.rect(), QColor("#211814"))
        track_color = QColor(255, 255, 255, 25)
        margin = 1
        track_rect = QRectF(margin, margin, w - 2 * margin, h - 2 * margin)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(track_rect, h * 0.5, h * 0.5)
        slider_color = QColor("#c56d43")
        t = (self._now() + self._phase_offset) % self.loop_duration
        p = t / float(self.loop_duration)
        p_smooth = p * p * (3.0 - 2.0 * p)
        slider_width_frac = 0.35
        track_w = track_rect.width()
        slider_w = track_w * slider_width_frac
        move_range = track_w + slider_w
        base_x = track_rect.left() + p_smooth * move_range - slider_w
        painter.setBrush(slider_color)
        for offset in (0.0, -move_range):
            x = base_x + offset
            rect = QRectF(x, track_rect.top(), slider_w, track_rect.height())
            painter.drawRoundedRect(rect, h * 0.5, h * 0.5)
        painter.end()


class LoadingOverlay(QWidget):
    def __init__(self, parent: QWidget, text: str = "Loading..."):
        super().__init__(parent)
        self._parent_window = parent

        self.setWindowFlags(
            Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.CustomizeWindowHint
        )
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        parent_geo = parent.geometry()
        self.setGeometry(
            parent_geo.x(),
            parent_geo.y(),
            parent_geo.width(),
            parent_geo.height(),
        )

        self.setStyleSheet(LOADING_OVERLAY_ROOT_STYLE)
        self.setObjectName("LoadingOverlayRoot")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.animation_widget = LoadingAnimationWidget()
        layout.addWidget(self.animation_widget, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.label = QLabel(text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet(LOADING_LABEL_STYLE)
        layout.addWidget(self.label)

        self._closing = False
        self.show()
        self.raise_()
        QTimer.singleShot(0, lambda: (self.update(), self.animation_widget.update()))

    def close(self, on_ready_callback=None):
        if getattr(self, "_closing", False):
            return
        self._closing = True
        if not callable(on_ready_callback):
            super().close()
            return
        def do_ready():
            try:
                on_ready_callback()
            except Exception:
                pass
            QTimer.singleShot(120, lambda: super(LoadingOverlay, self).close())
        QTimer.singleShot(50, do_ready)
        QTimer.singleShot(2000, lambda: super(LoadingOverlay, self).close())

    def update_parent_geometry(self):
        parent = self._parent_window
        if parent:
            geo = parent.geometry()
            self.setGeometry(geo.x(), geo.y(), geo.width(), geo.height())
            self.raise_()


class NonExpandingTabBar(QTabBar):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setExpanding(False)

    def tabSizeHint(self, index):
        return super().tabSizeHint(index)

    def sizeHint(self):
        hint = super().sizeHint()
        total = sum(self.tabSizeHint(i).width() for i in range(self.count())) + 16
        hint.setWidth(total)
        return hint


class ForceWrapLabel(QLabel):
    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWordWrap(True)
        self.set_smart_text(text)

    def set_smart_text(self, text: str) -> None:
        wrapped = "\u200b".join(text[i:i + 5] for i in range(0, len(text), 5))
        self.setText(wrapped)


class NoWheelSlider(QSlider):
    def wheelEvent(self, event):
        event.ignore()


class NoWheelSpinBox(QDoubleSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setStyleSheet(SPINBOX_STYLE)

    def wheelEvent(self, event):
        event.ignore()


class ReadOnlyInputBrowseTrigger(QObject):
    def __init__(self, parent: QObject, on_browse: Callable[[], None]):
        super().__init__(parent)
        self.on_browse = on_browse

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self.on_browse()
            return False
        return super().eventFilter(obj, event)


class TabHoverEventFilter(QObject):
    def __init__(self, container: QWidget, name_lbl: QLabel,
                 char_stack: QStackedWidget, tab_index: int):
        super().__init__(container)
        self.container = container
        self.name_lbl = name_lbl
        self.char_stack = char_stack
        self.tab_index = tab_index

    def eventFilter(self, obj, event):
        try:
            if obj is not self.container:
                return super().eventFilter(obj, event)
            try:
                current = self.char_stack.currentIndex()
            except (RuntimeError, SystemError):
                return False
            is_active = (current == self.tab_index)
            if event.type() == QEvent.Type.Enter:
                if not is_active and hasattr(self.container, "_inactive_hover_style"):
                    self.container.setStyleSheet(self.container._inactive_hover_style)
                if not is_active and hasattr(self.name_lbl, "_inactive_hover_style"):
                    self.name_lbl.setStyleSheet(self.name_lbl._inactive_hover_style)
            elif event.type() == QEvent.Type.Leave:
                if not is_active and hasattr(self.container, "_inactive_style"):
                    self.container.setStyleSheet(self.container._inactive_style)
                if not is_active and hasattr(self.name_lbl, "_inactive_style"):
                    self.name_lbl.setStyleSheet(self.name_lbl._inactive_style)
            return super().eventFilter(obj, event)
        except (RuntimeError, SystemError):
            return False
        except Exception:
            return False


class MissingLabelClickAdapter(QObject):
    def __init__(self, label: QLabel, on_clicked: Callable[[], None]):
        super().__init__(label)
        self.on_clicked = on_clicked
        self._pressed = False
        self._start_pos = None

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            self._pressed = True
            self._start_pos = self._get_pos(event)
            return False
        if event.type() == QEvent.Type.MouseButtonRelease:
            if self._pressed:
                pos = self._get_pos(event)
                start = self._start_pos or pos
                dx = pos.x() - start.x()
                dy = pos.y() - start.y()
                if (dx * dx + dy * dy) < CLICK_DRAG_THRESHOLD:
                    self.on_clicked()
            self._pressed = False
            self._start_pos = None
            return False
        return super().eventFilter(obj, event)

    @staticmethod
    def _get_pos(event):
        return event.globalPosition() if hasattr(event, "globalPosition") else event.globalPos()


# ==========================================
# 4. Multi-language system
# ==========================================

def load_language_file(root_dir: str, lang_code: str) -> Optional[Dict[str, Any]]:
    lang_path = os.path.join(root_dir, "language", f"{lang_code}.json")
    if not os.path.exists(lang_path):
        return None
    try:
        with open(lang_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def scan_available_languages(root_dir: str) -> Dict[str, Dict[str, Any]]:
    languages: Dict[str, Dict[str, Any]] = {}
    lang_dir = os.path.join(root_dir, "language")
    if not os.path.isdir(lang_dir):
        return languages
    for fname in os.listdir(lang_dir):
        if not fname.lower().endswith(".json"):
            continue
        code = fname.lower().removesuffix(".json")
        data = load_language_file(root_dir, code)
        if data is not None:
            languages[code] = data
    return languages


def safe_text(languages: Dict[str, Dict[str, Any]], active_code: str,
              key: str, fallback_value: str = None) -> str:
    if fallback_value is None:
        fallback_value = key
    t = languages.get(active_code)
    if isinstance(t, dict):
        v = t.get(key)
        if v is not None:
            return str(v)
    if active_code != "en":
        en = languages.get("en")
        if isinstance(en, dict):
            v = en.get(key)
            if v is not None:
                return str(v)
    return fallback_value


class TranslationProxy:
    def __init__(self, languages: Dict[str, Dict[str, Any]], current_lang: str):
        self._languages = languages
        self._current_lang = current_lang

    def __getitem__(self, key: str) -> str:
        return safe_text(self._languages, self._current_lang, key)

    def get(self, key: str, fallback: str = "") -> str:
        return safe_text(self._languages, self._current_lang, key, fallback)


# ==========================================
# 5. UI Layout Helper Functions
# ==========================================

def apply_tab_styles(tab_buttons: List[Dict[str, Any]], active_index: int) -> None:
    if not tab_buttons:
        return
    for i, tb in enumerate(tab_buttons):
        container = tb["container"]
        name_lbl = tb["name_lbl"]
        if i == active_index:
            container.setStyleSheet(TAB_ACTIVE_CONTAINER_STYLE)
            name_lbl.setStyleSheet(TAB_ACTIVE_LABEL_STYLE)
        else:
            container.setStyleSheet(TAB_INACTIVE_CONTAINER_STYLE)
            name_lbl.setStyleSheet(TAB_INACTIVE_LABEL_STYLE)


def _qt_object_alive(obj: Any) -> bool:
    if obj is None:
        return False
    try:
        return obj.window() is not None
    except RuntimeError as e:
        if "deleted" in str(e).lower():
            return False
        raise
    except Exception:
        return True


def reposition_overlay_button(interactor: QWidget, btn_reset_cam: QPushButton,
                              btn_wireframe: Optional[QPushButton] = None) -> None:
    if not _qt_object_alive(interactor) or not _qt_object_alive(btn_reset_cam):
        return
    btn_reset_cam.adjustSize()
    pw, ph = interactor.width(), interactor.height()
    margin, spacing = 20, 4
    x_reset = pw - btn_reset_cam.width() - margin
    y_reset = ph - btn_reset_cam.height() - margin
    btn_reset_cam.move(x_reset, y_reset)
    btn_reset_cam.raise_()
    if btn_wireframe and _qt_object_alive(btn_wireframe):
        btn_wireframe.adjustSize()
        x_wire = x_reset - btn_wireframe.width() - spacing
        btn_wireframe.move(x_wire, y_reset)
        btn_wireframe.raise_()


def init_main_splitter_sizes(splitter: QSplitter, is_default_char: bool = False) -> None:
    try:
        if not _qt_object_alive(splitter) or splitter.count() != 2:
            return
        w = splitter.width()
        if w <= 0 or w < 400:
            QTimer.singleShot(50, lambda: init_main_splitter_sizes(splitter, is_default_char))
            return
        left = int(w * 0.33) if is_default_char else int(w * 0.5)
        splitter.setSizes([left, w - left])
    except (RuntimeError, SystemError, Exception):
        pass


def init_slider_splitter_sizes(slider_splitter: QSplitter) -> None:
    try:
        if not _qt_object_alive(slider_splitter) or slider_splitter.count() != 2:
            return
        parent = slider_splitter.parent()
        while parent and not (hasattr(parent, "width") and parent.width() > 300):
            parent = parent.parent()
        panel_width = parent.width() if parent else 800
        if panel_width <= 0:
            panel_width = 800
        half = panel_width // 2
        slider_splitter.setSizes([half, panel_width - half])
    except (RuntimeError, SystemError, Exception):
        pass


def ensure_tab_scroll_widget_size(tab_scroll_widget: QWidget) -> None:
    if not tab_scroll_widget:
        return
    tab_scroll_widget.adjustSize()
    min_size = tab_scroll_widget.minimumSizeHint()
    current_size = tab_scroll_widget.size()
    if current_size.width() < min_size.width():
        tab_scroll_widget.resize(min_size.width(), current_size.height())


def create_top_bar(main_layout: QVBoxLayout, languages: Dict[str, Dict[str, Any]],
                   current_lang: str, on_lang_changed: Callable[[int], None],
                   T: "TranslationProxy" = None) -> QComboBox:
    top_bar = QWidget()
    top_bar_layout = QHBoxLayout(top_bar)
    top_bar_layout.setContentsMargins(8, 4, 8, 2)
    top_bar_layout.setSpacing(6)
    top_bar_layout.addStretch()
    lang_label = QLabel(T["label_language"] if T else "Language:")
    top_bar_layout.addWidget(lang_label)
    lang_combo = QComboBox()
    for code, content in languages.items():
        lang_name = content.get("lang_name", code)
        lang_combo.addItem(lang_name, code)
    idx = lang_combo.findData(current_lang)
    if idx >= 0:
        lang_combo.setCurrentIndex(idx)
    lang_combo.currentIndexChanged.connect(on_lang_changed)
    pal = lang_combo.palette()
    pal.setColor(QPalette.ColorRole.Light, QColor("#f4ddc4"))
    pal.setColor(QPalette.ColorRole.Mid, QColor("#f4ddc4"))
    pal.setColor(QPalette.ColorRole.BrightText, QColor("#f4ddc4"))
    lang_combo.setPalette(pal)
    fm = lang_combo.fontMetrics()
    max_width = 0
    for i in range(lang_combo.count()):
        text = lang_combo.itemText(i)
        w = fm.horizontalAdvance(text) + 20
        if w > max_width:
            max_width = w
    lang_combo.setMinimumWidth(max_width)
    lang_combo.setMaximumWidth(max_width)
    top_bar_layout.addWidget(lang_combo)
    main_layout.addWidget(top_bar)
    return lang_combo


def create_clickable_warning(text: str, tooltip: str, on_click: Callable[[], None]) -> QLabel:
    warn = QLabel(text)
    warn.setStyleSheet(WARNING_LABEL_STYLE)
    warn.setCursor(Qt.CursorShape.PointingHandCursor)
    warn.setToolTip(tooltip)
    warn.installEventFilter(MissingLabelClickAdapter(warn, on_click))
    return warn


def create_slider_row_widget(
    label_text: str, min_v: float, max_v: float, def_v: float,
    missing: bool, T: "TranslationProxy",
    on_value_changed: Callable[[float], None],
    on_edit: Optional[Callable[[], None]] = None,
    on_delete: Optional[Callable[[], None]] = None,
    on_reselect: Optional[Callable[[], None]] = None,
    is_custom: bool = True,
) -> QWidget:
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

    btn_reset = SmoothHoverButton(T["btn_text_reset"])
    btn_reset.setObjectName("btn_base_secondary")
    btn_reset.clicked.connect(lambda: spin.setValue(0.0))
    tools_layout.addWidget(btn_reset)

    if is_custom:
        if on_edit is not None:
            btn_edit = SmoothHoverButton(T["btn_text_edit"])
            btn_edit.setObjectName("btn_base_secondary")
            btn_edit.clicked.connect(on_edit)
            tools_layout.addWidget(btn_edit)
        if on_delete is not None:
            btn_del = SmoothHoverButton(T["btn_text_del"])
            btn_del.setObjectName("btn_del_base")
            btn_del.clicked.connect(on_delete)
            tools_layout.addWidget(btn_del)

    tools_layout.addStretch()
    tools_layout.addWidget(spin)
    tools_layout.addWidget(QLabel("%"))
    row_main_layout.addLayout(tools_layout)

    slider = NoWheelSlider(Qt.Orientation.Horizontal)
    slider.setRange(int(min_v * 100), int(max_v * 100))
    slider.setValue(int(def_v * 100))
    row_main_layout.addWidget(slider)

    slider.valueChanged.connect(
        lambda v: (
            spin.blockSignals(True),
            spin.setValue(v / 100.0),
            spin.blockSignals(False),
            on_value_changed(v / 100.0),
        )
    )
    spin.valueChanged.connect(
        lambda v: (
            slider.blockSignals(True),
            slider.setValue(int(v * 100)),
            slider.blockSignals(False),
            on_value_changed(v),
        )
    )

    if missing and on_reselect is not None:
        warn = create_clickable_warning(
            T["slider_missing_file"],
            T.get("tooltip_slider_missing", "Click to reselect the target mesh file."),
            on_reselect,
        )
        warn.setStyleSheet(WARNING_LABEL_SMALL_STYLE)
        row_main_layout.addWidget(warn)

    return row_widget


def create_char_info_row(
    v_layout: QVBoxLayout, char_name: str, T: "TranslationProxy",
    on_edit: Callable[[], None], has_pac_warning: bool = False,
    on_reselect_pac: Optional[Callable[[], None]] = None,
    on_save_pack: Optional[Callable[[], None]] = None,
    on_load_pack: Optional[Callable[[], None]] = None,
    on_reset_all: Optional[Callable[[], None]] = None,
) -> None:
    char_row = QHBoxLayout()
    prefix = T.get("char_label_prefix", "Character")
    char_label = QLabel(f"{prefix}: {char_name}")
    char_label.setStyleSheet(CHAR_LABEL_STYLE)
    char_row.addWidget(char_label)

    btn_edit_char_panel = SmoothHoverButton(T["btn_edit_char"])
    btn_edit_char_panel.setObjectName("btn_base_secondary")
    btn_edit_char_panel.setFixedHeight(28)
    btn_edit_char_panel.setToolTip(T["tooltip_edit_char"].format(name=char_name))
    btn_edit_char_panel.clicked.connect(on_edit)
    char_row.addWidget(btn_edit_char_panel)

    if on_reset_all is not None:
        btn_reset_all = SmoothHoverButton(T["btn_reset_all"])
        btn_reset_all.setObjectName("btn_base_secondary")
        btn_reset_all.setFixedHeight(28)
        btn_reset_all.setToolTip(T.get("btn_reset_all_tip", "Reset all sliders to default (0)"))
        btn_reset_all.clicked.connect(on_reset_all)
        char_row.addWidget(btn_reset_all)

    if on_save_pack is not None:
        btn_save_pack = SmoothHoverButton(T["btn_save_pack"])
        btn_save_pack.setObjectName("btn_base_secondary")
        btn_save_pack.setFixedHeight(28)
        btn_save_pack.setToolTip(T.get("pack_save_title", "Save/Share Character Pack"))
        btn_save_pack.clicked.connect(on_save_pack)
        char_row.addWidget(btn_save_pack)

    if on_load_pack is not None:
        btn_load_pack = SmoothHoverButton(T["btn_load_pack"])
        btn_load_pack.setObjectName("btn_base_secondary")
        btn_load_pack.setFixedHeight(28)
        btn_load_pack.setToolTip(T.get("pack_load_title", "Load Character Pack"))
        btn_load_pack.clicked.connect(on_load_pack)
        char_row.addWidget(btn_load_pack)

    char_row.addStretch()
    char_row_widget = QWidget()
    char_row_widget.setLayout(char_row)
    v_layout.addWidget(char_row_widget)

    if has_pac_warning and on_reselect_pac is not None:
        warn = create_clickable_warning(
            T["char_missing_pac"],
            T.get("tooltip_pac_missing", "Click to select a new PAC file."),
            on_reselect_pac,
        )
        v_layout.addWidget(warn)


# Aliases for main_window.py imports
ui_init_main_splitter_sizes = init_main_splitter_sizes
ui_init_slider_splitter_sizes = init_slider_splitter_sizes
ui_ensure_tab_scroll_widget_size = ensure_tab_scroll_widget_size


# ============================================
# ExportProgressDialog — Zstd compression progress dialog
# ============================================

class ExportProgressDialog(QDialog, FramelessDialogMixin):
    """
    Modal progress dialog shown during character-pack export with Zstd compression.
    
    Signals:
        cancel_requested  – emitted when user clicks Cancel
    """

    from PyQt6.QtCore import pyqtSignal
    cancel_requested = pyqtSignal()

    def __init__(self, T: "TranslationProxy", parent=None, output_path: str = "", title: str = ""):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setProperty("isDialog", True)
        self.setMinimumSize(
            ui_constants.EXPORT_PROGRESS_DIALOG_MIN_WIDTH,
            ui_constants.EXPORT_PROGRESS_DIALOG_MIN_HEIGHT,
        )
        self._output_path = output_path

        # Initialize frameless dialog behavior from mixin - allow resizing
        self.init_frameless_dialog(resizable=True)

        T = ui_constants.T  # fallback

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Custom title bar (same style as other dialogs) ---
        title_bar = QWidget()
        title_bar.setObjectName("customTitleBar")
        title_bar.setStyleSheet(ui_constants.TITLE_BAR_WIDGET_STYLE)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(12, 8, 8, 8)
        title_layout.setSpacing(8)

        self._title_label = QLabel(title or T.get("export_progress_title", "Export Character Pack"))
        self._title_label.setStyleSheet(ui_constants.TITLE_BAR_TITLE_LABEL_STYLE)
        title_layout.addWidget(self._title_label)
        title_layout.addStretch()

        self._close_btn = QPushButton("✕")
        self._close_btn.setFixedSize(36, 26)
        self._close_btn.setStyleSheet(ui_constants.TITLE_BAR_CLOSE_BUTTON_STYLE)
        self._close_btn.clicked.connect(self._on_close)
        title_layout.addWidget(self._close_btn)

        root.addWidget(title_bar)

        # --- Content area ---
        content = QWidget()
        content.setStyleSheet(ui_constants.DIALOG_CONTENT_BG)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 16, 20, 16)
        content_layout.setSpacing(10)

        # Status label
        self._status_label = QLabel(T.get("export_progress_status_collecting", "Collecting files..."))
        self._status_label.setStyleSheet(ui_constants.EXPORT_PROGRESS_STATUS_LABEL_STYLE)
        content_layout.addWidget(self._status_label)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setStyleSheet(ui_constants.EXPORT_PROGRESS_BAR_STYLE)
        content_layout.addWidget(self._progress_bar)

        # Filename / detail label
        self._detail_label = QLabel("")
        self._detail_label.setStyleSheet(ui_constants.EXPORT_PROGRESS_FILENAME_LABEL_STYLE)
        content_layout.addWidget(self._detail_label)

        content_layout.addStretch()

        # Button row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._cancel_btn = QPushButton(T.get("export_progress_cancel_button", "Cancel"))
        self._cancel_btn.setObjectName("btn_dialog_primary")
        self._cancel_btn.setMinimumHeight(32)
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self._cancel_btn)

        self._open_folder_btn = QPushButton(T.get("export_progress_open_folder_button", "Open Folder"))
        self._open_folder_btn.setObjectName("btn_dialog_secondary")
        self._open_folder_btn.setMinimumHeight(32)
        self._open_folder_btn.setVisible(False)
        self._open_folder_btn.clicked.connect(self._on_open_folder)
        btn_row.addWidget(self._open_folder_btn)

        self._done_btn = QPushButton(T.get("export_progress_done_button", "Done"))
        self._done_btn.setObjectName("btn_dialog_primary")
        self._done_btn.setMinimumHeight(32)
        self._done_btn.setVisible(False)
        self._done_btn.clicked.connect(self.accept)
        btn_row.addWidget(self._done_btn)

        content_layout.addLayout(btn_row)
        root.addWidget(content)

        # Internal state
        self._cancelled = False
        self._total_files = 0
        self._current_file = 0

    # ---- public API ----

    def is_cancelled(self) -> bool:
        return self._cancelled

    def set_total(self, total: int):
        """Set total number of files for file-count progress."""
        self._total_files = total
        self._current_file = 0
        self._progress_bar.setRange(0, max(total, 1))
        self._progress_bar.setValue(0)

    def advance_file(self, filename: str = ""):
        """Advance one file-step and update detail label."""
        self._current_file += 1
        self._progress_bar.setValue(self._current_file)
        if self._total_files > 0 and filename:
            count_text = ui_constants.T.get(
                "export_progress_files_count", "{current}/{total} files"
            ).format(current=self._current_file, total=self._total_files)
            self._detail_label.setText(f"{count_text}  —  {filename}")
        elif filename:
            self._detail_label.setText(filename)

    def set_status(self, text: str):
        """Update the main status text."""
        self._status_label.setText(text)

    def set_progress_percent(self, pct: int):
        """Set progress bar to a percentage (0-100)."""
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(max(0, min(pct, 100)))

    def mark_complete(self, output_path: str = ""):
        """Show Done + Open Folder buttons, hide Cancel, set progress to 100%."""
        self._output_path = output_path
        # Fix: set range to total_files so value=total_files is truly 100%
        self._progress_bar.setRange(0, max(self._total_files, 1))
        self._progress_bar.setValue(self._total_files)
        self._status_label.setText(
            ui_constants.T.get("export_progress_complete", "Export complete!")
        )
        self._cancel_btn.setVisible(False)
        self._open_folder_btn.setVisible(True)
        self._done_btn.setVisible(True)

    # ---- private ----

    def _on_cancel(self):
        self._cancelled = True
        self.cancel_requested.emit()
        self.close()

    def _on_close(self):
        self._cancelled = True
        self.cancel_requested.emit()
        self.close()

    def _on_open_folder(self):
        """Open the folder containing the exported ZIP file and select it."""
        import subprocess
        if self._output_path:
            # Make path absolute
            abs_path = os.path.abspath(self._output_path)
            if os.path.exists(abs_path):
                # Use /select to open folder and highlight the file
                # Using shell=True for reliable Windows explorer behavior
                cmd = f'explorer /select,"{abs_path}"'
                subprocess.Popen(cmd, shell=True)
            else:
                # File doesn't exist yet, open parent folder
                parent_dir = os.path.dirname(abs_path)
                if parent_dir and os.path.exists(parent_dir):
                    subprocess.Popen(f'explorer "{parent_dir}"', shell=True)


def create_slider_group(
    title: str, sliders_data: List[Tuple[str, Dict[str, Any]]],
    T: "TranslationProxy", is_default_group: bool,
    on_value_changed: Callable[[str, float], None],
    on_edit: Callable[[str], None],
    on_delete: Callable[[str], None], on_reselect: Callable[[str], None],
) -> QGroupBox:
    group = QGroupBox(title)
    group_main = QVBoxLayout(group)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll_content = QWidget()
    scroll_layout = QVBoxLayout(scroll_content)
    scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    if not sliders_data:
        if not is_default_group:
            scroll_layout.addWidget(QLabel(T["no_custom"]))
    else:
        for sid, info in sliders_data:
            path = info.get("path", "")
            missing = not path or not os.path.exists(path)
            row = create_slider_row_widget(
                label_text=info["name"],
                min_v=info["min"], max_v=info["max"],
                def_v=info.get("current_value", 0.0),
                missing=missing, T=T,
                on_value_changed=lambda v, s=sid: on_value_changed(s, v),
                on_edit=lambda s=sid: on_edit(s) if not is_default_group else None,
                on_delete=lambda s=sid: on_delete(s) if not is_default_group else None,
                on_reselect=lambda s=sid: on_reselect(s),
                is_custom=not is_default_group,
            )
            scroll_layout.addWidget(row)

    scroll.setWidget(scroll_content)
    group_main.addWidget(scroll)
    return group