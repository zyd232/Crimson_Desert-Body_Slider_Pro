"""
Frameless window management mixin for Body Slider Pro.

Provides:
- Custom title bar (Language combo + window controls)
- Window dragging
- Edge-based resizing and cursor handling
- Resize debouncing with hooks for subclass-specific behavior

Designed to be used as a mixin with QMainWindow-based windows.
"""

from typing import Any, Callable, Dict, List, Optional, Union

from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import (
    Qt,
    QTimer,
    QEvent,
    QPoint,
    QRect,
)
from PyQt6.QtGui import (
    QMouseEvent,
    QPalette,
    QColor,
    QCursor,
    QPixmap,
)
import sys
import os

from core.ui_constants import (
    TITLE_BAR_BG,
    TITLE_LABEL_STYLE,
    TITLE_SEP_STYLE,
    TITLE_SUB_STYLE,
    LANG_LABEL_STYLE,
    WINDOW_CONTROL_STYLE,
    WINDOW_CONTROL_SMALL_STYLE,
    WINDOW_CLOSE_STYLE,
)


class FramelessWindowManagerMixin:
    """
    Mixin for frameless QMainWindow: title bar, drag, edge resize, cursors.
    """

    # -------------------------
    # State initialization
    # -------------------------

    def _init_window_manager_state(self) -> None:
        """
        Initialize frameless window management state.
        Call this from the main window's __init__ instead of
        manually setting _resizing, _resize_debounce_timer, etc.
        """
        self._resizing = False
        self._resize_edge = None
        self._resize_start_pos = None
        self._resize_start_geom = None
        self.resize_grip = 8

        self._3d_resizing = False
        self._resize_debounce_timer = QTimer(self)
        self._resize_debounce_timer.setSingleShot(True)
        self._resize_debounce_timer.setInterval(150)
        self._resize_debounce_timer.timeout.connect(self._on_resize_stable)

    def _init_edge_cursor_timer(self) -> None:
        """
        Initialize edge cursor update timer.
        Call this once after the central widget is ready.
        """
        self._cursor_timer = QTimer(self)
        self._cursor_timer.timeout.connect(self._update_edge_cursor)
        self._cursor_timer.start(40)

    # -------------------------
    # Custom title bar
    # -------------------------

    def _create_custom_title_bar(
        self,
        main_layout: QVBoxLayout,
        languages: Dict[str, Dict[str, Any]],
        current_lang: str,
        on_lang_changed,
    ) -> None:
        """
        Create a custom title bar with:
        - Icon
        - Main title (from self.T['title'])
        - Version (from self.app_version)
        - Language combo
        - Min / Max / Close buttons

        Requirements on host class:
        - self.T: translation proxy
        - self.app_version: str
        """
        title_bar = QWidget()
        title_bar.setFixedHeight(36)
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(10, 0, 10, 0)
        title_bar_layout.setSpacing(6)
        title_bar_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Icon
        icon_label = QLabel()
        icon_label.setFixedWidth(24)
        icon_label.setFixedHeight(24)

        if getattr(sys, "frozen", False):
            icon_root = getattr(sys, "_MEIPASS", getattr(self, "resource_dir", ""))
        else:
            icon_root = getattr(self, "resource_dir", "")

        if icon_root:
            icon_path = os.path.join(icon_root, "core", "assets", "icon.ico")
            if os.path.exists(icon_path):
                pixmap = QPixmap(icon_path).scaled(
                    20, 20,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_bar_layout.addWidget(icon_label)

        # Title
        version = getattr(self, "app_version", "0.0.0")
        main_title = self.T["title"]  # type: ignore[attr-defined]
        title_label = QLabel(main_title)
        title_label.setStyleSheet(TITLE_LABEL_STYLE)
        title_bar_layout.addWidget(title_label)

        sep_label = QLabel(" - ")
        sep_label.setStyleSheet(TITLE_SEP_STYLE)
        title_bar_layout.addWidget(sep_label)

        subtitle_label = QLabel(f"v{version} - by zyd232")
        subtitle_label.setStyleSheet(TITLE_SUB_STYLE)
        title_bar_layout.addWidget(subtitle_label)

        title_bar_layout.addStretch()

        # Language combo
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

        # Expose lang_combo on the window for external access
        self.lang_combo = lang_combo

        lang_label = QLabel("Language:")
        lang_label.setStyleSheet(LANG_LABEL_STYLE)
        title_bar_layout.addWidget(lang_label)
        title_bar_layout.addWidget(lang_combo)

        # Min button
        btn_min = QPushButton("─")
        btn_min.setFixedSize(36, 26)
        btn_min.setStyleSheet(WINDOW_CONTROL_STYLE)
        btn_min.clicked.connect(self.showMinimized)  # type: ignore[attr-defined]
        title_bar_layout.addWidget(btn_min)

        # Max button
        self.btn_max = QPushButton("□")
        self.btn_max.setFixedSize(36, 26)
        self.btn_max.setStyleSheet(WINDOW_CONTROL_SMALL_STYLE)
        self.btn_max.clicked.connect(self.toggle_maximize)
        title_bar_layout.addWidget(self.btn_max)

        # Close button
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(36, 26)
        btn_close.setStyleSheet(WINDOW_CLOSE_STYLE)
        btn_close.clicked.connect(self.close)  # type: ignore[attr-defined]
        title_bar_layout.addWidget(btn_close)

        title_bar.setStyleSheet(TITLE_BAR_BG)
        main_layout.addWidget(title_bar)

    # -------------------------
    # Maximize toggle
    # -------------------------

    def toggle_maximize(self) -> None:
        if self.isMaximized():  # type: ignore[attr-defined]
            self.showNormal()  # type: ignore[attr-defined]
            self.btn_max.setText("□")
        else:
            self.showMaximized()  # type: ignore[attr-defined]
            self.btn_max.setText("❐")

    # -------------------------
    # Mouse events (drag + edge resize)
    # -------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self.isMaximized():  # type: ignore[attr-defined]
            self._resizing = False
            self._resize_edge = None
            return

        pos = event.position()
        cursor_pos = pos.toPoint()

        edge = self._edge_at(cursor_pos)
        if edge:
            self._resizing = True
            self._resize_edge = edge
            self._resize_start_pos = cursor_pos
            self._resize_start_geom = self.geometry()  # type: ignore[attr-defined]
            self._3d_resizing = True
            self._resize_debounce_timer.start()
        else:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()  # type: ignore[attr-defined]
            self._resizing = False
            self._resize_edge = None

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._resizing:
            global_pos = QCursor.pos()
            win_pos = self.mapFromGlobal(global_pos)  # type: ignore[attr-defined]
            start = self._resize_start_pos
            geom = self._resize_start_geom
            dx = win_pos.x() - start.x()
            dy = win_pos.y() - start.y()
            edge = self._resize_edge or ""

            x = geom.x()
            y = geom.y()
            w = geom.width()
            h = geom.height()
            min_w = 600
            min_h = 400

            if "left" in edge:
                new_x = geom.x() + dx
                new_w = geom.x() + geom.width() - new_x
                if new_w >= min_w:
                    x = new_x
                    w = new_w

            if edge in ("right", "bottom_right", "top_right"):
                w = max(min_w, w + dx)

            if "top" in edge:
                new_y = geom.y() + dy
                new_h = geom.y() + geom.height() - new_y
                if new_h >= min_h:
                    y = new_y
                    h = new_h

            if "bottom" in edge:
                h = max(min_h, h + dy)

            self.setGeometry(x, y, w, h)  # type: ignore[attr-defined]
        elif hasattr(self, "_drag_pos"):
            self.move(event.globalPosition().toPoint() - self._drag_pos)  # type: ignore[attr-defined]

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._resizing = False
        self._resize_edge = None
        if hasattr(self, "_drag_pos"):
            del self._drag_pos

    # -------------------------
    # Edge detection & cursor
    # -------------------------

    def _edge_at(self, pos) -> Optional[str]:
        r = self.rect()  # type: ignore[attr-defined]
        g = self.resize_grip
        x = pos.x()
        y = pos.y()
        width = r.width()
        height = r.height()

        if x <= g and y <= g:
            return "top_left"
        if x >= width - g and y <= g:
            return "top_right"
        if x <= g and y >= height - g:
            return "bottom_left"
        if x >= width - g and y >= height - g:
            return "bottom_right"

        if x <= g:
            return "left"
        if x >= width - g:
            return "right"
        if y <= g:
            return "top"
        if y >= height - g:
            return "bottom"
        return None

    @staticmethod
    def _cursor_for_edge(edge: str) -> Qt.CursorShape:
        if edge in ("top_left", "bottom_right"):
            return Qt.CursorShape.SizeFDiagCursor
        if edge in ("top_right", "bottom_left"):
            return Qt.CursorShape.SizeBDiagCursor
        if edge in ("left", "right"):
            return Qt.CursorShape.SizeHorCursor
        if edge in ("top", "bottom"):
            return Qt.CursorShape.SizeVerCursor
        return Qt.CursorShape.ArrowCursor

    def _update_edge_cursor(self) -> None:
        if self.isMaximized() or self._resizing:  # type: ignore[attr-defined]
            return

        global_pos = QCursor.pos()
        win_pos = self.mapFromGlobal(global_pos)  # type: ignore[attr-defined]

        if self.rect().contains(win_pos):  # type: ignore[attr-defined]
            edge = self._edge_at(win_pos)
            if edge:
                self.setCursor(self._cursor_for_edge(edge))  # type: ignore[attr-defined]
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)  # type: ignore[attr-defined]

    # -------------------------
    # ResizeEvent + debounce hooks
    # -------------------------

    def resizeEvent(self, event) -> None:
        # Update maximize button icon
        if hasattr(self, "btn_max"):
            if self.isMaximized():  # type: ignore[attr-defined]
                self.btn_max.setText("❐")
            else:
                self.btn_max.setText("□")

        # No-op if size unchanged
        if event.size() == event.oldSize():
            return

        # If we are actively resizing via edges, use debounce
        if getattr(self, "_resizing", False):
            timer = getattr(self, "_resize_debounce_timer", None)
            if timer is not None:
                timer.start()
            return

        # For other resize events (e.g. external), also debounce 3D updates
        self._3d_resizing = True
        timer = getattr(self, "_resize_debounce_timer", None)
        if timer is not None:
            timer.start()

    def _on_resize_stable(self) -> None:
        """
        Called after resize is stable (debounced).
        Delegates business-logic steps to protected hooks.
        """
        self._3d_resizing = False

        # Hook: update 3D plotter/renderer
        self.on_resize_stable_update_plotter()

        # Hook: persist window size / config
        self.on_resize_stable_save_config()

    # -------------------------
    # Hooks (to be overridden by subclasses)
    # -------------------------

    def on_resize_stable_update_plotter(self) -> None:
        """
        Override in subclass to refresh 3D viewer after resize.
        Default: no-op.
        """
        pass

    def on_resize_stable_save_config(self) -> None:
        """
        Override in subclass to save window geometry / config after resize.
        Default: no-op.
        """
        pass


