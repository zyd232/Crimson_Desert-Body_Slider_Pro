"""
Outfit management for Body Slider Pro.

Responsibilities:
- Activate / deactivate outfits (load PAC, compute morphs, add meshes).
- Unload all outfits for a character.
- Sync outfits panel visibility on character switch.
- Update outfit morphs when sliders change.
- Create OutfitsPanel UI instance (delegated to ui_outfits).
"""

import os
import shutil
from typing import TYPE_CHECKING, Any, Dict, Optional

import numpy as np

if TYPE_CHECKING:
    from core.mesh_viewer import MeshViewer


class OutfitHost:
    """
    Minimal adapter that exposes the subset of BodySlider
    needed by OutfitManager without importing the whole class.
    """

    def __init__(self, app: Any):
        self._app = app

    @property
    def root_dir(self) -> str:
        return self._app.root_dir

    @property
    def active_char_id(self) -> Optional[str]:
        return self._app.active_char_id

    @property
    def sliders_info(self) -> Dict[str, Dict[str, Any]]:
        return self._app.sliders_info

    @property
    def original_points(self) -> Dict[str, np.ndarray]:
        return self._app.original_points

    @property
    def original_faces(self) -> Dict[str, np.ndarray]:
        return self._app.original_faces

    @property
    def morph_data(self) -> Dict[str, Dict[str, np.ndarray]]:
        return self._app.morph_data

    @property
    def mesh_viewer_data(self) -> Dict[str, Dict]:
        return self._app.mesh_viewer_data

    @property
    def scene_base(self):
        return self._app.scene_base

    @property
    def pac_mesh(self):
        return self._app.pac_mesh

    # Outfit state (mirrors attributes on app)
    @property
    def active_outfit_path(self) -> Optional[str]:
        return self._app.active_outfit_path

    @active_outfit_path.setter
    def active_outfit_path(self, v: Optional[str]):
        self._app.active_outfit_path = v

    @property
    def active_outfit_mod_path(self) -> Optional[str]:
        return self._app.active_outfit_mod_path

    @active_outfit_mod_path.setter
    def active_outfit_mod_path(self, v: Optional[str]):
        self._app.active_outfit_mod_path = v

    @property
    def outfit_original_points(self) -> Dict[str, np.ndarray]:
        return self._app.outfit_original_points

    @outfit_original_points.setter
    def outfit_original_points(self, v: Dict[str, np.ndarray]):
        self._app.outfit_original_points = v

    @property
    def outfit_morph_data(self) -> Dict[str, Dict[str, np.ndarray]]:
        return self._app.outfit_morph_data

    @outfit_morph_data.setter
    def outfit_morph_data(self, v: Dict[str, Dict[str, np.ndarray]]):
        self._app.outfit_morph_data = v

    @property
    def outfit_faces(self) -> Dict[str, np.ndarray]:
        return self._app.outfit_faces

    @outfit_faces.setter
    def outfit_faces(self, v: Dict[str, np.ndarray]):
        self._app.outfit_faces = v

    def get_plotter(self) -> Optional["MeshViewer"]:
        return self._app._plotter

    def remove_mesh(self, name: str):
        viewer = self.get_plotter()
        if viewer:
            viewer.remove_mesh(name)

    def add_mesh(self, verts, faces, color, name, mesh_type="character"):
        viewer = self.get_plotter()
        if viewer:
            viewer.add_mesh(verts, faces, color=color, name=name, mesh_type=mesh_type)

    def update_mesh_vertices(self, name: str, verts):
        viewer = self.get_plotter()
        if viewer:
            viewer.update_mesh_vertices(name, verts)

    def compute_morph_delta(self, slider_id: str, target_path: str,
                            morph_data: Dict, original_points: Dict):
        from core.mesh_processor import compute_morph_delta
        compute_morph_delta(morph_data, slider_id, target_path, original_points)

    def apply_morphs(self, original_points, morph_data, sliders_info):
        from core.mesh_processor import apply_morphs
        return apply_morphs(original_points, morph_data, sliders_info)

    def parse_pac(self, data: bytes, path: str):
        from core.pac_builder import parse_pac
        return parse_pac(data, path)

    # Outfit link state (mirrors attributes on app)
    @property
    def outfit_link_states(self) -> Dict[str, bool]:
        return getattr(self._app, "outfit_link_states", {})

    @outfit_link_states.setter
    def outfit_link_states(self, v: Dict[str, bool]):
        self._app.outfit_link_states = v

    @property
    def outfit_slider_values(self) -> Dict[str, float]:
        return getattr(self._app, "outfit_slider_values", {})

    @outfit_slider_values.setter
    def outfit_slider_values(self, v: Dict[str, float]):
        self._app.outfit_slider_values = v

    @property
    def outfit_slider_mapping(self) -> Dict[str, Optional[str]]:
        return getattr(self._app, "outfit_slider_mapping", {})

    @outfit_slider_mapping.setter
    def outfit_slider_mapping(self, v: Dict[str, Optional[str]]):
        self._app.outfit_slider_mapping = v

    # Outfit config manager
    @property
    def outfit_config_mgr(self):
        return getattr(self._app, "outfit_config_mgr", None)

    # UI helpers (thin wrappers)
    def current_page(self):
        return self._app._current_page()

    def sync_outfits_panel_for_char(self, char_id: str):
        return self._app._sync_outfits_panel_for_char(char_id)

    def is_maximized(self) -> bool:
        return self._app.isMaximized()

    def window_width(self) -> int:
        return self._app.width()

    def window_height(self) -> int:
        return self._app.height()

    def resize_window(self, w: int, h: int):
        self._app.resize(w, h)


