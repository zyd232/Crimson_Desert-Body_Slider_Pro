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
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

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

    # Outfit UV / normal / material maps
    @property
    def outfit_uv_map(self) -> Dict[str, np.ndarray]:
        return self._app.outfit_uv_map

    @outfit_uv_map.setter
    def outfit_uv_map(self, v: Dict[str, np.ndarray]):
        self._app.outfit_uv_map = v

    @property
    def outfit_normal_map(self) -> Dict[str, np.ndarray]:
        return self._app.outfit_normal_map

    @outfit_normal_map.setter
    def outfit_normal_map(self, v: Dict[str, np.ndarray]):
        self._app.outfit_normal_map = v

    @property
    def outfit_material_map(self) -> Dict[str, str]:
        return self._app.outfit_material_map

    @outfit_material_map.setter
    def outfit_material_map(self, v: Dict[str, str]):
        self._app.outfit_material_map = v

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
        h.outfit_uv_map = {}
        h.outfit_normal_map = {}
        h.outfit_material_map = {}

        if outfit_pac_mesh:
            for sm in outfit_pac_mesh.submeshes:
                if sm.vertices:
                    h.outfit_original_points[sm.name] = np.array(sm.vertices, dtype=np.float32)
                if sm.faces is not None and len(sm.faces) > 0:
                    h.outfit_faces[sm.name] = np.array(sm.faces, dtype=np.int32)
                # UV coordinates
                if sm.uvs and len(sm.uvs) > 0:
                    h.outfit_uv_map[sm.name] = np.asarray(sm.uvs, dtype=np.float64)
                # Normals
                if sm.normals and len(sm.normals) > 0:
                    h.outfit_normal_map[sm.name] = np.asarray(sm.normals, dtype=np.float64)
                # Material name
                mat_name = getattr(sm, "material", None) or ""
                if mat_name:
                    h.outfit_material_map[sm.name] = mat_name
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

        # --- 独立服装滑块:从 outfit_config 读取记录,计算并合并 morph delta ---
        oc_sliders: List[Tuple[str, Dict[str, Any]]] = []
        ocm = h.outfit_config_mgr
        if ocm and mod_path:
            oc_map = ocm.list_outfit_sliders(char_id, mod_path)
            for sid, rec in oc_map.items():
                oc_sliders.append((sid, rec))
            if oc_sliders:
                self.refresh_outfit_custom_morphs(
                    char_id, original_path, mod_path,
                    [sid for sid, _ in oc_sliders],
                )

        viewer = h.get_plotter()
        if not viewer:
            return

        # Apply morphs to outfit mesh.
        # 独立服装滑块的 morph key 为 "custom/{slider_id}",不在 sliders_info 中,
        # 需要构建 effective_info 把它们的 current_value 合并进来供 apply_morphs 使用。
        effective_si: Dict[str, Dict[str, Any]] = dict(h.sliders_info)
        for sid, rec in oc_sliders:
            morph_key = self.outfit_custom_morph_key(sid)
            effective_si[morph_key] = {
                "name": rec.get("name", sid),
                "min": float(rec.get("min", -50)),
                "max": float(rec.get("max", 150)),
                "current_value": float(rec.get("current_value", 0.0)),
                "is_default": False,
            }

        morphed = h.apply_morphs(
            h.outfit_original_points,
            h.outfit_morph_data,
            effective_si,
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
        h.outfit_uv_map = {}
        h.outfit_normal_map = {}
        h.outfit_material_map = {}

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

        # --- 合并独立服装滑块的 current_value到 effective_info ---
        # 独立服装滑块的 morph key = "custom/{slider_id}",从 outfit_config
        # 读取当前 outfit 的记录;同时用内存 outfit_slider_values 覆盖最新拖动值
        # (outfit_slider_values 的 key 为 "outfit_custom/{slider_id}")。
        ocm = h.outfit_config_mgr
        if ocm and h.active_outfit_mod_path:
            oc_map = ocm.list_outfit_sliders(
                h.active_char_id or "", h.active_outfit_mod_path
            )
            if oc_map:
                if not isinstance(sliders_info, dict) or sliders_info is h.sliders_info:
                    sliders_info = dict(sliders_info)
                for sid, rec in oc_map.items():
                    morph_key = self.outfit_custom_morph_key(sid)
                    # 内存中的实时拖动值优先(若存在)
                    mem_key = f"outfit_{morph_key}"
                    live_val = slider_values.get(mem_key)
                    cv = float(live_val) if live_val is not None else float(
                        rec.get("current_value", 0.0)
                    )
                    sliders_info[morph_key] = {
                        "name": rec.get("name", sid),
                        "min": float(rec.get("min", -50)),
                        "max": float(rec.get("max", 150)),
                        "current_value": cv,
                        "is_default": False,
                    }

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
                    # Include "custom/" prefix so the short_id matches the slider_segment
                    # format used in MOD export (e.g. "custom/cd_phw_00_nude_00_0001_damian")
                    short_id = f"custom/{sub_entry}"
                    slider_dir = sub_path
                    candidates = [
                        os.path.join(slider_dir, mod_dir, pac_base),
                        os.path.join(slider_dir, mod_dir, base_no_ext + ".obj"),
                        os.path.join(slider_dir, mod_dir, base_no_ext + ".pac"),
                    ]
                    has_mesh = any(os.path.exists(c) for c in candidates)
                    if not has_mesh:
                        continue
                    # 优先判断是否为独立服装滑块(查 outfit_config),
                    # 避免子串匹配误将其关联到角色滑块。
                    oc_record = self._lookup_outfit_custom_record(
                        active_outfit_mod_path, short_id
                    )
                    if oc_record and oc_record.get("is_outfit_custom") is True:
                        # 独立服装滑块:不参与角色滑块匹配与 link
                        name = oc_record.get("name", short_id)
                        min_v = float(oc_record.get("min", -50))
                        max_v = float(oc_record.get("max", 150))
                        cur_v = float(oc_record.get("current_value", 0))
                        key = f"outfit_{short_id}"
                        discovered[key] = {
                            "short_id": short_id,
                            "name": name,
                            "min": min_v,
                            "max": max_v,
                            "current_value": cur_v,
                            "char_slider_id": None,
                            "is_custom": True,
                            "is_outfit_custom": True,
                            "path": oc_record.get("path", ""),
                            "slider_id": oc_record.get("slider_id", sub_entry),
                        }
                    else:
                        char_sid = self._find_char_slider_by_short_id(short_id, char_id, sliders_info, is_custom=True)
                        if char_sid:
                            # 已链接角色自定义滑块:沿用角色滑块属性
                            cinfo = sliders_info[char_sid]
                            name = cinfo.get("name", short_id)
                            min_v = float(cinfo.get("min", -50))
                            max_v = float(cinfo.get("max", 150))
                            cur_v = float(cinfo.get("current_value", 0))
                            key = f"outfit_{short_id}"
                            discovered[key] = {
                                "short_id": short_id,
                                "name": name,
                                "min": min_v,
                                "max": max_v,
                                "current_value": cur_v,
                                "char_slider_id": char_sid,
                                "is_custom": True,
                                "is_outfit_custom": False,
                            }
                        else:
                            # 既无角色滑块也无 outfit_config 记录:遗留目录,
                            # 默认当成无链接项展示(不参与 link)
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
                                "char_slider_id": None,
                                "is_custom": True,
                                "is_outfit_custom": False,
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

        # Order: character sliders (default first, then linked custom) in
        # sliders_info iteration order, then outfit-custom (independent)
        # sliders last, then any leftover legacy entries.
        result: Dict[str, Dict[str, Any]] = {}
        oc_keys: List[str] = []
        leftover_keys: List[str] = []

        # 1) 已链接角色滑块(默认 + 自定义),按 sliders_info 顺序
        for full_sid, info in sliders_info.items():
            parts = full_sid.split(".", 1)
            if len(parts) == 2:
                fid_short_id = parts[1]
                key = f"outfit_{fid_short_id}"
                if key in discovered:
                    result[key] = discovered[key]
                    continue
                # For custom sliders: full_sid uses "." but discovered key uses "/"
                if fid_short_id.startswith("custom."):
                    custom_key = f"outfit_{fid_short_id.replace('.', '/', 1)}"
                    if custom_key in discovered:
                        result[custom_key] = discovered[custom_key]

        # 2) 分类剩余项:独立服装滑块 vs 遗留目录
        for key, info in discovered.items():
            if key in result:
                continue
            if info.get("is_outfit_custom", False):
                oc_keys.append(key)
            else:
                leftover_keys.append(key)

        # 3) 追加顺序:先遗留(无角色匹配但非独立),再独立服装滑块
        for key in leftover_keys:
            result[key] = discovered[key]
        for key in oc_keys:
            result[key] = discovered[key]

        return result

    @staticmethod
    def _find_char_slider_by_short_id(
        short_id: str, char_id: str, sliders_info: Dict[str, Dict[str, Any]],
        is_custom: bool = False
    ) -> Optional[str]:
        """
        Find the character slider full_id that corresponds to the outfit slider.

        For default sliders: match by short_id part of full_id (e.g. "breast_size_type_01")
        For custom sliders: match by path containing "custom/{base_name}"
            (e.g. target_mesh/{char_id}/custom/{base_name}.obj)
            short_id for custom now includes "custom/" prefix (e.g. "custom/cd_phw_00_nude_00_0001_damian")

        Returns the full_id if found, None otherwise.
        """
        for full_id, info in sliders_info.items():
            if is_custom:
                # Custom slider: short_id includes "custom/" prefix.
                # Match by checking if the slider path contains the short_id.
                path = info.get("path", "")
                normalized = path.replace("\\", "/")
                if short_id in normalized:
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

    def adjust_window_width(self, show_panel: bool, is_default_char: bool = True):
        """
        Adjust main window width based on whether OutfitsPanel is shown.
        Controls 3 panels for default chars (Outfits, Outfit Default Sliders,
        Outfit Custom Sliders) or 2 panels for custom chars (Outfits,
        Outfit Custom Sliders).
        """
        h = self.host
        if h.is_maximized():
            return

        # Each panel ~200px; default chars have 3 panels, custom chars have 2
        panel_count = 3 if is_default_char else 2
        outfit_w = 200 * panel_count
        w = h.window_width()

        if show_panel:
            if w < 1800:
                h.resize_window(w + outfit_w, h.window_height())
        else:
            if w > 1300:
                h.resize_window(w - outfit_w, h.window_height())

    # ===================== Outfit Custom (independent) Sliders =====================
    #
    # 独立服装滑块的业务方法。与角色滑块完全解耦:
    #   - Target mesh 部署到 exported_outfit/{char_id}/custom/{slider_id}/<mod_dir>/<file>
    #     文件名保持与原始 outfit 同名,slider_id 仅体现在目录层级
    #   - morph delta 始终从部署后的 mesh 文件计算,写入 outfit_morph_data(以
    #     "custom/{slider_id}" 为 key,与 short_id 一致)
    #   - 属性持久化到 outfit_config/{char_id}.json(is_outfit_custom=true)
    #   - 不写入 outfit_index.json,不与角色滑块建立链接

    # ---- morph key convention ----
    @staticmethod
    def outfit_custom_morph_key(slider_id: str) -> str:
        """Morph key for an outfit-custom slider = short_id = custom/{slider_id}."""
        return f"custom/{slider_id}"

    # ---- internal: lookup outfit_config record ----
    def _lookup_outfit_custom_record(
        self, active_outfit_mod_path: str, short_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Query outfit_config JSON for an outfit-custom slider record.
        Returns the record dict or None.
        """
        h = self.host
        ocm = h.outfit_config_mgr
        if not ocm or not active_outfit_mod_path:
            return None
        # short_id is "custom/{slider_id}"; OCM stores it directly
        data = ocm.get_all_for_char(h.active_char_id or "")
        rec = data.get(active_outfit_mod_path, {}).get(short_id)
        if isinstance(rec, dict):
            return rec
        # backslash fallback
        alt_path = active_outfit_mod_path.replace("/", "\\")
        rec = data.get(alt_path, {}).get(short_id)
        if isinstance(rec, dict):
            return rec
        return None

    # ---- path helpers ----
    def _outfit_custom_deploy_dir(
        self, char_id: str, slider_id: str
    ) -> str:
        """exported_outfit/{char_id}/custom/{slider_id}"""
        h = self.host
        return os.path.join(
            h.root_dir, "exported_outfit", char_id, "custom", slider_id
        )

    def _outfit_custom_target_candidates(
        self,
        char_id: str,
        slider_id: str,
        mod_dir: str,
        pac_base: str,
        base_no_ext: str,
    ) -> List[str]:
        """Candidate target mesh paths for one outfit-custom slider."""
        deploy_dir = os.path.join(
            self._outfit_custom_deploy_dir(char_id, slider_id),
            mod_dir if mod_dir else "",
        )
        return [
            os.path.join(deploy_dir, pac_base),
            os.path.join(deploy_dir, base_no_ext + ".obj"),
            os.path.join(deploy_dir, base_no_ext + ".pac"),
        ]

    # ---- ADD ----
    def add_outfit_custom_slider(
        self,
        char_id: str,
        slider_id: str,
        slider_name: str,
        min_v: float,
        max_v: float,
        src_mesh_path: str,
        outfit_original_path: str,
        outfit_mod_path: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Deploy a new outfit-custom slider for the currently active outfit.

        - Copies src_mesh_path into exported_outfit/.../custom/{slider_id}/<mod_dir>/<file>
          (keeps the original outfit file name)
        - Computes morph delta into outfit_morph_data
        - Returns (slider_id, None) on success or (None, error) on failure.

        Note: persistence to outfit_config JSON is performed by the caller
        (BodySlider) to keep this manager free of UI concerns; this method
        only returns the final deployed target path via the slider_info it
        builds.
        """
        h = self.host
        if not char_id or not slider_id or not src_mesh_path or not outfit_original_path:
            return None, "Missing required parameters."
        if not os.path.exists(src_mesh_path):
            return None, "Source mesh file does not exist."

        # Resolve <mod_dir> and <file> from the active outfit
        pac_base = os.path.basename(outfit_original_path)          # e.g. cd_xxx.pac
        base_no_ext = os.path.splitext(pac_base)[0]
        mod_dir = os.path.dirname(outfit_mod_path or "")            # "" if top-level

        deploy_dir = os.path.join(
            self._outfit_custom_deploy_dir(char_id, slider_id),
            mod_dir if mod_dir else "",
        )
        try:
            os.makedirs(deploy_dir, exist_ok=True)
        except OSError as e:
            return None, f"Cannot create deploy directory: {e}"

        # Target file name = keep the original outfit file name
        dest_file = os.path.join(deploy_dir, pac_base)
        try:
            shutil.copy2(src_mesh_path, dest_file)
        except OSError as e:
            return None, f"Copy failed: {e}"

        # Compute morph delta into outfit_morph_data (uses active outfit points)
        morph_key = self.outfit_custom_morph_key(slider_id)
        if h.outfit_original_points:
            try:
                h.compute_morph_delta(
                    morph_key, dest_file,
                    h.outfit_morph_data, h.outfit_original_points,
                )
            except Exception:
                # non-fatal: slider exists but won't deform until mesh fixed
                pass

        return slider_id, None

    def get_deployed_target_path(
        self,
        char_id: str,
        slider_id: str,
        outfit_original_path: str,
        outfit_mod_path: str,
    ) -> str:
        """
        Return the deployed mesh path (best candidate) for an outfit-custom
        slider for the given active outfit. Used to recompute morph after edit.
        """
        if not outfit_original_path:
            return ""
        pac_base = os.path.basename(outfit_original_path)
        base_no_ext = os.path.splitext(pac_base)[0]
        mod_dir = os.path.dirname(outfit_mod_path or "")
        for c in self._outfit_custom_target_candidates(
            char_id, slider_id, mod_dir, pac_base, base_no_ext
        ):
            if os.path.exists(c):
                return c
        return ""

    # ---- EDIT ----
    def edit_outfit_custom_slider(
        self,
        char_id: str,
        old_slider_id: str,
        new_slider_id: str,
        new_src_mesh_path: str,
        outfit_original_path: str,
        outfit_mod_path: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Edit an outfit-custom slider. Handles three cases:
          1) slider_id unchanged, new mesh provided -> overwrite mesh, recompute
          2) slider_id changed -> rename deploy dir, recompute; caller updates JSON
          3) slider_id changed and mesh provided -> both

        Returns (new_slider_id, None) on success or (None, error).
        Persistence (JSON rename + path update) is the caller's responsibility.
        """
        h = self.host
        if not char_id or not old_slider_id or not new_slider_id:
            return None, "Missing required parameters."
        if not outfit_original_path:
            return None, "No active outfit."

        old_deploy_root = self._outfit_custom_deploy_dir(char_id, old_slider_id)
        new_deploy_root = self._outfit_custom_deploy_dir(char_id, new_slider_id)

        # 1) If slider_id changed, rename the deploy directory first.
        if new_slider_id != old_slider_id:
            if os.path.isdir(old_deploy_root) and not os.path.exists(new_deploy_root):
                try:
                    shutil.move(old_deploy_root, new_deploy_root)
                except OSError as e:
                    return None, f"Cannot rename slider directory: {e}"
            elif os.path.isdir(old_deploy_root) and os.path.exists(new_deploy_root):
                # Target exists: merge is unsafe; refuse.
                return None, "Target slider id already exists on disk."

            # Replace morph_data key
            old_key = self.outfit_custom_morph_key(old_slider_id)
            new_key = self.outfit_custom_morph_key(new_slider_id)
            md = h.outfit_morph_data or {}
            if old_key in md:
                md[new_key] = md.pop(old_key)

        # 2) If a new mesh file was provided, overwrite the deployed file.
        if new_src_mesh_path:
            if not os.path.exists(new_src_mesh_path):
                return None, "New source mesh file does not exist."
            pac_base = os.path.basename(outfit_original_path)
            base_no_ext = os.path.splitext(pac_base)[0]
            mod_dir = os.path.dirname(outfit_mod_path or "")
            deploy_dir = os.path.join(
                new_deploy_root, mod_dir if mod_dir else ""
            )
            try:
                os.makedirs(deploy_dir, exist_ok=True)
            except OSError as e:
                return None, f"Cannot create deploy directory: {e}"
            dest_file = os.path.join(deploy_dir, pac_base)
            # Remove any stale previously-deployed candidate files for this outfit
            for stale_ext in (".obj", ".pac"):
                if not pac_base.lower().endswith(stale_ext):
                    stale = os.path.join(deploy_dir, base_no_ext + stale_ext)
                    if os.path.exists(stale):
                        try:
                            os.remove(stale)
                        except OSError:
                            pass
            try:
                shutil.copy2(new_src_mesh_path, dest_file)
            except OSError as e:
                return None, f"Copy failed: {e}"

            # Recompute morph delta with new key/target
            new_key = self.outfit_custom_morph_key(new_slider_id)
            if h.outfit_original_points:
                # Clear old delta then recompute
                h.outfit_morph_data.pop(new_key, None)
                try:
                    h.compute_morph_delta(
                        new_key, dest_file,
                        h.outfit_morph_data, h.outfit_original_points,
                    )
                except Exception:
                    pass

        return new_slider_id, None

    # ---- DELETE ----
    def delete_outfit_custom_slider(
        self,
        char_id: str,
        slider_id: str,
    ) -> bool:
        """
        Delete an outfit-custom slider's deployed directory and morph data.
        Returns True if anything was removed.
        """
        h = self.host
        removed = False

        deploy_root = self._outfit_custom_deploy_dir(char_id, slider_id)
        if os.path.isdir(deploy_root):
            try:
                shutil.rmtree(deploy_root)
                removed = True
            except OSError:
                pass

        morph_key = self.outfit_custom_morph_key(slider_id)
        md = h.outfit_morph_data or {}
        if morph_key in md:
            md.pop(morph_key, None)
            removed = True

        return removed

    # ---- refresh morph after structural change ----
    def refresh_outfit_custom_morphs(
        self,
        char_id: str,
        outfit_original_path: str,
        outfit_mod_path: str,
        slider_ids: List[str],
    ) -> None:
        """
        Recompute morph deltas for the given outfit-custom sliders against the
        currently active outfit. Called after add/edit or when outfit activated.
        """
        h = self.host
        if not h.outfit_original_points or not outfit_original_path:
            return
        pac_base = os.path.basename(outfit_original_path)
        base_no_ext = os.path.splitext(pac_base)[0]
        mod_dir = os.path.dirname(outfit_mod_path or "")
        for sid in slider_ids:
            target = ""
            for c in self._outfit_custom_target_candidates(
                char_id, sid, mod_dir, pac_base, base_no_ext
            ):
                if os.path.exists(c):
                    target = c
                    break
            if not target:
                continue
            morph_key = self.outfit_custom_morph_key(sid)
            h.outfit_morph_data.pop(morph_key, None)
            try:
                h.compute_morph_delta(
                    morph_key, target,
                    h.outfit_morph_data, h.outfit_original_points,
                )
            except Exception:
                pass