"""
Async file-tree data loader for Body Slider Pro.

Scans a directory on a background thread and emits the result
as a list of dicts so the UI thread can populate the QTreeWidget
without blocking.
"""

import os
from typing import List, Dict, Any, Tuple

from PyQt6.QtCore import QThread, QObject, pyqtSignal


class FileTreeScannerThread(QThread):
    """
    Walks a directory tree and emits a flat list of entries.
    
    Signal:
        finished(entries: List[Dict[str, Any]])
            Each dict has keys:
                - name: str          file/dir name
                - type: "dir" | "file"
                - path: str           absolute path
                - parent_name: str | None   parent folder name (None for top-level)
    """
    finished = pyqtSignal(list)

    def __init__(self, root_dir: str, allowed_extensions: Tuple[str, ...]):
        super().__init__()
        self.root_dir = os.path.abspath(root_dir)
        self.allowed_extensions = tuple(e.lower() for e in allowed_extensions)
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def _is_allowed(self, name: str) -> bool:
        return any(name.lower().endswith(ext) for ext in self.allowed_extensions)

    def _scan_dir(self, dir_path: str, parent_path: str, entries: List[Dict[str, Any]]):
        """Recursively collect dirs and allowed files."""
        if self._cancelled:
            return
        try:
            child_names = os.listdir(dir_path)
        except OSError:
            return

        dirs = []
        files = []
        for name in child_names:
            full = os.path.join(dir_path, name)
            if os.path.isdir(full):
                dirs.append(name)
            elif self._is_allowed(name):
                files.append(name)

        for name in sorted(dirs):
            full = os.path.join(dir_path, name)
            entries.append({
                "name": name,
                "type": "dir",
                "path": full,
                "parent_path": parent_path,
            })
            self._scan_dir(full, full, entries)

        for name in sorted(files):
            full = os.path.join(dir_path, name)
            entries.append({
                "name": name,
                "type": "file",
                "path": full,
                "parent_path": parent_path,
            })

    def run(self):
        entries: List[Dict[str, Any]] = []
        self._scan_dir(self.root_dir, self.root_dir, entries)
        if not self._cancelled:
            self.finished.emit(entries)


class FileTreeBatchScannerThread(QThread):
    """
    在后台线程分批扫描目录，每扫描完一批通过信号发送到主线程。
    
    这样主线程只需要处理少量条目的 QTreeWidgetItem 创建，
    大幅降低单次阻塞时间，UI 始终流畅。
    
    Signals:
        batch_ready(entries: List[Dict[str, Any]]) - 每批数据就绪
        scan_completed() - 扫描全部完成
    """
    batch_ready = pyqtSignal(list)
    scan_completed = pyqtSignal()

    def __init__(self, root_dir: str, allowed_extensions: Tuple[str, ...], batch_size: int = 50):
        super().__init__()
        self.root_dir = os.path.abspath(root_dir)
        self.allowed_extensions = tuple(e.lower() for e in allowed_extensions)
        self.batch_size = batch_size
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def _is_allowed(self, name: str) -> bool:
        return any(name.lower().endswith(ext) for ext in self.allowed_extensions)

    def _scan_and_emit(self, dir_path: str, parent_path: str):
        """扫描一个目录，收集条目，达到批次大小时发送信号。"""
        if self._cancelled:
            return

        try:
            child_names = os.listdir(dir_path)
        except OSError:
            return

        dirs = []
        files = []
        for name in child_names:
            full = os.path.join(dir_path, name)
            if os.path.isdir(full):
                dirs.append(name)
            elif self._is_allowed(name):
                files.append(name)

        batch = []
        # 先收集目录
        for name in sorted(dirs):
            if self._cancelled:
                return
            full = os.path.join(dir_path, name)
            batch.append({
                "name": name,
                "type": "dir",
                "path": full,
                "parent_path": parent_path,
            })

        # 再收集文件
        for name in sorted(files):
            if self._cancelled:
                return
            full = os.path.join(dir_path, name)
            batch.append({
                "name": name,
                "type": "file",
                "path": full,
                "parent_path": parent_path,
            })

        # 如果当前目录的条目超过批次大小，分批发送
        if len(batch) > self.batch_size:
            for i in range(0, len(batch), self.batch_size):
                if self._cancelled:
                    return
                self.batch_ready.emit(batch[i:i + self.batch_size])
                # 给信号处理留一点时间
                import time
                time.sleep(0.001)
        elif batch:
            self.batch_ready.emit(batch)

        # 递归扫描子目录
        for name in sorted(dirs):
            if self._cancelled:
                return
            full = os.path.join(dir_path, name)
            self._scan_and_emit(full, full)

    def run(self):
        if not self._cancelled:
            self._scan_and_emit(self.root_dir, self.root_dir)
        if not self._cancelled:
            self.scan_completed.emit()


class SingleDirScannerThread(QThread):
    """
    只扫描指定目录的一级内容（不递归），用于懒加载。
    
    Signal:
        finished(entries: List[Dict[str, Any]])
            Each dict has keys:
                - name: str          file/dir name
                - type: "dir" | "file"
                - path: str           absolute path
                - parent_path: str    parent folder path
    """
    finished = pyqtSignal(list)

    def __init__(self, dir_path: str, allowed_extensions: Tuple[str, ...]):
        super().__init__()
        self.dir_path = os.path.abspath(dir_path)
        self.allowed_extensions = tuple(e.lower() for e in allowed_extensions)
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def _is_allowed(self, name: str) -> bool:
        return any(name.lower().endswith(ext) for ext in self.allowed_extensions)

    def run(self):
        entries: List[Dict[str, Any]] = []
        if self._cancelled:
            self.finished.emit(entries)
            return

        try:
            child_names = os.listdir(self.dir_path)
        except OSError:
            self.finished.emit(entries)
            return

        dirs = []
        files = []
        for name in child_names:
            full = os.path.join(self.dir_path, name)
            if os.path.isdir(full):
                dirs.append(name)
            elif self._is_allowed(name):
                files.append(name)

        for name in sorted(dirs):
            if self._cancelled:
                return
            full = os.path.join(self.dir_path, name)
            entries.append({
                "name": name,
                "type": "dir",
                "path": full,
                "parent_path": self.dir_path,
            })

        for name in sorted(files):
            if self._cancelled:
                return
            full = os.path.join(self.dir_path, name)
            entries.append({
                "name": name,
                "type": "file",
                "path": full,
                "parent_path": self.dir_path,
            })

        if not self._cancelled:
            self.finished.emit(entries)


class FileTreeBuildWorker(QObject):
    """
    Helper that runs FileTreeScannerThread and provides a simple API.
    Used by OutfitFileTree to load data asynchronously.
    """

    def __init__(self):
        super().__init__()
        self._thread: FileTreeScannerThread = None

    def scan(self, root_dir: str, allowed_extensions: Tuple[str, ...],
              callback) -> FileTreeScannerThread:
        """
        Start scanning in background.
        
        Args:
            root_dir: Root directory to scan.
            allowed_extensions: Tuple of allowed file extensions.
            callback: Callable(List[Dict]) called on main thread when done.
        
        Returns:
            The QThread (can be used to cancel).
        """
        self._thread = FileTreeScannerThread(root_dir, allowed_extensions)
        self._thread.finished.connect(callback)
        self._thread.start()
        return self._thread

    def cancel(self):
        if self._thread is not None:
            self._thread.cancel()
