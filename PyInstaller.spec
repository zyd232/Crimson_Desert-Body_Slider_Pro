# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Body Slider Pro
"""
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Directories to exclude at root level only (project working/data directories)
exclude_root_dirs = [
    ".backup",
    "bs",
    "build",
    "char_config",
    "crash_report",
    "exported_mesh",
    "exported_mod",
    "exported_outfit",
    "language",
    "original_mesh",
    "original_outfit",
    "README",
    "target_mesh"
]

# Directories to exclude at **any level** in the path (recursive exclusion)
exclude_all_dirs = [
    "__pycache__",
    ".github",
    ".git",
    ".vscode",
    "graphify-out"
]

# Files to exclude at **any level** in the path (recursive exclusion)
exclude_all_files = [
    # Example: ".pyc" will exclude core/.pyc and any/path/.pyc
]

# Specific root-level files to exclude (if they appear in datas)
exclude_root_files = [
    ".gitignore",
    ".graphifyignore",
    "build.bat",
    "config.json",
    "convert_icon.py", 
    "PyInstaller.spec",   
    "requirements.txt",
    "run_graphify.bat"
]

# Collect core resources (data files in core/)
core_datas = collect_data_files("core")

a = Analysis(
    ['body_slider_launcher.py'],
    pathex=[],
    binaries=None,
    datas=core_datas,
    hiddenimports=[
        'trimesh',
        'PyQt6',
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtOpenGL',
        'PyQt6.QtOpenGLWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'jupyter_client',
        'ipykernel',
        'notebook',
        'IPython',
        'pyvista',
        'pyvistaqt',
        'vtk',
        'vtkmodules',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove excluded dirs and specific root files from datas
filtered_datas = []
for item in a.datas:
    # PyInstaller may use different data structures in different versions
    # item is (src, dst) or (src, dst, type) or similar
    if isinstance(item, (list, tuple)):
        if len(item) < 2:
            filtered_datas.append(item)
            continue
        src, dst = item[0], item[1]
        dst_str = str(dst).lower().replace("\\", "/")

        # exclude root-level directories
        if any(dst_str.startswith(d + "/") for d in exclude_root_dirs):
            continue

        # exclude specific root files (no '/' in dst)
        if "/" not in dst_str and dst_str in exclude_root_files:
            continue

        # exclude directories at any level (recursive)
        if any("/" + d + "/" in dst_str or dst_str.startswith(d + "/") for d in exclude_all_dirs):
            continue

        # exclude files at any level (recursive)
        if any("/" + f == dst_str[-len(f) - 1:] or dst_str == f for f in exclude_all_files):
            continue

        filtered_datas.append(item)
    else:
        filtered_datas.append(item)
a.datas = filtered_datas

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Body Slider Pro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='core/assets/icon.ico',
)