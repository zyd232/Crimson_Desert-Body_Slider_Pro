"""
Functional/backend logic for Body Slider Pro.
"""

import os
import re
import json
import shutil
import subprocess
import sys
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import numpy as np
import trimesh

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QFileDialog,
    QMessageBox,
    QDialog,
    QInputDialog,
)
from PyQt6.QtCore import (
    QObject,
    Qt,
    QTimer,
    QThread,
)

from core.mesh_viewer import MeshViewer
from core.pac_builder import (
    IncrementalPACBuilder,
    parse_pac,
    ParsedMesh,
)
from core.mesh_validator import (
    validate_target_mesh_against_original,
    validate_pac_compatibility,
    get_pac_submesh_signature,
    get_mesh_signature_from_arrays,
)
from core.mesh_processor import (
    compute_morph_delta,
    apply_morphs,
    compute_vertex_normals,
)
from core.ui_components import (
    DEFAULT_MOD_PATH,
    DEFAULT_PAC_NAME,
    DEFAULT_CHAR_ID,
    DEFAULT_CHAR_NAME,
    SLIDER_NAME_MAX_LEN,
    CHAR_NAME_MAX_LEN,
    CHAR_ID_PATTERN,
    OBJ_FILE_FILTER,
    PAC_FILE_FILTER,
    MESH_FILE_FILTER,
    SliderInfo,
    CharacterInfo,
    TranslationProxy,
    AddCharacterDialog,
    EditCharacterDialog,
    AddSliderDialog,
    EditSliderDialog,
    RangeInputDialog,
    DarkMessageBox,
    CharacterPackSelectDialog,
    CharacterPackLoadDialog,
    PackConflictResolveDialog,
    CharacterSortDialog,
    scan_available_languages,
    safe_text,
    show_info,
    show_warning,
    show_critical,
    show_question,
    show_choice,
    DEFAULT_SLIDERS,
)
from core.ui_constants import (
    QSS_STYLESHEET,
)

from core.crash_handler import safe_connect
from core.pack_handler_mixin import PackHandlerMixin
from core.data_loader_worker import StartupDataInitWorker
from core.custom_slider_manager import CustomSliderManager
from core.config_manager import ConfigManager
from core.ui_window_manager import FramelessWindowManagerMixin
from core.ui_outfits import OutfitsPanel
from core.outfit_manager import OutfitManager
from core.main_window import MainWindowUIMixin


