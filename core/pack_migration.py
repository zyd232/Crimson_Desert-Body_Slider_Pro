# -*- coding: utf-8 -*-
"""
Legacy character-pack migration: rename custom-slider files to slider local ID.

Before Body Slider Pro `app_version` 1.3.1 (and Outfitter `outfitter_version`
1.2.4), custom-slider target meshes stored their *original source* file name
instead of the slider local id. This module rewrites an *extracted* pack
(temp_dir) so that on-disk file names / folder names and the paths recorded in
``char_config/{cid}.json`` and ``exported_outfit/{cid}/outfit_index.json`` all
conform to the new convention:

    target_mesh/{cid}/custom/{local_id}.{ext}
    exported_outfit/{cid}/custom/{local_id}/...
    {char_id}.json  ->  sliders[local_id].path updated
    outfit_index.json -> target_body_folders / outfits updated

The migration operates **only** on the extracted temp directory; it never
touches the live project. Safely no-ops when there is nothing to migrate.
"""

import json
import logging
import os
import shutil
from typing import Dict, Optional, Set, Tuple

logger = logging.getLogger(__name__)

INDEX_FILENAME = "outfit_index.json"


# --------------------------------------------------------------------------- #
# Path helpers
# --------------------------------------------------------------------------- #
def _norm(p: str) -> str:
    """Normalise a path to forward slashes (for index/relative-path storage)."""
    if not p:
        return p
    return p.replace("\\", "/")