class FramelessDialogMixin:
    """
    Mixin for frameless QDialog: drag + edge resize + cursor via timer.

    Design:
    - Reuses the same idea as the main window: use a small timer to sample
      global cursor position and decide edge/cursor/resize behavior.
    - This avoids issues where child widgets consume mouse events.
    - Intended usage: DialogBase(QDialog, FramelessDialogMixin)
    """

    def init_frameless_dialog(self, resizable: bool = True, resize_margin: int = 8) -> None:
        """
        Initialize frameless dialog behavior.
        Call from subclass __init__ after super().__init__().
        """
        self._resizable = resizable
        self._resize_margin = resize_margin

        self._drag_pos: Optional[QPoint] = None
        self._resizing = False
        self._resize_edge: Optional[str] = None
        self._resize_start_global: QPoint = QPoint()
        self._resize_start_geom: QRect = QRect()

        self.setMouseTracking(True)

        # Timer-based edge cursor and resize (like main window)
        self._dialog_cursor_timer = QTimer(self)
        self._dialog_cursor_timer.setInterval(30)
        self._dialog_cursor_timer.timeout.connect(self._dialog_update_edge_cursor)
        self._dialog_cursor_timer.start()

    # -------------------------
    # Mouse events (drag + resize start)
    # -------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            edge = self._dialog_edge_at(pos)
            if self._resizable and edge:
                # Start resize from this edge
                self._resizing = True
                self._resize_edge = edge
                self._resize_start_global = event.globalPosition().toPoint()
                self._resize_start_geom = self.geometry()  # type: ignore[attr-defined]
            else:
                # Start drag
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()  # type: ignore[attr-defined]
                self._resizing = False
                self._resize_edge = None

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        # Drag when not resizing
        if not self._resizing and self._drag_pos is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)  # type: ignore[attr-defined]

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            if self._resizing:
                self._resizing = False
                self._resize_edge = None
                self.setCursor(Qt.CursorShape.ArrowCursor)  # type: ignore[attr-defined]

    # -------------------------
    # Edge detection helpers
    # -------------------------

    def _dialog_edge_at(self, pos: QPoint) -> Optional[str]:
        if not self._resizable:
            return None

        margin = self._resize_margin
        rect = self.rect()  # type: ignore[attr-defined]
        x, y = pos.x(), pos.y()
        w, h = rect.width(), rect.height()

        on_left = x <= margin
        on_right = x >= w - margin
        on_top = y <= margin
        on_bottom = y >= h - margin

        if on_top and on_left:
            return "top_left"
        if on_top and on_right:
            return "top_right"
        if on_bottom and on_left:
            return "bottom_left"
        if on_bottom and on_right:
            return "bottom_right"
        if on_left:
            return "left"
        if on_right:
            return "right"
        if on_top:
            return "top"
        if on_bottom:
            return "bottom"
        return None

    @staticmethod
    def _cursor_for_edge(edge: str) -> "Qt.CursorShape":
        if edge in ("top_left", "bottom_right"):
            return Qt.CursorShape.SizeFDiagCursor
        if edge in ("top_right", "bottom_left"):
            return Qt.CursorShape.SizeBDiagCursor
        if edge in ("left", "right"):
            return Qt.CursorShape.SizeHorCursor
        if edge in ("top", "bottom"):
            return Qt.CursorShape.SizeVerCursor
        return Qt.CursorShape.ArrowCursor

    # -------------------------
    # Timer-based cursor and resize (robust across child widgets)
    # -------------------------

    def _dialog_update_edge_cursor(self) -> None:
        # If actively resizing, update geometry continuously based on cursor
        if self._resizing and self._resize_edge:
            global_pos = QCursor.pos()
            delta = global_pos - self._resize_start_global
            geom = self._resize_start_geom
            x, y, w, h = geom.x(), geom.y(), geom.width(), geom.height()

            min_w = self.minimumWidth()  # type: ignore[attr-defined]
            min_h = self.minimumHeight()  # type: ignore[attr-defined]
            edge = self._resize_edge

            # Right
            if "right" in edge:
                w = max(min_w, w + delta.x())
            # Left
            if "left" in edge:
                new_w = max(min_w, w - delta.x())
                if new_w > min_w:
                    x += delta.x()
                    w = new_w

            # Bottom
            if "bottom" in edge:
                h = max(min_h, h + delta.y())
            # Top
            if "top" in edge:
                new_h = max(min_h, h - delta.y())
                if new_h > min_h:
                    y += delta.y()
                    h = new_h

            self.setGeometry(x, y, w, h)  # type: ignore[attr-defined]
            return

        # Otherwise decide cursor shape
        global_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(global_pos)  # type: ignore[attr-defined]
        if not self.rect().contains(local_pos):  # type: ignore[attr-defined]
            # Cursor not over dialog: reset if not resizing
            if not self._resizing:
                self.setCursor(Qt.CursorShape.ArrowCursor)  # type: ignore[attr-defined]
            return

        edge = self._dialog_edge_at(local_pos)
        if edge:
            self.setCursor(self._cursor_for_edge(edge))  # type: ignore[attr-defined]
        else:
            if self.cursor().shape() != Qt.CursorShape.ArrowCursor:  # type: ignore[attr-defined]
                self.setCursor(Qt.CursorShape.ArrowCursor)  # type: ignore[attr-defined]


class SimpleDragDialogMixin:
    """
    Mixin for simple frameless QDialog: drag only, no resize.
    Intended usage: SomeDialog(QDialog, SimpleDragDialogMixin)
    """

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()  # type: ignore[attr-defined]

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if getattr(self, "_drag_pos", None) is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)  # type: ignore[attr-defined]

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_pos = None