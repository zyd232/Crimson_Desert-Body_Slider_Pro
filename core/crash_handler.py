"""
Crash report collector for Body Slider Pro.
Captures unhandled exceptions and writes logs to crash_report/ directory.
"""

import sys
import os
import time
import platform
import traceback
from typing import Optional


def get_crash_report_dir(root_dir: str) -> str:
    """Get or create the crash_report directory."""
    crash_dir = os.path.join(root_dir, "crash_report")
    os.makedirs(crash_dir, exist_ok=True)
    return crash_dir


def load_version(root_dir: str) -> str:
    """Load app version from core/version.txt. Falls back to 'unknown'."""
    version_file = os.path.join(root_dir, "core", "version.txt")
    try:
        if os.path.exists(version_file):
            with open(version_file, "r", encoding="utf-8") as f:
                version = f.read().strip()
                if version:
                    return version
    except Exception:
        pass
    return "unknown"


class CrashHandler:
    """
    Global crash handler that captures:
    - Unhandled Python exceptions
    - System exit / keyboard interrupt (optional)
    Writes structured logs to crash_report/ directory.
    """

    def __init__(self, root_dir: str, app_name: str = "Body Slider Pro", app_version: Optional[str] = None):
        self.root_dir = root_dir
        self.app_name = app_name
        self.app_version = app_version if app_version is not None else load_version(root_dir)
        self.crash_dir = get_crash_report_dir(root_dir)

        # Keep reference to original hook
        self._original_excepthook = sys.excepthook

    def install(self):
        """Install the global exception hook."""
        sys.excepthook = self._excepthook

    @staticmethod
    def _timestamp() -> str:
        """Return a safe timestamp string for filenames."""
        return time.strftime("%Y%m%d_%H%M%S", time.localtime())

    def _log_filename(self, prefix: str = "crash") -> str:
        ts = self._timestamp()
        return f"{prefix}_{ts}.log"

    def _collect_system_info(self) -> str:
        info = []
        info.append("=" * 60)
        info.append("SYSTEM INFORMATION")
        info.append("=" * 60)
        info.append(f"App Name:    {self.app_name}")
        info.append(f"App Version: {self.app_version}")
        info.append(f"OS:          {platform.system()} {platform.release()} {platform.version()}")
        info.append(f"Arch:        {platform.machine()}")
        info.append(f"Python:      {platform.python_version()}")
        info.append(f"Exec:        {sys.executable}")
        info.append(f"Frozen:      {getattr(sys, 'frozen', False)}")
        if getattr(sys, "frozen", False):
            info.append(f"Executable: {sys.argv[0]}")
        info.append(f"Working Dir: {os.getcwd()}")
        info.append("")
        return "\n".join(info)

    def _excepthook(self, exc_type, exc_value, exc_traceback):
        """
        Handler for unhandled exceptions.
        Writes a log file and (on desktop) shows a simple message box if possible.
        """
        # Ignore SystemExit / KeyboardInterrupt by default (clean shutdown)
        if issubclass(exc_type, (SystemExit, KeyboardInterrupt)):
            if self._original_excepthook:
                self._original_excepthook(exc_type, exc_value, exc_traceback)
            return

        # Build error message
        tb_lines = "".join(
            traceback.format_exception(exc_type, exc_value, exc_traceback)
        )

        system_info = self._collect_system_info()

        log_lines = []
        log_lines.append("=" * 60)
        log_lines.append("CRASH REPORT")
        log_lines.append("=" * 60)
        log_lines.append(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
        log_lines.append(f"Exception: {exc_type.__name__}: {exc_value}")
        log_lines.append("")
        log_lines.append("-" * 60)
        log_lines.append("TRACEBACK")
        log_lines.append("-" * 60)
        log_lines.append(tb_lines)
        log_lines.append("")
        log_lines.append(system_info)

        full_log = "\n".join(log_lines)

        # Write log file
        filename = self._log_filename("crash")
        filepath = os.path.join(self.crash_dir, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(full_log)
        except Exception:
            # Last-resort: write to current directory
            try:
                with open("crash.log", "a", encoding="utf-8") as f:
                    f.write(full_log + "\n")
            except Exception:
                pass

        # Try to show a minimal message box (best-effort, non-blocking).
        # Avoid letting a second exception escape back into PyQt.
        try:
            self._show_crash_dialog_safe(filepath)
        except Exception:
            pass

    @staticmethod
    def _show_crash_dialog_safe(log_path: Optional[str] = None):
        """
        Attempt to show a simple message box if PyQt6 is available and safe.
        Designed to avoid secondary crashes.
        """
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            from PyQt6.QtCore import Qt

            app = QApplication.instance()
            if not app:
                return

            msg = QMessageBox()
            msg.setWindowTitle("Unexpected Error")
            msg.setText("The application encountered an unexpected error and needs to close.")
            msg.setInformativeText(
                "A crash report has been saved. "
                "Please attach it when reporting the issue."
            )
            if log_path:
                msg.setDetailedText(f"Log file:\n{log_path}")
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.setDefaultButton(QMessageBox.StandardButton.Ok)
            msg.exec()
        except Exception:
            # Avoid any recursion / second crash
            pass


def write_crash_report(
    root_dir: str,
    error_message: str,
    exc_info=None,
    prefix: str = "error",
) -> str:
    """
    Utility to manually write a crash/error report from within try/except.

    Returns path to the log file.
    """
    crash_dir = get_crash_report_dir(root_dir)

    tb = ""
    try:
        if exc_info:
            tb = "".join(traceback.format_exception(*exc_info))
        else:
            tb = "".join(traceback.format_exception(*sys.exc_info()))
    except Exception:
        tb = "(traceback unavailable)"

    log_lines = []
    log_lines.append("=" * 60)
    log_lines.append("ERROR REPORT")
    log_lines.append("=" * 60)
    log_lines.append(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
    log_lines.append(f"Message: {error_message}")
    log_lines.append("")
    log_lines.append("-" * 60)
    log_lines.append("TRACEBACK")
    log_lines.append("-" * 60)
    log_lines.append(tb)

    full_log = "\n".join(log_lines)

    filename = CrashHandler(root_dir)._log_filename(prefix)
    filepath = os.path.join(crash_dir, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_log)
    except Exception:
        pass

    return filepath


def safe_connect(signal, slot, *args, **kwargs):
    """
    Wrapper for PyQt signal.connect that:
    - Catches and logs exceptions in the slot
    - Prevents unhandled exceptions from escaping back into Qt
      and causing 'object has been deleted' / SystemError crashes.
    """
    def _wrapped(*sargs, **skwargs):
        try:
            slot(*sargs, **skwargs)
        except Exception:
            try:
                write_crash_report(
                    root_dir=".",
                    error_message="Unhandled exception in PyQt slot",
                    exc_info=sys.exc_info(),
                    prefix="slot_error",
                )
            except Exception:
                pass

    return signal.connect(_wrapped, *args, **kwargs)
