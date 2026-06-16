# -*- coding: utf-8 -*-
"""
Custom Slider Management Module for Body Slider Pro.
Handles adding, deleting, editing, renaming, and path resolution for custom morph sliders.
Encapsulated from BodySlider to keep body_slider_func.py lean.
"""

import os
import shutil
import re
from typing import Dict, Any, List, Optional, Set, Tuple


SLIDER_NAME_MAX_LEN = 64


class CustomSliderManager:
    """
    Centralized manager for all custom (non-default) slider operations.
    Accessed via BodySlider.custom_slider_mgr.
    """

    def __init__(self, window_host):
        """
        :param window_host: BodySlider instance providing:
            - root_dir, char_config_dir
            - characters, character_sliders, sliders_info, active_char_id
            - _char_custom_dir(), _char_target_mesh_dir(), _norm_path()
            - generate_slider_id(), T (translations)
        """
        self.w = window_host

    # ===================== ADD =====================

    def add_custom_slider(
        self,
        char_id: str,
        slider_name: str,
        min_v: float,
        max_v: float,
        obj_path: str,
        existing_ids: Optional[List[str]] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Add a new custom slider.

        Returns:
            (full_slider_id, error_message)
            - On success: (full_id, None)
            - On failure: (None, error_string)
        """
        if not slider_name or not slider_name.strip():
            return None, "Slider name is empty."

        slider_name = slider_name.strip()
        if len(slider_name) > SLIDER_NAME_MAX_LEN:
            slider_name = slider_name[:SLIDER_NAME_MAX_LEN]

        # Ensure target directory
        char_custom_dir = self.w._char_custom_dir(char_id)
        os.makedirs(char_custom_dir, exist_ok=True)

        # Copy mesh into project-managed directory
        try:
            final_path = self._ensure_file_in_custom_dir(obj_path, char_custom_dir)
        except Exception as e:
            return None, f"Copy failed: {str(e)}"

        # Generate unique full slider ID (e.g. "damiane.big_nose")
        existing_ids = existing_ids or list(self.w.sliders_info.keys())
        full_id = self.w.generate_slider_id(char_id, slider_name, avoid_set=set(existing_ids))

        # Store relative path (relative to root_dir)
        rel_path = self.to_relative_path(final_path)

        slider_info: Dict[str, Any] = {
            "name": slider_name,
            "min": float(min_v),
            "max": float(max_v),
            "path": rel_path,
            "current_value": 0.0,
            "is_default": False,
        }

        # Write into sliders_info (in-memory runtime map)
        self.w.sliders_info[full_id] = slider_info

        # Also ensure character_sliders entry is in sync
        self._sync_slider_to_char_config(char_id, full_id, slider_info)

        return full_id, None

    # ===================== DELETE =====================

    def delete_custom_slider(self, char_id: str, full_sid: str) -> bool:
        """
        Delete a custom slider by its full ID (e.g. "damiane.big_nose").
        Optionally removes its file if safe.
        """
        if not full_sid or full_sid not in self.w.sliders_info:
            return False

        info = self.w.sliders_info[full_sid]
        if info.get("is_default", False):
            return False  # protect default sliders

        path = info.get("path", "")
        abs_path = self.to_absolute_path(path)

        # Remove file only if it is canonical and not referenced elsewhere
        if abs_path and os.path.isabs(abs_path) and os.path.exists(abs_path):
            if self._is_canonical_slider_path(full_sid, abs_path):
                if not self._is_file_referenced_globally(abs_path, exclude_sid=full_sid):
                    try:
                        os.remove(abs_path)
                    except OSError:
                        pass

        # Remove from sliders_info
        del self.w.sliders_info[full_sid]

        # Remove from character_sliders
        self._remove_slider_from_char_config(char_id, full_sid)

        return True

    # ===================== RENAME =====================

    def rename_custom_slider(self, full_sid: str, new_name: str) -> bool:
        """
        Rename a custom slider (update its display name only).
        """
        if not full_sid or full_sid not in self.w.sliders_info:
            return False

        info = self.w.sliders_info[full_sid]
        if info.get("is_default", False):
            return False

        if not new_name or not new_name.strip():
            return False

        new_name = new_name.strip()
        if len(new_name) > SLIDER_NAME_MAX_LEN:
            new_name = new_name[:SLIDER_NAME_MAX_LEN]

        info["name"] = new_name
        return True

    # ===================== EDIT (full) =====================

    def edit_custom_slider(
        self,
        full_sid: str,
        new_name: str,
        new_full_id: str,
        new_path: str,
        new_min: float,
        new_max: float,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Edit an existing custom slider (name, id, path, range).
        Returns (new_full_id, error_message).
        """
        if not full_sid or full_sid not in self.w.sliders_info:
            return None, "Slider not found."

        info = self.w.sliders_info[full_sid]
        if info.get("is_default", False):
            return None, "Cannot edit default slider."

        new_name = (new_name or "").strip() or info["name"]
        if len(new_name) > SLIDER_NAME_MAX_LEN:
            new_name = new_name[:SLIDER_NAME_MAX_LEN]

        # Ensure file in managed dir
        try:
            final_path = self._ensure_file_in_custom_dir(new_path, self.w._char_custom_dir(self.w.active_char_id))
        except Exception as e:
            return None, f"Copy failed: {str(e)}"

        rel_path = self.to_relative_path(final_path)

        # If ID changed, remove old entry
        if new_full_id != full_sid:
            del self.w.sliders_info[full_sid]

        new_info: Dict[str, Any] = {
            "name": new_name,
            "min": float(new_min),
            "max": float(new_max),
            "path": rel_path,
            "current_value": 0.0,
            "is_default": False,
        }

        self.w.sliders_info[new_full_id] = new_info
        return new_full_id, None

    # ===================== RESELECT FILE =====================

    def reselect_slider_file(self, full_sid: str, new_obj_path: str) -> Optional[str]:
        """
        Change a slider's file via the "reselect" flow.
        Reuses change_slider_morph logic.
        """
        return self.change_slider_morph(full_sid, new_obj_path)

    # ===================== CHANGE MORPH FILE =====================

    def change_slider_morph(self, full_sid: str, new_obj_path: str) -> Optional[str]:
        """
        Change the morph mesh file for an existing custom slider.
        Returns error message or None on success.
        """
        if not full_sid or full_sid not in self.w.sliders_info:
            return "Slider not found."

        info = self.w.sliders_info[full_sid]
        if info.get("is_default", False):
            return "Cannot change default slider morph."

        char_custom_dir = self.w._char_custom_dir(self.w.active_char_id)
        try:
            final_path = self._ensure_file_in_custom_dir(new_obj_path, char_custom_dir)
        except Exception as e:
            return f"Copy failed: {str(e)}"

        old_path = info.get("path", "")
        old_abs = self.to_absolute_path(old_path)

        # Clean up old file if safe
        if old_abs and os.path.isabs(old_abs) and os.path.exists(old_abs):
            if self._is_canonical_slider_path(full_sid, old_abs):
                if not self._is_file_referenced_globally(old_abs, exclude_sid=full_sid):
                    try:
                        os.remove(old_abs)
                    except OSError:
                        pass

        info["path"] = self.to_relative_path(final_path)
        return None

    # ===================== PATH UTILS =====================

    @staticmethod
    def _slider_local_id_from_name(name: str) -> str:
        s = name.strip().lower()
        s = re.sub(r"\s+", "_", s)
        s = re.sub(r"[^a-z0-9_]", "", s)
        return s.strip("_") or "slider"

    def to_relative_path(self, abs_path: str) -> str:
        """
        Convert absolute path to relative path (relative to root_dir).
        Falls back to absolute path on cross-device or errors.
        """
        if not abs_path:
            return ""
        if os.path.isabs(abs_path):
            try:
                rel = os.path.relpath(abs_path, self.w.root_dir)
                return self.w._norm_path(rel)
            except (ValueError, OSError):
                return abs_path
        return abs_path

    def to_absolute_path(self, saved_path: str) -> str:
        """
        Resolve a stored path (usually relative) to an absolute path.
        """
        if not saved_path:
            return ""
        if os.path.isabs(saved_path):
            return saved_path
        return os.path.abspath(os.path.join(self.w.root_dir, saved_path))

    # ===================== INTERNAL HELPERS =====================

    def _ensure_file_in_custom_dir(self, src: str, target_dir: str) -> str:
        """
        Ensure the source file is copied/moved into target_dir.
        Avoids name collisions by appending _0, _1, ...
        Returns the final absolute path.
        """
        os.makedirs(target_dir, exist_ok=True)
        src_abs = os.path.abspath(src)

        # Already in target_dir: keep as is
        if src_abs.startswith(os.path.abspath(target_dir)):
            return src_abs

        base, ext = os.path.splitext(os.path.basename(src_abs))
        dest = os.path.join(target_dir, base + ext)

        # Avoid collision
        if os.path.exists(dest) or os.path.abspath(dest) == src_abs:
            i = 0
            while True:
                candidate = os.path.join(target_dir, f"{base}_{i}{ext}")
                if not os.path.exists(candidate):
                    dest = candidate
                    break
                i += 1

        if os.path.abspath(dest) != src_abs:
            shutil.copy2(src_abs, dest)
        return os.path.abspath(dest)

    def _is_canonical_slider_path(self, sid: str, path: str) -> bool:
        """
        Check if path is inside the canonical target_mesh for the active character.
        """
        if not path or not self.w.active_char_id:
            return False
        try:
            target_dir = self.w._char_target_mesh_dir(self.w.active_char_id)
            return os.path.abspath(path).startswith(os.path.abspath(target_dir))
        except (ValueError, OSError):
            return False

    def _is_file_referenced_globally(self, file_path: str, exclude_sid: str = None) -> bool:
        """
        Check if a file is referenced by other characters/sliders.
        """
        file_abs = os.path.abspath(file_path)

        # Check characters' PAC paths
        for cid, c in self.w.characters.items():
            pac = c.get("original_pac_path", "")
            if pac and os.path.abspath(pac) == file_abs:
                return True

        # Check character_sliders
        for cid, sliders in self.w.character_sliders.items():
            if not isinstance(sliders, dict):
                continue
            for local_id, info in sliders.items():
                if not isinstance(info, dict):
                    continue
                full_sid = f"{cid}.{local_id}"
                if full_sid == exclude_sid:
                    continue
                p = info.get("path", "")
                if p and os.path.abspath(p) == file_abs:
                    return True

        # Check sliders_info
        for sid, info in self.w.sliders_info.items():
            if sid == exclude_sid:
                continue
            p = info.get("path", "")
            if p and os.path.abspath(p) == file_abs:
                return True

        return False

    def _sync_slider_to_char_config(self, char_id: str, full_sid: str, slider_info: Dict[str, Any]):
        """
        Sync a slider entry into character_sliders[char_id] as local_id -> info.
        """
        self.w.character_sliders.setdefault(char_id, {})
        sliders_cfg = self.w.character_sliders[char_id]

        # Derive local_id from full_sid
        prefix = char_id + "."
        if full_sid.startswith(prefix):
            local_id = full_sid[len(prefix):]
        else:
            local_id = self._slider_local_id_from_name(slider_info.get("name", "slider"))

        # Avoid collision
        base_local = local_id
        while local_id in sliders_cfg:
            local_id = f"{base_local}_{len(sliders_cfg)}"

        sliders_cfg[local_id] = slider_info

    def _remove_slider_from_char_config(self, char_id: str, full_sid: str):
        """
        Remove slider entry from character_sliders[char_id].
        """
        sliders_cfg = self.w.character_sliders.get(char_id, {})
        if not isinstance(sliders_cfg, dict):
            return

        prefix = char_id + "."
        if full_sid.startswith(prefix):
            local_id = full_sid[len(prefix):]
            sliders_cfg.pop(local_id, None)
        else:
            # Fallback: find by matching name
            name_to_find = self.w.sliders_info.get(full_sid, {}).get("name")
            to_remove = []
            for lid, info in sliders_cfg.items():
                if isinstance(info, dict) and info.get("name") == name_to_find:
                    to_remove.append(lid)
            for lid in to_remove:
                sliders_cfg.pop(lid, None)

    # ===================== MERGE FOR IMPORT =====================

    def merge_sliders_for_import(
        self,
        char_id: str,
        existing_sliders: Dict[str, Any],
        new_sliders: Dict[str, Any],
        merge_choices: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Merge sliders when importing a character pack with Merge mode.

        - existing_sliders: {local_id: slider_info} from current char config
        - new_sliders: {local_id: slider_info} from imported pack config
        - merge_choices:
            {
              "conflicts": {local_id: "existing" | "new" | None},
              "new_only": {local_id: bool}
            }

        Rules:
        - Default sliders (is_default=True) are always kept from existing.
        - For conflicts:
            - "existing": keep existing slider as is
            - "new": use new slider, ensure file in target_mesh, update path
            - None: drop slider (do not include)
        - For new_only:
            - True: add new slider, ensure file, update path
            - False: do not add

        After merge, cleans up orphan files in target_mesh/{char_id}.
        """
        conflicts = merge_choices.get("conflicts", {})
        new_only = merge_choices.get("new_only", {})

        char_target_dir = self.w._char_target_mesh_dir(char_id)
        os.makedirs(char_target_dir, exist_ok=True)

        merged: Dict[str, Any] = {}

        # 1) Always keep existing default sliders
        for local_id, info in existing_sliders.items():
            if not isinstance(info, dict):
                continue
            if info.get("is_default", False):
                merged[local_id] = info.copy()

        # 2) Handle conflicts
        for local_id, choice in conflicts.items():
            ex = existing_sliders.get(local_id)
            nw = new_sliders.get(local_id)
            if choice == "existing" and isinstance(ex, dict):
                merged[local_id] = ex.copy()
            elif choice == "new" and isinstance(nw, dict):
                slider = nw.copy()
                slider["path"] = self._copy_target_mesh_into(char_id, slider.get("path", ""))
                merged[local_id] = slider

        # 3) Handle new-only sliders
        for local_id, include in new_only.items():
            if not include:
                continue
            nw = new_sliders.get(local_id)
            if not isinstance(nw, dict):
                continue
            slider = nw.copy()
            slider["path"] = self._copy_target_mesh_into(char_id, slider.get("path", ""))
            merged[local_id] = slider

        # 4) Clean up orphan files in target_mesh/{char_id}
        self._cleanup_orphan_mesh_files(char_id, merged)

        return merged

    def _copy_target_mesh_into(self, char_id: str, src_path: str) -> str:
        """
        Copy a target mesh file into target_mesh/{char_id}, avoiding collisions.
        Returns the final absolute path.
        """
        if not src_path:
            return src_path

        src_abs = os.path.abspath(src_path)
        char_target_dir = self.w._char_target_mesh_dir(char_id)
        os.makedirs(char_target_dir, exist_ok=True)

        # If already inside this char's target_mesh, keep as is
        if src_abs.startswith(os.path.abspath(char_target_dir)):
            return src_abs

        base, ext = os.path.splitext(os.path.basename(src_abs))
        dest = os.path.join(char_target_dir, base + ext)

        if os.path.exists(dest):
            i = 0
            while True:
                candidate = os.path.join(char_target_dir, f"{base}_{i}{ext}")
                if not os.path.exists(candidate):
                    dest = candidate
                    break
                i += 1

        if os.path.abspath(dest) != src_abs:
            shutil.copy2(src_abs, dest)

        return os.path.abspath(dest)

    def _cleanup_orphan_mesh_files(self, char_id: str, merged_sliders: Dict[str, Any]):
        """
        Remove files in target_mesh/{char_id} that are no longer referenced
        by any slider in merged_sliders.
        """
        char_target_dir = self.w._char_target_mesh_dir(char_id)
        if not os.path.isdir(char_target_dir):
            return

        # Collect all referenced files (absolute paths) under target_mesh/{char_id}
        referenced: Set[str] = set()

        for info in merged_sliders.values():
            if not isinstance(info, dict):
                continue
            p = info.get("path", "")
            if not p:
                continue
            abs_p = self.to_absolute_path(p)
            if abs_p and os.path.abspath(abs_p).startswith(os.path.abspath(char_target_dir)):
                referenced.add(os.path.abspath(abs_p))

        # Walk target_mesh/{char_id} and remove unreferenced files
        for dirpath, _, filenames in os.walk(char_target_dir, topdown=False):
            for fn in filenames:
                fp = os.path.abspath(os.path.join(dirpath, fn))
                if fp not in referenced:
                    try:
                        os.remove(fp)
                    except OSError:
                        pass

        # Remove empty directories
        for dirpath, _, _ in os.walk(char_target_dir, topdown=False):
            try:
                if dirpath != char_target_dir and not os.listdir(dirpath):
                    os.rmdir(dirpath)
            except OSError:
                pass