def _file_base_no_ext(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def _stored_path_from_temp_abs(temp_dir: str, abs_path: str) -> str:
    """
    Convert an absolute path inside ``temp_dir/target_mesh/...`` into the
    *stored* relative form used in char_config / outfit_index:
    ``target_mesh/{cid}/...`` (forward slashes).

    Anchoring against ``temp_dir/target_mesh`` (the semantic root that will
    become ``root_dir/target_mesh`` after import) keeps the recorded path stable
    regardless of where temp_dir lives on disk. Falls back to a best-effort
    relative path if the file is not under temp_dir.
    """
    tm_root = os.path.join(temp_dir, "target_mesh")
    try:
        rel = os.path.relpath(abs_path, tm_root)
    except ValueError:
        # Cross-drive fallback: use the basename-relative guess.
        return _norm(os.path.basename(abs_path))
    return _norm(os.path.join("target_mesh", rel))


def _resolve_target_file_in_temp(temp_dir: str, cid: str, stored_path: str) -> Optional[str]:
    """
    Resolve a slider ``path`` (stored relative to root_dir, e.g.
    ``target_mesh/{cid}/custom/foo.obj``) to its absolute location inside
    ``temp_dir``. Returns None if it cannot be located.
    """
    if not stored_path:
        return None
    norm = stored_path.replace("\\", "/")
    # Strip leading "target_mesh/" then anchor under temp_dir/target_mesh.
    if norm.startswith("target_mesh/"):
        norm = norm[len("target_mesh/"):]
    cand = os.path.join(temp_dir, "target_mesh", norm)
    if os.path.isfile(cand):
        return cand
    # Some legacy packs may store an absolute path already; try as-is / basename fallback.
    if os.path.isabs(stored_path) and os.path.isfile(stored_path):
        return stored_path
    base = os.path.basename(stored_path)
    # Last-resort search inside target_mesh/{cid}.
    tm_dir = os.path.join(temp_dir, "target_mesh", cid)
    if os.path.isdir(tm_dir):
        for _r, _d, _files in os.walk(tm_dir):
            if base in _files:
                return os.path.join(_r, base)
    return None


# --------------------------------------------------------------------------- #
# Rename-map construction
# --------------------------------------------------------------------------- #
def build_custom_slider_rename_map(
    temp_dir: str, cid: str
) -> Dict[str, str]:
    """
    Inspect ``temp_dir/char_config/{cid}.json`` and build a mapping of
    ``old_file_basename -> local_id`` for every custom slider whose stored
    file-name base differs from its local id.

    Only entries where old != new are recorded, so callers can iterate the map
    to know exactly what to rename.
    """
    cfg_path = os.path.join(temp_dir, "char_config", f"{cid}.json")
    if not os.path.isfile(cfg_path):
        return {}

    try:
        with open(cfg_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception:
        return {}

    sliders = data.get("sliders") if isinstance(data, dict) else None
    if not isinstance(sliders, dict) or not sliders:
        return {}

    rename_map: Dict[str, str] = {}
    for local_id, info in sliders.items():
        if not isinstance(info, dict):
            continue
        if info.get("is_default", False):
            continue
        stored_path = info.get("path", "") or ""
        old_base = _file_base_no_ext(stored_path)
        if not old_base or old_base == local_id:
            continue
        # Avoid clobbering an earlier mapping if two sliders share a base name.
        if old_base in rename_map and rename_map[old_base] != local_id:
            # Ambiguous: prefer recorded first; skip the duplicate to stay safe.
            continue
        rename_map[old_base] = local_id
    return rename_map


# --------------------------------------------------------------------------- #
# core migration step A: target_mesh + char_config
# --------------------------------------------------------------------------- #
def migrate_target_mesh_and_config(
    temp_dir: str, cid: str, root_dir: str
) -> int:
    """
    Rename custom-slider target-mesh files inside ``temp_dir/target_mesh/{cid}``
    to ``{local_id}{ext}`` and rewrite the corresponding ``path`` entries in
    ``temp_dir/char_config/{cid}.json``.

    Returns the number of sliders migrated.
    """
    cfg_path = os.path.join(temp_dir, "char_config", f"{cid}.json")
    if not os.path.isfile(cfg_path):
        return 0

    try:
        with open(cfg_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception:
        return 0

    if not isinstance(data, dict):
        return 0
    sliders = data.get("sliders")
    if not isinstance(sliders, dict) or not sliders:
        return 0

    migrated = 0
    char_target_dir = os.path.join(temp_dir, "target_mesh", cid)

    for local_id, info in list(sliders.items()):
        if not isinstance(info, dict) or info.get("is_default", False):
            continue
        stored_path = info.get("path", "") or ""
        if not stored_path:
            continue

        src_abs = _resolve_target_file_in_temp(temp_dir, cid, stored_path)
        if not src_abs:
            continue

        ext = os.path.splitext(src_abs)[1]
        old_base = _file_base_no_ext(src_abs)
        if old_base == local_id:
            # Already compliant: still ensure the recorded relative path uses the
            # canonical form (rooted at target_mesh/, independent of temp_dir).
            new_rel = _stored_path_from_temp_abs(temp_dir, src_abs)
            if new_rel != stored_path:
                info["path"] = new_rel
            continue

        # Determine destination directory: keep the file in the same folder it
        # currently lives in (custom/ if it was there, root target_mesh/{cid}
        # otherwise) - we only force the *file name* to local_id.
        src_dir = os.path.dirname(src_abs)
        dest = os.path.join(src_dir, local_id + ext)

        if os.path.abspath(dest) == os.path.abspath(src_abs):
            continue

        # Handle a pre-existing compliant-named file (e.g. both old & new exist).
        if os.path.exists(dest):
            # Prefer the explicitly-compliant file; remove the stray old file.
            try:
                os.remove(src_abs)
            except OSError:
                pass
        else:
            try:
                shutil.move(src_abs, dest)
            except OSError as e:
                logger.warning(
                    "pack_migration: failed to rename %s -> %s: %s",
                    src_abs, dest, e,
                )
                continue

        # Update stored path to the new file, rooted at target_mesh/ (canonical
        # form, independent of where temp_dir lives on disk).
        info["path"] = _stored_path_from_temp_abs(temp_dir, dest)
        migrated += 1

    if migrated:
        try:
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error("pack_migration: failed to write %s: %s", cfg_path, e)

    return migrated


# --------------------------------------------------------------------------- #
# core migration step B: exported_outfit dirs + outfit_index.json
# --------------------------------------------------------------------------- #
def migrate_exported_outfit(
    temp_dir: str, cid: str, root_dir: str, rename_map: Dict[str, str]
) -> int:
    """
    Rename ``exported_outfit/{cid}/custom/{old_base}`` directories to
    ``custom/{local_id}`` and rewrite ``outfit_index.json`` so its
    ``target_body_folders`` and ``outfits`` entries point at the new paths.

    ``rename_map`` is the ``old_file_basename -> local_id`` map produced by
    :func:`build_custom_slider_rename_map`.

    Returns the number of slider directories renamed.
    """
    if not rename_map:
        return 0

    exported_root = os.path.join(temp_dir, "exported_outfit", cid)
    if not os.path.isdir(exported_root):
        return 0

    # ---- 1) Rename custom/* slider folders --------------------------------
    custom_dir = os.path.join(exported_root, "custom")
    renamed_dirs: Dict[str, str] = {}  # old_segment -> new_segment  (e.g. "custom/foo" -> "custom/bar")
    renamed_count = 0

    if os.path.isdir(custom_dir):
        for entry in os.listdir(custom_dir):
            entry_path = os.path.join(custom_dir, entry)
            if not os.path.isdir(entry_path):
                continue
            new_local = rename_map.get(entry)
            if not new_local or new_local == entry:
                continue
            dest_path = os.path.join(custom_dir, new_local)
            if os.path.exists(dest_path):
                # Merge into existing compliant folder then drop the old one.
                try:
                    shutil.rmtree(entry_path)
                except OSError:
                    pass
            else:
                try:
                    shutil.move(entry_path, dest_path)
                except OSError as e:
                    logger.warning(
                        "pack_migration: failed to rename exported dir %s -> %s: %s",
                        entry_path, dest_path, e,
                    )
                    continue
            old_seg = f"custom/{entry}"
            new_seg = f"custom/{new_local}"
            renamed_dirs[old_seg] = new_seg
            renamed_count += 1

    if not renamed_dirs:
        # Nothing renamed on disk; index may still contain stale references if
        # the folders were already compliant but index paths were not - handled below.
        pass

    # ---- 2) Rewrite outfit_index.json -------------------------------------
    index_path = os.path.join(exported_root, INDEX_FILENAME)
    if not os.path.isfile(index_path):
        return renamed_count

    try:
        with open(index_path, "r", encoding="utf-8-sig") as f:
            index_data = json.load(f)
    except Exception as e:
        logger.warning("pack_migration: failed to read %s: %s", index_path, e)
        return renamed_count

    if not isinstance(index_data, dict):
        return renamed_count

    changed = False

    # Build a broader replacement set: also consider direct old_base -> new_local
    # (in case the index uses bare file names rather than custom/ segments).
    full_replace: Dict[str, str] = {}
    for old_base, new_local in rename_map.items():
        for old_seg, new_seg in (
            (f"custom/{old_base}", f"custom/{new_local}"),
            (f"{old_base}.obj", f"{new_local}.obj"),
            (f"{old_base}.pac", f"{new_local}.pac"),
            (old_base, new_local),
        ):
            if old_seg != new_seg:
                full_replace.setdefault(old_seg, new_seg)

    def _rewrite_path(p: str) -> str:
        """Replace any known old segment inside a stored relative path."""
        if not isinstance(p, str) or not p:
            return p
        out = p
        for old_seg, new_seg in full_replace.items():
            if old_seg in out:
                out = out.replace(old_seg, new_seg)
        return out

    # target_body_folders: {target_body_file_rel -> output_folder_rel}
    tb = index_data.get("target_body_folders")
    if isinstance(tb, dict) and tb:
        new_tb: Dict[str, str] = {}
        for k, v in tb.items():
            nk = _rewrite_path(k)
            nv = _rewrite_path(v) if isinstance(v, str) else v
            if nk != k or nv != v:
                changed = True
            new_tb[nk] = nv
        index_data["target_body_folders"] = new_tb

    # outfits: {original_outfit_rel -> [exported_rel, ...]}
    outfits = index_data.get("outfits")
    if isinstance(outfits, dict) and outfits:
        new_outfits: Dict[str, list] = {}
        for k, v in outfits.items():
            nk = _rewrite_path(k)
            if isinstance(v, list):
                nv = [_rewrite_path(x) if isinstance(x, str) else x for x in v]
            else:
                nv = v
            if nk != k or nv != v:
                changed = True
            new_outfits[nk] = nv
        index_data["outfits"] = new_outfits

    if changed:
        try:
            with open(index_path, "w", encoding="utf-8-sig") as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("pack_migration: failed to write %s: %s", index_path, e)

    return renamed_count


# --------------------------------------------------------------------------- #
# public entry point
# --------------------------------------------------------------------------- #
def migrate_legacy_custom_sliders(
    temp_dir: str, cid: str, root_dir: str
) -> Tuple[int, int]:
    """
    Run the full legacy custom-slider migration for one character inside an
    extracted pack (``temp_dir``).

    Performs:
      1. Rename custom target-mesh files to ``{local_id}{ext}`` and update
         ``char_config/{cid}.json`` paths.
      2. (When ``exported_outfit/{cid}`` exists) rename ``custom/{old_base}``
         folders and rewrite ``outfit_index.json``.

    Returns ``(migrated_files, migrated_dirs)``.
    """
    rename_map = build_custom_slider_rename_map(temp_dir, cid)
    if not rename_map:
        # Nothing to rename, but still normalise config paths (no-op typically).
        migrated_files = migrate_target_mesh_and_config(temp_dir, cid, root_dir)
        return migrated_files, 0

    migrated_files = migrate_target_mesh_and_config(temp_dir, cid, root_dir)
    # Rebuild the map after config rewrite so exported-outfit migration uses the
    # final local ids (the map is keyed on local_id which is unchanged, but keep
    # it consistent against any path normalisation that occurred).
    rename_map = build_custom_slider_rename_map(temp_dir, cid)
    migrated_dirs = migrate_exported_outfit(temp_dir, cid, root_dir, rename_map)
    return migrated_files, migrated_dirs


def needs_app_migration(pack_version: str) -> bool:
    """True when a Body Slider Pro pack version predates the 1.3.1 rename."""
    return _version_lt(pack_version, "1.3.1")


def needs_outfitter_migration(pack_version: str) -> bool:
    """True when an Outfitter pack version predates the 1.2.4 rename."""
    return _version_lt(pack_version, "1.2.4")


def _version_lt(version_str: str, threshold: str) -> bool:
    """Return True when version_str < threshold (semver tuple compare)."""
    def _parse(v: str):
        parts = []
        for p in str(v).split("."):
            try:
                parts.append(int(p))
            except ValueError:
                parts.append(0)
        return tuple(parts)
    try:
        return _parse(version_str) < _parse(threshold)
    except Exception:
        return False
