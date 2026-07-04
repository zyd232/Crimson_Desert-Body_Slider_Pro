"""
Outfit slider config persistence for Body Slider Pro.

Stores per-outfit slider parameters in outfit_config/{char_id}.json so that
each outfit file maintains independent slider values and link states.

JSON structure:
{
  "<mod_path>": {
    "<short_id>": {
      "name": "...",
      "min": -50.0,
      "max": 150.0,
      "current_value": 30.0,
      "is_linked": false
    }
  }
}
"""

import os
import json
from typing import Any, Dict, List, Optional


class OutfitConfigManager:
    """
    Manages outfit slider configuration persistence.

    Each character has its own JSON file under outfit_config/{char_id}.json.
    Within that file, each outfit (identified by mod_path) stores a dict of
    slider configs keyed by short_id.
    """

    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.config_dir = os.path.join(root_dir, "outfit_config")
        os.makedirs(self.config_dir, exist_ok=True)

    # ---------- path helpers ----------

    def _config_path(self, char_id: str) -> str:
        return os.path.join(self.config_dir, f"{char_id}.json")

    # ---------- read / write ----------

    def _read_file(self, char_id: str) -> Dict[str, Any]:
        path = self._config_path(char_id)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
        return {}

    def _write_file(self, char_id: str, data: Dict[str, Any]) -> None:
        path = self._config_path(char_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    # ---------- public API ----------

    def get_all_for_char(self, char_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Return the full config dict for a character.
        Returns {mod_path: {short_id: slider_info}}.
        """
        return self._read_file(char_id)

    def get_slider(
        self, char_id: str, outfit_mod_path: str, short_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Return slider config for a specific outfit + slider.
        Returns None if not found.
        """
        data = self._read_file(char_id)
        return data.get(outfit_mod_path, {}).get(short_id)

    def save_slider(
        self,
        char_id: str,
        outfit_mod_path: str,
        short_id: str,
        slider_info: Dict[str, Any],
    ) -> None:
        """
        Save (or update) a single slider's config.
        """
        data = self._read_file(char_id)
        if outfit_mod_path not in data:
            data[outfit_mod_path] = {}
        data[outfit_mod_path][short_id] = slider_info
        self._write_file(char_id, data)

    def save_config(
        self, char_id: str, data: Dict[str, Dict[str, Any]]
    ) -> None:
        """
        Overwrite the entire config for a character.
        """
        self._write_file(char_id, data)

    def delete_slider(
        self, char_id: str, outfit_mod_path: str, short_id: str
    ) -> None:
        """
        Delete a single slider's config from outfit_config JSON.
        Called when switching from unlinked to linked (linked state has no JSON record).
        """
        data = self._read_file(char_id)
        if outfit_mod_path in data:
            data[outfit_mod_path].pop(short_id, None)
            # Clean up empty mod_path entries
            if not data[outfit_mod_path]:
                del data[outfit_mod_path]
            self._write_file(char_id, data)

    def delete_config(self, char_id: str) -> None:
        """
        Delete the outfit config file for a character.
        """
        path = self._config_path(char_id)
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    # ===================== Outfit-Custom (independent) Sliders =====================
    #
    # 独立服装滑块(不链接角色滑块)的持久化。与上面的角色滑块 link/unlink 记录
    # 共用同一个 JSON 文件,但通过字段 ``is_outfit_custom=True`` 标识与隔离,且
    # 不写入 ``is_linked`` 字段。
    #
    # short_id 约定为 ``custom/{slider_id}``,与 exported_outfit 目录结构中的
    # slider_segment 一致。

    SHORT_ID_PREFIX = "custom/"

    def outfit_slider_short_id(self, slider_id: str) -> str:
        """Build the JSON short_id for an outfit-custom slider."""
        return f"{self.SHORT_ID_PREFIX}{slider_id}"

    def slider_id_from_short_id(self, short_id: str) -> str:
        """Extract the bare slider_id from a ``custom/{slider_id}`` short_id."""
        if short_id.startswith(self.SHORT_ID_PREFIX):
            return short_id[len(self.SHORT_ID_PREFIX):]
        return short_id

    def is_outfit_custom_short_id(self, short_id: str) -> bool:
        return short_id.startswith(self.SHORT_ID_PREFIX)

    def save_outfit_slider(
        self,
        char_id: str,
        outfit_mod_path: str,
        slider_id: str,
        slider_info: Dict[str, Any],
    ) -> str:
        """
        Save (or update) an outfit-custom slider's config.

        slider_info should NOT contain ``is_linked``; this method forces
        ``is_outfit_custom=True`` and stores the morph-delta target ``path``.

        Returns the short_id used as the JSON key.
        """
        short_id = self.outfit_slider_short_id(slider_id)
        record: Dict[str, Any] = {
            "name": slider_info.get("name", slider_id),
            "min": float(slider_info.get("min", -50.0)),
            "max": float(slider_info.get("max", 150.0)),
            "current_value": float(slider_info.get("current_value", 0.0)),
            "is_outfit_custom": True,
            "path": slider_info.get("path", ""),
            "slider_id": slider_id,
        }
        self.save_slider(char_id, outfit_mod_path, short_id, record)
        return short_id

    def get_outfit_slider(
        self,
        char_id: str,
        outfit_mod_path: str,
        slider_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Return the config for one outfit-custom slider, or None.
        """
        short_id = self.outfit_slider_short_id(slider_id)
        return self.get_slider(char_id, outfit_mod_path, short_id)

    def delete_outfit_slider(
        self,
        char_id: str,
        outfit_mod_path: str,
        slider_id: str,
    ) -> None:
        """
        Delete one outfit-custom slider's config from the JSON.
        """
        short_id = self.outfit_slider_short_id(slider_id)
        self.delete_slider(char_id, outfit_mod_path, short_id)

    def rename_outfit_slider(
        self,
        char_id: str,
        outfit_mod_path: str,
        old_slider_id: str,
        new_slider_id: str,
    ) -> str:
        """
        Rename an outfit-custom slider's key in the JSON (short_id changes) and
        return the new short_id. Other fields are preserved.
        """
        old_record = self.get_outfit_slider(char_id, outfit_mod_path, old_slider_id)
        if not old_record:
            # Nothing to rename; ensure no stale key left.
            self.delete_outfit_slider(char_id, outfit_mod_path, old_slider_id)
            return self.outfit_slider_short_id(new_slider_id)
        new_record = dict(old_record)
        new_record["slider_id"] = new_slider_id
        new_record["name"] = old_record.get("name", new_slider_id)
        # Remove old, write new
        self.delete_outfit_slider(char_id, outfit_mod_path, old_slider_id)
        self.save_outfit_slider(char_id, outfit_mod_path, new_slider_id, new_record)
        return self.outfit_slider_short_id(new_slider_id)

    def list_outfit_sliders(
        self,
        char_id: str,
        outfit_mod_path: str,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Return all outfit-custom sliders for one outfit: {slider_id: record}.
        """
        data = self._read_file(char_id)
        out: Dict[str, Dict[str, Any]] = {}
        for short_id, record in data.get(outfit_mod_path, {}).items():
            if not isinstance(record, dict):
                continue
            if record.get("is_outfit_custom") is not True:
                continue
            sid = record.get("slider_id") or self.slider_id_from_short_id(short_id)
            out[sid] = record
        return out

    def list_outfit_slider_ids(self, char_id: str) -> List[str]:
        """
        Return all outfit-custom slider ids across all outfits for a character.
        Used for global id-uniqueness checks when adding/editing.
        """
        data = self._read_file(char_id)
        ids: List[str] = []
        for _mod_path, sliders in data.items():
            if not isinstance(sliders, dict):
                continue
            for short_id, record in sliders.items():
                if not isinstance(record, dict):
                    continue
                if record.get("is_outfit_custom") is not True:
                    continue
                sid = record.get("slider_id") or self.slider_id_from_short_id(short_id)
                if sid and sid not in ids:
                    ids.append(sid)
        return ids
