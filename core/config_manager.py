"""
Config & path management for Body Slider Pro.
Handles config file read/write, character configs, slider configs,
path utilities, default slider management, and migration logic.
"""

import os
import json
import shutil
import re
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------- public constants (imported from ui_components at runtime) ----------
# These are passed into ConfigManager so this module stays independent.


class ConfigManager:
    """
    Centralized config and path management.
    Holds references to core data structures and provides
    all config-related operations.
    """

    def __init__(
        self,
        root_dir: str,
        config_path: str,
        char_config_dir: str,
        characters: Dict[str, Dict[str, Any]],
        character_sliders: Dict[str, Dict[str, Any]],
        sliders_info: Dict[str, Dict[str, Any]],
        camera_positions: Dict[str, Any],
        languages: Dict[str, Any],
        allowed_char_keys: Set[str],
        allowed_slider_keys: Set[str],
        default_character_order: List[str],
        default_sliders: Dict[str, Any],
        default_pac_name: str,
        default_char_id: str,
        default_char_name: str,
        default_mod_path: str,
    ):
        self.root_dir = root_dir
        self.config_path = config_path
        self.char_config_dir = char_config_dir
        os.makedirs(self.char_config_dir, exist_ok=True)

        # References to core data structures (mutated in-place)
        self.characters = characters
        self.character_sliders = character_sliders
        self.sliders_info = sliders_info
        self.camera_positions = camera_positions
        self.languages = languages

        # Config
        self.allowed_char_keys = allowed_char_keys
        self.allowed_slider_keys = allowed_slider_keys
        self.default_character_order = default_character_order
        self.default_sliders = default_sliders

        # Defaults
        self.default_pac_name = default_pac_name
        self.default_char_id = default_char_id
        self.default_char_name = default_char_name
        self.default_mod_path = default_mod_path

        # State
        self.current_lang: str = "en"
        self.saved_window_size: Optional[List[int]] = None
        self.active_char_id: Optional[str] = None
        self.wireframe_enabled: bool = False

    # ---------- path helpers ----------

    def char_config_path(self, char_id: str) -> str:
        return os.path.join(self.char_config_dir, f"{char_id}.json")

    @staticmethod
    def norm_path(p: str) -> str:
        if not p:
            return p
        return os.path.normpath(p).replace("/", "\\")

    def char_original_mesh_dir(self, char_id: str) -> str:
        return self.norm_path(os.path.join(self.root_dir, "original_mesh", char_id))

    def char_target_mesh_dir(self, char_id: str) -> str:
        return self.norm_path(os.path.join(self.root_dir, "target_mesh", char_id))

    def char_custom_dir(self, char_id: str) -> str:
        d = self.norm_path(os.path.join(self.char_target_mesh_dir(char_id), "custom"))
        os.makedirs(d, exist_ok=True)
        return d

    def ensure_char_dirs(self, char_id: str) -> None:
        os.makedirs(self.char_original_mesh_dir(char_id), exist_ok=True)
        os.makedirs(self.char_target_mesh_dir(char_id), exist_ok=True)
        self.char_custom_dir(char_id)

    def ensure_file_in_project(self, src_path: str, target_dir: str) -> str:
        src_path = os.path.abspath(src_path)
        os.makedirs(target_dir, exist_ok=True)

        if src_path.startswith(os.path.abspath(target_dir)):
            return self.norm_path(src_path)

        base, ext = os.path.splitext(os.path.basename(src_path))
        dest = self.norm_path(os.path.join(target_dir, base + ext))

        if os.path.exists(dest):
            i = 0
            while True:
                candidate = self.norm_path(os.path.join(target_dir, f"{base}_{i}{ext}"))
                if not os.path.exists(candidate):
                    dest = candidate
                    break
                i += 1

        if os.path.abspath(dest) != src_path:
            shutil.copy2(src_path, dest)
        return dest

    def remap_slider_path(self, path: str, char_target_dir: str) -> str:
        if not path or not os.path.exists(path):
            return path
        try:
            rel = os.path.relpath(path, os.path.join(self.root_dir, "target_mesh"))
            if not rel.startswith(".."):
                filename = os.path.basename(path)
                if os.path.dirname(rel):
                    maybe = os.path.join(char_target_dir, os.path.dirname(rel), filename)
                else:
                    maybe = os.path.join(char_target_dir, filename)
                if os.path.exists(maybe):
                    return maybe
        except (ValueError, OSError):
            pass
        return path

    def normalize_pac_path(self, pac: str, cid: str) -> str:
        if not pac:
            return pac
        if not os.path.isabs(pac):
            pac = os.path.abspath(os.path.join(self.root_dir, pac))
        if os.path.exists(pac):
            return pac
        try:
            rel = os.path.relpath(pac, self.root_dir)
            if rel.startswith("original_mesh" + os.sep):
                parts = rel.split(os.sep)
                filename = parts[-1]
                candidate = os.path.join(self.root_dir, "original_mesh", cid, filename)
                if os.path.exists(candidate):
                    return candidate
        except (ValueError, OSError):
            pass
        return pac

    @staticmethod
    def resolve_default_pac(legacy_pac: str, new_pac: str) -> Optional[str]:
        if os.path.exists(new_pac):
            return new_pac
        if os.path.exists(legacy_pac):
            os.makedirs(os.path.dirname(new_pac), exist_ok=True)
            shutil.move(legacy_pac, new_pac)
            return new_pac
        return None

    # ---------- slider id helpers ----------

    @staticmethod
    def slider_local_id_from_name(name: str) -> str:
        s = name.strip().lower()
        s = re.sub(r"\s+", "_", s)
        s = re.sub(r"[^a-z0-9_]", "", s)
        return s.strip("_") or "slider"

    def generate_slider_id(self, char_id: str, name: str, avoid_set: Set[str] = None) -> str:
        base = self.slider_local_id_from_name(name)
        avoid = {sid.split(".", 1)[-1] for sid in (avoid_set or set())}

        candidate = base
        if candidate not in avoid:
            return f"{char_id}.{candidate}"

        i = 0
        while True:
            candidate = f"{base}_{i}"
            if candidate not in avoid:
                return f"{char_id}.{candidate}"
            i += 1

    def slider_local_id_from_info(self, info: Dict[str, Any]) -> str:
        return self.slider_local_id_from_name(info.get("name", "slider"))

    # ---------- config load ----------

    def load_config(self) -> None:
        data = self._read_config_file()
        if isinstance(data, dict):
            self.current_lang = data.get("app_language", "en")
            self.saved_window_size = data.get("window_size", None)

            camera_positions = data.get("camera_positions", {})
            if not isinstance(camera_positions, dict):
                camera_positions = {}

            self.camera_positions.clear()
            self.camera_positions.update(camera_positions)

            self.wireframe_enabled = bool(data.get("wireframe_enabled", False))
            active_id = data.get("active_character", None)
            saved_character_order = data.get("character_order", [])
            if not isinstance(saved_character_order, list):
                saved_character_order = []
        else:
            self.current_lang = "en"
            self.saved_window_size = None
            self.camera_positions.clear()
            self.wireframe_enabled = False
            active_id = None
            saved_character_order = []

        self.sliders_info.clear()
        self.characters.clear()
        self.character_sliders.clear()

        self._load_all_characters_from_files()

        valid_character_order = []
        used_in_order = set()
        for char_id in saved_character_order:
            if char_id in self.characters:
                valid_character_order.append(char_id)
                used_in_order.add(char_id)
            else:
                self.character_sliders.pop(char_id, None)

        for default_id in self.default_character_order:
            if default_id not in self.characters:
                self._migrate_or_init_default(default_id)

        # Ensure newly imported characters (not in saved_character_order) are included
        for char_id in list(self.characters.keys()):
            if char_id not in used_in_order:
                valid_character_order.append(char_id)
                used_in_order.add(char_id)

        chars_snapshot = dict(self.characters)
        self.characters.clear()
        self.characters.update(self._order_characters_from(valid_character_order, chars_snapshot))

        if not self.characters:
            self._migrate_or_init_default(None)
        elif active_id and active_id in self.characters:
            self.active_char_id = active_id
        else:
            self.active_char_id = next(iter(self.characters))

        self._ensure_default_sliders_in_config(self.active_char_id)
        self._load_sliders_for_character(self.active_char_id)

    def _read_config_file(self) -> Any:
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def _order_characters_from(
        self,
        saved_character_order: List[str],
        chars: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Order characters based on saved_character_order, using provided chars dict
        (so it is safe even if self.characters has already been cleared).
        """
        ordered_ids: List[str] = []
        seen = set()

        for cid in saved_character_order:
            if cid in chars and cid not in seen:
                ordered_ids.append(cid)
                seen.add(cid)

        for cid in chars:
            if cid not in seen:
                ordered_ids.append(cid)
                seen.add(cid)

        defaults = [cid for cid in ordered_ids if chars[cid].get("is_default", False)]
        customs = [cid for cid in ordered_ids if not chars[cid].get("is_default", False)]

        final: Dict[str, Dict[str, Any]] = {}
        for cid in defaults + customs:
            final[cid] = chars[cid]
        return final

    def _load_all_characters_from_files(self) -> None:
        if not os.path.exists(self.char_config_dir):
            return

        for filename in os.listdir(self.char_config_dir):
            if not filename.endswith(".json"):
                continue
            char_id = filename[:-5]
            filepath = os.path.join(self.char_config_dir, filename)

            char_data = self._read_char_config_file(filepath)
            if not isinstance(char_data, dict):
                continue

            char_info = char_data.get("character", {})
            char_sliders = char_data.get("sliders", {})

            if not isinstance(char_info, dict):
                continue

            char_info.setdefault("id", char_id)
            char_info.setdefault("name", char_id)
            if "is_default" not in char_info:
                char_info["is_default"] = char_id in self.default_character_order
            char_info.setdefault("mod_path", self.default_mod_path)

            pac = char_info.get("original_pac_path", "")
            if pac and not os.path.isabs(pac):
                pac = os.path.abspath(os.path.join(self.root_dir, pac))
            char_info["original_pac_path"] = pac

            self.characters[char_id] = char_info

            if char_sliders and isinstance(char_sliders, dict):
                self.character_sliders[char_id] = char_sliders

    @staticmethod
    def _read_char_config_file(filepath: str) -> Any:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    # ---------- default sliders ----------

    def _apply_default_sliders(self, char_id: str) -> None:
        if not char_id:
            return
        char = self.characters.get(char_id)
        if not char or not char.get("is_default", False):
            return

        char_target_dir = self.char_target_mesh_dir(char_id)

        from core.ui_components import safe_text, DEFAULT_SLIDERS

        for full_id, def_info in DEFAULT_SLIDERS.items():
            if not full_id.startswith(char_id + "."):
                continue

            sid = full_id
            name = safe_text(
                self.languages,
                self.current_lang,
                def_info["name_key"],
                def_info.get("name_key"),
            )
            filename = def_info.get("filename", "")
            path = os.path.join(char_target_dir, filename) if filename else ""

            existing = self.sliders_info.get(sid, {})
            current_value = existing.get("current_value", 0.0)

            self.sliders_info[sid] = {
                "name": name,
                "min": float(def_info.get("min", 0.0)),
                "max": float(def_info.get("max", 100.0)),
                "path": path,
                "current_value": current_value,
                "is_default": True,
            }

    def _is_default_slider(self, sid: str) -> bool:
        from core.ui_components import DEFAULT_SLIDERS
        return sid in DEFAULT_SLIDERS

    def _ensure_default_sliders_in_config(self, char_id: str) -> None:
        if not char_id:
            return

        char = self.characters.get(char_id)
        if not char or not char.get("is_default", False):
            return

        from core.ui_components import safe_text, DEFAULT_SLIDERS

        self.character_sliders.setdefault(char_id, {})
        sliders_cfg = self.character_sliders[char_id]
        existing = sliders_cfg if isinstance(sliders_cfg, dict) else {}

        prefix = char_id + "."
        char_target_dir = self.char_target_mesh_dir(char_id)

        default_local_ids: set = set()
        new_cfg: dict = {}

        for full_id, def_info in DEFAULT_SLIDERS.items():
            if not full_id.startswith(prefix):
                continue

            local_id = full_id[len(prefix):]
            default_local_ids.add(local_id)

            filename = def_info.get("filename", "")
            path = os.path.join(char_target_dir, filename) if filename else ""

            entry = existing.get(local_id)
            current_value = 0.0
            if isinstance(entry, dict):
                current_value = float(entry.get("current_value", 0.0))

            name_key = def_info.get("name_key", local_id)
            slider_name = safe_text(
                self.languages,
                self.current_lang,
                name_key,
                name_key,
            )

            new_cfg[local_id] = {
                "name": slider_name,
                "min": float(def_info.get("min", -100.0)),
                "max": float(def_info.get("max", 100.0)),
                "path": path,
                "current_value": current_value,
                "is_default": True,
            }

        for local_id, entry in existing.items():
            if local_id in default_local_ids:
                continue
            if not isinstance(entry, dict):
                continue
            is_default = entry.get("is_default", False)
            if is_default:
                continue
            new_cfg[local_id] = entry

        self.character_sliders[char_id] = new_cfg

        self._save_char_config_file(
            char_id,
            char,
            new_cfg,
        )

    def _load_sliders_for_character(self, char_id: str) -> None:
        if not char_id:
            self.sliders_info.clear()
            return

        from core.ui_components import safe_text, DEFAULT_SLIDERS

        sliders_cfg = self.character_sliders.get(char_id, {})
        self.sliders_info.clear()
        char_target_dir = self.char_target_mesh_dir(char_id)

        if not sliders_cfg:
            char = self.characters.get(char_id, {})
            if char and char.get("is_default", False):
                self._apply_default_sliders(char_id)
            return

        for local_id, info in sliders_cfg.items():
            if not isinstance(info, dict):
                continue

            sid = f"{char_id}.{local_id}"
            ic = info.copy()

            if self._is_default_slider(sid):
                def_info = DEFAULT_SLIDERS[sid]
                filename = def_info.get("filename", "")
                path = os.path.join(char_target_dir, filename) if filename else ""
                current_value = ic.get("current_value", 0.0)
                name_key = def_info.get("name_key", local_id)
                slider_name = safe_text(
                    self.languages,
                    self.current_lang,
                    name_key,
                    name_key,
                )
                ic = {
                    "name": slider_name,
                    "min": float(def_info.get("min", -100.0)),
                    "max": float(def_info.get("max", 100.0)),
                    "path": path,
                    "current_value": current_value,
                    "is_default": True,
                }
            else:
                name = ic.get("name")
                path = ic.get("path")
                if not name or not path:
                    continue

                if not os.path.isabs(path):
                    path = os.path.abspath(os.path.join(self.root_dir, path))
                candidate = self.remap_slider_path(path, char_target_dir)
                ic["path"] = candidate

                if "min" not in ic or "max" not in ic:
                    continue

                ic.setdefault("current_value", 0.0)
                ic.setdefault("is_default", False)

            self.sliders_info[sid] = ic

    # ---------- migration / defaults ----------

    def _migrate_or_init_default(self, active_id: Optional[str]) -> None:
        default_pac_name = self.default_pac_name
        legacy_pac = os.path.join(self.root_dir, "original_mesh", default_pac_name)
        new_pac = os.path.join(self.root_dir, "original_mesh", self.default_char_id, default_pac_name)

        pac_path = self.resolve_default_pac(legacy_pac, new_pac)

        char_info = {
            "name": self.default_char_name,
            "id": self.default_char_id,
            "is_default": True,
            "original_pac_path": pac_path or "",
            "mod_path": self.default_mod_path,
        }
        self.characters[self.default_char_id] = char_info
        self._save_char_config_file(self.default_char_id, char_info, {})
        self.active_char_id = self.default_char_id

    # ---------- config save ----------

    def _cleanup_redundant_config(self, data: Optional[Dict[str, Any]] = None) -> None:
        for c in self.characters.values():
            if not isinstance(c, dict):
                continue
            for k in list(c.keys()):
                if k not in self.allowed_char_keys:
                    del c[k]

        valid_ids = set(self.characters.keys())
        for cid in list(self.character_sliders.keys()):
            if cid not in valid_ids:
                del self.character_sliders[cid]
                continue
            sliders = self.character_sliders[cid]
            if not isinstance(sliders, dict):
                continue
            for sid, info in list(sliders.items()):
                if not isinstance(info, dict):
                    del sliders[sid]
                    continue
                for k in list(info.keys()):
                    if k not in self.allowed_slider_keys:
                        del info[k]

    def _compute_local_id(self, sid: str, info: Dict[str, Any], prefix: str, used: Set[str]) -> str:
        if sid.startswith(prefix):
            base_local = sid[len(prefix):]
        else:
            base_local = self.slider_local_id_from_info(info)

        candidate = base_local
        if candidate not in used:
            return candidate

        i = 0
        while True:
            candidate = f"{base_local}_{i}"
            if candidate not in used:
                return candidate
            i += 1

    def _save_char_config_file(
        self,
        char_id: str,
        char_info: Dict[str, Any],
        sliders: Dict[str, Any],
    ) -> None:
        cc = char_info.copy()
        if cc.get("original_pac_path"):
            try:
                rel = os.path.relpath(cc["original_pac_path"], self.root_dir)
                cc["original_pac_path"] = self.norm_path(rel)
            except (ValueError, OSError):
                pass
        if cc.get("mod_path"):
            cc["mod_path"] = self.norm_path(cc["mod_path"])

        save_sliders: Dict[str, Any] = {}
        for local_id, info in sliders.items():
            ic = info.copy()
            if "path" in ic and ic["path"]:
                try:
                    rel = os.path.relpath(ic["path"], self.root_dir)
                    ic["path"] = self.norm_path(rel)
                except (ValueError, OSError):
                    pass
            save_sliders[local_id] = ic

        char_data = {
            "character": cc,
            "sliders": save_sliders,
        }

        filepath = self.char_config_path(char_id)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(char_data, f, indent=4, ensure_ascii=False)

    def save_config(
        self,
        current_cam: Optional[List],
        window_size: Optional[List[int]],
        wireframe_enabled: bool,
    ) -> None:
        """
        Save global config and per-character configs.
        UI-specific values (camera, window_size, wireframe) are passed in
        to keep this module UI-agnostic.
        """
        self._cleanup_redundant_config()

        if self.active_char_id:
            self.character_sliders.setdefault(self.active_char_id, {})
            char_sliders = self.character_sliders[self.active_char_id]
            char_sliders.clear()
            used_local_ids: Set[str] = set()

            prefix = self.active_char_id + "."
            for sid, info in self.sliders_info.items():
                local_id = self._compute_local_id(sid, info, prefix, used_local_ids)
                used_local_ids.add(local_id)
                char_sliders[local_id] = info

        for cid, c in self.characters.items():
            sliders = self.character_sliders.get(cid, {})
            self._save_char_config_file(cid, c, sliders)

        # Save global camera position if provided
        if current_cam:
            self.camera_positions["global"] = current_cam

        # Use the actual insertion order of self.characters (respects user drag-sort)
        character_order = list(self.characters.keys())

        config_data = {
            "app_language": self.current_lang,
            "active_character": self.active_char_id,
            "character_order": character_order,
            "camera_positions": self.camera_positions,
            "wireframe_enabled": wireframe_enabled,
        }
        if window_size is not None:
            config_data["window_size"] = window_size

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)

    # ---------- sync sliders to config (used on character switch) ----------

    def sync_sliders_to_config(self, char_id: str) -> None:
        self.character_sliders.setdefault(char_id, {})
        char_sliders = self.character_sliders[char_id]
        char_sliders.clear()
        used_local_ids: Set[str] = set()
        prefix = char_id + "."

        for sid, info in self.sliders_info.items():
            if sid.startswith(prefix):
                base_local = sid[len(prefix):]
            else:
                base_local = self.slider_local_id_from_name(info.get("name", "slider"))

            local_id = base_local
            if local_id in used_local_ids:
                i = 0
                while local_id in used_local_ids:
                    local_id = f"{base_local}_{i}"
                    i += 1
            used_local_ids.add(local_id)
            char_sliders[local_id] = info