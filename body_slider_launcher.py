"""
Body Slider Pro - Launcher
Entry point for the application. Initializes and starts the main window.
"""

import sys
import os

# Ensure core package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from core.body_slider_func import BodySlider
from core.crash_handler import CrashHandler


def main():
    # Determine root_dir (same logic as BodySlider)
    if getattr(sys, "frozen", False):
        root_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        root_dir = os.path.dirname(os.path.abspath(__file__))

    # Install global crash handler before creating UI
    crash_handler = CrashHandler(root_dir)
    crash_handler.install()

    app = QApplication(sys.argv)

    # Set application icon:
    # - In frozen build: use PyInstaller extract dir (_MEIPASS)
    # - In dev: use project root_dir
    if getattr(sys, "frozen", False):
        icon_root = getattr(sys, "_MEIPASS", root_dir)
    else:
        icon_root = root_dir

    icon_path = os.path.join(
        icon_root,
        "core",
        "assets",
        "icon.ico",
    )
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = BodySlider()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()