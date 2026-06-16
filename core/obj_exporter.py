"""
OBJ export module for Body Slider Pro.

Exports morphed meshes to standard .obj file,
with multi-object separation, texcoords, and normals.

Each original submesh becomes a separate 'o' (object) in the .obj file.
Each object uses its original material name via 'usemtl'.
Format: v, vt, vn, f.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Any

import numpy as np


def _sanitize_obj_name(name: str) -> str:
    """Sanitize a name for use as an OBJ object name."""
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", (name or "").strip()).strip("_")
    return cleaned or "mesh"


def export_mesh_data_to_obj(
    morphed_meshes: Dict[str, Dict[str, np.ndarray]],
    material_map: Dict[str, str],
    uv_map: Dict[str, np.ndarray],
    normal_map: Dict[str, np.ndarray],
    output_path: str,
) -> None:
    """
    Export morphed meshes (given as raw vertices/faces) to a single .obj file.

    Each entry in morphed_meshes is:
        {
          "vertices": (V,3) numpy array of MORPHED positions,
          "faces": (F,3) numpy array of triangle indices (0-based).
        }

    Texture coordinates (uvs) and normals are taken from the original PAC data
    (uv_map and normal_map), as they don't change with morphing.

    Args:
        morphed_meshes: dict of {name: {vertices, faces}}
        material_map: dict of {submesh_name: material_name} from PAC data
        uv_map: dict of {submesh_name: np.ndarray (V,2)} — original texcoords
        normal_map: dict of {submesh_name: np.ndarray (V,3)} — original normals
        output_path: path to write the .obj file
    """
    output = Path(output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    submesh_data: List[dict] = []

    for name, data in morphed_meshes.items():
        vertices = np.asarray(data["vertices"], dtype=np.float64)
        faces = np.asarray(data["faces"], dtype=np.int64)

        if len(vertices) == 0 or len(faces) == 0:
            continue

        safe_name = _sanitize_obj_name(name)
        mat_name = material_map.get(name, safe_name)

        # Get original UVs and normals (they stay the same after morphing)
        uvs = uv_map.get(name, None)
        normals = normal_map.get(name, None)

        # Validate lengths match morphed vertex count
        n_verts = len(vertices)
        if uvs is not None and len(uvs) != n_verts:
            uvs = None
        if normals is not None and len(normals) != n_verts:
            normals = None

        submesh_data.append({
            "name": safe_name,
            "mat_name": mat_name,
            "vertices": vertices,  # (V,3)
            "uvs": uvs,            # (V,2) or None
            "normals": normals,    # (V,3) or None
            "faces": faces,        # (F,3)
        })

    if not submesh_data:
        output.write_text("# No meshes to export\n", encoding="utf-8")
        return

    # Assemble OBJ lines
    # Keep mtllib/usemtl in OBJ (for compatibility), but do NOT create the .mtl file.
    mtl_name = output.with_suffix(".mtl").name
    obj_lines: List[str] = [
        "# Exported by Body Slider Pro",
        f"mtllib {mtl_name}",
    ]

    vertex_offset = 1  # 1-based global offset; v, vt, vn are 1:1

    for sm in submesh_data:
        verts = sm["vertices"]
        uvs = sm["uvs"]
        normals = sm["normals"]
        faces = sm["faces"]
        name = sm["name"]
        mat_name = sm["mat_name"]

        n_verts = len(verts)
        if n_verts == 0 or len(faces) == 0:
            continue

        has_uv = uvs is not None
        has_norm = normals is not None

        # Object header
        obj_lines.append(f"o {name}")
        obj_lines.append(f"usemtl {mat_name}")

        # Write vertices
        for v in verts:
            obj_lines.append(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}")

        # Write texture coordinates (if available)
        # OBJ expects V=0 at bottom, but PAC stores V=0 at top.
        # Need to flip V: V_obj = 1.0 - V_pac
        if has_uv:
            for uv in uvs:
                obj_lines.append(f"vt {uv[0]:.6f} {1.0 - uv[1]:.6f}")

        # Write vertex normals (if available)
        if has_norm:
            for n in normals:
                obj_lines.append(f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}")

        # Write faces using global 1-based indices
        for face in faces:
            a = vertex_offset + int(face[0])
            b = vertex_offset + int(face[1])
            c = vertex_offset + int(face[2])

            # All three indices (v, vt, vn) share the same value since
            # they are per-vertex and written in the same order.
            if has_uv and has_norm:
                obj_lines.append(f"f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}")
            elif has_uv:
                obj_lines.append(f"f {a}/{a} {b}/{b} {c}/{c}")
            elif has_norm:
                obj_lines.append(f"f {a}//{a} {b}//{b} {c}//{c}")
            else:
                obj_lines.append(f"f {a} {b} {c}")

        vertex_offset += n_verts

    # Write OBJ file
    output.write_text("\n".join(obj_lines) + "\n", encoding="utf-8")