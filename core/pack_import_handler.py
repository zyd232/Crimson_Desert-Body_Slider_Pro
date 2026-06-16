# -*- coding: utf-8 -*-
"""
Pack Import Handler for Body Slider Pro.

Handles the business logic for importing character packs with outfit support.
This module provides the new import flow that:
1. Checks if existing char has outfit data
2. Compares mesh files when both have outfit data
3. Allows overwrite or merge choices for outfit data
4. Merges outfit files with conflict resolution
"""

import os
import json
import hashlib
import shutil
from typing import Dict, List, Optional, Set, Tuple, Any


# ==========================================
# File Comparison Utilities
# ==========================================

def _file_hash(filepath: str) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except (OSError, IOError):
        return ""


def _get_files_in_dir(dirpath: str) -> Dict[str, str]:
    """
    Get all files in a directory with their relative paths and hashes.
    Returns {rel_path: hash} mapping.
    """
    result = {}
    if not os.path.isdir(dirpath):
        return result
    for dirpath_walk, _, filenames in os.walk(dirpath):
        for fn in filenames:
            full_path = os.path.join(dirpath_walk, fn)
            rel_path = os.path.relpath(full_path, dirpath)
            result[rel_path] = _file_hash(full_path)
    return result


def compare_mesh_directories(
    pack_mesh_dir: str,
    existing_mesh_dir: str,
    dir_name: str  # "original_mesh" or "target_mesh"
) -> Tuple[bool, List[str]]:
    """
    Compare mesh directories between pack and existing data.
    
    Returns:
        (identical, diff_details) - True if all files match, list of differences
    """
    pack_files = _get_files_in_dir(pack_mesh_dir)
    existing_files = _get_files_in_dir(existing_mesh_dir)
    
    all_paths = set(pack_files.keys()) | set(existing_files.keys())
    differences = []
    
    for rel_path in sorted(all_paths):
        pack_hash = pack_files.get(rel_path, "")
        existing_hash = existing_files.get(rel_path, "")
        
        if rel_path not in pack_files:
            differences.append(f"[{dir_name}] Missing in pack: {rel_path}")
        elif rel_path not in existing_files:
            differences.append(f"[{dir_name}] New in pack: {rel_path}")
        elif pack_hash != existing_hash:
            differences.append(f"[{dir_name}] Content differs: {rel_path}")
    
    identical = len(differences) == 0
    return identical, differences


def compare_mesh_data(temp_dir: str, root_dir: str, char_id: str) -> Tuple[bool, str]:
    """
    Compare all mesh directories (original_mesh and target_mesh) for a character.
    
    Returns:
        (identical, diff_summary) - True if all match, summary string of differences
    """
    pack_original = os.path.join(temp_dir, "original_mesh", char_id)
    existing_original = os.path.join(root_dir, "original_mesh", char_id)
    pack_target = os.path.join(temp_dir, "target_mesh", char_id)
    existing_target = os.path.join(root_dir, "target_mesh", char_id)
    
    all_differences = []
    
    # Compare original_mesh
    if os.path.isdir(pack_original) or os.path.isdir(existing_original):
        identical, diffs = compare_mesh_directories(
            pack_original, existing_original, "original_mesh"
        )
        if not identical:
            all_differences.extend(diffs)
    
    # Compare target_mesh
    if os.path.isdir(pack_target) or os.path.isdir(existing_target):
        identical, diffs = compare_mesh_directories(
            pack_target, existing_target, "target_mesh"
        )
        if not identical:
            all_differences.extend(diffs)
    
    return len(all_differences) == 0, "\n".join(all_differences) if all_differences else ""


# ==========================================
# Outfit Data Utilities
# ==========================================

def has_outfit_data(root_dir: str, char_id: str) -> bool:
    """Check if a character has outfit data in the project (checks both directories)."""
    for dir_name in ("original_outfit", "exported_outfit"):
        outfit_dir = os.path.join(root_dir, dir_name, char_id)
        if not os.path.isdir(outfit_dir):
            continue
        try:
            for _, _, files in os.walk(outfit_dir):
                if files:
                    return True
        except OSError:
            pass
    return False


def has_outfit_data_in_zip(zip_path: str, char_id: str) -> bool:
    """Check if a character has outfit data in the ZIP pack."""
    import zipfile
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            all_filenames = {info.filename for info in zf.infolist()}
            has_original = any(
                fn.startswith(f"original_outfit/{char_id}/") for fn in all_filenames
            )
            has_exported = any(
                fn.startswith(f"exported_outfit/{char_id}/") for fn in all_filenames
            )
            return has_original or has_exported
    except Exception:
        return False


