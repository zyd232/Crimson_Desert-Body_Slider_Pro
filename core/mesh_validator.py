"""
Mesh structure validation utilities.
Pure-functional logic for comparing original and target meshes.
No UI dependencies.
"""

import os
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from .pac_builder import parse_pac, ParsedMesh


def get_pac_submesh_signature(pac_mesh: ParsedMesh) -> List[Tuple[str, int]]:
    """
    Extract a signature from a ParsedMesh: list of (submesh_name, vertex_count).
    Used to compare mesh structures.
    """
    if not pac_mesh or not pac_mesh.submeshes:
        return []
    return [(sm.name, len(sm.vertices)) for sm in pac_mesh.submeshes]


def get_mesh_signature_from_arrays(
    original_points: Dict[str, np.ndarray],
    original_faces: Dict[str, np.ndarray],
) -> List[Tuple[str, int]]:
    """
    Build a mesh signature from existing geometry arrays:
    original_points[name] = vertices, original_faces[name] = faces.
    Returns list of (name, vertex_count).
    """
    if not original_points or not original_faces:
        return []
    sig: List[Tuple[str, int]] = []
    for name, verts in original_points.items():
        fcs = original_faces.get(name)
        if verts is None or fcs is None or len(verts) == 0 or len(fcs) == 0:
            continue
        sig.append((name, len(verts)))
    return sig


def _parse_obj_signature(target_path: str) -> Optional[List[Tuple[str, int]]]:
    """
    Parse an OBJ file by 'o ' lines to get per-object (name, vertex_count).
    Avoids trimesh merging geometries with the same material.
    Returns None on failure.
    """
    try:
        with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return None

    obj_items: List[Tuple[str, int]] = []
    current_name: Optional[str] = None
    current_vcount: int = 0

    for line in lines:
        s = line.strip()
        if s.startswith("o "):
            if current_name is not None:
                obj_items.append((current_name, current_vcount))
            current_name = s[2:].strip()
            current_vcount = 0
        elif s.startswith("v ") and not s.startswith("vn") and not s.startswith("vt"):
            current_vcount += 1

    if current_name is not None:
        obj_items.append((current_name, current_vcount))

    # Filter out empty or unnamed objects
    return [(n, vc) for n, vc in obj_items if n and vc > 0]


def validate_target_mesh_against_original(
    target_path: str,
    original_sig: List[Tuple[str, int]],
    translation_fn: Callable[[str, str], str],
) -> Optional[str]:
    """
    Validate that the target mesh (PAC or OBJ) has compatible structure
    with the original mesh described by original_sig.

    Args:
        target_path: path to target mesh (PAC or OBJ).
        original_sig: list of (name, vertex_count) for original mesh.
        translation_fn: function(key, fallback) -> str to get localized text.

    Returns:
        - None if valid or if original_sig is empty (skip validation).
        - Error message string if invalid.
    """
    if not original_sig:
        return None  # No original reference; skip validation

    ext = target_path.lower().split(".")[-1]

    if ext == "pac":
        return _validate_pac_target(target_path, original_sig, translation_fn)
    else:
        # OBJ or similar
        return _validate_obj_target(target_path, original_sig, translation_fn)


def _validate_pac_target(
    target_path: str,
    original_sig: List[Tuple[str, int]],
    translation_fn: Callable[[str, str], str],
) -> Optional[str]:
    try:
        with open(target_path, "rb") as f:
            data = f.read()
        target_pac = parse_pac(data, target_path)
    except Exception as e:
        return translation_fn(
            "mesh_validation_pac_parse_error",
            "Failed to parse target PAC file: {error}".format(error=str(e)),
        )

    target_sig = get_pac_submesh_signature(target_pac)

    # Check count
    if len(original_sig) != len(target_sig):
        return translation_fn(
            "mesh_validation_submesh_count_mismatch",
            "Target mesh has {target_count} submeshes, but original has {original_count}. "
            "Please use a target mesh with the same structure.",
        ).format(
            target_count=len(target_sig),
            original_count=len(original_sig),
        )

    # Check names and vertex counts
    mismatches = []
    for (orig_name, orig_vc), (tgt_name, tgt_vc) in zip(original_sig, target_sig):
        if orig_name != tgt_name:
            mismatches.append(
                translation_fn(
                    "mesh_validation_name_mismatch_detail",
                    "Submesh name mismatch: expected '{expected}', got '{actual}'.",
                ).format(expected=orig_name, actual=tgt_name)
            )
        elif orig_vc != tgt_vc:
            mismatches.append(
                translation_fn(
                    "mesh_validation_vertex_count_mismatch_detail",
                    "Submesh '{name}' vertex count mismatch: "
                    "expected {expected}, got {actual}.",
                ).format(name=orig_name, expected=orig_vc, actual=tgt_vc)
            )

    if mismatches:
        header = translation_fn(
            "mesh_validation_target_invalid",
            "The selected target mesh is incompatible with the original mesh:\n\n",
        )
        return header + "\n".join(mismatches)

    return None


