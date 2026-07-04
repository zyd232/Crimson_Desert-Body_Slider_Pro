"""
Outfits file-tree widget for Body Slider Pro.

Provides a QTreeWidget-based file browser with:
- Folder/file icons (using Qt style standard icons)
- Path indicator (breadcrumb-style label above the tree)
- Toolbar with Expand All / Collapse All / Select All / Deselect All / Refresh buttons
- Checkboxes on all items (folders auto-check/uncheck based on children)
- Hover & selection styling (via QSS in ui_constants.py)
- Double-click to toggle folder expand/collapse
- Emits signals on item activation (double-click on file)
- Async tree building via FileTreeScannerThread (background thread scan)
- Refresh preserves checked state and activated selection
- Loading overlay during refresh operation with animation widget

Designed to be used by Outfits panel.
"""

import os
from typing import Optional, List, Dict, Any, Set

from PyQt6.QtWidgets import (
    QApplication,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QStyleFactory,
    QFrame,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QEvent, QRect
from PyQt6.QtGui import QFont

from core.ui_constants import SCROLL_BAR_STYLE


class OutfitFileTree(QWidget):
    """
    File-tree widget for Outfits panel.

    Signals:
        itemActivated(filePath: str)
        itemDeactivated(filePath: str)
        itemChecked(filePath: str, checked: bool)
        checkedFilesChanged(checked_count: int, total_files: int)
    """

    itemActivated = pyqtSignal(str)
    itemDeactivated = pyqtSignal(str)
    itemChecked = pyqtSignal(str, bool)
    checkedFilesChanged = pyqtSignal(int, int)

    def __init__(
        self,
        root_dir: str,
        allowed_extensions: tuple = (".pac",),
        parent: Optional[QWidget] = None,
        T=None,
    ):
        super().__init__(parent)
        self.root_dir = os.path.abspath(root_dir)
        self.allowed_extensions = tuple(e.lower() for e in allowed_extensions)
        self._current_activated_path: Optional[str] = None
        self._T = T

        # Tracked file set for incremental updates
        self._file_set: Set[str] = set()

        # Scanner thread reference (for cancellation)
        self._scanner_thread = None

        # Path-to-item map for incremental tree building (batch scanner)
        self._path_to_item: Dict[str, QTreeWidgetItem] = {}

        # Lazy loading state: track which directories have been loaded
        self._loaded_dirs: Set[str] = set()
        # In-progress loaders: {dir_path: thread}
        self._pending_loaders: Dict[str, Any] = {}

        # Import styles from ui_constants
        from core.ui_constants import (
            COLOR_BG_PANEL,
            COLOR_TEXT_DIM,
            COLOR_TEXT_BRIGHT,
            COLOR_ACCENT,
            COLOR_BORDER_ACCENT,
            COLOR_BG_HOVER,
            COLOR_BG_SURFACE,
            BTN_TREE_CONTROL_STYLE,
            BTN_REFRESH_STYLE,
            BTN_SELECT_ALL_STYLE,
            BTN_DESELECT_ALL_STYLE,
            TREE_REFRESH_OVERLAY_STYLE,
            TREE_REFRESH_LABEL_STYLE,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- Path indicator label (breadcrumb) ----
        self._path_label = QLabel()
        self._path_label.setObjectName("OutfitFilePathLabel")
        self._path_label.setStyleSheet(
            f"QLabel#OutfitFilePathLabel {{ "
            f"background-color: transparent; "
            f"color: {COLOR_TEXT_DIM}; "
            f"font-size: 11px; "
            f"padding: 2px 8px; "
            f"border: none; "
            f"}}"
        )
        self._path_label.setWordWrap(False)
        layout.addWidget(self._path_label)

        # ---- Toolbar ----
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(4, 4, 4, 2)
        toolbar.setSpacing(4)

        # Expand All button
        self._btn_expand_all = QPushButton("+")
        self._btn_expand_all.setObjectName("btn_tree_control")
        self._btn_expand_all.setStyleSheet(BTN_TREE_CONTROL_STYLE)
        self._btn_expand_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_expand_all.setFixedSize(18, 18)
        self._btn_expand_all.setToolTip(self._tr("tooltip_tree_expand_all", "Expand All"))
        self._btn_expand_all.clicked.connect(self._on_expand_all)

        # Collapse All button
        self._btn_collapse_all = QPushButton("-")
        self._btn_collapse_all.setObjectName("btn_tree_control")
        self._btn_collapse_all.setStyleSheet(BTN_TREE_CONTROL_STYLE)
        self._btn_collapse_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_collapse_all.setFixedSize(18, 18)
        self._btn_collapse_all.setToolTip(self._tr("tooltip_tree_collapse_all", "Collapse All"))
        self._btn_collapse_all.clicked.connect(self._on_collapse_all)

        # Refresh button - uses "⟳" (U+21B3, Anticlockwise Arrows)
        self._btn_refresh = QPushButton("\u21bb")
        self._btn_refresh.setObjectName("btn_refresh")
        self._btn_refresh.setStyleSheet(BTN_REFRESH_STYLE)
        self._btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_refresh.setFixedSize(18, 18)
        self._btn_refresh.setToolTip(self._tr("tooltip_tree_refresh", "Refresh"))
        self._btn_refresh.clicked.connect(self.refresh_async)

        # Select All button - uses "☑" (U+2611, Ballot Box with Check)
        self._btn_select_all = QPushButton("\u2611")
        self._btn_select_all.setObjectName("btn_select_all")
        self._btn_select_all.setStyleSheet(BTN_SELECT_ALL_STYLE)
        self._btn_select_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_select_all.setFixedSize(18, 18)
        self._btn_select_all.setToolTip(self._tr("tooltip_tree_select_all", "Select All"))
        self._btn_select_all.clicked.connect(self.select_all)

        # Deselect All button - uses "☐" (U+2610, Ballot Box)
        self._btn_deselect_all = QPushButton("\u2610")
        self._btn_deselect_all.setObjectName("btn_deselect_all")
        self._btn_deselect_all.setStyleSheet(BTN_DESELECT_ALL_STYLE)
        self._btn_deselect_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_deselect_all.setFixedSize(18, 18)
        self._btn_deselect_all.setToolTip(self._tr("tooltip_tree_deselect_all", "Deselect All"))
        self._btn_deselect_all.clicked.connect(self.deselect_all)

        toolbar.addWidget(self._btn_expand_all)
        toolbar.addWidget(self._btn_collapse_all)
        toolbar.addWidget(self._btn_refresh)
        toolbar.addWidget(self._btn_select_all)
        toolbar.addWidget(self._btn_deselect_all)
        toolbar.addStretch()

        layout.addLayout(toolbar)

        # ---- QTreeWidget with Fusion style ----
        self._tree = QTreeWidget()
        self._tree.setStyle(QStyleFactory.create('Fusion'))
        self._tree.setHeaderHidden(True)
        self._tree.header().setTextElideMode(Qt.TextElideMode.ElideNone)
        self._tree.setItemsExpandable(True)
        self._tree.setExpandsOnDoubleClick(True)
        self._tree.setIndentation(14)
        self._tree.setSelectionMode(self._tree.SelectionMode.SingleSelection)
        self._tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._tree.setFrameStyle(QFrame.Shape.NoFrame)
        self._tree.setColumnCount(1)
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)

        # Fusion style QSS for checkbox and tree appearance
        self._tree.setStyleSheet("""
            QTreeWidget {
                background-color: #2a1d18;
                color: #d9c0aa;
                border: none;
                outline: none;
                font-size: 12px;
            }
            QTreeWidget::item {
                padding: 2px 4px;
                border: none;
            }
            QTreeWidget::item:selected {
                background-color: #443025;
                color: #f4ddc4;
            }
            QTreeWidget::item:hover {
                background-color: #3e2a20;
            }
            QTreeWidget::branch {
                background-color: transparent;
            }
            QCheckBox {
                spacing: 4px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 2px;
                border: 1px solid #6b4932;
                background-color: #1b130f;
            }
            QCheckBox::indicator:checked {
                background-color: #c56d43;
                border: 1px solid #c56d43;
                image: none;
            }
            QCheckBox::indicator:unchecked:hover {
                border-color: #c56d43;
            }
        """ + SCROLL_BAR_STYLE)

        self._tree.itemChanged.connect(self._on_item_changed)
        self._tree.itemSelectionChanged.connect(self._on_item_selection_changed)
        self._tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._tree.viewport().installEventFilter(self)
        self._tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Debounce timer for column width recalculation
        self._column_width_timer = QTimer(self)
        self._column_width_timer.setSingleShot(True)
        self._column_width_timer.setInterval(150)
        self._column_width_timer.timeout.connect(self._ensure_column_width)
        self._tree.expanded.connect(self._schedule_column_width)
        self._tree.expanded.connect(self._on_directory_expanded)
        self._tree.collapsed.connect(self._schedule_column_width)

        layout.addWidget(self._tree, stretch=1)

        # ---- Loading overlay is created on-demand in _show_tree_loading() ----
        # (Following Outfitter pattern: create new overlay instance each time)
        self._refresh_overlay = None

        # ---- Build tree asynchronously on startup ----
        if os.path.isdir(self.root_dir):
            self._build_tree_async(show_loading=False)
        else:
            self._tree.expandAll()

        self._update_path_label()
        QTimer.singleShot(200, self._ensure_column_width)
        QTimer.singleShot(600, self._ensure_column_width)

    # ------------ translation helper ------------

    def _tr(self, key: str, fallback: str = "") -> str:
        if not self._T:
            return fallback or key
        try:
            if hasattr(self._T, "get"):
                return self._T.get(key, fallback or key)
            if isinstance(self._T, dict):
                return self._T.get(key, fallback or key)
        except Exception:
            pass
        return fallback or key

    # ------------ public helpers ------------

    def set_root_dir(self, root_dir: str):
        self.root_dir = os.path.abspath(root_dir)
        self._current_activated_path = None
        self._file_set.clear()
        self._loaded_dirs.clear()
        self._cancel_all_loaders()
        if os.path.isdir(self.root_dir):
            self._build_tree_async(show_loading=False)
        else:
            self._tree.clear()
            self._tree.expandAll()
        self._update_path_label()
        self._schedule_column_width()

    def get_current_activated_path(self) -> Optional[str]:
        return self._current_activated_path

    # ---- Scanner management ----

    def _cancel_scanner(self):
        """Cancel any running background scanner thread and disconnect signals.
        
        严格按照 Outfitter 项目的实现：不阻塞主线程。
        旧线程会在检查到 _cancelled 标志后自行退出，不需要等待。
        """
        if self._scanner_thread:
            try:
                self._scanner_thread.finished.disconnect()
            except TypeError:
                pass
            if self._scanner_thread.isRunning():
                self._scanner_thread.cancel()
                # 不等待旧线程退出，让它自行终止
                # wait() 会阻塞主线程，导致 loading 动画卡住
            self._scanner_thread = None

    # ---- Loading overlay helpers (严格按照 Outfitter 项目的实现) ----

    def _show_tree_loading(self, text: str = None):
        """Show loading overlay on the file tree area.

        严格按照 Outfitter 项目的 _show_tree_loading_overlay 实现：
        - 每次创建新的 overlay 实例（而非复用），确保 LoadingAnimationWidget timer 自动启动
        - 不调用 QApplication.processEvents()
        - 使用 show() + raise_() 让 Qt 事件循环自动处理UI更新
        """
        if text is None:
            text = self._tr("loading_ellipsis", "Loading...")

        # 清理旧的 overlay（如果有）
        self._cancel_refresh_overlay()

        # Lazy import to avoid circular dependency
        from core.ui_components import LoadingAnimationWidget
        from core.ui_constants import TREE_REFRESH_OVERLAY_STYLE, TREE_REFRESH_LABEL_STYLE

        # 创建新的 overlay 实例
        overlay = QWidget(self._tree)
        overlay.setObjectName("TreeRefreshOverlay")
        overlay.setStyleSheet(TREE_REFRESH_OVERLAY_STYLE)
        overlay.setGeometry(self._tree.rect())
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        overlay_layout = QVBoxLayout(overlay)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        overlay_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 创建新的 LoadingAnimationWidget（timer 会自动启动）
        anim = LoadingAnimationWidget(transparent=True)
        overlay_layout.addWidget(anim, alignment=Qt.AlignmentFlag.AlignHCenter)

        label = QLabel(text)
        label.setObjectName("TreeRefreshLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(TREE_REFRESH_LABEL_STYLE)
        overlay_layout.addWidget(label)

        overlay.show()
        overlay.raise_()
        self._refresh_overlay = overlay
        self._btn_refresh.setEnabled(False)

    def _cancel_refresh_overlay(self):
        """Cancel and clean up the current refresh overlay."""
        if self._refresh_overlay is not None:
            try:
                self._refresh_overlay.hide()
            except Exception:
                pass
            try:
                self._refresh_overlay.deleteLater()
            except Exception:
                pass
            self._refresh_overlay = None

    def _hide_tree_loading(self):
        """Hide loading overlay from the file tree area."""
        self._cancel_refresh_overlay()
        self._btn_refresh.setEnabled(True)

    # ---- Async tree building (lazy loading - single level) ----

    def _build_tree_async(self, show_loading: bool = True):
        """
        Start an async single-level scan of the root directory.
        Only loads the top-level entries (lazy loading).
        """
        self._cancel_all_loaders()

        if show_loading:
            self._show_tree_loading()

        # Reset lazy loading state
        self._loaded_dirs.clear()

        from core.file_tree_worker import SingleDirScannerThread

        self._scanner_thread = SingleDirScannerThread(self.root_dir, self.allowed_extensions)
        self._scanner_thread.finished.connect(self._on_top_level_done)
        self._scanner_thread.start()

    def _on_top_level_done(self, entries: List[Dict[str, Any]]):
        """
        Called on the main thread when the top-level scan completes.
        Builds only the top-level tree items (directories are placeholders).
        """
        if self._scanner_thread is not None:
            try:
                self._scanner_thread.finished.disconnect(self._on_top_level_done)
            except TypeError:
                pass
            self._scanner_thread = None

        self._hide_tree_loading()

        # Mark root as loaded
        self._loaded_dirs.add(os.path.abspath(self.root_dir))

        self._tree.clear()
        self._path_to_item.clear()

        folder_icon = self._folder_icon()
        file_icon = self._file_icon()

        for entry in entries:
            name = entry["name"]
            entry_type = entry["type"]
            full_path = entry["path"]

            if entry_type == "dir":
                display_text = "\U0001f4c1 " + name
                icon = folder_icon
            else:
                display_text = "\U0001f4c4 " + name
                icon = file_icon

            item = QTreeWidgetItem(self._tree, [display_text])
            item.setData(0, Qt.ItemDataRole.UserRole, {"type": entry_type, "path": full_path})
            item.setIcon(0, icon)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setData(0, Qt.ItemDataRole.CheckStateRole, Qt.CheckState.Unchecked)

            self._path_to_item[full_path] = item

        self._update_path_label()
        QTimer.singleShot(50, self._ensure_column_width)
        QTimer.singleShot(300, self._ensure_column_width)

    # ---- Lazy loading: expand directory on demand ----

    def _on_directory_expanded(self, index):
        """
        Called when a tree item is expanded. If it's a directory that hasn't
        been loaded yet, start a background scan to load its contents.
        
        PyQt6 的 QTreeWidget.expanded 信号传递 QModelIndex。
        """
        from PyQt6.QtCore import QModelIndex
        if not isinstance(index, QModelIndex):
            return
        item = self._tree.itemFromIndex(index)
        if item is None:
            return

        meta = item.data(0, Qt.ItemDataRole.UserRole)
        if not meta or meta.get("type") != "dir":
            return

        dir_path = meta.get("path", "")
        if not dir_path:
            return

        # Already loaded or currently loading
        if dir_path in self._loaded_dirs:
            return
        if dir_path in self._pending_loaders:
            return

        # Start background scan for this directory
        self._load_directory_async(dir_path, item)

    def _load_directory_async(self, dir_path: str, parent_item: QTreeWidgetItem):
        """
        Start a background scan for a single directory (non-recursive).
        When complete, populate the directory item with its children.
        
        如果该目录已经在加载中，直接返回避免重复加载。
        """
        # 防止重复加载
        if dir_path in self._pending_loaders:
            return
        
        from core.file_tree_worker import SingleDirScannerThread

        thread = SingleDirScannerThread(dir_path, self.allowed_extensions)
        weak_thread = [thread]
        def on_done(entries):
            self._on_dir_scan_done(dir_path, parent_item, entries)
        thread.finished.connect(on_done)
        thread.start()
        self._pending_loaders[dir_path] = thread
        # 保持强引用防止 GC
        if not hasattr(self, '_thread_refs'):
            self._thread_refs = []
        self._thread_refs.append(weak_thread)

    def _on_dir_scan_done(self, dir_path: str, parent_item: QTreeWidgetItem,
                          entries: List[Dict[str, Any]]):
        """
        Called on the main thread when a single directory scan completes.
        Populate the parent_item with the scanned entries.
        """
        # 从 pending 中移除
        self._pending_loaders.pop(dir_path, None)
        
        # Verify the parent item still exists (hasn't been deleted)
        try:
            _ = parent_item.text(0)
        except (RuntimeError, SystemError):
            return

        # 如果已经有子项了，说明已经加载过了（可能是竞态条件），直接返回
        if parent_item.childCount() > 0:
            return

        # Mark as loaded
        self._loaded_dirs.add(dir_path)

        folder_icon = self._folder_icon()
        file_icon = self._file_icon()

        # 保存父项的勾选状态，子项应继承
        parent_check = parent_item.checkState(0)

        for entry in entries:
            name = entry["name"]
            entry_type = entry["type"]
            full_path = entry["path"]

            if entry_type == "dir":
                display_text = "\U0001f4c1 " + name
                icon = folder_icon
            else:
                display_text = "\U0001f4c4 " + name
                icon = file_icon

            item = QTreeWidgetItem(parent_item, [display_text])
            item.setData(0, Qt.ItemDataRole.UserRole, {"type": entry_type, "path": full_path})
            item.setIcon(0, icon)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            
            # 继承父目录的勾选状态
            if parent_check == Qt.CheckState.Checked:
                item.setData(0, Qt.ItemDataRole.CheckStateRole, Qt.CheckState.Checked)
            else:
                item.setData(0, Qt.ItemDataRole.CheckStateRole, Qt.CheckState.Unchecked)

            self._path_to_item[full_path] = item

        # 如果父项是勾选状态，更新 file_set
        if parent_check == Qt.CheckState.Checked:
            self._tree.itemChanged.disconnect(self._on_item_changed)
            try:
                for entry in entries:
                    if entry["type"] == "file":
                        self._file_set.add(entry["path"])
                    elif entry["type"] == "dir":
                        # 子目录也勾选了，需要递归收集其下的文件
                        # 但因为子目录下的内容还没加载，先跳过，等展开时再处理
                        pass
            finally:
                self._tree.itemChanged.connect(self._on_item_changed)
            QTimer.singleShot(0, self._emit_checked_files_changed)

        QTimer.singleShot(50, self._ensure_column_width)

    # ------------ Async refresh (lazy loading) ----

    def _cancel_all_loaders(self):
        """Cancel all running background scanner threads (top-level + pending dir loaders)."""
        # Cancel top-level scanner
        self._cancel_scanner()
        # Cancel all pending directory loaders - 先取消，再等待完成，最后清理引用
        threads_to_wait = []
        for dir_path, thread in list(self._pending_loaders.items()):
            try:
                thread.finished.disconnect()
            except TypeError:
                pass
            if thread.isRunning():
                thread.cancel()
                threads_to_wait.append(thread)
        self._pending_loaders.clear()
        # 等待所有线程完成（短暂等待，避免阻塞 UI）
        for t in threads_to_wait:
            t.wait(500)  # 最多等待 500ms

    def refresh_async(self):
        """
        Refresh the file tree using lazy loading.
        
        架构：
        1. 取消所有正在进行的后台扫描
        2. 重置懒加载状态（清空已加载目录）
        3. 只重新扫描顶层目录
        4. 子目录内容在用户展开时按需加载
        """
        self._show_tree_loading()
        QTimer.singleShot(0, self._do_lazy_refresh)

    def _do_lazy_refresh(self):
        """Reset lazy loading state and reload top-level only."""
        # Reset lazy loading state
        self._loaded_dirs.clear()
        self._file_set.clear()
        self._current_activated_path = None

        # Cancel all in-progress loaders
        self._cancel_all_loaders()

        # Reload top-level
        from core.file_tree_worker import SingleDirScannerThread

        self._scanner_thread = SingleDirScannerThread(self.root_dir, self.allowed_extensions)
        self._scanner_thread.finished.connect(self._on_refresh_done)
        self._scanner_thread.start()

    def _on_refresh_done(self, entries: List[Dict[str, Any]]):
        """
        Called on main thread when the refresh top-level scan completes.
        Rebuilds only the top-level tree items.
        """
        if self._scanner_thread is not None:
            try:
                self._scanner_thread.finished.disconnect(self._on_refresh_done)
            except TypeError:
                pass
            self._scanner_thread = None

        self._hide_tree_loading()

        # Mark root as loaded
        self._loaded_dirs.add(os.path.abspath(self.root_dir))

        self._tree.clear()
        self._path_to_item.clear()

        folder_icon = self._folder_icon()
        file_icon = self._file_icon()

        for entry in entries:
            name = entry["name"]
            entry_type = entry["type"]
            full_path = entry["path"]

            if entry_type == "dir":
                display_text = "\U0001f4c1 " + name
                icon = folder_icon
            else:
                display_text = "\U0001f4c4 " + name
                icon = file_icon

            item = QTreeWidgetItem(self._tree, [display_text])
            item.setData(0, Qt.ItemDataRole.UserRole, {"type": entry_type, "path": full_path})
            item.setIcon(0, icon)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setData(0, Qt.ItemDataRole.CheckStateRole, Qt.CheckState.Unchecked)

            self._path_to_item[full_path] = item

        self._update_path_label()
        QTimer.singleShot(50, self._ensure_column_width)
        QTimer.singleShot(0, lambda: self.checkedFilesChanged.emit(0, self._count_total_files()))

    # ---- Sync refresh (for small trees or fallback) ----

    def refresh(self):
        """Synchronous refresh."""
        checked_paths = self._collect_checked_paths()
        activated_info = self._get_activated_info()
        self._build_tree()
        self._tree.expandAll()
        QTimer.singleShot(50, self._ensure_column_width)

        path_to_item: Dict[str, QTreeWidgetItem] = {}
        for i in range(self._tree.topLevelItemCount()):
            self._index_items(self._tree.topLevelItem(i), path_to_item)

        if checked_paths:
            for i in range(self._tree.topLevelItemCount()):
                self._uncheck_all(self._tree.topLevelItem(i))
            for p in checked_paths:
                item = path_to_item.get(p)
                if item:
                    item.setCheckState(0, Qt.CheckState.Checked)
            self._refresh_file_set()
            QTimer.singleShot(0, lambda: self.checkedFilesChanged.emit(
                len(self._file_set), self._count_total_files()))

        if activated_info:
            original_path = activated_info["original_path"]
            item_to_select = path_to_item.get(original_path)
            if item_to_select:
                meta = item_to_select.data(0, Qt.ItemDataRole.UserRole)
                new_path = meta["path"] if meta else original_path
                parent = item_to_select.parent()
                while parent:
                    parent.setExpanded(True)
                    parent = parent.parent()
                self._tree.itemSelectionChanged.disconnect(self._on_item_selection_changed)
                self._tree.clearSelection()
                self._tree.setCurrentItem(item_to_select)
                item_to_select.setSelected(True)
                self._tree.itemSelectionChanged.connect(self._on_item_selection_changed)
                self._tree.scrollToItem(item_to_select)
        self._current_activated_path = new_path
        QTimer.singleShot(30, lambda p=new_path: self.itemActivated.emit(p))

    # ------------ toolbar actions ------------

    def _on_expand_all(self):
        """Expand all directories by doing a full recursive scan in the background."""
        self._show_tree_loading(self._tr("loading_ellipsis", "Expanding all..."))
        QTimer.singleShot(0, self._do_expand_all)

    def _do_expand_all(self):
        """Use FileTreeScannerThread to recursively scan the entire tree."""
        self._cancel_all_loaders()
        from core.file_tree_worker import FileTreeScannerThread
        self._scanner_thread = FileTreeScannerThread(self.root_dir, self.allowed_extensions)
        self._scanner_thread.finished.connect(self._on_expand_all_done)
        self._scanner_thread.start()

    def _on_expand_all_done(self, entries: List[Dict[str, Any]]):
        """Build the full tree from recursive scan results and expand all."""
        if self._scanner_thread is not None:
            try:
                self._scanner_thread.finished.disconnect(self._on_expand_all_done)
            except TypeError:
                pass
            self._scanner_thread = None

        self._hide_tree_loading()

        # Mark all dirs as loaded
        self._loaded_dirs.clear()
        self._loaded_dirs.add(os.path.abspath(self.root_dir))

        self._tree.clear()
        self._path_to_item.clear()

        folder_icon = self._folder_icon()
        file_icon = self._file_icon()

        # Build parent_path -> item map
        # The root directory items have parent_path == root_dir, so we need a virtual root
        parent_map: Dict[str, QTreeWidgetItem] = {}
        # Use a special key for root - top-level items go directly into the tree
        root_abs = os.path.abspath(self.root_dir)

        for entry in entries:
            name = entry["name"]
            entry_type = entry["type"]
            full_path = entry["path"]
            parent_path = entry.get("parent_path", self.root_dir)

            if entry_type == "dir":
                display_text = "\U0001f4c1 " + name
                icon = folder_icon
                self._loaded_dirs.add(os.path.abspath(full_path))
            else:
                display_text = "\U0001f4c4 " + name
                icon = file_icon

            item = QTreeWidgetItem([display_text])
            item.setData(0, Qt.ItemDataRole.UserRole, {"type": entry_type, "path": full_path})
            item.setIcon(0, icon)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setData(0, Qt.ItemDataRole.CheckStateRole, Qt.CheckState.Unchecked)

            self._path_to_item[full_path] = item

            # Find parent and add as child
            # parent_path is the absolute path of the parent folder
            # If parent_path == root_dir, add as top-level item
            parent_abs = os.path.abspath(parent_path) if parent_path else root_abs
            parent = parent_map.get(parent_abs)
            if parent:
                parent.addChild(item)
            else:
                self._tree.addTopLevelItem(item)

            if entry_type == "dir":
                parent_map[os.path.abspath(full_path)] = item

        self._tree.expandAll()
        self._update_path_label()
        QTimer.singleShot(50, self._ensure_column_width)
        QTimer.singleShot(300, self._ensure_column_width)

    def _on_collapse_all(self):
        self._tree.collapseAll()


    # ------------ checkbox cascade logic ------------

    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        meta = item.data(0, Qt.ItemDataRole.UserRole)
        if not meta:
            return

        self._tree.itemChanged.disconnect(self._on_item_changed)
        try:
            check = item.checkState(0)
            if meta["type"] == "dir":
                self._set_children_check_state(item, check)
            self._sync_parent_check_states_up(item)
            self._incremental_update_file_set(item, check)
        finally:
            self._tree.itemChanged.connect(self._on_item_changed)

        is_checked = check == Qt.CheckState.Checked
        if meta["type"] == "file":
            self.itemChecked.emit(meta["path"], is_checked)
        QTimer.singleShot(0, self._emit_checked_files_changed)

    def _set_children_check_state(self, parent: QTreeWidgetItem, state: Qt.CheckState):
        for i in range(parent.childCount()):
            child = parent.child(i)
            child.setCheckState(0, state)
            meta = child.data(0, Qt.ItemDataRole.UserRole)
            if meta and meta["type"] == "dir":
                self._set_children_check_state(child, state)

    def _incremental_update_file_set(self, item: QTreeWidgetItem, check: Qt.CheckState):
        """Update file set incrementally when checkbox changes.

        从树数据结构收集文件路径，不使用 os.walk 避免阻塞 UI 线程。
        """
        meta = item.data(0, Qt.ItemDataRole.UserRole)
        if not meta:
            return
        if meta["type"] == "file":
            if check == Qt.CheckState.Checked:
                self._file_set.add(meta["path"])
            else:
                self._file_set.discard(meta["path"])
        elif meta["type"] == "dir":
            if check == Qt.CheckState.Checked:
                # 从树结构中收集，而非从文件系统遍历
                self._collect_all_files_from_item(item, self._file_set)
            else:
                # 从树结构中收集需要移除的路径
                to_remove: Set[str] = set()
                self._collect_all_files_from_item(item, to_remove)
                self._file_set -= to_remove

    @staticmethod
    def _add_all_files_in_dir(dir_path: str, out: Set[str]):
        for root, _, files in os.walk(dir_path):
            for f in files:
                out.add(os.path.join(root, f))

    @staticmethod
    def _collect_paths_in_dir(dir_path: str, out: Set[str]):
        for root, _, files in os.walk(dir_path):
            for f in files:
                out.add(os.path.join(root, f))

    def _sync_parent_check_states_up(self, item: QTreeWidgetItem):
        parent = item.parent()
        if not isinstance(parent, QTreeWidgetItem):
            return
        while isinstance(parent, QTreeWidgetItem):
            meta = parent.data(0, Qt.ItemDataRole.UserRole)
            if not meta or meta["type"] != "dir":
                break
            all_checked = True
            for i in range(parent.childCount()):
                child = parent.child(i)
                child_meta = child.data(0, Qt.ItemDataRole.UserRole)
                if not child_meta:
                    all_checked = False
                    break
                if child.checkState(0) != Qt.CheckState.Checked:
                    all_checked = False
                    break
            wanted = Qt.CheckState.Checked if all_checked else Qt.CheckState.Unchecked
            if parent.checkState(0) != wanted:
                parent.setData(0, Qt.ItemDataRole.CheckStateRole, wanted)
            parent = parent.parent()

    def _emit_checked_files_changed(self):
        total_files = self._count_total_files()
        self.checkedFilesChanged.emit(len(self._file_set), total_files)

    def _count_total_files(self) -> int:
        total = 0
        for i in range(self._tree.topLevelItemCount()):
            total += self._count_files_in_item(self._tree.topLevelItem(i))
        return total

    def _count_files_in_item(self, item: QTreeWidgetItem) -> int:
        count = 0
        meta = item.data(0, Qt.ItemDataRole.UserRole)
        if meta and meta.get("type") == "file":
            count = 1
        for i in range(item.childCount()):
            count += self._count_files_in_item(item.child(i))
        return count

    # ------------ public select/deselect methods ------------

    def select_all(self):
        self._tree.itemChanged.disconnect(self._on_item_changed)
        try:
            for i in range(self._tree.topLevelItemCount()):
                self._set_item_and_children_checked(
                    self._tree.topLevelItem(i), Qt.CheckState.Checked
                )
            self._file_set = set()
            for i in range(self._tree.topLevelItemCount()):
                self._collect_all_files(self._tree.topLevelItem(i), self._file_set)
        finally:
            self._tree.itemChanged.connect(self._on_item_changed)
        QTimer.singleShot(0, self._emit_checked_files_changed)

    def deselect_all(self):
        self._tree.itemChanged.disconnect(self._on_item_changed)
        try:
            for i in range(self._tree.topLevelItemCount()):
                self._set_item_and_children_checked(
                    self._tree.topLevelItem(i), Qt.CheckState.Unchecked
                )
            self._file_set.clear()
        finally:
            self._tree.itemChanged.connect(self._on_item_changed)
        QTimer.singleShot(0, self._emit_checked_files_changed)

    def _set_item_and_children_checked(self, item: QTreeWidgetItem, check_state: Qt.CheckState):
        item.setCheckState(0, check_state)
        for i in range(item.childCount()):
            self._set_item_and_children_checked(item.child(i), check_state)

    def _collect_all_files(self, item: QTreeWidgetItem, out: Set[str]):
        meta = item.data(0, Qt.ItemDataRole.UserRole)
        if meta and meta.get("type") == "file":
            out.add(meta["path"])
        for i in range(item.childCount()):
            self._collect_all_files(item.child(i), out)

    # ------------ refresh helper methods ------------

    def _collect_checked_paths(self) -> Set[str]:
        out: Set[str] = set()
        for i in range(self._tree.topLevelItemCount()):
            self._collect_files(self._tree.topLevelItem(i), out)
        return out

    def _collect_files(self, item: QTreeWidgetItem, out: Set[str]):
        """Collect checked file paths from tree structure (no filesystem I/O).
        
        严格从树数据结构收集，不使用 os.walk 避免阻塞 UI 线程。
        """
        if not item:
            return
        meta = item.data(0, Qt.ItemDataRole.UserRole)
        if not meta:
            return
        check = item.checkState(0)
        if meta["type"] == "file" and check == Qt.CheckState.Checked:
            out.add(meta["path"])
        elif meta["type"] == "dir" and check == Qt.CheckState.Checked:
            # 从树结构中收集，而非从文件系统遍历
            self._collect_all_files_from_item(item, out)
        else:
            for i in range(item.childCount()):
                self._collect_files(item.child(i), out)

    @staticmethod
    def _collect_all_files_from_item(item: QTreeWidgetItem, out: Set[str]):
        """Recursively collect all file paths from a tree item (no filesystem I/O)."""
        for i in range(item.childCount()):
            child = item.child(i)
            child_meta = child.data(0, Qt.ItemDataRole.UserRole)
            if child_meta:
                if child_meta["type"] == "file":
                    out.add(child_meta["path"])
                elif child_meta["type"] == "dir":
                    # 递归收集子目录中的文件
                    OutfitFileTree._collect_all_files_from_item(child, out)

    @staticmethod
    def _collect_all_files_in_dir(dir_path: str, out: Set[str]):
        for root, _, files in os.walk(dir_path):
            for f in files:
                out.add(os.path.join(root, f))

    def _refresh_file_set(self):
        new_set: Set[str] = set()
        for i in range(self._tree.topLevelItemCount()):
            self._collect_files(self._tree.topLevelItem(i), new_set)
        self._file_set = new_set

    def _uncheck_all(self, item: QTreeWidgetItem):
        item.setCheckState(0, Qt.CheckState.Unchecked)
        for i in range(item.childCount()):
            self._uncheck_all(item.child(i))

    def _index_items(self, item: QTreeWidgetItem, path_to_item: Dict[str, QTreeWidgetItem]):
        meta = item.data(0, Qt.ItemDataRole.UserRole)
        if meta:
            path_to_item[meta["path"]] = item
        for i in range(item.childCount()):
            self._index_items(item.child(i), path_to_item)

    def _get_activated_info(self) -> Optional[Dict[str, str]]:
        selected = self._tree.selectedItems()
        if not selected:
            return None
        item = selected[0]
        meta = item.data(0, Qt.ItemDataRole.UserRole)
        if not meta or meta.get("type") != "file":
            return None
        return {"original_path": meta["path"]}

    # ------------ public checkbox methods ------------

    def get_checked_file_paths(self) -> List[str]:
        return list(self._file_set)

    # ------------ event filter ------------

    def eventFilter(self, obj, event):
        if obj is self._tree.viewport():
            if event.type() == QEvent.Type.Resize:
                self._schedule_column_width()
                if self._refresh_overlay is not None and self._refresh_overlay.isVisible():
                    self._refresh_overlay.setGeometry(self._tree.rect())
                return False
            if event.type() == QEvent.Type.MouseButtonPress:
                item = self._tree.itemAt(event.pos())
                if item is None:
                    self._tree.clearSelection()
                    self._path_label.setText(self.root_dir)
                    return True
        return super().eventFilter(obj, event)

    # ------------ path label ------------

    def _update_path_label(self):
        if self._tree.selectedItems():
            item = self._tree.selectedItems()[0]
            meta = item.data(0, Qt.ItemDataRole.UserRole)
            if meta and "path" in meta:
                path = meta["path"]
                try:
                    rel = os.path.relpath(path, self.root_dir)
                    if rel == ".":
                        self._path_label.setText(self.root_dir)
                    else:
                        self._path_label.setText(os.path.join(self.root_dir, rel))
                except ValueError:
                    self._path_label.setText(path)
            return
        self._path_label.setText(self.root_dir)

    # ------------ selection-based activation ------------

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        if not self._tree.selectedItems():
            item.setSelected(True)

        # 对于未加载的目录，双击时手动触发展开并加载
        # （因为未加载的目录没有子项，Qt 的 setExpandsOnDoubleClick 不会触发 expanded 信号）
        meta = item.data(0, Qt.ItemDataRole.UserRole)
        if meta and meta.get("type") == "dir":
            dir_path = meta.get("path", "")
            if dir_path and dir_path not in self._loaded_dirs:
                if dir_path not in self._pending_loaders:
                    item.setExpanded(True)
                    self._load_directory_async(dir_path, item)

    def _on_item_selection_changed(self):
        self._update_path_label()
        selected_items = self._tree.selectedItems()
        if not selected_items:
            previous_path = self._current_activated_path
            if previous_path:
                self.itemDeactivated.emit(previous_path)
                self._current_activated_path = None
            return

        item = selected_items[0]
        meta = item.data(0, Qt.ItemDataRole.UserRole)
        if not meta:
            return

        if meta.get("type") != "file":
            previous_path = self._current_activated_path
            if previous_path:
                self.itemDeactivated.emit(previous_path)
                self._current_activated_path = None
            return

        new_path = meta["path"]
        previous_path = self._current_activated_path

        if previous_path == new_path:
            return

        if previous_path:
            self.itemDeactivated.emit(previous_path)

        self._current_activated_path = new_path
        self.itemActivated.emit(new_path)

    # ------------ synchronous tree building (fallback) ------------

    def _build_tree(self):
        """Synchronous tree build — used only as fallback."""
        self._tree.clear()
        if not os.path.isdir(self.root_dir):
            return

        folder_icon = self._folder_icon()
        file_icon = self._file_icon()

        dirs = []
        files = []
        try:
            for entry in os.listdir(self.root_dir):
                full_path = os.path.join(self.root_dir, entry)
                if os.path.isdir(full_path):
                    dirs.append(entry)
                elif any(entry.lower().endswith(ext) for ext in self.allowed_extensions):
                    files.append(entry)
        except OSError:
            return

        for entry in sorted(dirs):
            full_path = os.path.join(self.root_dir, entry)
            item = QTreeWidgetItem(self._tree, ["📁 " + entry])
            item.setData(0, Qt.ItemDataRole.UserRole, {"type": "dir", "path": full_path})
            item.setIcon(0, folder_icon)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setData(0, Qt.ItemDataRole.CheckStateRole, Qt.CheckState.Unchecked)
            self._populate_dir(full_path, item, folder_icon, file_icon)

        for entry in sorted(files):
            full_path = os.path.join(self.root_dir, entry)
            item = QTreeWidgetItem(self._tree, ["📄 " + entry])
            item.setData(0, Qt.ItemDataRole.UserRole, {"type": "file", "path": full_path})
            item.setIcon(0, file_icon)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setData(0, Qt.ItemDataRole.CheckStateRole, Qt.CheckState.Unchecked)

    def _populate_dir(self, dir_path: str, parent_item: QTreeWidgetItem,
                      folder_icon, file_icon):
        try:
            all_entries = os.listdir(dir_path)
        except PermissionError:
            return

        dirs = []
        files = []
        for entry in all_entries:
            full_path = os.path.join(dir_path, entry)
            if os.path.isdir(full_path):
                dirs.append(entry)
            elif any(entry.lower().endswith(ext) for ext in self.allowed_extensions):
                files.append(entry)

        for entry in sorted(dirs):
            full_path = os.path.join(dir_path, entry)
            item = QTreeWidgetItem(parent_item, ["📁 " + entry])
            item.setData(0, Qt.ItemDataRole.UserRole, {"type": "dir", "path": full_path})
            item.setIcon(0, folder_icon)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setData(0, Qt.ItemDataRole.CheckStateRole, Qt.CheckState.Unchecked)
            self._populate_dir(full_path, item, folder_icon, file_icon)

        for entry in sorted(files):
            full_path = os.path.join(dir_path, entry)
            item = QTreeWidgetItem(parent_item, ["📄 " + entry])
            item.setData(0, Qt.ItemDataRole.UserRole, {"type": "file", "path": full_path})
            item.setIcon(0, file_icon)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setData(0, Qt.ItemDataRole.CheckStateRole, Qt.CheckState.Unchecked)

    # ------------ icon helpers ------------

    def _folder_icon(self):
        from PyQt6.QtGui import QIcon
        return QIcon()

    def _file_icon(self):
        from PyQt6.QtGui import QIcon
        return QIcon()

    # ------------ column width management ------------

    def _schedule_column_width(self, *args):
        self._column_width_timer.start()

    def _ensure_column_width(self):
        try:
            if not self._tree:
                return
            header = self._tree.header()
            if not header:
                return
            # Calculate needed width considering indentation at each level
            needed = 100
            for i in range(self._tree.topLevelItemCount()):
                item = self._tree.topLevelItem(i)
                if item:
                    needed = max(needed, self._longest_visible_width(item, 0))
            current = header.sectionSize(0)
            if current < needed:
                header.resizeSection(0, min(needed + 42, 800))
        except (RuntimeError, SystemError):
            pass

    def _item_text_width(self, item: QTreeWidgetItem) -> int:
        try:
            fm = self._tree.fontMetrics()
            text = item.text(0)
            return fm.horizontalAdvance(text)
        except (RuntimeError, SystemError):
            return 0

    def _longest_visible_width(self, item: QTreeWidgetItem, depth: int) -> int:
        """Calculate the widest visible width considering indentation.
        
        Each level adds indentation (14px), so the visible width needed is:
        text_width + indentation * depth + branch_arrow_space
        """
        try:
            indent = self._tree.indentation()  # 14px per level
            # 42px for checkbox (14px indicator + 4px spacing) + padding (4px + 4px) + safety margin (10px)
            visible_w = self._item_text_width(item) + indent * depth + 42
            for i in range(item.childCount()):
                child = item.child(i)
                if child:
                    visible_w = max(visible_w, self._longest_visible_width(child, depth + 1))
            return visible_w
        except (RuntimeError, SystemError):
            return 0
