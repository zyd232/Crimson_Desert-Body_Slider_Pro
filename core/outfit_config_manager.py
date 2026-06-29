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
from typing import Any, Dict, Optional


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
