# -*- coding: utf-8 -*-
"""
Mesh processing core for Body Slider Pro.
Pure functional mathematical operations for 3D meshes using NumPy.
No UI or threading logic should be present here.
"""

import os
import numpy as np
import trimesh
from typing import Dict, List, Optional, Set, Tuple, Any

# Lazy import to avoid circular imports
def _get_parse_pac():
    from core.pac_builder import parse_pac
    return parse_pac

def match_submesh_name(
    original_points: Dict[str, np.ndarray],
    target_sm: Any,  # SubMesh
    used: Set[str]
) -> Optional[str]:
    """Match a target submesh to an original submesh by name or vertex count."""
    for name in original_points:
        if name == target_sm.name and name not in used:
            return name
            
    c = len(target_sm.vertices)
    for name, orig_verts in original_points.items():
        if len(orig_verts) == c and name not in used:
            return name
    return None

def find_matching_geom(
    count: int,
    by_count: Dict[int, List],
    used: Set[str],
    pac_name: str
) -> Optional[Tuple[str, Any]]:
    """Find a matching geometry in the loaded obj file."""
    if count not in by_count:
        return None
        
    candidates = by_count[count]
    for c_name, c_geom in candidates:
        if c_name == pac_name and c_name not in used:
            return c_name, c_geom
            
    for c_name, c_geom in candidates:
        if c_name not in used:
            return c_name, c_geom
            
    return None

def compute_morph_delta(
    morph_data: Dict[str, Dict[str, np.ndarray]],
    slider_id: str,
    target_path: str,
    original_points: Dict[str, np.ndarray]
) -> None:
    """
    Compute morph delta between target mesh (OBJ or PAC) and original points.
    Supports:
      - OBJ via trimesh
      - PAC via internal parser
    """
    if not target_path or not os.path.exists(target_path):
        return

    ext = target_path.lower().split(".")[-1]

    if ext == "pac":
        _compute_morph_delta_pac(morph_data, slider_id, target_path, original_points)
    else:
        _compute_morph_delta_obj(morph_data, slider_id, target_path, original_points)


def _compute_morph_delta_pac(
    morph_data: Dict[str, Dict[str, np.ndarray]],
    slider_id: str,
    target_path: str,
    original_points: Dict[str, np.ndarray]
) -> None:
    try:
        parse_pac = _get_parse_pac()
    except Exception as e:
        print(f"Error importing parse_pac: {e}")
        return

    try:
        with open(target_path, "rb") as f:
            data = f.read()
        pac_mesh = parse_pac(data, target_path)
    except Exception as e:
        print(f"Error loading PAC {target_path}: {e}")
        return

    deltas = {}
    used: Set[str] = set()

    # Correct logic: iterate over target PAC submeshes, then match against original_points
    for t_sm in pac_mesh.submeshes:
        t_verts = np.array(t_sm.vertices, dtype=np.float32)
        if len(t_verts) == 0:
            continue

        matched_name = match_submesh_name(original_points, t_sm, used)
        if matched_name is None or matched_name not in original_points:
            continue

        orig_verts = original_points[matched_name]
        if len(t_verts) == len(orig_verts):
            used.add(matched_name)
            deltas[matched_name] = t_verts - orig_verts

    if deltas:
        morph_data[slider_id] = deltas


def _parse_obj_by_objects(target_path: str) -> Dict[str, np.ndarray]:
    """
    Parse OBJ by 'o ' headers into per-object vertex arrays.
    Correctly groups vertices per object via face references.
    """
    try:
        with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading OBJ {target_path}: {e}")
        return {}

    all_vertices: List[float] = []
    # For each object name, track set of vertex indices used by its faces
    obj_indices: Dict[str, set] = {}
    current_name: Optional[str] = "Default"

    for line in lines:
        s = line.strip()
        if s.startswith("o "):
            current_name = s[2:].strip()
            if current_name not in obj_indices:
                obj_indices[current_name] = set()
        elif s.startswith("v "):
            parts = s.split()
            if len(parts) >= 4:
                all_vertices.extend([float(parts[1]), float(parts[2]), float(parts[3])])
        elif s.startswith("f "):
            if current_name not in obj_indices:
                obj_indices[current_name] = set()
            indices = obj_indices[current_name]
            parts = s.split()
            for p in parts[1:]:
                idx = int(p.split("/")[0])
                # OBJ is 1-based; handle negative indices
                if idx < 0:
                    idx = len(all_vertices) // 3 + idx
                else:
                    idx = idx - 1
                indices.add(idx)

    # Build per-object vertex arrays
    objects: Dict[str, np.ndarray] = {}
    verts_arr = np.array(all_vertices, dtype=np.float32).reshape(-1, 3)

    for name, idx_set in obj_indices.items():
        if not idx_set:
            continue
        idx_list = sorted(idx_set)
        objects[name] = verts_arr[idx_list]

    return objects


def _compute_morph_delta_obj(
    morph_data: Dict[str, Dict[str, np.ndarray]],
    slider_id: str,
    target_path: str,
    original_points: Dict[str, np.ndarray]
) -> None:
    obj_verts_by_name = _parse_obj_by_objects(target_path)
    if not obj_verts_by_name:
        return

    by_count: Dict[int, List] = {}
    for g_name, verts in obj_verts_by_name.items():
        vc = len(verts)
        by_count.setdefault(vc, []).append((g_name, verts))

    deltas = {}
    used: Set[str] = set()

    for pac_name, orig_verts in original_points.items():
        c = len(orig_verts)
        matched = find_matching_geom(c, by_count, used, pac_name)
        if matched is None:
            continue

        t_name, t_verts = matched
        used.add(t_name)
        if len(t_verts) == c:
            deltas[pac_name] = t_verts - orig_verts

    if deltas:
        morph_data[slider_id] = deltas

def apply_morphs(
    original_points: Dict[str, np.ndarray],
    morph_data: Dict[str, Dict[str, np.ndarray]],
    sliders_info: Dict[str, dict]
) -> Dict[str, np.ndarray]:
    """Apply current slider values to base vertices and return the new morphed points."""
    morphed_points = {}
    for pac_name, base_verts in original_points.items():
        # Avoid in-place += to prevent Numpy dtype crash
        current_verts = base_verts.copy()
        
        for sid, deltas in morph_data.items():
            if pac_name in deltas:
                val = sliders_info.get(sid, {}).get("current_value", 0.0)
                if val != 0.0:
                    # Use + to create new array instead of in-place +=
                    current_verts = current_verts + deltas[pac_name] * (val / 100.0)
                    
        # Convert back to float32 for OpenGL rendering
        morphed_points[pac_name] = current_verts.astype(np.float32)
    return morphed_points

def compute_vertex_normals(verts: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Compute smoothed vertex normals for a mesh."""
    normals = np.zeros_like(verts, dtype=np.float64)
    v0 = verts[faces[:, 0]]
    v1 = verts[faces[:, 1]]
    v2 = verts[faces[:, 2]]

    edge1 = v1 - v0
    edge2 = v2 - v0
    face_normals = np.cross(edge1, edge2)

    np.add.at(normals, faces[:, 0], face_normals)
    np.add.at(normals, faces[:, 1], face_normals)
    np.add.at(normals, faces[:, 2], face_normals)

    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    lengths = np.maximum(lengths, 1e-9)
    normals = normals / lengths
    return normals