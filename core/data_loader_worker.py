"""
Background data loader worker for Body Slider Pro.
Responsible for heavy initialization (mesh parsing, morph computation)
in a separate thread to keep the UI responsive.

DESIGN:
- Receives only clean data (no window/UI reference).
- Emits results via signals to be consumed safely in main thread.
"""

import os
import numpy as np
import trimesh
from typing import Any, Dict, List, Optional, Set, Tuple
from PyQt6.QtCore import QObject, pyqtSignal

from core.pac_builder import parse_pac, ParsedMesh, SubMesh
from core.mesh_processor import compute_morph_delta


class StartupDataInitWorker(QObject):
    """
    Worker object moved to a QThread to perform startup data initialization
    without blocking the UI.
    """

    finished_signal = pyqtSignal()
    result_signal = pyqtSignal(
        str,        # original_pac_path
        dict,       # original_points
        dict,       # original_faces (if needed)
        dict,       # morph_data
        list,       # custom_sliders (if needed)
        object      # pac_mesh (ParsedMesh for export)
    )

    def __init__(
        self,
        active_char_id: str,
        characters: dict,
        character_sliders: dict,
        char_config_dir: str,
        root_dir: str
    ):
        super().__init__()
        self.active_char_id = active_char_id
        self.characters = characters
        self.character_sliders = character_sliders  # {char_id: {full_slider_id: info}}
        self.char_config_dir = char_config_dir
        self.root_dir = root_dir

    # Public entry for QThread.started

    def run(self) -> None:
        try:
            self.execute_load()
        except Exception as e:
            import traceback
            print(f"[Worker Error] {e}")
            traceback.print_exc()
        finally:
            # 必须在最后确保发射完结信号，否则主界面会无限 Loading！
            self.finished_signal.emit()

    # Core implementation: pure data work, no UI touches

    def execute_load(self) -> None:
        if not self.active_char_id or self.active_char_id not in self.characters:
            # Emit empty results so the main thread still continues.
            self.result_signal.emit("", {}, {}, {}, [], None)
            return

        char = self.characters[self.active_char_id]
        original_pac_path = char.get("original_pac_path", "")

        # Ensure char dirs (using new path: target_mesh/{char_id}/custom/)
        custom_dir = self._char_custom_dir(self.active_char_id)
        self._ensure_char_dirs(custom_dir)

        try:
            if not original_pac_path or not os.path.exists(original_pac_path):
                raise RuntimeError("Original PAC not found for character: " + self.active_char_id)

            with open(original_pac_path, "rb") as f:
                pac_data = f.read()

            pac_mesh = parse_pac(pac_data, original_pac_path)

            # Build geometries and collect original_points
            geometries, original_points = self._build_geometries(pac_mesh)

            # Build scene_base is NOT needed here (UI-related),
            # but we still compute what's needed for morphs.

            # Compute morph deltas for each slider using character_sliders
            morph_data: Dict[str, Dict[str, np.ndarray]] = {}
            sliders_for_char = self.character_sliders.get(self.active_char_id, {})

            for full_sid, info in sliders_for_char.items():
                target_path = info.get("path", "")
                # Must convert to absolute path, otherwise os.path.exists fails and morph data is lost
                if target_path and not os.path.isabs(target_path):
                    target_path = os.path.abspath(os.path.join(self.root_dir, target_path))
                
                compute_morph_delta(
                    morph_data, full_sid, target_path, original_points
                )

            # Compute bounding info (used later in UI)
            all_v = np.vstack(list(original_points.values()))
            min_b = all_v.min(axis=0)
            max_b = all_v.max(axis=0)
            total_height = max_b[1] - min_b[1]
            center_xz = np.array([
                (min_b[0] + max_b[0]) / 2,
                (min_b[2] + max_b[2]) / 2,
            ])

            # We store these into char config dict so main thread can read them,
            # or we can extend the signal if needed. For now, store locally in char dict.
            char["_min_b"] = min_b.tolist()
            char["_max_b"] = max_b.tolist()
            char["_total_height"] = float(total_height)
            char["_center_xz"] = center_xz.tolist()

            # Store scene_base data as geometries dict (main thread will reconstruct trimesh.Scene if needed)
            original_faces: Dict[str, np.ndarray] = {}
            for sm in pac_mesh.submeshes:
                verts = np.array(sm.vertices, dtype=np.float32)
                faces = np.array(sm.faces, dtype=np.int32)
                if len(verts) > 0 and len(faces) > 0:
                    original_faces[sm.name] = faces

            # custom_sliders: for now pass empty list (can be extended if needed)
            custom_sliders: List[Any] = []

            # Emit results via signal (no direct UI writes)
            self.result_signal.emit(
                original_pac_path,
                original_points,
                original_faces,
                morph_data,
                custom_sliders,
                pac_mesh  # ParsedMesh for OBJ export
            )

        except Exception as e:
            print(f"Init Data Error: {e}")
            # Still emit something so main thread can continue.
            self.result_signal.emit("", {}, {}, {}, [], None)

    # ---------- helpers (no window) ----------

    @staticmethod
    def _build_geometries(pac_mesh: ParsedMesh):
        geometries: Dict[str, trimesh.Trimesh] = {}
        original_points: Dict[str, np.ndarray] = {}

        for sm in pac_mesh.submeshes:
            verts = np.array(sm.vertices, dtype=np.float32)
            faces = np.array(sm.faces, dtype=np.int32)
            if len(verts) == 0 or len(faces) == 0:
                continue
            geom = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
            geometries[sm.name] = geom
            original_points[sm.name] = verts.copy()

        return geometries, original_points

    # ---------- path helpers ----------

    def _char_custom_dir(self, char_id: str) -> str:
        """
        Return custom mesh directory for the given character.
        Path: target_mesh/{char_id}/custom/
        """
        return os.path.join(
            self.root_dir, "target_mesh", char_id, "custom"
        )

    def _ensure_char_dirs(self, custom_dir: str) -> None:
        """Ensure custom mesh directories exist."""
        os.makedirs(custom_dir, exist_ok=True)