def find_outfit_duplicates(
    temp_dir: str,
    root_dir: str,
    char_id: str
) -> Tuple[List[Dict], List[Dict]]:
    """
    Find duplicate outfit files between pack and existing data.
    Skips outfit_index.json and outfit_index.json.bak.
    
    Returns:
        (duplicate_groups, unique_pack_files) where:
        - duplicate_groups: list of {rel_path, options: [{label, source, path, dest_dir}], 
                               source_type: "original" | "exported",
                               original_key: str (for exported files, the original_outfit rel_path 
                               this file is associated with)}
        - unique_pack_files: list of {rel_path, source_path, dest_dir}
    
    KEY CHANGE: Only original_outfit duplicates are shown to the user.
    Exported_outfit duplicates are automatically associated with the corresponding
    original_outfit file, so the user's choice for original_outfit determines
    what happens to the exported files.
    """
    SKIP_FILES = {"outfit_index.json", "outfit_index.json.bak"}
    
    # Collect pack outfit files with their source directory type
    pack_original = os.path.join(temp_dir, "original_outfit", char_id)
    pack_exported = os.path.join(temp_dir, "exported_outfit", char_id)
    
    # Collect existing outfit files
    existing_original = os.path.join(root_dir, "original_outfit", char_id)
    existing_exported = os.path.join(root_dir, "exported_outfit", char_id)
    
    # Build file maps: {rel_path: {path, dest_dir}}
    # dest_dir is "original_outfit" or "exported_outfit" to know where to copy
    pack_original_files = {}
    if os.path.isdir(pack_original):
        for dirpath, _, filenames in os.walk(pack_original):
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, pack_original)
                pack_original_files[rel] = {"path": full, "dest_dir": "original_outfit"}
    
    pack_exported_files = {}
    if os.path.isdir(pack_exported):
        for dirpath, _, filenames in os.walk(pack_exported):
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, pack_exported)
                pack_exported_files[rel] = {"path": full, "dest_dir": "exported_outfit"}
    
    existing_original_files = {}
    if os.path.isdir(existing_original):
        for dirpath, _, filenames in os.walk(existing_original):
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, existing_original)
                existing_original_files[rel] = {"path": full, "dest_dir": "original_outfit"}
    
    existing_exported_files = {}
    if os.path.isdir(existing_exported):
        for dirpath, _, filenames in os.walk(existing_exported):
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, existing_exported)
                existing_exported_files[rel] = {"path": full, "dest_dir": "exported_outfit"}
    
    # ---- Step 1: Find original_outfit duplicates (shown to user) ----
    original_duplicate_rels = set(pack_original_files.keys()) & set(existing_original_files.keys())
    # Remove index files
    original_duplicate_rels -= {r for r in original_duplicate_rels if os.path.basename(r) in SKIP_FILES}
    
    duplicate_groups = []
    for rel_path in sorted(original_duplicate_rels):
        pack_info = pack_original_files[rel_path]
        existing_info = existing_original_files[rel_path]
        duplicate_groups.append({
            "rel_path": rel_path,
            "dest_dir": "original_outfit",
            "source_type": "original",
            "original_key": rel_path,
            "options": [
                {
                    "label": "Keep existing",
                    "source": "existing",
                    "path": existing_info["path"],
                },
                {
                    "label": "Use imported",
                    "source": "pack",
                    "path": pack_info["path"],
                },
            ],
        })
    
    # ---- Step 2: Find exported_outfit duplicates (associated with original_outfit) ----
    exported_duplicate_rels = set(pack_exported_files.keys()) & set(existing_exported_files.keys())
    exported_duplicate_rels -= {r for r in exported_duplicate_rels if os.path.basename(r) in SKIP_FILES}
    
    # Build a mapping: for each exported duplicate, try to find the corresponding
    # original_outfit duplicate by extracting the "mod_dir + filename" portion.
    # 
    # exported_outfit/{char_id}/{slider_segment}/{mod_dir}/{file}
    # original_outfit/{char_id}/{mod_dir}/{file}
    #
    # The {slider_segment} can be multi-level for custom sliders, e.g.
    #   "custom/cd_phw_00_nude_00_0001_damian"
    # So we need to find which prefix (slider_segment) to strip.
    # Strategy: for each exported rel_path, try to match the suffix against
    # known original_outfit duplicate rel_paths.
    
    for rel_path in sorted(exported_duplicate_rels):
        pack_info = pack_exported_files[rel_path]
        existing_info = existing_exported_files[rel_path]
        
        # Try to find the corresponding original_outfit rel_path by checking
        # if any part of the exported path (after stripping the slider_segment prefix)
        # matches an original duplicate.
        # 
        # Split by "/" and try progressively longer suffixes:
        # e.g. "custom/cd_phw_00_nude_00_0001_damian/character/model/.../file.pac"
        #   try "character/model/.../file.pac" (strip 2 segments)
        #   try "cd_phw_00_nude_00_0001_damian/character/model/.../file.pac" (strip 1 segment)
        #   etc.
        # 
        # Also try: "breast_size_type_01/character/model/.../file.pac"
        #   try "character/model/.../file.pac" (strip 1 segment)
        
        parts = rel_path.replace("\\", "/").split("/")
        original_key = None
        
        # Try stripping from 1 to len(parts)-1 segments from the front
        for strip_count in range(1, len(parts)):
            candidate = "/".join(parts[strip_count:])
            if candidate in original_duplicate_rels:
                original_key = candidate
                break
        
        # If no match found among original duplicates, try matching against ALL
        # original pack files (not just duplicates) - the exported file may correspond
        # to an original file that's not a duplicate itself.
        if original_key is None:
            for strip_count in range(1, len(parts)):
                candidate = "/".join(parts[strip_count:])
                if candidate in pack_original_files:
                    original_key = candidate
                    break
        
        # If still no match, fall back to using the filename only
        if original_key is None:
            filename = os.path.basename(rel_path)
            for orig_rel in original_duplicate_rels:
                if os.path.basename(orig_rel) == filename:
                    original_key = orig_rel
                    break
        
        # If absolutely no match, use the exported rel_path itself as the key
        if original_key is None:
            original_key = "__exported_orphan__" + rel_path
        
        duplicate_groups.append({
            "rel_path": rel_path,
            "dest_dir": "exported_outfit",
            "source_type": "exported",
            "original_key": original_key,
            "options": [
                {
                    "label": "Keep existing",
                    "source": "existing",
                    "path": existing_info["path"],
                },
                {
                    "label": "Use imported",
                    "source": "pack",
                    "path": pack_info["path"],
                },
            ],
        })
    
    # ---- Step 3: Collect unique pack files ----
    unique_pack_files = []
    all_pack_files = {**pack_original_files, **pack_exported_files}
    all_existing_files = {**existing_original_files, **existing_exported_files}
    
    for rel_path, pack_info in sorted(all_pack_files.items()):
        if os.path.basename(rel_path) in SKIP_FILES:
            continue
        if rel_path not in all_existing_files:
            unique_pack_files.append({
                "rel_path": rel_path,
                "source_path": pack_info["path"],
                "dest_dir": pack_info["dest_dir"],
            })
    
    return duplicate_groups, unique_pack_files