class BodySlider(QMainWindow, MainWindowUIMixin, PackHandlerMixin, FramelessWindowManagerMixin):
    DEFAULT_CHARACTER_ORDER = ["damiane"]

    ALLOWED_CHAR_KEYS = {
        "name",
        "id",
        "is_default",
        "original_pac_path",
        "mod_path",
    }

    ALLOWED_SLIDER_KEYS = {
        "name",
        "min",
        "max",
        "path",
        "current_value",
        "is_default",
    }

    def __init__(self):
        super().__init__()

        # Directories
        if getattr(sys, "frozen", False):
            self.resource_dir = os.path.abspath(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)))
        else:
            self.resource_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        if getattr(sys, "frozen", False):
            self.root_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        self.config_path = os.path.join(self.root_dir, "config.json")
        self.char_config_dir = os.path.join(self.root_dir, "char_config")
        os.makedirs(self.char_config_dir, exist_ok=True)

        # Core data structures
        self.languages = scan_available_languages(self.root_dir)
        self.current_lang = "en"

        self.sliders_info: Dict[str, Dict[str, Any]] = {}
        self.camera_positions: Dict[str, Any] = {}

        self.characters: Dict[str, Dict[str, Any]] = {}
        self.character_sliders: Dict[str, Dict[str, Any]] = {}
        self.active_char_id: Optional[str] = None

        self.original_points: Dict[str, np.ndarray] = {}
        self.original_faces: Dict[str, np.ndarray] = {}
        self.morph_data: Dict[str, Dict[str, np.ndarray]] = {}
        self.mesh_viewer_data: Dict[str, Dict] = {}
        self.pac_mesh = None
        self.pac_submesh_names: Set[str] = set()
        self.scene_base = None
        self.original_pac_path = ""
        self.custom_dir = ""

        # Outfit state
        self.active_outfit_path = None
        self.active_outfit_mod_path = None
        self.outfit_original_points: Dict[str, np.ndarray] = {}
        self.outfit_morph_data: Dict[str, Dict[str, np.ndarray]] = {}
        self.outfit_faces: Dict[str, np.ndarray] = {}

        # Initialize frameless window management state via mixin
        self._init_window_manager_state()

        self._splitter_resizing = False
        self._splitter_resize_timer = QTimer(self)
        self._splitter_resize_timer.setSingleShot(True)
        self._splitter_resize_timer.setInterval(150)
        self._splitter_resize_timer.timeout.connect(self._on_splitter_resize_stable)

        # Track splitter-related QTimer instances so they can be cancelled during page teardown.
        self._splitter_timers: List[QTimer] = []

        # Initialize ConfigManager and load config
        self.cm = ConfigManager(
            root_dir=self.root_dir,
            config_path=self.config_path,
            char_config_dir=self.char_config_dir,
            characters=self.characters,
            character_sliders=self.character_sliders,
            sliders_info=self.sliders_info,
            camera_positions=self.camera_positions,
            languages=self.languages,
            allowed_char_keys=self.ALLOWED_CHAR_KEYS,
            allowed_slider_keys=self.ALLOWED_SLIDER_KEYS,
            default_character_order=self.DEFAULT_CHARACTER_ORDER,
            default_sliders=DEFAULT_SLIDERS,
            default_pac_name=DEFAULT_PAC_NAME,
            default_char_id=DEFAULT_CHAR_ID,
            default_char_name=DEFAULT_CHAR_NAME,
            default_mod_path=DEFAULT_MOD_PATH,
        )
        self.cm.load_config()

        # Sync loaded config back to this instance
        self.current_lang = self.cm.current_lang
        self.saved_window_size = self.cm.saved_window_size
        self.active_char_id = self.cm.active_char_id
        self.wireframe_enabled = self.cm.wireframe_enabled

        if self.current_lang not in self.languages:
            self.current_lang = "en"

        self.T = TranslationProxy(self.languages, self.current_lang)

        # Mount custom slider manager (after T and core state are ready)
        self.custom_slider_mgr = CustomSliderManager(self)

        # Mount outfit manager
        self.outfit_mgr = OutfitManager(self)

        window_flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowFlags(window_flags)

        self.app_version = self._load_version()

        self.setWindowTitle(
            f"{self.T['title']} - v{self.app_version} - by zyd232"
        )
        ws = getattr(self, "saved_window_size", None)
        if isinstance(ws, (list, tuple)) and len(ws) == 2:
            w, h = int(ws[0]), int(ws[1])
            if 600 <= w <= 2560 and 400 <= h <= 1440:
                self.resize(w, h)
            else:
                self.resize(1300, 900)
        else:
            self.resize(1300, 900)
        self.setStyleSheet(QSS_STYLESHEET)

        # Create central widget and layout early so LoadingOverlay
        # is attached to the correct widget. init_ui() will populate
        # this layout instead of creating a new central widget.
        self.central = QWidget()
        self.setCentralWidget(self.central)
        self.main_layout = QVBoxLayout(self.central)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.show()
        self._startup_loading = self._show_loading(
            self.T.get("startup_loading_text", "Starting application...")
        )

        QTimer.singleShot(0, self.start_data_init_thread)

    # ---------- startup ----------

    def start_data_init_thread(self):
        if hasattr(self, "_data_init_thread") and self._data_init_thread.isRunning():
            return

        from core.data_loader_worker import StartupDataInitWorker

        char_sliders_for_worker: Dict[str, Dict[str, Any]] = {}
        for cid, sliders in self.character_sliders.items():
            if not isinstance(sliders, dict):
                continue
            full: Dict[str, Any] = {}
            for local_id, info in sliders.items():
                full[f"{cid}.{local_id}"] = info
            char_sliders_for_worker[cid] = full

        self._data_init_worker = StartupDataInitWorker(
            self.active_char_id,
            self.characters,
            char_sliders_for_worker,
            self.char_config_dir,
            self.root_dir
        )

        self._data_init_thread = QThread()
        self._data_init_worker.moveToThread(self._data_init_thread)

        self._data_init_thread.started.connect(self._data_init_worker.run)
        self._data_init_worker.result_signal.connect(self.receive_init_data)
        self._data_init_worker.finished_signal.connect(self._on_data_init_finished)
        self._data_init_worker.finished_signal.connect(self._data_init_thread.quit)
        self._data_init_worker.finished_signal.connect(self._data_init_worker.deleteLater)
        self._data_init_thread.finished.connect(self._data_init_thread.deleteLater)

        self._data_init_thread.start()

    def receive_init_data(
        self,
        pac_path: str,
        points: dict,
        faces: dict,
        morph_data: dict,
        custom_sliders: list,
        pac_mesh=None
    ):
        self.original_pac_path = pac_path
        self.original_points = points
        self.original_faces = faces
        self.morph_data = morph_data
        self.custom_sliders = custom_sliders
        self.pac_mesh = pac_mesh

        self.scene_base = None
        self.pac_submesh_names = set()

        try:
            geometries: Dict[str, trimesh.Trimesh] = {}
            for name, verts in points.items():
                fcs = faces.get(name)
                if fcs is None or len(verts) == 0 or len(fcs) == 0:
                    continue
                geom = trimesh.Trimesh(
                    vertices=verts.astype(np.float32),
                    faces=fcs.astype(np.int32),
                    process=False
                )
                geometries[name] = geom

            if geometries:
                self.scene_base = trimesh.Scene(geometries)
                self.pac_submesh_names = set(geometries.keys())
                all_v = np.vstack([g.vertices for g in geometries.values()])
                self.min_b = all_v.min(axis=0)
                self.max_b = all_v.max(axis=0)
            else:
                self.min_b = np.array([0.0, 0.0, 0.0], dtype=np.float32)
                self.max_b = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        except Exception:
            self.scene_base = None
            self.min_b = np.array([0.0, 0.0, 0.0], dtype=np.float32)
            self.max_b = np.array([0.0, 0.0, 0.0], dtype=np.float32)

    def _on_data_init_finished(self) -> None:
        self.centralWidget().installEventFilter(self)
        self._init_edge_cursor_timer()
        QTimer.singleShot(10, self._startup_step_init_ui)

    def _startup_step_init_ui(self) -> None:
        try:
            self.init_ui()
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("[STARTUP ERROR] init_ui failed:", e)
        QTimer.singleShot(10, self._startup_step_refresh_plotter)

    def _startup_step_refresh_plotter(self) -> None:
        try:
            self._refresh_active_page_plotter()
        except Exception:
            pass
        QTimer.singleShot(10, self._startup_step_reset_camera)

    def _startup_step_reset_camera(self) -> None:
        try:
            global_cam = self.camera_positions.get("global")
            if not global_cam:
                self.reset_camera_view()
        except Exception:
            self.reset_camera_view()
        QTimer.singleShot(10, self._startup_step_update_morphs)

    def _startup_step_update_morphs(self) -> None:
        try:
            self.update_all_morphs()
        except Exception:
            pass
        QTimer.singleShot(10, self._startup_step_hide_loading)

    def _startup_step_hide_loading(self) -> None:
        loading = getattr(self, "_startup_loading", None)
        self._startup_loading = None
        if not loading:
            return

        def ensure_render():
            try:
                self.update_all_morphs()
            except Exception:
                pass

        self._hide_loading(loading, on_ready_callback=ensure_render)

    # ---------- path helpers ----------

    def _char_custom_dir(self, char_id: str) -> str:
        return self.cm.char_custom_dir(char_id)

    def _char_target_mesh_dir(self, char_id: str) -> str:
        return self.cm.char_target_mesh_dir(char_id)

    @staticmethod
    def _norm_path(path: str) -> str:
        return os.path.normpath(path).replace("\\", "/")

    # ---------- defaults / language ----------

    # ---------- _refresh_3d_preview ----------

    def _refresh_3d_preview(self, refresh_sliders_ui: bool = True) -> None:
        """
        Refresh 3D preview: reload mesh data, recompute morphs, and refresh UI.
        Used when the active character's PAC or slider data changes without switching characters.
        """
        char_id = self.active_char_id
        if not char_id:
            return

        # Reset mesh state
        self.original_points = {}
        self.original_faces = {}
        self.morph_data = {}
        self.pac_mesh = None
        self.pac_submesh_names = set()
        self.scene_base = None

        # Reload mesh data
        self.init_data()

        # Refresh 3D plotter
        self._refresh_active_page_plotter()

        # Recompute morph deltas for all sliders
        for sid, info in self.sliders_info.items():
            target_path = info.get("path", "")
            if target_path and self.original_points:
                try:
                    self.compute_morph_delta(sid, target_path)
                except Exception:
                    pass

        # Refresh slider UI if requested
        if refresh_sliders_ui:
            self.refresh_slider_ui()

        # Update 3D render
        if self.scene_base:
            self.update_all_morphs()

    def _refresh_default_slider_names(self) -> None:
        if not self.active_char_id:
            return
        char = self.characters.get(self.active_char_id, {})
        if not char or not char.get("is_default", False):
            return

        prefix = self.active_char_id + "."
        for sid, info in self.sliders_info.items():
            if not sid.startswith(prefix) or not info.get("is_default", False):
                continue
            full_id = sid
            if full_id not in DEFAULT_SLIDERS:
                continue
            name_key = DEFAULT_SLIDERS[full_id].get("name_key", sid[len(prefix):])
            info["name"] = safe_text(self.languages, self.current_lang, name_key, name_key)

    def on_lang_changed(self, i: int) -> None:
        loading = self._show_loading(self.T.get("lang_loading_text", "Changing language..."))

        def do_lang_change():
            nonlocal loading
            try:
                QApplication.processEvents()
                lang = self.lang_combo.itemData(i)
                self.current_lang = lang
                self.cm.current_lang = lang
                self.T = TranslationProxy(self.languages, self.current_lang)
                self.setWindowTitle(f"{self.T['title']} - v{self.app_version} - by zyd232")
                self.save_config()
                self._refresh_default_slider_names()
                self.refresh_char_tabs()
                self._refresh_active_page_plotter()
                self.refresh_slider_ui()
                plotter = self._plotter
                if plotter:
                    plotter.show()

                def on_lang_ready():
                    try:
                        self.update_all_morphs()
                    except Exception:
                        pass

                self._hide_loading(loading, on_ready_callback=on_lang_ready)
            except Exception as e:
                import traceback
                print(f"[on_lang_changed ERROR] {e}")
                traceback.print_exc()
                self._hide_loading(loading)
                show_warning(self, self.T["msg_error"], f"语言切换失败: {e}")

        QTimer.singleShot(50, do_lang_change)

    def _load_version(self) -> str:
        version_path = os.path.join(self.resource_dir, "core", "version.txt")
        try:
            with open(version_path, "r", encoding="utf-8") as f:
                v = f.read().strip()
                return v if v else "0.0.0"
        except (OSError, ValueError):
            return "0.0.0"

    def check_files_on_startup(self) -> None:
        pass

    # ---------- config / path delegation ----------

    def generate_slider_id(self, char_id: str, name: str, avoid_set: Set[str] = None) -> str:
        return self.cm.generate_slider_id(char_id, name, avoid_set)

    def save_config(self) -> None:
        current_cam = self._get_camera_position()
        if not self.isMaximized():
            w, h = self.width(), self.height()
            window_size = [w, h] if 400 <= w <= 2560 and 300 <= h <= 1440 else None
        else:
            window_size = None
        viewer = self._plotter
        wireframe_enabled = bool(getattr(viewer, "_wireframe_enabled", False)) if viewer else False
        self.cm.save_config(current_cam, window_size, wireframe_enabled)

    def _get_camera_position(self):
        try:
            plotter = self._plotter
            if plotter:
                return [list(x) for x in plotter.camera_position]
        except Exception:
            pass
        return None

    def _save_camera_and_config(self):
        cam = self._get_camera_position()
        if cam:
            self.camera_positions["global"] = cam
        try:
            self.save_config()
        except Exception:
            pass

    # ---------- mesh validation helpers ----------

    def _get_original_mesh_signature(self) -> List[Tuple[str, int]]:
        if hasattr(self, "pac_mesh") and self.pac_mesh is not None:
            sig = get_pac_submesh_signature(self.pac_mesh)
            if sig:
                return sig
        return get_mesh_signature_from_arrays(
            getattr(self, "original_points", {}),
            getattr(self, "original_faces", {}),
        )

    def init_data(self) -> None:
        from core.data_loader_worker import StartupDataInitWorker

        char_sliders_for_worker: Dict[str, Dict[str, Any]] = {}
        for cid, sliders in self.character_sliders.items():
            if not isinstance(sliders, dict):
                continue
            full: Dict[str, Any] = {}
            for local_id, info in sliders.items():
                full[f"{cid}.{local_id}"] = info
            char_sliders_for_worker[cid] = full

        temp_worker = StartupDataInitWorker(
            self.active_char_id,
            self.characters,
            char_sliders_for_worker,
            self.char_config_dir,
            self.root_dir
        )
        temp_worker.result_signal.connect(self.receive_init_data)
        temp_worker.execute_load()

    def compute_morph_delta(
        self,
        slider_id: str,
        target_path: str,
        morph_data: Dict[str, Dict[str, np.ndarray]] = None,
        original_points: Dict[str, np.ndarray] = None,
    ) -> None:
        """
        Compute morph delta between target mesh and original points.
        
        Args:
            slider_id: Slider identifier.
            target_path: Path to target mesh (.obj or .pac).
            morph_data: Target morph_data dict. Defaults to self.morph_data.
            original_points: Target original_points dict. Defaults to self.original_points.
        """
        target_morph_data = morph_data if morph_data is not None else self.morph_data
        target_original_points = original_points if original_points is not None else self.original_points
        compute_morph_delta(target_morph_data, slider_id, target_path, target_original_points)

    # ---------- UI init ----------
    # (init_ui and related UI methods now provided by MainWindowUIMixin)

    def on_resize_stable_update_plotter(self):
        plotter = getattr(self, "_plotter", None)
        if plotter is not None:
            try:
                plotter.update()
            except Exception:
                pass

    def on_resize_stable_save_config(self):
        try:
            self.save_config()
        except Exception:
            pass

    # ---------- switch character ----------

    def _switch_to_character_by_id(self, char_id: str):
        if char_id == self.active_char_id:
            return

        self._save_camera_and_config()

        loading = self._show_loading(self.T.get("switch_loading_text", "Switching character..."))

        def do_switch():
            nonlocal loading
            QApplication.processEvents()

            def ensure_render_on_switch():
                try:
                    self.update_all_morphs()
                except Exception:
                    pass

            try:
                self.switch_character(char_id, loading=None)
            finally:
                self._hide_loading(loading, on_ready_callback=ensure_render_on_switch)
                loading = None

        QTimer.singleShot(80, do_switch)

    def switch_character(self, char_id: str, loading: "LoadingOverlay" = None, force_refresh: bool = False):
        if char_id == self.active_char_id and not force_refresh:
            return

        self._save_current_wireframe_state()

        if self.active_char_id:
            cam = self._get_camera_position()
            if cam:
                self.camera_positions["global"] = cam

        if self.active_char_id:
            self._sync_sliders_to_config(self.active_char_id)

        self.active_char_id = char_id
        self.cm.active_char_id = char_id
        char = self.characters[char_id]
        self.original_pac_path = char.get("original_pac_path", "")
        self.custom_dir = self.cm.char_custom_dir(char_id)
        self.cm.ensure_char_dirs(char_id)

        self.cm._load_sliders_for_character(char_id)

        self.original_points = {}
        self.original_faces = {}
        self.morph_data = {}
        self.pac_mesh = None
        self.pac_submesh_names = set()
        self.scene_base = None

        self.init_data()

        char_list = list(self.characters.keys())
        if char_id in char_list:
            index = char_list.index(char_id)
            self.char_stack.setCurrentIndex(index)
            self._set_active_tab(index)

        self._refresh_active_page_plotter()
        self.refresh_slider_ui()

        if self.scene_base:
            self.update_all_morphs()

        page_index = self.char_stack.currentIndex()
        is_default_char = self.characters.get(char_id, {}).get("is_default", False)
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(
            lambda idx=page_index, default=is_default_char: self._init_splitter_by_index(idx, default)
        )
        timer.start(50)
        self._splitter_timers.append(timer)

        self._sync_outfits_panel_for_char(char_id)
        self.save_config()

    def _sync_sliders_to_config(self, char_id: str):
        self.cm.sync_sliders_to_config(char_id)

    def _adjust_outfits_window_width(self, show_panel: bool):
        if self.isMaximized():
            return
        outfit_w = 240
        w = self.width()
        if show_panel:
            if w < 1600:
                self.resize(w + outfit_w, self.height())
        else:
            if w > 1100:
                self.resize(w - outfit_w, self.height())

    # ---------- Outfits handlers (delegated to OutfitManager) ----------

    def _on_outfit_activated(self, original_path: str, mod_path: str):
        self.outfit_mgr.activate_outfit(original_path, mod_path)

    def _on_outfit_deactivated(self, original_path: str):
        self.outfit_mgr.deactivate_outfit()

    def _on_outfits_unload_all(self):
        char_id = self.active_char_id or ""
        self.outfit_mgr.unload_all_outfits(char_id)
        # Refresh slider UI to properly remove the Outfits panel
        # and hide the toggle button when no outfits remain
        self.refresh_slider_ui()

    # ---------- character CRUD ----------

    def add_character(self):
        existing_ids = list(self.characters.keys())
        dlg = AddCharacterDialog(self.T, existing_ids, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        result = dlg.get_result()
        if not result:
            return

        name, char_id, pac_path, mod_path = result

        viewer_before = self._plotter
        saved_wireframe = bool(getattr(viewer_before, "_wireframe_enabled", False)) if viewer_before else False

        char_orig_dir = self.cm.char_original_mesh_dir(char_id)
        final_pac = self.cm.ensure_file_in_project(pac_path, char_orig_dir)

        self.characters[char_id] = {
            "name": name,
            "id": char_id,
            "original_pac_path": final_pac,
            "mod_path": mod_path,
        }

        prev_cam = self._get_camera_position()
        prev_center = None
        if hasattr(self, "min_b") and hasattr(self, "max_b"):
            prev_center = [
                float((self.min_b[0] + self.max_b[0]) / 2.0),
                float((self.min_b[1] + self.max_b[1]) / 2.0),
                float((self.min_b[2] + self.max_b[2]) / 2.0),
            ]

        self.camera_positions["global"] = None

        self.refresh_char_tabs()
        self.switch_character(char_id)

        if (prev_cam and prev_center
                and hasattr(self, "min_b") and hasattr(self, "max_b")
                and isinstance(prev_cam, (list, tuple))
                and len(prev_cam) == 2):

            new_center = [
                float((self.min_b[0] + self.max_b[0]) / 2.0),
                float((self.min_b[1] + self.max_b[1]) / 2.0),
                float((self.min_b[2] + self.max_b[2]) / 2.0),
            ]

            prev_eye = prev_cam[0]
            prev_target = prev_cam[1]

            if (isinstance(prev_eye, (list, tuple)) and len(prev_eye) >= 3
                    and isinstance(prev_target, (list, tuple)) and len(prev_target) >= 3):

                dx = prev_eye[0] - prev_center[0]
                dy = prev_eye[1] - prev_center[1]
                dz = prev_eye[2] - prev_center[2]

                new_eye = [new_center[0] + dx, new_center[1] + dy, new_center[2] + dz]

                viewer = self._plotter
                if viewer:
                    new_cam = [new_eye, new_center]
                    viewer.set_camera_position(new_cam)
                    self.camera_positions["global"] = new_cam

        current_viewer = self._plotter
        if current_viewer:
            current_viewer.set_wireframe(saved_wireframe)
            self._sync_wireframe_button(saved_wireframe)

    def sort_characters(self):
        if len(self.characters) <= 1:
            return

        items = []
        for cid, c in self.characters.items():
            items.append({
                "id": cid,
                "name": c.get("name", cid),
                "char_id": c.get("id", cid),
            })

        dlg = CharacterSortDialog(self.T, items, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        new_order = dlg.get_order()
        if not new_order:
            return

        self._save_current_wireframe_state()
        cam = self._get_camera_position()
        if cam:
            self.camera_positions["global"] = cam

        new_characters: Dict[str, Dict[str, Any]] = {}
        for cid in new_order:
            if cid in self.characters:
                new_characters[cid] = self.characters[cid]
        self.characters = new_characters
        self.cm.characters = new_characters

        self.save_config()
        self.refresh_char_tabs()
        self._refresh_active_page_plotter()
        self.refresh_slider_ui()

        if self.scene_base:
            self.update_all_morphs()

    def _cleanup_old_pac_files(self, char_id: str, keep_pac_path: str) -> None:
        orig_dir = self.cm.char_original_mesh_dir(char_id)
        if not os.path.isdir(orig_dir):
            return
        keep_abs = os.path.abspath(keep_pac_path)
        try:
            for fname in os.listdir(orig_dir):
                if not fname.lower().endswith(".pac"):
                    continue
                fpath = os.path.abspath(os.path.join(orig_dir, fname))
                if fpath == keep_abs:
                    continue
                try:
                    if os.path.isfile(fpath):
                        os.remove(fpath)
                except OSError:
                    pass
        except OSError:
            pass

    def edit_character(self, char_id: str):
        if char_id not in self.characters:
            return

        if self._check_outfits_block():
            return

        existing_ids = list(self.characters.keys())
        dlg = EditCharacterDialog(self.T, self.characters[char_id], existing_ids, self.root_dir, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        result = dlg.get_result()
        if not result:
            return

        name, new_id, pac_path, mod_path = result
        old_id = char_id

        self._save_current_wireframe_state()

        loading = None
        old_pac_path = self.characters.get(old_id, {}).get("original_pac_path", "")
        if pac_path and old_pac_path and os.path.abspath(pac_path) != os.path.abspath(old_pac_path):
            pac_error = validate_pac_compatibility(
                pac_path,
                old_pac_path,
                translation_fn=lambda key, fallback: self.T.get(key, fallback),
            )
            if pac_error:
                show_warning(self, self.T.get("mesh_validation_title", "PAC File Incompatible"), pac_error)
                return

        if new_id != old_id:
            loading = self._show_loading(self.T.get("switch_loading_text", "Switching character, please wait..."))
            self._move_char_dir(self.cm.char_original_mesh_dir(old_id), self.cm.char_original_mesh_dir(new_id))
            self._move_char_dir(self.cm.char_target_mesh_dir(old_id), self.cm.char_target_mesh_dir(new_id))
            old_config = self.cm.char_config_path(old_id)
            new_config = self.cm.char_config_path(new_id)
            if os.path.exists(old_config) and not os.path.exists(new_config):
                try:
                    shutil.move(old_config, new_config)
                except (OSError, shutil.Error):
                    pass

            old_orig_dir = self.cm.char_original_mesh_dir(old_id)
            new_orig_dir = self.cm.char_original_mesh_dir(new_id)
            pac_abs = os.path.abspath(pac_path)

            if pac_abs.startswith(os.path.abspath(old_orig_dir) + os.sep):
                remainder = os.path.relpath(pac_abs, os.path.abspath(old_orig_dir))
                pac_path = os.path.join(new_orig_dir, remainder)

        char_orig_dir = self.cm.char_original_mesh_dir(new_id)
        final_pac = self.cm.ensure_file_in_project(pac_path, char_orig_dir)

        if new_id != old_id:
            old_target = self.cm.char_target_mesh_dir(old_id)
            new_target = self.cm.char_target_mesh_dir(new_id)
            old_target_abs = os.path.abspath(old_target)
            new_target_abs = os.path.abspath(new_target)

            def remap_path(path: str) -> str:
                if not path:
                    return path
                p_abs = os.path.abspath(path)
                if p_abs.startswith(old_target_abs + os.sep):
                    rel = os.path.relpath(p_abs, old_target_abs)
                    return os.path.normpath(os.path.join(new_target_abs, rel))
                p_text = p_abs.replace(os.sep, "/")
                if "/target_mesh/" + old_id + "/" in p_text:
                    new_text = p_text.replace("/target_mesh/" + old_id + "/", "/target_mesh/" + new_id + "/")
                    return new_text.replace("/", os.sep)
                return path

            new_sliders_info = {}
            for sid, info in self.sliders_info.items():
                ic = info.copy()
                ic["path"] = remap_path(ic.get("path", ""))
                new_sid = (new_id + "." + sid[len(old_id) + 1:]) if sid.startswith(old_id + ".") else sid
                new_sliders_info[new_sid] = ic
            self.sliders_info.clear()
            self.sliders_info.update(new_sliders_info)

            sliders = self.character_sliders.get(old_id, {})
            new_sliders = {}
            for local_id, info in (sliders or {}).items():
                if not isinstance(info, dict):
                    new_sliders[local_id] = info
                else:
                    s = info.copy()
                    s["path"] = remap_path(s.get("path", ""))
                    new_sliders[local_id] = s

            del self.characters[old_id]
            self.character_sliders.pop(old_id, None)
            self.character_sliders[new_id] = new_sliders

            if self.active_char_id == old_id:
                self.active_char_id = new_id

        old_pac = self.characters.get(new_id, {}).get("original_pac_path", "")
        old_char = self.characters.get(old_id, {})
        self.characters[new_id] = {
            "name": name,
            "id": new_id,
            "is_default": old_char.get("is_default", False),
            "original_pac_path": final_pac,
            "mod_path": mod_path,
        }

        self._cleanup_old_pac_files(new_id, final_pac)
        self.save_config()

        if loading:
            QTimer.singleShot(100, lambda: self._do_edit_after_loading_with_loading(new_id, loading))
        else:
            cam = self._get_camera_position()
            if cam:
                self.camera_positions["global"] = cam

            pac_changed = (old_pac and final_pac and
                           os.path.abspath(old_pac) != os.path.abspath(final_pac))
            if pac_changed:
                self._refresh_3d_preview(refresh_sliders_ui=True)
            else:
                self.switch_character(new_id)
                self.refresh_char_tabs()
                self._refresh_active_page_plotter()
                self.refresh_slider_ui()

    def _do_edit_after_loading_with_loading(self, new_id: str, loading: "LoadingOverlay"):
        self.switch_character(new_id)
        self.refresh_char_tabs()
        self.refresh_slider_ui()

        def ensure_render_after_edit():
            try:
                self.update_all_morphs()
            except Exception:
                pass

        self._hide_loading(loading, on_ready_callback=ensure_render_after_edit)

    def _dir_referenced_by_others(self, dir_path: str, exclude_char_id: str) -> bool:
        """
        Check if the given directory is referenced by any character other than exclude_char_id.
        Returns True if referenced (should NOT delete), False otherwise.
        """
        abs_dir = os.path.abspath(dir_path)
        for cid, c in self.characters.items():
            if cid == exclude_char_id:
                continue
            pac_path = c.get("original_pac_path", "")
            if pac_path and os.path.abspath(pac_path).startswith(abs_dir + os.sep):
                return True
            slider_dir = self.character_sliders.get(cid, {})
            for sid, info in slider_dir.items():
                if isinstance(info, dict):
                    s_path = info.get("path", "")
                    if s_path and os.path.abspath(s_path).startswith(abs_dir + os.sep):
                        return True
        return False

    @staticmethod
    def _move_char_dir(src_dir: str, dst_dir: str):
        if not os.path.exists(src_dir) or os.path.exists(dst_dir):
            return
        os.makedirs(dst_dir, exist_ok=True)
        for item in os.listdir(src_dir):
            s = os.path.join(src_dir, item)
            d = os.path.join(dst_dir, item)
            shutil.move(s, d)
        try:
            os.rmdir(src_dir)
        except OSError:
            pass

    def delete_character(self, char_id: str):
        c = self.characters.get(char_id)
        if not c:
            return

        if c.get("is_default", False):
            show_warning(self, self.T["msg_error"], self.T.get("char_del_default_protected", "Default characters cannot be deleted."))
            return
        if len(self.characters) <= 1:
            show_warning(self, self.T["msg_error"], self.T.get("char_del_last_protected", "Cannot delete the last character."))
            return

        reply = show_question(
            self,
            self.T["char_del_title"],
            self.T.get('char_del_confirm', 'Delete character "{name}" and all related files?').format(name=c["name"]),
            yes_text=self.T["btn_yes"],
            no_text=self.T["btn_no"],
        )
        if not reply:
            return

        char_id_for_delete = char_id

        self._save_current_wireframe_state()

        viewer_before_delete = self._plotter
        saved_camera_before_delete = None
        saved_wireframe_before_delete = bool(getattr(viewer_before_delete, "_wireframe_enabled", False)) if viewer_before_delete else False
        if viewer_before_delete:
            cam = self._get_camera_position()
            if cam:
                saved_camera_before_delete = cam

        self._save_camera_and_config()

        loading = self._show_loading(self.T.get("deleting_character_text", "Deleting character..."))

        def do_delete():
            nonlocal loading
            QApplication.processEvents()

            try:
                if self.active_char_id == char_id_for_delete:
                    new_active = next((cid for cid in self.characters if cid != char_id_for_delete), None)
                    self.active_char_id = new_active

                orig_dir = self.cm.char_original_mesh_dir(char_id_for_delete)
                target_dir = self.cm.char_target_mesh_dir(char_id_for_delete)

                for d in (orig_dir, target_dir):
                    if not os.path.exists(d):
                        continue
                    if self._dir_referenced_by_others(d, exclude_char_id=char_id_for_delete):
                        continue
                    try:
                        shutil.rmtree(d)
                    except OSError:
                        pass

                char_config_file = self.cm.char_config_path(char_id_for_delete)
                if os.path.exists(char_config_file):
                    try:
                        os.remove(char_config_file)
                    except OSError:
                        pass

                del self.characters[char_id_for_delete]
                self.character_sliders.pop(char_id_for_delete, None)
                
                # Only remove sliders belonging to the deleted character
                prefix = char_id_for_delete + "."
                to_remove = [sid for sid in self.sliders_info if sid.startswith(prefix)]
                for sid in to_remove:
                    del self.sliders_info[sid]
                
                self.morph_data.clear()

                # BUG FIX: If the deleted character was active and we switched to a new character,
                # we need to reload that character's sliders from its config file into BOTH
                # character_sliders AND sliders_info before calling switch_character.
                # Otherwise, switch_character -> _sync_sliders_to_config will clear
                # character_sliders[new_active] (since sliders_info is empty for that char),
                # and the slider data will be lost when save_config writes the empty state to disk.
                if self.active_char_id and self.active_char_id != char_id_for_delete:
                    new_char_config_file = self.cm.char_config_path(self.active_char_id)
                    if os.path.exists(new_char_config_file):
                        try:
                            with open(new_char_config_file, "r", encoding="utf-8") as f:
                                char_data = json.load(f)
                            if isinstance(char_data, dict):
                                sliders_from_file = char_data.get("sliders", {})
                                if isinstance(sliders_from_file, dict) and sliders_from_file:
                                    self.character_sliders[self.active_char_id] = sliders_from_file
                                    # Also populate sliders_info so _sync_sliders_to_config has data
                                    new_prefix = self.active_char_id + "."
                                    for local_id, info in sliders_from_file.items():
                                        if isinstance(info, dict):
                                            full_sid = f"{new_prefix}{local_id}"
                                            self.sliders_info[full_sid] = info
                        except (json.JSONDecodeError, OSError):
                            pass

                self.refresh_char_tabs()

                loading.update_parent_geometry()
                loading.raise_()
                loading.show()
                QApplication.processEvents()

                if self.active_char_id and self.active_char_id in self.characters:
                    self.switch_character(self.active_char_id, loading=None, force_refresh=True)

                def on_ready_after_delete():
                    try:
                        current_viewer = self._plotter
                        if current_viewer and saved_camera_before_delete:
                            current_viewer.set_camera_position(saved_camera_before_delete)
                            self.camera_positions["global"] = saved_camera_before_delete
                        if current_viewer:
                            current_viewer.set_wireframe(saved_wireframe_before_delete)
                            self._sync_wireframe_button(saved_wireframe_before_delete)
                    except Exception:
                        pass
                    QTimer.singleShot(500, lambda: self.update_all_morphs())

                self._hide_loading(loading, on_ready_callback=on_ready_after_delete)
            except Exception as e:
                import traceback
                print(f"[delete_character ERROR] {e}")
                traceback.print_exc()
                self._hide_loading(loading)
                show_warning(self, self.T["msg_error"], f"删除角色失败: {e}")

        QTimer.singleShot(80, do_delete)

    def reset_character_to_default(self):
        char_id = self.active_char_id
        char = self.characters[char_id]
        if not char.get("is_default", False):
            return

        reply = show_question(
            self,
            self.T.get("reset_char_title", "Reset Character"),
            self.T.get('reset_char_msg', 'Reset "{name}" to default settings?\nThis will restore all character properties, clear custom sliders, and reset all slider values to 0.').format(name=char["name"]),
            yes_text=self.T["btn_yes"],
            no_text=self.T["btn_no"],
        )
        if not reply:
            return

        new_pac = os.path.join(self.root_dir, "original_mesh", DEFAULT_CHAR_ID, DEFAULT_PAC_NAME)

        self.characters[char_id] = {
            "name": DEFAULT_CHAR_NAME,
            "id": DEFAULT_CHAR_ID,
            "is_default": True,
            "original_pac_path": new_pac,
            "mod_path": DEFAULT_MOD_PATH,
        }

        self.character_sliders[char_id] = {}
        self.sliders_info.clear()
        self.morph_data.clear()

        self._refresh_3d_preview(refresh_sliders_ui=True)

    # ---------- reset_all_sliders ----------

    def reset_all_sliders(self):
        char_id = self.active_char_id
        char = self.characters.get(char_id)
        if not char or not char.get("is_default", False):
            return

        msg = self.T.get("reset_all_msg", "Reset all character settings and sliders to default?")
        title = self.T.get("reset_all_title", "Reset All")
        if not show_question(self, title, msg):
            return

        # Deactivate current outfit if any (also removes outfit meshes from viewer)
        if self.active_outfit_path:
            self.outfit_mgr.deactivate_outfit()

        # Remove outfit directories for this character (same as Unload All Outfits)
        dirs_to_remove = [
            os.path.join(self.root_dir, "original_outfit", char_id),
            os.path.join(self.root_dir, "exported_outfit", char_id),
        ]
        for d in dirs_to_remove:
            if os.path.isdir(d):
                try:
                    shutil.rmtree(d)
                except Exception:
                    pass

        new_pac = os.path.join(self.root_dir, "original_mesh", DEFAULT_CHAR_ID, DEFAULT_PAC_NAME)

        self.characters[char_id] = {
            "name": DEFAULT_CHAR_NAME,
            "id": DEFAULT_CHAR_ID,
            "is_default": True,
            "original_pac_path": new_pac,
            "mod_path": DEFAULT_MOD_PATH,
        }

        new_sliders_info: Dict[str, Dict[str, Any]] = {}
        for sid, info in self.sliders_info.items():
            if info.get("is_default", False):
                s = info.copy()
                s["current_value"] = 0.0
                new_sliders_info[sid] = s
        self.sliders_info.clear()
        self.sliders_info.update(new_sliders_info)

        self.morph_data.clear()
        self.original_points = {}
        self.pac_mesh = None
        self.pac_submesh_names = set()
        self.scene_base = None
        self.character_sliders[char_id] = {}

        self.cm._ensure_default_sliders_in_config(char_id)
        self.cm._load_sliders_for_character(char_id)
        self._refresh_3d_preview(refresh_sliders_ui=True)
        
        # Sync outfits toggle button visibility (hide it since outfits are removed)
        self._sync_outfits_panel_for_char(char_id)

    # ---------- outfit block guard ----------

    def _check_outfits_block(self) -> bool:
        """
        Check whether the current character has outfit data.
        Returns True if blocked (outfits exist), False if safe to proceed.
        """
        char_id = self.active_char_id
        if not char_id:
            return False
        if hasattr(self, 'outfit_mgr') and self.outfit_mgr:
            if self.outfit_mgr.has_outfits_for_char(char_id):
                show_warning(
                    self,
                    self.T.get("outfit_block_title", "Operation Not Allowed"),
                    self.T.get("outfit_block_msg",
                        "Cannot perform this operation while the character has Outfit data.\n\n"
                        "To proceed, please \"Unload All Outfits\" first."),
                )
                return True
        return False

    # ---------- guide_add_slider ----------

    def guide_add_slider(self):
        if not self.active_char_id:
            return

        if self._check_outfits_block():
            return

        existing_ids = list(self.sliders_info.keys())

        dlg = AddSliderDialog(self.T, existing_ids, self.active_char_id, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        result = dlg.get_result()
        if not result:
            return

        name, full_id, mesh_path, vmin, vmax = result

        original_sig = self._get_original_mesh_signature()
        error_msg = validate_target_mesh_against_original(
            mesh_path,
            original_sig,
            translation_fn=lambda key, fallback: self.T.get(key, fallback),
        )
        if error_msg:
            show_warning(self, self.T.get("mesh_validation_title", "Target Mesh Incompatible"), error_msg)
            return

        add_result, err = self.custom_slider_mgr.add_custom_slider(
            char_id=self.active_char_id,
            slider_name=name,
            min_v=vmin,
            max_v=vmax,
            obj_path=mesh_path,
            existing_ids=existing_ids,
        )

        if not add_result or err:
            show_critical(self, self.T["msg_error"], err or "Failed to add slider.")
            return

        info = self.sliders_info.get(add_result)
        final_path = self.custom_slider_mgr.to_absolute_path(info.get("path", "")) if info else ""
        if final_path:
            self.compute_morph_delta(add_result, final_path)

        # 如果当前有激活的 outfit，为新的自定义滑块重新计算 outfit morph delta
        self._refresh_outfit_morph_for_slider(add_result)

        self.save_config()
        self.refresh_slider_ui()

    def _refresh_outfit_morph_for_slider(self, sid: str) -> None:
        """
        当自定义滑块添加/修改/删除后，如果当前有激活的 outfit，
        需要重新计算该滑块对应的 outfit morph delta。
        
        使用通用路径提取逻辑：从滑块 path 中提取 target_mesh/之后、char_id之后、
        扩展名之前的部分作为 exported_outfit 的路径段。
        """
        if not hasattr(self, 'outfit_mgr') or not self.outfit_mgr:
            return
        
        h = self.outfit_mgr.host
        if not h.active_outfit_path or not h.outfit_original_points:
            return
        
        info = h.sliders_info.get(sid)
        if not info:
            return
        
        # 从滑块 path 提取路径段（兼容绝对路径和相对路径）
        slider_path = info.get("path", "")
        normalized = slider_path.replace("\\", "/")
        # 查找 target_mesh/ 的位置（兼容绝对路径和相对路径）
        tm_idx = normalized.find("target_mesh/")
        if tm_idx >= 0:
            normalized = normalized[tm_idx + len("target_mesh/"):]
        parts = normalized.split("/", 1)
        after_char_id = parts[1] if len(parts) > 1 else normalized
        slider_segment = os.path.splitext(after_char_id)[0]
        
        char_id = h.active_char_id or ""
        original_path = h.active_outfit_path
        mod_path = h.active_outfit_mod_path or ""
        
        pac_base = os.path.basename(original_path)
        base_no_ext = os.path.splitext(pac_base)[0]
        mod_dir = os.path.dirname(mod_path)
        
        exported_dir = os.path.join(
            h.root_dir, "exported_outfit", char_id, slider_segment
        )
        
        candidates = []
        c1 = os.path.join(exported_dir, mod_dir, pac_base)
        if os.path.exists(c1):
            candidates.append(c1)
        c2 = os.path.join(exported_dir, mod_dir, base_no_ext + ".obj")
        if os.path.exists(c2):
            candidates.append(c2)
        c3 = os.path.join(exported_dir, mod_dir, base_no_ext + ".pac")
        if os.path.exists(c3):
            candidates.append(c3)
        
        if candidates:
            h.compute_morph_delta(
                sid,
                candidates[0],
                h.outfit_morph_data,
                h.outfit_original_points,
            )
            # 更新 outfit 显示
            self.outfit_mgr.update_outfit_morphs()

    # ---------- slider CRUD ----------

    def _reselect_slider_file(self, sid: Optional[str]):
        if not sid or sid not in self.sliders_info:
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            self.T.get("file_dialog_select_target_mesh", "Select Target Mesh"),
            self.cm.char_target_mesh_dir(self.active_char_id),
            MESH_FILE_FILTER,
        )
        if not path:
            return

        err = self.custom_slider_mgr.reselect_slider_file(sid, path)
        if err:
            show_critical(self, self.T["msg_error"], err)
            return

        info = self.sliders_info[sid]
        final_path = self.custom_slider_mgr.to_absolute_path(info.get("path", ""))
        if final_path:
            self.compute_morph_delta(sid, final_path)

        self.save_config()
        self.refresh_slider_ui()

    def _reselect_pac_for_character(self, char_id: str):
        if char_id not in self.characters:
            return
        char_orig_dir = self.cm.char_original_mesh_dir(char_id)
        os.makedirs(char_orig_dir, exist_ok=True)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Original PAC",
            "",
            PAC_FILE_FILTER,
        )
        if not path:
            return
        final_pac = self.cm.ensure_file_in_project(path, char_orig_dir)
        self.characters[char_id]["original_pac_path"] = final_pac
        self.save_config()
        self.refresh_slider_ui()

    def rename_slider(self, sid: Optional[str]):
        if not sid or sid not in self.sliders_info:
            return

        dlg = RangeInputDialog(
            self.T,
            self,
            title=self.T["dlg_edit_title"],
            label=self.T["dlg_edit_msg"],
            text=self.sliders_info[sid].get("name", ""),
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        new_name = dlg.text().strip()
        if not new_name:
            return

        ok = self.custom_slider_mgr.rename_custom_slider(sid, new_name)
        if not ok:
            return

        self.save_config()
        self.refresh_slider_ui()

    def edit_slider(self, sid: Optional[str]):
        if not sid or sid not in self.sliders_info:
            return

        info = self.sliders_info[sid]
        if info.get("is_default", False):
            return

        if self._check_outfits_block():
            return

        existing_ids = list(self.sliders_info.keys())
        dlg = EditSliderDialog(
            self.T,
            existing_ids,
            self.active_char_id,
            info.get("name", ""),
            sid,
            info.get("path", ""),
            float(info.get("min", 0.0)),
            float(info.get("max", 100.0)),
            self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        result = dlg.get_result()
        if not result:
            return

        new_name, new_full_id, new_path, new_min, new_max = result

        original_sig = self._get_original_mesh_signature()
        error_msg = validate_target_mesh_against_original(
            new_path,
            original_sig,
            translation_fn=lambda key, fallback: self.T.get(key, fallback),
        )
        if error_msg:
            show_warning(self, self.T.get("mesh_validation_title", "Target Mesh Incompatible"), error_msg)
            return

        self.morph_data.pop(sid, None)

        new_id, err = self.custom_slider_mgr.edit_custom_slider(
            full_sid=sid,
            new_name=new_name,
            new_full_id=new_full_id,
            new_path=new_path,
            new_min=new_min,
            new_max=new_max,
        )

        if not new_id or err:
            show_critical(self, self.T["msg_error"], err or "Failed to edit slider.")
            return

        final_path = self.custom_slider_mgr.to_absolute_path(
            self.sliders_info[new_id].get("path", "")
        )
        if final_path:
            self.compute_morph_delta(new_id, final_path)

        # 如果当前有激活的 outfit，为修改后的滑块重新计算 outfit morph delta
        self._refresh_outfit_morph_for_slider(new_id)

        self.save_config()
        self.refresh_slider_ui()

    def change_slider_morph(self, sid: Optional[str]):
        if not sid or sid not in self.sliders_info:
            return

        info = self.sliders_info[sid]
        if info.get("is_default", False):
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            self.T["dlg_select_morph_title"],
            self.cm.char_target_mesh_dir(self.active_char_id),
            MESH_FILE_FILTER,
        )
        if not path:
            return

        final_candidate = os.path.abspath(path)
        old_path = info.get("path", "")
        if old_path and os.path.abspath(old_path) == final_candidate:
            return

        err = self.custom_slider_mgr.change_slider_morph(sid, path)
        if err:
            show_critical(self, self.T["msg_error"], err)
            return

        new_info = self.sliders_info[sid]
        final_path = self.custom_slider_mgr.to_absolute_path(new_info.get("path", ""))
        if final_path:
            self.compute_morph_delta(sid, final_path)

        # 如果当前有激活的 outfit，为修改后的滑块重新计算 outfit morph delta
        self._refresh_outfit_morph_for_slider(sid)

        self.save_config()
        self.refresh_slider_ui()
        self.update_all_morphs()

    def remove_slider(self, sid: Optional[str]):
        if not sid or sid not in self.sliders_info:
            return

        info = self.sliders_info[sid]
        if info.get("is_default", False):
            return

        if self._check_outfits_block():
            return

        char_id = self.active_char_id or ""
        ok = self.custom_slider_mgr.delete_custom_slider(char_id, sid)
        if not ok:
            return

        self.save_config()
        self.refresh_slider_ui()
        self.update_all_morphs()

    # ---------- morph update (MeshViewer) ----------

    def update_all_morphs(self):
        viewer = self._plotter
        if not viewer:
            return

        morphed_points = apply_morphs(
            self.original_points,
            self.morph_data,
            self.sliders_info
        )

        for name, base in self.mesh_viewer_data.items():
            if name not in morphed_points:
                continue
            viewer.update_mesh_vertices(name, morphed_points[name])

        # Update outfit morphs if active
        if (
            hasattr(self, "outfit_mgr")
            and self.outfit_mgr
            and self.outfit_mgr.host.active_outfit_path
        ):
            self.outfit_mgr.update_outfit_morphs()

    # ---------- export OBJ ----------

    def save_model_obj(self):
        page = self._current_page()
        btn_obj = getattr(page, "btn_obj", None) if page else None
        if not btn_obj:
            return
        btn_obj.setText(self.T["processing"])
        btn_obj.setEnabled(False)
        QApplication.processEvents()
        char_id = self.active_char_id or "default"
        out_dir = os.path.join(self.root_dir, "exported_mesh")
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        out_path = os.path.join(out_dir, f"{char_id}.obj")

        try:
            self._export_current_mesh_to_obj(out_path)
            msg = DarkMessageBox(self)
            msg.setWindowTitle(self.T["msg_success"])
            msg.setText(f"{self.T['msg_save_to']}\n{out_path}")
            msg.setIcon(QMessageBox.Icon.Information)

            ok_btn = msg.addButton(self.T["btn_ok"], QMessageBox.ButtonRole.AcceptRole)
            open_btn = msg.addButton(self.T["btn_open_folder"], QMessageBox.ButtonRole.ActionRole)

            ok_btn.clicked.connect(lambda: setattr(msg, "_clicked_button", ok_btn))
            open_btn.clicked.connect(lambda: setattr(msg, "_clicked_button", open_btn))

            msg.exec()
            if msg.clickedButton() is open_btn:
                subprocess.Popen(["explorer", os.path.dirname(out_path)])
        except Exception as e:
            show_critical(self, self.T["msg_error"], str(e))
        finally:
            btn_obj.setText(self.T["btn_export_obj"])
            btn_obj.setEnabled(True)

    def _export_current_mesh_to_obj(self, obj_path: str):
        if not self.pac_mesh or not hasattr(self.pac_mesh, "submeshes"):
            return

        material_map: Dict[str, str] = {}
        uv_map: Dict[str, np.ndarray] = {}
        normal_map: Dict[str, np.ndarray] = {}

        for sm in self.pac_mesh.submeshes:
            mat_name = getattr(sm, "material", None) or getattr(sm, "material_name", "")
            if mat_name:
                material_map[sm.name] = mat_name

            uvs = getattr(sm, "uvs", None)
            if uvs and isinstance(uvs, (list, tuple)) and len(uvs) > 0:
                uv_map[sm.name] = np.asarray(uvs, dtype=np.float64)

            normals = getattr(sm, "normals", None)
            if normals and isinstance(normals, (list, tuple)) and len(normals) > 0:
                normal_map[sm.name] = np.asarray(normals, dtype=np.float64)

        morphed_meshes: Dict[str, Dict[str, np.ndarray]] = {}
        for name, base in self.mesh_viewer_data.items():
            if name not in self.original_points:
                continue
            orig = self.original_points[name]
            morphed = orig.copy()

            for sid, info in self.sliders_info.items():
                md = self.morph_data.get(sid)
                cv = info.get("current_value", 0.0)
                if md is not None and name in md:
                    morphed += md[name] * (cv / 100.0)

            morphed_meshes[name] = {
                "vertices": morphed,
                "faces": base["faces"],
            }

        from core.obj_exporter import export_mesh_data_to_obj
        export_mesh_data_to_obj(morphed_meshes, material_map, uv_map, normal_map, obj_path)

    # ---------- ModExportWorker (async MOD export) ----------

    class ModExportWorker(QObject):
        """Worker that exports MOD folder in a background thread with progress signals."""
        from PyQt6.QtCore import pyqtSignal
        progress = pyqtSignal(str, int)  # status_text, percent (0-100)
        finished = pyqtSignal(str, str)  # mod_dir, error_message (empty=success)
        cancel_requested = pyqtSignal()  # Signal to request cancellation

        def __init__(self, char_id: str, original_pac: str, mod_path: str,
                     mod_dir: str, files_dir: str, char_name: str,
                     sliders_info: Dict[str, Dict], root_dir: str):
            super().__init__()
            self.char_id = char_id
            self.original_pac = original_pac
            self.mod_path = mod_path
            self.mod_dir = mod_dir
            self.files_dir = files_dir
            self.char_name = char_name
            self.sliders_info = sliders_info
            self.root_dir = root_dir
            self._cancelled = False
            self._executor = None
            # Pre-computed target mesh cache: {target_file_path: {submesh_name: vertices_array}}
            self._target_cache: Dict[str, Dict[str, _np.ndarray]] = {}
            # Pre-computed submesh names for each target: {target_file_path: [submesh_names]}
            self._target_submesh_names: Dict[str, List[str]] = {}

        def cancel(self):
            """Request cancellation of the export operation."""
            self._cancelled = True
            if self._executor:
                self._executor.shutdown(wait=False, cancel_futures=True)

        def _is_cancelled(self):
            """Check if cancellation was requested."""
            return self._cancelled

        def _parse_obj_lightweight(self, obj_path: str) -> Dict[str, 'Dict[str, _np.ndarray]']:
            """
            Lightweight .obj parser that extracts per-group vertices.
            Returns {group_name: {'vertices': np.ndarray}} or {'__single__': {'vertices': np.ndarray}}.
            """
            import numpy as _np
            vertices = []
            faces = []
            groups = {}  # group_name -> list of face indices
            current_group = '__single__'
            
            with open(obj_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    parts = line.strip().split()
                    if not parts:
                        continue
                    if parts[0] == 'v' and len(parts) >= 4:
                        vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
                    elif parts[0] == 'f' and len(parts) >= 4:
                        face_indices = []
                        for p in parts[1:]:
                            face_indices.append(int(p.split('/')[0]) - 1)
                        faces.append(face_indices)
                    elif parts[0] == 'o' or (parts[0] == 'g' and len(parts) > 1):
                        current_group = parts[1] if len(parts) > 1 else '__unnamed__'
                        if current_group not in groups:
                            groups[current_group] = []
                    elif parts[0] == 'g' and len(parts) == 1:
                        current_group = '__unnamed__'
                        if current_group not in groups:
                            groups[current_group] = []
            
            if not vertices:
                return {}
            
            vert_array = _np.array(vertices, dtype=_np.float32)
            
            # If no groups defined, all faces belong to __single__
            if not groups:
                groups = {'__single__': list(range(len(faces)))}
            
            result = {}
            for group_name, face_idx_list in groups.items():
                if not face_idx_list:
                    continue
                # Collect unique vertex indices for this group
                unique_indices = set()
                for fi in face_idx_list:
                    if 0 <= fi < len(faces):
                        for vi in faces[fi]:
                            if 0 <= vi < len(vert_array):
                                unique_indices.add(vi)
                if unique_indices:
                    result[group_name] = vert_array[list(unique_indices)]
            
            return result

        def _preload_target_meshes(self, exported_outfit_root: str, start_pct: int = 40, end_pct: int = 45):
            """
            Preload all target mesh files from exported_outfit into cache.
            This avoids repeated file I/O in export_single_outfit.
            
            Args:
                exported_outfit_root: Root directory to scan for mesh files.
                start_pct: Starting percentage for progress (default 40).
                end_pct: Ending percentage for progress (default 45).
            """
            import numpy as _np
            from core.pac_builder import parse_pac
            
            # Collect all files first for progress tracking
            all_files = []
            for slider_dir_name in os.listdir(exported_outfit_root):
                slider_dir = os.path.join(exported_outfit_root, slider_dir_name)
                if not os.path.isdir(slider_dir):
                    continue
                for outfit_dirpath, _, outfit_filenames in os.walk(slider_dir):
                    for fn in outfit_filenames:
                        if fn.lower().endswith(".obj") or fn.lower().endswith(".pac"):
                            all_files.append(os.path.join(outfit_dirpath, fn))
            
            total = len(all_files)
            pct_range = max(end_pct - start_pct, 1)
            
            for i, target_file in enumerate(all_files):
                # Check cancellation periodically
                if i % 10 == 0 and self._is_cancelled():
                    return
                
                fn = os.path.basename(target_file)
                try:
                    submesh_data: Dict[str, _np.ndarray] = {}
                    if fn.lower().endswith(".pac"):
                        with open(target_file, "rb") as f:
                            target_pac_bytes = f.read()
                        target_pac_mesh = parse_pac(target_pac_bytes, target_file)
                        for sm in target_pac_mesh.submeshes:
                            if sm.vertices:
                                submesh_data[sm.name] = _np.array(sm.vertices, dtype=_np.float32)
                    else:
                        # Use lightweight parser instead of trimesh
                        submesh_data = self._parse_obj_lightweight(target_file)
                    
                    if submesh_data:
                        self._target_cache[target_file] = submesh_data
                        self._target_submesh_names[target_file] = list(submesh_data.keys())
                    
                    # Emit progress with percentage proportional to files processed
                    if total > 0:
                        current_pct = start_pct + int((i + 1) / total * pct_range)
                        self.progress.emit(f"Preloading meshes... ({i+1}/{total})", current_pct)
                except Exception:
                    pass

        def run(self):
            import json as _json
            import numpy as _np
            from core.pac_builder import parse_pac, IncrementalPACBuilder
            from core.mesh_processor import compute_morph_delta

            error_msg = ""
            try:
                # ---- Step 1: Export Character Body PAC (0%-5%) ----
                # Note: This step is fast (~3-4s), so we allocate only 0%-5% of progress
                self.progress.emit("Exporting character body PAC...", 0)

                if self._is_cancelled():
                    self.finished.emit(self.mod_dir, "Cancelled by user")
                    return

                with open(self.original_pac, "rb") as f:
                    pac_bytes = f.read()
                char_pac_mesh = parse_pac(pac_bytes, self.original_pac)

                char_original_points: Dict[str, _np.ndarray] = {}
                for sm in char_pac_mesh.submeshes:
                    if sm.vertices:
                        char_original_points[sm.name] = _np.array(sm.vertices, dtype=_np.float32)

                self.progress.emit("Computing morph deltas...", 1)

                char_morph_data: Dict[str, Dict[str, _np.ndarray]] = {}
                slider_count = len(self.sliders_info)
                for i, (sid, info) in enumerate(self.sliders_info.items()):
                    if self._is_cancelled():
                        self.finished.emit(self.mod_dir, "Cancelled by user")
                        return
                    
                    target_path = info.get("path", "")
                    if not target_path or not os.path.exists(target_path):
                        continue
                    try:
                        compute_morph_delta(char_morph_data, sid, target_path, char_original_points)
                    except Exception:
                        pass
                    # Scale to 1%-3% range
                    pct = 1 + int((i + 1) / slider_count * 2)
                    self.progress.emit(f"Computing slider: {info.get('name', sid)}...", pct)

                if self._is_cancelled():
                    self.finished.emit(self.mod_dir, "Cancelled by user")
                    return

                self.progress.emit("Applying morphs...", 3)

                new_positions: Dict[str, _np.ndarray] = {}
                for name, orig in char_original_points.items():
                    morphed = orig.copy()
                    for sid, info in self.sliders_info.items():
                        md = char_morph_data.get(sid)
                        cv = info.get("current_value", 0.0)
                        if md is not None and name in md:
                            morphed += md[name] * (cv / 100.0)
                    new_positions[name] = morphed

                self.progress.emit("Building PAC file...", 4)

                inc = IncrementalPACBuilder(self.original_pac)
                pac_sm_names = [sm.name for sm in inc.original_mesh.submeshes]

                def transform_func(sm_idx, vi, orig_v):
                    pac_name = pac_sm_names[sm_idx] if sm_idx < len(pac_sm_names) else None
                    if not pac_name or pac_name not in new_positions:
                        return orig_v
                    if pac_name not in char_original_points:
                        return orig_v
                    orig_verts = char_original_points[pac_name]
                    morphed_verts = new_positions[pac_name]
                    if vi >= len(orig_verts):
                        return orig_v
                    ov = orig_verts[vi]
                    mv = morphed_verts[vi]
                    return (
                        float(orig_v[0] + mv[0] - ov[0]),
                        float(orig_v[1] + mv[1] - ov[1]),
                        float(orig_v[2] + mv[2] - ov[2]),
                    )

                inc.apply_vertex_transform(transform_func)
                pac_data = inc.build()

                game_rel_dir = os.path.join(self.files_dir, self.mod_path)
                os.makedirs(game_rel_dir, exist_ok=True)
                pac_filename = os.path.basename(self.original_pac)
                mod_pac_path = os.path.join(game_rel_dir, pac_filename)
                with open(mod_pac_path, "wb") as f:
                    f.write(pac_data)

                # ---- Step 2: Export Outfit PACs (5%-95%) ----
                self.progress.emit("Checking outfits...", 5)

                original_outfit_root = os.path.join(self.root_dir, "original_outfit", self.char_id)
                exported_outfit_root = os.path.join(self.root_dir, "exported_outfit", self.char_id)

                if os.path.isdir(original_outfit_root):
                    outfit_pac_files = []
                    for dirpath, _, filenames in os.walk(original_outfit_root):
                        for fn in filenames:
                            if fn.lower().endswith(".pac"):
                                outfit_pac_files.append(os.path.join(dirpath, fn))

                    total_outfits = len(outfit_pac_files)
                    if total_outfits > 0:
                        import threading
                        from concurrent.futures import ThreadPoolExecutor, as_completed

                        # ---- Preload all target mesh files into cache (5%-70%) ----
                        # This is the most time-consuming step (~120s for 10k+ meshes)
                        self._preload_target_meshes(exported_outfit_root, 5, 70)

                        completed_count = 0
                        count_lock = threading.Lock()

                        def export_single_outfit(outfit_pac_path: str) -> str:
                            rel_path = os.path.relpath(outfit_pac_path, original_outfit_root)
                            outfit_pac_dir = os.path.dirname(rel_path)
                            ofn = os.path.basename(outfit_pac_path)
                            base_no_ext = os.path.splitext(ofn)[0]

                            try:
                                with open(outfit_pac_path, "rb") as f:
                                    outfit_pac_bytes = f.read()
                                outfit_pac_mesh = parse_pac(outfit_pac_bytes, outfit_pac_path)
                            except Exception:
                                return ofn

                            outfit_original_points: Dict[str, _np.ndarray] = {}
                            original_submesh_names = []
                            for sm in outfit_pac_mesh.submeshes:
                                if sm.vertices:
                                    outfit_original_points[sm.name] = _np.array(sm.vertices, dtype=_np.float32)
                                    original_submesh_names.append(sm.name)

                            if not outfit_original_points:
                                return ofn

                            outfit_morph_data: Dict[str, Dict[str, _np.ndarray]] = {}
                            for sid, info in self.sliders_info.items():
                                slider_path = info.get("path", "")
                                normalized = slider_path.replace("\\", "/")
                                tm_idx = normalized.find("target_mesh/")
                                if tm_idx >= 0:
                                    normalized = normalized[tm_idx + len("target_mesh/"):]
                                parts = normalized.split("/", 1)
                                after_char_id = parts[1] if len(parts) > 1 else normalized
                                slider_ref_path = os.path.splitext(after_char_id)[0]

                                exported_dir = os.path.join(exported_outfit_root, slider_ref_path)
                                target_subdir = os.path.join(exported_dir, outfit_pac_dir) if outfit_pac_dir else exported_dir

                                candidates = []
                                c1 = os.path.join(target_subdir, ofn)
                                if os.path.exists(c1):
                                    candidates.append(c1)
                                c2 = os.path.join(target_subdir, base_no_ext + ".obj")
                                if os.path.exists(c2):
                                    candidates.append(c2)
                                c3 = os.path.join(target_subdir, base_no_ext + ".pac")
                                if os.path.exists(c3):
                                    candidates.append(c3)

                                if not candidates:
                                    continue

                                target_file = candidates[0]

                                # Use preloaded cache for target submesh names and vertices
                                cached_submeshes = self._target_cache.get(target_file)
                                if cached_submeshes is None:
                                    # Fallback: load from file if not in cache
                                    try:
                                        cached_submeshes = {}
                                        if target_file.lower().endswith(".pac"):
                                            with open(target_file, "rb") as f:
                                                target_pac_bytes = f.read()
                                            target_pac_mesh = parse_pac(target_pac_bytes, target_file)
                                            for sm in target_pac_mesh.submeshes:
                                                if sm.vertices:
                                                    cached_submeshes[sm.name] = _np.array(sm.vertices, dtype=_np.float32)
                                        else:
                                            import trimesh as _trimesh
                                            obj_data = _trimesh.load(target_file)
                                            if isinstance(obj_data, _trimesh.Scene):
                                                for geom_name, geom in obj_data.geometry.items():
                                                    if isinstance(geom, _trimesh.Trimesh):
                                                        cached_submeshes[geom_name] = geom.vertices.astype(_np.float32)
                                            elif isinstance(obj_data, _trimesh.Trimesh):
                                                cached_submeshes["__single__"] = obj_data.vertices.astype(_np.float32)
                                    except Exception:
                                        continue

                                target_submesh_names = list(cached_submeshes.keys())

                                orig_set = set(original_submesh_names)
                                target_set = set(target_submesh_names)
                                if orig_set != target_set:
                                    continue

                                # Compute morph delta directly from cached data (avoid file I/O)
                                try:
                                    deltas = {}
                                    for pac_name, orig_verts in outfit_original_points.items():
                                        if pac_name in cached_submeshes:
                                            target_verts = cached_submeshes[pac_name]
                                            if len(target_verts) == len(orig_verts):
                                                deltas[pac_name] = target_verts - orig_verts
                                    if deltas:
                                        outfit_morph_data[sid] = deltas
                                except Exception:
                                    pass

                            dest_dir = os.path.join(self.files_dir, outfit_pac_dir) if outfit_pac_dir else self.files_dir
                            os.makedirs(dest_dir, exist_ok=True)

                            if not outfit_morph_data:
                                shutil.copy2(outfit_pac_path, os.path.join(dest_dir, ofn))
                                return ofn

                            new_outfit_positions: Dict[str, _np.ndarray] = {}
                            for name, orig in outfit_original_points.items():
                                morphed = orig.copy()
                                for sid, info in self.sliders_info.items():
                                    md = outfit_morph_data.get(sid)
                                    cv = info.get("current_value", 0.0)
                                    if md is not None and name in md:
                                        morphed += md[name] * (cv / 100.0)
                                new_outfit_positions[name] = morphed

                            inc2 = IncrementalPACBuilder(outfit_pac_path)
                            pac_sm_names2 = [sm.name for sm in inc2.original_mesh.submeshes]

                            def transform_func2(sm_idx, vi, orig_v):
                                pac_name = pac_sm_names2[sm_idx] if sm_idx < len(pac_sm_names2) else None
                                if not pac_name or pac_name not in new_outfit_positions:
                                    return orig_v
                                if pac_name not in outfit_original_points:
                                    return orig_v
                                orig_verts = outfit_original_points[pac_name]
                                morphed_verts = new_outfit_positions[pac_name]
                                if vi >= len(orig_verts):
                                    return orig_v
                                ov = orig_verts[vi]
                                mv = morphed_verts[vi]
                                return (
                                    float(orig_v[0] + mv[0] - ov[0]),
                                    float(orig_v[1] + mv[1] - ov[1]),
                                    float(orig_v[2] + mv[2] - ov[2]),
                                )

                            inc2.apply_vertex_transform(transform_func2)
                            outfit_pac_data = inc2.build()

                            with open(os.path.join(dest_dir, ofn), "wb") as f:
                                f.write(outfit_pac_data)

                            return ofn

                        cpu_count = os.cpu_count() or 2
                        max_workers = min(max(2, cpu_count), 16, total_outfits)

                        self._executor = ThreadPoolExecutor(max_workers=max_workers)
                        futures = {
                            self._executor.submit(export_single_outfit, opp): opp
                            for opp in outfit_pac_files
                        }

                        for future in as_completed(futures):
                            if self._is_cancelled():
                                self._executor.shutdown(wait=False, cancel_futures=True)
                                self.finished.emit(self.mod_dir, "Cancelled by user")
                                return

                            ofn = os.path.basename(futures[future])
                            try:
                                future.result()
                            except Exception:
                                pass

                            with count_lock:
                                completed_count += 1
                                oi = completed_count
                                # Outfit export runs from 70% (after preload) to 95%
                                pct = 70 + int(oi / max(total_outfits, 1) * 25)
                                self.progress.emit(f"Exporting outfit: {ofn} ({oi}/{total_outfits})", pct)

                        self._executor.shutdown(wait=True)

                if self._is_cancelled():
                    self.finished.emit(self.mod_dir, "Cancelled by user")
                    return

                # ---- Step 3: Generate mod.json (95%-100%) ----
                self.progress.emit("Generating mod.json...", 95)

                names_list = self.char_name

                mod_json = {
                    "modinfo": {
                        "title": f"Body Slider MOD - {names_list}",
                        "name": f"Body Slider MOD - {names_list}",
                        "author": "Body Slider Pro - by zyd232",
                        "version": "1.0.0",
                        "description": f"Model modifications for {names_list}",
                        "generator": "Body Slider Pro",
                        "nexus_url": "https://www.nexusmods.com/crimsondesert/mods/2727",
                    },
                    "files_dir": "files",
                }

                with open(os.path.join(self.mod_dir, "mod.json"), "w", encoding="utf-8") as f:
                    _json.dump(mod_json, f, indent=2, ensure_ascii=False)

                self.progress.emit("Export complete!", 100)

            except Exception as e:
                error_msg = str(e)
                import traceback
                traceback.print_exc()

            self.finished.emit(self.mod_dir, error_msg)

    # ---------- package and export as MOD folder (async with progress dialog) ----------

    def package_and_export_mod(self):
        """
        Export current active character's morphed mesh as a MOD folder.
        Uses ExportProgressDialog with a background ModExportWorker thread.
        """
        char_id = self.active_char_id
        if not char_id:
            show_warning(
                self,
                self.T.get("msg_error", "Error"),
                self.T.get("mod_no_original_pac", "No active character selected."),
            )
            return

        char = self.characters.get(char_id, {})
        original_pac = char.get("original_pac_path", "")
        mod_path = char.get("mod_path", "") or "models/human"

        if not original_pac or not os.path.exists(original_pac):
            show_warning(
                self,
                self.T.get("msg_error", "Error"),
                self.T.get("mod_no_original_pac", "No original PAC file configured for this character. Cannot export MOD."),
            )
            return

        # Determine mod directory
        mod_dir = os.path.join(self.root_dir, "exported_mod", f"Body_Slider_Mod_{char_id}")
        mod_folder_name = f"Body_Slider_Mod_{char_id}"

        # Check if mod_dir exists (synchronous dialog before loading)
        if os.path.exists(mod_dir):
            reply = show_choice(
                self,
                self.T.get("mod_folder_exists_title", "Folder Already Exists"),
                self.T.get(
                    "mod_folder_exists",
                    "The folder '{folder}' already exists in exported_mod.\n"
                    "Do you want to:\n"
                    "- Delete: remove the existing folder and export again\n"
                    "- Rename: create a new folder with a custom name\n"
                    "- Cancel",
                ).format(folder=mod_folder_name),
                [
                    self.T.get("mod_action_delete", "Delete"),
                    self.T.get("mod_action_rename", "Rename"),
                    self.T.get("btn_cancel", "Cancel"),
                ],
            )

            if reply is None or reply == self.T.get("btn_cancel", "Cancel"):
                return

            if reply == self.T.get("mod_action_rename", "Rename"):
                mod_folder_name = self._prompt_mod_folder_name(mod_dir)
                if not mod_folder_name:
                    return
                mod_dir = os.path.join(self.root_dir, "exported_mod", mod_folder_name)
            else:
                # Delete existing
                try:
                    shutil.rmtree(mod_dir)
                except Exception:
                    pass

        os.makedirs(mod_dir, exist_ok=True)
        files_dir = os.path.join(mod_dir, "files")

        char_name = char.get("name", char_id)

        # Show progress dialog (not loading overlay)
        from core.ui_components import ExportProgressDialog

        progress_dlg = ExportProgressDialog(
            self.T, 
            self, 
            title=self.T.get("mod_export_title", "Export MOD Folder")
        )
        progress_dlg.set_total(100)
        progress_dlg.set_status(self.T.get("mod_exporting_text", "Exporting MOD..."))
        progress_dlg.show()
        QApplication.processEvents()

        # Create and start background worker
        worker_obj = self.ModExportWorker(
            char_id=char_id,
            original_pac=original_pac,
            mod_path=mod_path,
            mod_dir=mod_dir,
            files_dir=files_dir,
            char_name=char_name,
            sliders_info=self.sliders_info,
            root_dir=self.root_dir,
        )

        worker_thread = QThread()
        worker_obj.moveToThread(worker_thread)

        # Connect progress signal
        worker_obj.progress.connect(lambda status, pct: progress_dlg.set_status(status))
        worker_obj.progress.connect(lambda status, pct: progress_dlg.set_progress_percent(pct))

        # Connect finished signal with proper cancel handling
        def on_export_finished(mod_dir_result: str, error_msg: str):
            # Close progress dialog first
            progress_dlg.close()
            
            # Quit and wait for thread to finish
            worker_thread.quit()
            if not worker_thread.wait(3000):
                # Force stop if still running after 3 seconds
                worker_thread.terminate()
                worker_thread.wait(1000)
            
            # Safe to clean up now
            worker_obj.deleteLater()
            worker_thread.deleteLater()

            # Handle cancellation - just return, no error message
            if error_msg and "Cancelled" in error_msg:
                return

            # Handle error
            if error_msg:
                show_critical(self, self.T.get("msg_error", "Error"), error_msg)
                return

            # Show success
            progress_dlg.mark_complete(output_path=mod_dir_result)
            progress_dlg._output_path = mod_dir_result
            QApplication.processEvents()
            progress_dlg.exec()

            if not progress_dlg._cancelled:
                import subprocess as _subprocess
                success_msg = self.T.get("mod_exported_title", "MOD Exported") + ":\n\n"
                success_msg += f"{self.T.get('mod_folder', 'Folder')}: {mod_dir_result}\n\n"
                success_msg += self.T.get(
                    "mod_usage_folder",
                    "You can use the '{folder}' folder as a MOD package.",
                ).format(folder=mod_folder_name)

                msg = DarkMessageBox(self)
                msg.setWindowTitle(self.T.get("msg_success", "Success"))
                msg.setText(success_msg)
                msg.setIcon(QMessageBox.Icon.Information)

                ok_btn = msg.addButton(self.T.get("btn_ok", "OK"), QMessageBox.ButtonRole.AcceptRole)
                open_btn = msg.addButton(self.T.get("btn_open_folder", "Open Folder"), QMessageBox.ButtonRole.ActionRole)

                ok_btn.clicked.connect(lambda: setattr(msg, "_clicked_button", ok_btn))
                open_btn.clicked.connect(lambda: setattr(msg, "_clicked_button", open_btn))

                msg.exec()
                if msg.clickedButton() is open_btn:
                    _subprocess.Popen(["explorer", mod_dir_result])

        worker_obj.finished.connect(on_export_finished)

        # Connect cancel button - properly cancel the worker
        def on_cancel_clicked():
            worker_obj.cancel()

        progress_dlg.cancel_requested.connect(on_cancel_clicked)

        worker_thread.started.connect(worker_obj.run)
        worker_thread.start()

    # ----------

    def _prompt_mod_folder_name(self, mod_dir: str) -> Optional[str]:
        """Prompt user for a custom MOD folder name."""
        from core.ui_components import ModRenameDialog
        mod_folder_name = None
        while mod_folder_name is None:
            rename_dlg = ModRenameDialog(
                T=self.T,
                parent=self,
                title=self.T.get("mod_rename_title", "Rename MOD Folder"),
                prompt=self.T.get(
                    "mod_rename_prompt",
                    "Enter a new folder name (max 64 characters, must follow Windows naming rules):",
                ),
                text="Body_Slider_Mod_Custom",
            )
            if rename_dlg.exec() != QDialog.DialogCode.Accepted:
                return ""

            candidate = rename_dlg.text()
            if not candidate:
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("mod_rename_required", "Folder name is required."))
                continue
            if len(candidate) > 64:
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("mod_rename_too_long", "Folder name too long."))
                continue
            invalid_chars = r'<>:"/\|?*'
            if any(c in invalid_chars for c in candidate):
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("mod_rename_invalid_chars", "Invalid characters."))
                continue
            reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
            if candidate.upper().rstrip() in reserved:
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("mod_rename_reserved", "Reserved name."))
                continue
            candidate_subdir = os.path.join(os.path.dirname(mod_dir), candidate)
            if os.path.exists(candidate_subdir):
                show_warning(self, self.T.get("msg_error", "Error"), self.T.get("mod_rename_exists", "Folder exists."))
                continue
            mod_folder_name = candidate
        return mod_folder_name

    def _export_character_pac(self, char_id: str, original_pac: str, mod_path: str, files_dir: str):
        """
        Export the character's body PAC with all sliders applied.
        Uses IncrementalPACBuilder (same logic as pack_handler_mixin.py save_model_pac_and_mod).
        """
        import numpy as np
        from core.pac_builder import parse_pac, IncrementalPACBuilder
        from core.mesh_processor import compute_morph_delta

        # Parse original PAC
        with open(original_pac, "rb") as f:
            pac_bytes = f.read()
        char_pac_mesh = parse_pac(pac_bytes, original_pac)

        # Extract original points per submesh
        char_original_points: Dict[str, np.ndarray] = {}
        for sm in char_pac_mesh.submeshes:
            if sm.vertices:
                char_original_points[sm.name] = np.array(sm.vertices, dtype=np.float32)

        # Compute morph deltas for each slider
        char_morph_data: Dict[str, Dict[str, np.ndarray]] = {}
        for sid, info in self.sliders_info.items():
            target_path = info.get("path", "")
            if not target_path or not os.path.exists(target_path):
                continue
            try:
                compute_morph_delta(char_morph_data, sid, target_path, char_original_points)
            except Exception:
                pass

        # Compute morphed vertex positions
        new_positions: Dict[str, np.ndarray] = {}
        for name, orig in char_original_points.items():
            morphed = orig.copy()
            for sid, info in self.sliders_info.items():
                md = char_morph_data.get(sid)
                cv = info.get("current_value", 0.0)
                if md is not None and name in md:
                    morphed += md[name] * (cv / 100.0)
            new_positions[name] = morphed

        # Build new PAC using IncrementalPACBuilder
        inc = IncrementalPACBuilder(original_pac)
        pac_sm_names = [sm.name for sm in inc.original_mesh.submeshes]

        def transform_func(sm_idx, vi, orig_v,
                           new_positions=new_positions,
                           char_original_points=char_original_points,
                           pac_sm_names=pac_sm_names):
            pac_name = pac_sm_names[sm_idx] if sm_idx < len(pac_sm_names) else None
            if not pac_name or pac_name not in new_positions:
                return orig_v
            if pac_name not in char_original_points:
                return orig_v
            orig_verts = char_original_points[pac_name]
            morphed_verts = new_positions[pac_name]
            if vi >= len(orig_verts):
                return orig_v
            ov = orig_verts[vi]
            mv = morphed_verts[vi]
            return (
                float(orig_v[0] + mv[0] - ov[0]),
                float(orig_v[1] + mv[1] - ov[1]),
                float(orig_v[2] + mv[2] - ov[2]),
            )

        inc.apply_vertex_transform(transform_func)
        pac_data = inc.build()

        # Write to files/<mod_path>/
        game_rel_dir = os.path.join(files_dir, mod_path)
        os.makedirs(game_rel_dir, exist_ok=True)
        pac_filename = os.path.basename(original_pac)
        mod_pac_path = os.path.join(game_rel_dir, pac_filename)
        with open(mod_pac_path, "wb") as f:
            f.write(pac_data)

    def _export_outfit_pacs(self, char_id: str, original_outfit_root: str, exported_outfit_root: str, files_dir: str):
        """
        Export all outfit PACs with sliders applied.
        
        For each PAC in original_outfit/{char_id}/:
        1. Parse the PAC to get original points
        2. For each slider, look up the target mesh in exported_outfit/{char_id}/{slider_ref_path}/
        3. Validate submesh compatibility between original and target
        4. Compute morph deltas and apply transforms
        5. Build new PAC via IncrementalPACBuilder
        6. Write to files/<original_outfit_relative_path>/
        """
        import numpy as np
        from core.pac_builder import parse_pac, IncrementalPACBuilder
        from core.mesh_processor import compute_morph_delta

        # Find all .pac files in original_outfit/{char_id}/
        outfit_pac_files = []
        for dirpath, _, filenames in os.walk(original_outfit_root):
            for fn in filenames:
                if fn.lower().endswith(".pac"):
                    outfit_pac_files.append(os.path.join(dirpath, fn))

        if not outfit_pac_files:
            return

        # Track mismatches for warning dialog
        mismatches: List[str] = []

        for outfit_pac_path in outfit_pac_files:
            # Compute relative path from original_outfit root
            rel_path = os.path.relpath(outfit_pac_path, original_outfit_root)
            outfit_pac_dir = os.path.dirname(rel_path)  # Directory part only
            pac_filename = os.path.basename(outfit_pac_path)
            base_no_ext = os.path.splitext(pac_filename)[0]

            # Parse original outfit PAC
            try:
                with open(outfit_pac_path, "rb") as f:
                    outfit_pac_bytes = f.read()
                outfit_pac_mesh = parse_pac(outfit_pac_bytes, outfit_pac_path)
            except Exception:
                continue

            # Extract original points per submesh
            outfit_original_points: Dict[str, np.ndarray] = {}
            original_submesh_names = []
            for sm in outfit_pac_mesh.submeshes:
                if sm.vertices:
                    outfit_original_points[sm.name] = np.array(sm.vertices, dtype=np.float32)
                    original_submesh_names.append(sm.name)

            if not outfit_original_points:
                continue

            # Compute morph deltas for each slider
            outfit_morph_data: Dict[str, Dict[str, np.ndarray]] = {}
            for sid, info in self.sliders_info.items():
                # Extract slider_ref_path from the slider's target path
                # e.g., target_mesh/damiane/areola_puffy.obj -> areola_puffy/
                # e.g., target_mesh/damiane/custom/cd_phw_00_nude_00_0001_damian.pac -> custom/cd_phw_00_nude_00_0001_damian/
                slider_path = info.get("path", "")
                normalized = slider_path.replace("\\", "/")
                tm_idx = normalized.find("target_mesh/")
                if tm_idx >= 0:
                    normalized = normalized[tm_idx + len("target_mesh/"):]
                parts = normalized.split("/", 1)
                after_char_id = parts[1] if len(parts) > 1 else normalized
                slider_ref_path = os.path.splitext(after_char_id)[0]

                # Look for target mesh in exported_outfit/{char_id}/{slider_ref_path}/{outfit_pac_dir}/
                exported_dir = os.path.join(exported_outfit_root, slider_ref_path)
                target_subdir = os.path.join(exported_dir, outfit_pac_dir) if outfit_pac_dir else exported_dir

                # Candidate target files
                candidates = []
                c1 = os.path.join(target_subdir, pac_filename)
                if os.path.exists(c1):
                    candidates.append(c1)
                c2 = os.path.join(target_subdir, base_no_ext + ".obj")
                if os.path.exists(c2):
                    candidates.append(c2)
                c3 = os.path.join(target_subdir, base_no_ext + ".pac")
                if os.path.exists(c3):
                    candidates.append(c3)

                if not candidates:
                    continue

                target_file = candidates[0]

                # Validate submesh compatibility between original and target
                target_submesh_names = []
                try:
                    if target_file.lower().endswith(".pac"):
                        with open(target_file, "rb") as f:
                            target_pac_bytes = f.read()
                        target_pac_mesh = parse_pac(target_pac_bytes, target_file)
                        for sm in target_pac_mesh.submeshes:
                            if sm.vertices:
                                target_submesh_names.append(sm.name)
                    else:
                        # .obj file - use trimesh to load and get geometry names
                        import trimesh
                        obj_data = trimesh.load(target_file)
                        if isinstance(obj_data, trimesh.Scene):
                            for geom_name in obj_data.geometry.keys():
                                target_submesh_names.append(geom_name)
                        elif isinstance(obj_data, trimesh.Trimesh):
                            target_submesh_names = list(outfit_original_points.keys())
                        else:
                            target_submesh_names = list(outfit_original_points.keys())
                except Exception:
                    continue

                # Validate submesh names match
                orig_set = set(original_submesh_names)
                target_set = set(target_submesh_names)
                if orig_set != target_set:
                    mismatch_msg = f"{rel_path} | Slider: {sid} | "
                    missing_in_target = orig_set - target_set
                    extra_in_target = target_set - orig_set
                    details = []
                    if missing_in_target:
                        details.append(f"Missing in target: {missing_in_target}")
                    if extra_in_target:
                        details.append(f"Extra in target: {extra_in_target}")
                    mismatch_msg += "; ".join(details)
                    mismatches.append(mismatch_msg)
                    continue

                # Compute morph delta (compute_morph_delta writes to outfit_morph_data[sid] = deltas)
                try:
                    compute_morph_delta(outfit_morph_data, sid, target_file, outfit_original_points)
                except Exception:
                    pass

            # Determine destination directory (files/<relative_dir>/)
            dest_dir = os.path.join(files_dir, outfit_pac_dir) if outfit_pac_dir else files_dir
            os.makedirs(dest_dir, exist_ok=True)

            # Check if any morph data was computed
            if not outfit_morph_data:
                shutil.copy2(outfit_pac_path, os.path.join(dest_dir, pac_filename))
                continue

            # Compute morphed vertex positions
            new_positions: Dict[str, np.ndarray] = {}
            for name, orig in outfit_original_points.items():
                morphed = orig.copy()
                for sid, info in self.sliders_info.items():
                    md = outfit_morph_data.get(sid)
                    cv = info.get("current_value", 0.0)
                    if md is not None and name in md:
                        morphed += md[name] * (cv / 100.0)
                new_positions[name] = morphed

            # Build new PAC using IncrementalPACBuilder
            inc = IncrementalPACBuilder(outfit_pac_path)
            pac_sm_names = [sm.name for sm in inc.original_mesh.submeshes]

            def transform_func(sm_idx, vi, orig_v,
                               new_positions=new_positions,
                               outfit_original_points=outfit_original_points,
                               pac_sm_names=pac_sm_names):
                pac_name = pac_sm_names[sm_idx] if sm_idx < len(pac_sm_names) else None
                if not pac_name or pac_name not in new_positions:
                    return orig_v
                if pac_name not in outfit_original_points:
                    return orig_v
                orig_verts = outfit_original_points[pac_name]
                morphed_verts = new_positions[pac_name]
                if vi >= len(orig_verts):
                    return orig_v
                ov = orig_verts[vi]
                mv = morphed_verts[vi]
                return (
                    float(orig_v[0] + mv[0] - ov[0]),
                    float(orig_v[1] + mv[1] - ov[1]),
                    float(orig_v[2] + mv[2] - ov[2]),
                )

            inc.apply_vertex_transform(transform_func)
            pac_data = inc.build()

            # Write to files/<relative_dir>/{pac_filename}
            with open(os.path.join(dest_dir, pac_filename), "wb") as f:
                f.write(pac_data)

        # Show mismatch warning if any
        if mismatches:
            mismatch_text = self.T.get("outfit_submesh_mismatch_title", "Outfit Submesh Mismatch Warning") + "\n\n"
            mismatch_text += self.T.get("outfit_submesh_mismatch_msg", "The following outfit PACs have submesh mismatches and were skipped:") + "\n\n"
            for m in mismatches:
                mismatch_text += f"• {m}\n"
            
            from PyQt6.QtWidgets import QMessageBox
            from core.ui_dialogs import DarkMessageBox
            msg = DarkMessageBox(self)
            msg.setWindowTitle(self.T.get("msg_warning", "Warning"))
            msg.setText(mismatch_text)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.addButton(self.T.get("btn_ok", "OK"), QMessageBox.ButtonRole.AcceptRole)
            msg.exec()

    # ---------- close event ----------

    def closeEvent(self, e):
        if hasattr(self, "_data_init_thread"):
            try:
                self._data_init_thread.quit()
                self._data_init_thread.wait(2000)
            except Exception:
                pass

        for i in range(self.char_stack.count()):
            w = self.char_stack.widget(i)
            if hasattr(w, "plotter"):
                self._close_plotter(w.plotter)

        self._save_camera_and_config()

        super().closeEvent(e)