def _validate_obj_target(
    target_path: str,
    original_sig: List[Tuple[str, int]],
    translation_fn: Callable[[str, str], str],
) -> Optional[str]:
    obj_items = _parse_obj_signature(target_path)
    if obj_items is None:
        return translation_fn(
            "mesh_validation_obj_load_error",
            "Failed to load target OBJ file.",
        )

    # Check count
    if len(original_sig) != len(obj_items):
        return translation_fn(
            "mesh_validation_obj_count_mismatch",
            "Target OBJ has {target_count} objects, but original has {original_count}. "
            "Please use a target mesh with the same structure.",
        ).format(
            target_count=len(obj_items),
            original_count=len(original_sig),
        )

    # Try to match: first by name, then by vertex count
    used_obj = set()
    mismatches = []

    for orig_name, orig_vc in original_sig:
        matched = None

        # 1) exact name match
        for i, (oname, ovc) in enumerate(obj_items):
            if i in used_obj:
                continue
            if oname == orig_name:
                matched = (i, oname, ovc)
                break

        # 2) vertex count match if no name match
        if matched is None:
            for i, (oname, ovc) in enumerate(obj_items):
                if i in used_obj:
                    continue
                if ovc == orig_vc:
                    matched = (i, oname, ovc)
                    break

        # 3) fallback: any unused
        if matched is None:
            for i, (oname, ovc) in enumerate(obj_items):
                if i in used_obj:
                    continue
                matched = (i, oname, ovc)
                break

        if matched is None:
            mismatches.append(
                translation_fn(
                    "mesh_validation_no_match",
                    "No matching object found for submesh '{name}'.",
                ).format(name=orig_name)
            )
            continue

        i, oname, ovc = matched
        used_obj.add(i)

        if oname != orig_name and ovc == orig_vc:
            # Different name but same vertex count: acceptable with note
            pass
        elif oname != orig_name or ovc != orig_vc:
            mismatches.append(
                translation_fn(
                    "mesh_validation_obj_mismatch_detail",
                    "Original submesh '{orig}' ({orig_vc} verts) "
                    "does not match OBJ object '{obj}' ({obj_vc} verts).",
                ).format(
                    orig=orig_name, orig_vc=orig_vc,
                    obj=oname, obj_vc=ovc
                )
            )

    if mismatches:
        header = translation_fn(
            "mesh_validation_target_invalid",
            "The selected target mesh is incompatible with the original mesh:\n\n",
        )
        return header + "\n".join(mismatches)

    return None


def validate_pac_compatibility(
    new_pac_path: str,
    old_pac_path: str,
    translation_fn: Callable[[str, str], str],
) -> Optional[str]:
    """
    Compare two PAC files for structural compatibility.
    Used when user changes PAC file in Edit Character.

    Returns:
        - None if compatible
        - Error message string if not
    """
    try:
        with open(old_pac_path, "rb") as f:
            old_data = f.read()
        old_mesh = parse_pac(old_data, old_pac_path)
    except Exception as e:
        return translation_fn(
            "mesh_validation_old_pac_error",
            "Failed to parse original PAC file: {error}".format(error=str(e)),
        )

    try:
        with open(new_pac_path, "rb") as f:
            new_data = f.read()
        new_mesh = parse_pac(new_data, new_pac_path)
    except Exception as e:
        return translation_fn(
            "mesh_validation_new_pac_error",
            "Failed to parse new PAC file: {error}".format(error=str(e)),
        )

    old_sig = get_pac_submesh_signature(old_mesh)
    new_sig = get_pac_submesh_signature(new_mesh)

    # Check count
    if len(old_sig) != len(new_sig):
        return translation_fn(
            "mesh_validation_pac_submesh_count_mismatch",
            "New PAC has {new_count} submeshes, but original PAC has {old_count}. "
            "The mesh structures are incompatible and cannot be replaced.",
        ).format(
            new_count=len(new_sig),
            old_count=len(old_sig),
        )

    # Check names and vertex counts
    mismatches = []
    for (old_name, old_vc), (new_name, new_vc) in zip(old_sig, new_sig):
        if old_name != new_name:
            mismatches.append(
                translation_fn(
                    "mesh_validation_name_mismatch_detail",
                    "Submesh name mismatch: expected '{expected}', got '{actual}'.",
                ).format(expected=old_name, actual=new_name)
            )
        elif old_vc != new_vc:
            mismatches.append(
                translation_fn(
                    "mesh_validation_vertex_count_mismatch_detail",
                    "Submesh '{name}' vertex count mismatch: "
                    "expected {expected}, got {actual}.",
                ).format(name=old_name, expected=old_vc, actual=new_vc)
            )

    if mismatches:
        header = translation_fn(
            "mesh_validation_pac_incompatible",
            "The new PAC file is incompatible with the original PAC file:\n\n",
        )
        return header + "\n".join(mismatches)

    return None  # Compatible