def copy_outfit_files(
    unique_files: List[Dict],
    root_dir: str,
    char_id: str,
) -> int:
    """
    Copy unique outfit files from pack to project.
    Returns number of files copied.
    """
    count = 0
    skipped = 0
    for file_info in unique_files:
        rel_path = file_info["rel_path"]
        source_path = file_info["source_path"]
        dest_dir_name = file_info.get("dest_dir", "exported_outfit")
        
        # Safety check: verify source file exists
        if not os.path.exists(source_path):
            print(f"[Outfit Copy] Warning: source file not found, skipping: {source_path}")
            skipped += 1
            continue
        
        dest_dir = os.path.join(root_dir, dest_dir_name, char_id)
        dest_path = os.path.join(dest_dir, rel_path)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copy2(source_path, dest_path)
        count += 1
    
    if skipped > 0:
        print(f"[Outfit Copy] Skipped {skipped} file(s) due to missing source files.")
    return count


def apply_outfit_merge_choices(
    duplicate_groups: List[Dict],
    choices: Dict[str, str],
    root_dir: str,
    char_id: str,
) -> int:
    """
    Apply user's merge choices for duplicate outfit files.
    For each file, copy the chosen version to the destination.
    
    Returns number of files processed.
    """
    count = 0
    skipped = 0
    for group in duplicate_groups:
        rel_path = group["rel_path"]
        chosen_source = choices.get(rel_path, "existing")
        dest_dir_name = group.get("dest_dir", "exported_outfit")
        
        # Find the chosen option
        chosen_option = None
        for opt in group["options"]:
            if opt["source"] == chosen_source:
                chosen_option = opt
                break
        
        if chosen_option is None:
            continue
        
        src_path = chosen_option["path"]
        
        # Safety check: verify source file exists (check twice to be safe)
        if not os.path.exists(src_path):
            print(f"[Outfit Merge] Warning: source file not found (before copy), skipping: {src_path}")
            skipped += 1
            continue
        
        dest_dir = os.path.join(root_dir, dest_dir_name, char_id)
        dest_path = os.path.join(dest_dir, rel_path)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        # If source and destination are the same file (user chose "Keep existing"),
        # skip this file since no action is needed.
        try:
            same_file = os.path.samefile(src_path, dest_path)
        except OSError:
            same_file = os.path.abspath(src_path) == os.path.abspath(dest_path)
        
        if same_file:
            count += 1
            continue
        
        # Delete existing file if it exists, then copy chosen version
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except OSError:
                pass
        
        # Final check right before copy
        if not os.path.exists(src_path):
            print(f"[Outfit Merge] Warning: source file disappeared before copy, skipping: {src_path}")
            skipped += 1
            continue
        
        try:
            shutil.copy2(src_path, dest_path)
            count += 1
        except FileNotFoundError:
            print(f"[Outfit Merge] Error: source file not found during copy: {src_path}")
            skipped += 1
            continue
    
    if skipped > 0:
        print(f"[Outfit Merge] Skipped {skipped} file(s) due to missing source files.")
    return count