class OutfitManager:
    """
    Encapsulates all outfit-related behavior.
    """

    def __init__(self, app: Any):
        self.host = OutfitHost(app)

    # ---------- path helpers ----------

    def has_outfits_for_char(self, char_id: str) -> bool:
        """
        Check if outfits exist for the given character (uses internal root_dir).
        """
        root_dir = self.host.root_dir
        original_outfit_dir = os.path.join(root_dir, "original_outfit", char_id)
        if not os.path.isdir(original_outfit_dir):
            return False
        try:
            for _, _, files in os.walk(original_outfit_dir):
                if files:
                    return True
        except OSError:
            return False
        return False

    @staticmethod
    def has_outfits_for_char_static(root_dir: str, char_id: str) -> bool:
        """
        Static variant for external callers that manage root_dir.
        """
        original_outfit_dir = os.path.join(root_dir, "original_outfit", char_id)
        if not os.path.isdir(original_outfit_dir):
            return False
        try:
            for _, _, files in os.walk(original_outfit_dir):
                if files:
                    return True
        except OSError:
            return False
        return False

    # ---------- UI: create outfits panel ----------

    def create_outfits_panel(self, app: Any) -> Optional[Any]:
        """
        Create and return an OutfitsPanel instance if outfits exist
        for the current character; otherwise return None.
        """
        char_id = self.host.active_char_id
        if not char_id:
            return None
        if not self.has_outfits_for_char(char_id):
            return None

        from core.ui_outfits import OutfitsPanel
        return OutfitsPanel(app, char_id)

    # ---------- activate / deactivate ----------

    def activate_outfit(self, original_path: str, mod_path: str):
        """
        Called when an outfit file is activated in OutfitsPanel.
        - Load outfit mesh from PAC.
        - Compute morph deltas for outfit.
        - Add outfit meshes to viewer.
        """
        h = self.host
        char_id = h.active_char_id or ""
        if not char_id or not original_path:
            return

        # Deactivate previous if any
        if h.active_outfit_path:
            self.deactivate_outfit()

        h.active_outfit_path = original_path
        h.active_outfit_mod_path = mod_path

        # Load outfit (PAC or OBJ)
        outfit_pac_mesh = None
        outfit_obj_data = None
        
        try:
            if original_path.lower().endswith(".pac"):
                with open(original_path, "rb") as f:
                    outfit_pac_mesh = h.parse_pac(f.read(), original_path)
            elif original_path.lower().endswith(".obj"):
                import trimesh
                mesh = trimesh.load(original_path, force='mesh')
                outfit_obj_data = {
                    "vertices": np.array(mesh.vertices, dtype=np.float32),
                    "faces": np.array(mesh.faces, dtype=np.int32),
                }
        except Exception:
            h.active_outfit_path = None
            h.active_outfit_mod_path = None
            return

        # Build original_points and faces for outfit
        h.outfit_original_points = {}
        h.outfit_faces = {}
        h.outfit_morph_data = {}

        if outfit_pac_mesh:
            for sm in outfit_pac_mesh.submeshes:
                if sm.vertices:
                    h.outfit_original_points[sm.name] = np.array(sm.vertices, dtype=np.float32)
                if sm.faces is not None and len(sm.faces) > 0:
                    h.outfit_faces[sm.name] = np.array(sm.faces, dtype=np.int32)
        elif outfit_obj_data:
            obj_name = os.path.splitext(os.path.basename(original_path))[0]
            h.outfit_original_points[obj_name] = outfit_obj_data["vertices"]
            h.outfit_faces[obj_name] = outfit_obj_data["faces"]

        # For each slider, compute morph delta if exported mesh exists.
        # Target mesh can be .obj or .pac.
        pac_base = os.path.basename(original_path)  # e.g. cd_phw_00_ub_00_0170.pac
        base_no_ext = os.path.splitext(pac_base)[0]  # e.g. cd_phw_00_ub_00_0170

        # mod_path is the relative path from original_outfit_root to this outfit file,
        # e.g. "breast_size_type_01/character/model/1_pc/2_phw/armor/9_upperbody/cd_phw_00_ub_00_0170.pac"
        # We need its directory part to mirror the same structure under exported_outfit.
        mod_dir = os.path.dirname(mod_path)

        for sid, info in h.sliders_info.items():
            # Extract the slider segment from the target mesh path.
            # Example: "target_mesh/damiane/custom/cd_phw_00_nude_00_0001_damian.pac"
            #   -> after removing "target_mesh/" prefix: "damiane/custom/cd_phw_00_nude_00_0001_damian.pac"
            #   -> after removing char_id segment: "custom/cd_phw_00_nude_00_0001_damian.pac"
            #   -> after removing extension: "custom/cd_phw_00_nude_00_0001_damian"
            # Example: "target_mesh/damiane/breast_size_type_01.obj"
            #   -> "breast_size_type_01"
            # 从滑块的 path 中提取 slider_segment（即 target_mesh/{char_id}/之后的部分去掉扩展名）
            # path 可能是绝对路径如 D:\...\target_mesh\damiane\breast_size_type_01.obj
            # 也可能是相对路径如 target_mesh\damiane\breast_size_type_01.obj
            slider_path = info.get("path", "")
            normalized = slider_path.replace("\\", "/")
            # 查找 target_mesh/ 的位置（兼容绝对路径和相对路径）
            tm_idx = normalized.find("target_mesh/")
            if tm_idx >= 0:
                normalized = normalized[tm_idx + len("target_mesh/"):]
            parts = normalized.split("/", 1)
            after_char_id = parts[1] if len(parts) > 1 else normalized
            slider_segment = os.path.splitext(after_char_id)[0]

            exported_dir = os.path.join(
                h.root_dir, "exported_outfit", char_id, slider_segment
            )

            # Candidate paths under this slider:
            # exported_outfit/<char_id>/<slider_segment>/<mod_dir>/<file>
            candidates = []

            # 1) exact original name (for PAC targets)
            c1 = os.path.join(exported_dir, mod_dir, pac_base)
            if os.path.exists(c1):
                candidates.append(c1)

            # 2) .obj
            c2 = os.path.join(exported_dir, mod_dir, base_no_ext + ".obj")
            if os.path.exists(c2):
                candidates.append(c2)

            # 3) .pac (in case original was not .pac or for consistency)
            c3 = os.path.join(exported_dir, mod_dir, base_no_ext + ".pac")
            if os.path.exists(c3):
                candidates.append(c3)

            # Use first existing candidate; compute_morph_delta already handles both obj/pac.
            if candidates:
                target_path = candidates[0]
                h.compute_morph_delta(
                    sid,
                    target_path,
                    h.outfit_morph_data,
                    h.outfit_original_points,
                )

        viewer = h.get_plotter()
        if not viewer:
            return

        # Apply morphs to outfit mesh
        morphed = h.apply_morphs(
            h.outfit_original_points,
            h.outfit_morph_data,
            h.sliders_info,
        )

        # Add outfit meshes with prefix "outfit_"
        for name, verts in morphed.items():
            faces = h.outfit_faces.get(name)
            if faces is None:
                continue
            mesh_name = f"outfit_{name}"
            h.add_mesh(verts, faces, color="beige", name=mesh_name, mesh_type="outfit")
            h.mesh_viewer_data[mesh_name] = {
                "vertices": verts.copy(),
                "faces": faces.copy(),
            }

    def deactivate_outfit(self):
        """
        Remove outfit meshes from viewer and clear outfit state.
        """
        h = self.host

        # Remove all meshes with "outfit_" prefix.
        keys_to_remove = [k for k in h.mesh_viewer_data if k.startswith("outfit_")]
        for key in keys_to_remove:
            try:
                h.remove_mesh(key)
            except Exception:
                pass
            h.mesh_viewer_data.pop(key, None)

        h.active_outfit_path = None
        h.active_outfit_mod_path = None
        h.outfit_original_points = {}
        h.outfit_morph_data = {}
        h.outfit_faces = {}

    # ---------- unload all ----------

    def unload_all_outfits(self, char_id: str):
        """
        Called from OutfitsPanel 'Unload All Outfits' button.
        Deletes outfit directories and index, then refreshes UI.
        """
        h = self.host

        if not char_id:
            return

        # Remove active outfit mesh
        if h.active_outfit_path:
            self.deactivate_outfit()

        dirs_to_remove = [
            os.path.join(h.root_dir, "original_outfit", char_id),
            os.path.join(h.root_dir, "exported_outfit", char_id),
        ]

        for d in dirs_to_remove:
            if os.path.isdir(d):
                try:
                    shutil.rmtree(d)
                except Exception:
                    pass

        # Delete outfit config file
        ocm = h.outfit_config_mgr
        if ocm:
            ocm.delete_config(char_id)

        # Refresh outfits panel
        h.sync_outfits_panel_for_char(char_id)

    # ---------- morph update for outfit ----------

    def update_outfit_morphs(self):
        """
        Update outfit mesh vertices based on current slider values.
        Called from update_all_morphs.
        """
        h = self.host

        # Require active outfit and original points; morph_data is optional.
        if (
            not h.active_outfit_path
            or not h.outfit_original_points
        ):
            return

        outfit_morph_data = h.outfit_morph_data or {}

        # If no outfit meshes are visible, skip.
        has_outfit_mesh = any(
            k.startswith("outfit_")
            for k in h.mesh_viewer_data
        )
        if not has_outfit_mesh:
            return

        # -- Build effective sliders_info for unlinked outfit sliders --
        sliders_info = h.sliders_info
        link_states = h.outfit_link_states or {}
        slider_values = h.outfit_slider_values or {}
        slider_mapping = h.outfit_slider_mapping or {}

        if link_states:
            effective_info: Dict[str, Dict[str, Any]] = dict(sliders_info)
            for outfit_key, linked in link_states.items():
                if not linked:
                    char_sid = slider_mapping.get(outfit_key)
                    if char_sid and char_sid in effective_info:
                        val = slider_values.get(outfit_key, 0.0)
                        # Shallow copy to avoid mutating original data
                        entry = dict(effective_info[char_sid])
                        entry["current_value"] = val
                        effective_info[char_sid] = entry
            sliders_info = effective_info

        outfit_morphed = h.apply_morphs(
            h.outfit_original_points,
            outfit_morph_data,
            sliders_info,
        )

        for key in list(h.mesh_viewer_data.keys()):
            if not key.startswith("outfit_"):
                continue
            base_name = key[len("outfit_"):]
            if base_name not in outfit_morphed:
                continue
            h.update_mesh_vertices(key, outfit_morphed[base_name])

    # ---------- outfit slider discovery ----------

    def discover_outfit_sliders(self, char_id: str, active_outfit_mod_path: str) -> Dict[str, Dict[str, Any]]:
        """
        Scan exported_outfit/{char_id}/ for sliders that have meshes
        for the currently active outfit.

        Returns an OrderedDict-like dict mapping outfit_slider_key -> slider_info.
        The order follows the character slider order in sliders_info (default first, then custom).
        Each info contains:
            - short_id: the slider segment (e.g. "breast_size_type_01")
            - name: display name (from character slider if matched, else short_id)
            - min: min value (from character slider if matched, else -50)
            - max: max value (from character slider if matched, else 150)
            - current_value: current value from character slider if matched, else 0
            - char_slider_id: the full character slider ID if matched, else None
            - is_custom: True if the slider is under "custom/" subdirectory
        """
        h = self.host
        root_dir = h.root_dir
        sliders_info = h.sliders_info

        exported_root = os.path.join(root_dir, "exported_outfit", char_id)
        if not os.path.isdir(exported_root):
            return {}

        # mod_path is relative from original_outfit_root, e.g.
        # "breast_size_type_01/character/model/1_pc/2_phw/armor/9_upperbody/cd_phw_00_ub_00_0170.pac"
        pac_base = os.path.basename(active_outfit_mod_path)
        base_no_ext = os.path.splitext(pac_base)[0]
        mod_dir = os.path.dirname(active_outfit_mod_path)

        # Build a lookup: short_id -> discovered info
        discovered: Dict[str, Dict[str, Any]] = {}

        try:
            entries = sorted(os.listdir(exported_root))
        except OSError:
            return {}

        for entry in entries:
            entry_path = os.path.join(exported_root, entry)
            if not os.path.isdir(entry_path):
                continue

            # Determine is_custom and short_id
            if entry == "custom":
                try:
                    custom_entries = sorted(os.listdir(entry_path))
                except OSError:
                    continue
                for sub_entry in custom_entries:
                    sub_path = os.path.join(entry_path, sub_entry)
                    if not os.path.isdir(sub_path):
                        continue
                    short_id = sub_entry
                    slider_dir = sub_path
                    candidates = [
                        os.path.join(slider_dir, mod_dir, pac_base),
                        os.path.join(slider_dir, mod_dir, base_no_ext + ".obj"),
                        os.path.join(slider_dir, mod_dir, base_no_ext + ".pac"),
                    ]
                    has_mesh = any(os.path.exists(c) for c in candidates)
                    if not has_mesh:
                        continue
                    char_sid = self._find_char_slider_by_short_id(short_id, char_id, sliders_info, is_custom=True)
                    if char_sid:
                        cinfo = sliders_info[char_sid]
                        name = cinfo.get("name", short_id)
                        min_v = float(cinfo.get("min", -50))
                        max_v = float(cinfo.get("max", 150))
                        cur_v = float(cinfo.get("current_value", 0))
                    else:
                        name = short_id
                        min_v = -50.0
                        max_v = 150.0
                        cur_v = 0.0
                    key = f"outfit_{short_id}"
                    discovered[key] = {
                        "short_id": short_id,
                        "name": name,
                        "min": min_v,
                        "max": max_v,
                        "current_value": cur_v,
                        "char_slider_id": char_sid,
                        "is_custom": True,
                    }
            else:
                short_id = entry
                candidates = [
                    os.path.join(entry_path, mod_dir, pac_base),
                    os.path.join(entry_path, mod_dir, base_no_ext + ".obj"),
                    os.path.join(entry_path, mod_dir, base_no_ext + ".pac"),
                ]
                has_mesh = any(os.path.exists(c) for c in candidates)
                if not has_mesh:
                    continue
                char_sid = self._find_char_slider_by_short_id(short_id, char_id, sliders_info)
                if char_sid:
                    cinfo = sliders_info[char_sid]
                    name = cinfo.get("name", short_id)
                    min_v = float(cinfo.get("min", -50))
                    max_v = float(cinfo.get("max", 150))
                    cur_v = float(cinfo.get("current_value", 0))
                else:
                    name = short_id
                    min_v = -50.0
                    max_v = 150.0
                    cur_v = 0.0
                key = f"outfit_{short_id}"
                discovered[key] = {
                    "short_id": short_id,
                    "name": name,
                    "min": min_v,
                    "max": max_v,
                    "current_value": cur_v,
                    "char_slider_id": char_sid,
                    "is_custom": False,
                }

        # Order by character slider order (sliders_info iteration order)
        result: Dict[str, Dict[str, Any]] = {}
        for full_sid, info in sliders_info.items():
            parts = full_sid.split(".", 1)
            if len(parts) == 2:
                fid_short_id = parts[1]
                key = f"outfit_{fid_short_id}"
                if key in discovered:
                    result[key] = discovered[key]

        # Append any discovered sliders not matched to character sliders
        for key, info in discovered.items():
            if key not in result:
                result[key] = info

        return result

    @staticmethod
    def _find_char_slider_by_short_id(
        short_id: str, char_id: str, sliders_info: Dict[str, Dict[str, Any]],
        is_custom: bool = False
    ) -> Optional[str]:
        """
        Find the character slider full_id that corresponds to the outfit slider.

        For default sliders: match by short_id part of full_id (e.g. "breast_size_type_01")
        For custom sliders: match by path containing "custom/{short_id}"
            (e.g. target_mesh/{char_id}/custom/{short_id}.obj)

        Returns the full_id if found, None otherwise.
        """
        for full_id, info in sliders_info.items():
            if is_custom:
                # Custom slider: match by path containing "custom/{short_id}"
                path = info.get("path", "")
                # Normalize path separators
                normalized = path.replace("\\", "/")
                # Check if path contains "custom/{short_id}"
                if f"custom/{short_id}" in normalized:
                    return full_id
            else:
                # Default slider: match by short_id part of full_id
                parts = full_id.split(".", 1)
                if len(parts) == 2:
                    fid_char_id, fid_short_id = parts
                    if fid_char_id == char_id and fid_short_id == short_id:
                        return full_id
        return None

    # ---------- window width for outfits panel ----------

    def adjust_window_width(self, show_panel: bool):
        """
        Adjust main window width based on whether OutfitsPanel is shown.
        Now controls 3 panels: Outfits, Outfit Default Sliders, Outfit Custom Sliders.
        """
        h = self.host
        if h.is_maximized():
            return

        # Each panel ~200px, 3 panels total
        outfit_w = 200 * 3
        w = h.window_width()

        if show_panel:
            if w < 1800:
                h.resize_window(w + outfit_w, h.window_height())
        else:
            if w > 1300:
                h.resize_window(w - outfit_w, h.window_height())