def overwrite_outfit_data(
    temp_dir: str,
    root_dir: str,
    char_id: str,
) -> bool:
    """
    Overwrite existing outfit data with pack's outfit data.
    Deletes existing directories first, then copies from pack.
    """
    # Delete existing
    for dir_name in ("original_outfit", "exported_outfit"):
        existing_dir = os.path.join(root_dir, dir_name, char_id)
        if os.path.exists(existing_dir):
            try:
                shutil.rmtree(existing_dir)
            except Exception:
                pass
    
    # Copy from pack
    for dir_name in ("original_outfit", "exported_outfit"):
        src_dir = os.path.join(temp_dir, dir_name, char_id)
        if not os.path.isdir(src_dir):
            continue
        dst_dir = os.path.join(root_dir, dir_name, char_id)
        os.makedirs(dst_dir, exist_ok=True)
        for item in os.listdir(src_dir):
            sp = os.path.join(src_dir, item)
            dp = os.path.join(dst_dir, item)
            if os.path.isdir(sp):
                if os.path.exists(dp):
                    shutil.rmtree(dp)
                shutil.copytree(sp, dp)
            else:
                shutil.copy2(sp, dp)
    
    return True


# ==========================================
# Import Flow Orchestrator
# ==========================================

class PackImportStrategy:
    """
    Determines the import strategy for a character based on:
    - Whether the character already exists
    - Whether the pack has outfit data
    - Whether the existing character has outfit data
    - Whether mesh files match
    """
    
    # Strategy constants
    STRATEGY_NEW = "new"                    # New character, simple import
    STRATEGY_OVERWRITE = "overwrite"        # Overwrite all data
    STRATEGY_MERGE_SLIDERS = "merge_sliders"  # Merge sliders (no outfit conflict)
    STRATEGY_MESH_MISMATCH = "mesh_mismatch"  # Meshes differ, must delete and import
    STRATEGY_OUTFIT_CHOICE = "outfit_choice"  # Both have outfits, user chooses
    STRATEGY_RENAME = "rename"              # Incompatible mesh, rename character
    
    @staticmethod
    def determine(char_id: str, 
                  exists: bool,
                  pack_has_outfit: bool,
                  existing_has_outfit: bool,
                  pack_type: str,
                  pac_matches: bool = True) -> str:
        """
        Determine the import strategy for a character.
        
        Args:
            char_id: Character ID
            exists: Whether character already exists in project
            pack_has_outfit: Whether pack has outfit data for this char
            existing_has_outfit: Whether existing char has outfit data
            pack_type: "app" or "outfitter"
            pac_matches: Whether PAC files match (for merge scenario)
        
        Returns:
            Strategy constant
        """
        if not exists:
            return PackImportStrategy.STRATEGY_NEW
        
        # Character exists
        if not pack_has_outfit and not existing_has_outfit:
            # Neither has outfit - original merge/overwrite flow
            if pack_type == "outfitter":
                return PackImportStrategy.STRATEGY_OVERWRITE
            # For app packs, user gets to choose overwrite vs merge
            return PackImportStrategy.STRATEGY_MERGE_SLIDERS
        
        if pack_has_outfit and not existing_has_outfit:
            # Pack has outfit, existing doesn't - just import with outfit
            return PackImportStrategy.STRATEGY_OVERWRITE
        
        if not pack_has_outfit and existing_has_outfit:
            # Existing has outfit, pack doesn't - merge sliders only
            return PackImportStrategy.STRATEGY_MERGE_SLIDERS
        
        # Both have outfit data
        if not pac_matches:
            return PackImportStrategy.STRATEGY_MESH_MISMATCH
        
        return PackImportStrategy.STRATEGY_OUTFIT_CHOICE