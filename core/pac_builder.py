"""
PAC 文件构建器 - 将修改后的 OBJ 网格打包为 PAC 格式
基于 Crimson Desert Mod Workbench 的 Round-trip 工作流

支持两种模式：
1. 简化模式：从头创建 PAC 文件（用于没有原始 PAC 的情况）
2. Round-trip 模式：基于原始 PAC 进行修补（推荐，需要原始 PAC 文件）
"""

import struct
import json
import math
import copy
import logging
import numpy as np
from pathlib import Path
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

PAR_MAGIC = b"PAR "


# ── Data structures ──

@dataclass
class SubMesh:
    name: str
    material: str
    texture: str
    vertices: List[Tuple[float, float, float]]
    uvs: List[Tuple[float, float]]
    faces: List[Tuple[int, int, int]]
    normals: List[Tuple[float, float, float]]
    bone_indices: List[Tuple[int, ...]]
    bone_weights: List[Tuple[float, ...]]
    source_vertex_map: List[int]
    vertex_count: int
    face_count: int
    source_vertex_offsets: List[int]
    source_vertex_stride: int = 40
    source_index_offset: int = -1
    source_descriptor_offset: int = -1
    source_lod_count: int = 1
    # Original descriptor bbox (for stable quantization in round-trip)
    source_bbox_min: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    source_bbox_extent: Tuple[float, float, float] = (1.0, 1.0, 1.0)


@dataclass
class ParsedMesh:
    path: str
    format: str  # "pac"
    submeshes: List[SubMesh]
    total_vertices: int = 0
    total_faces: int = 0
    has_uvs: bool = False
    has_bones: bool = False
    bbox_min: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    bbox_max: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    lod_levels: List[List[SubMesh]] = None  # for PAMLOD-style; unused here
    # internal
    _original_data: bytes = None


@dataclass
class PacDescriptor:
    name: str
    material: str
    bbox_min: Tuple[float, float, float]
    bbox_extent: Tuple[float, float, float]
    vertex_counts: List[int]
    index_counts: List[int]
    palette: Tuple[int, ...]
    descriptor_offset: int
    stored_lod_count: int


# ── Utilities ──

def compute_bbox(vertices: List[Tuple[float, float, float]]) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    if not vertices:
        return ((0, 0, 0), (1, 1, 1))
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    zs = [v[2] for v in vertices]
    bmin = (min(xs), min(ys), min(zs))
    bmax = (max(xs), max(ys), max(zs))
    return bmin, bmax


def compute_smooth_normals(vertices: List[Tuple[float, float, float]],
                           faces: List[Tuple[int, int, int]]) -> List[Tuple[float, float, float]]:
    normals = [[0.0, 0.0, 0.0] for _ in vertices]
    for a, b, c in faces:
        v0 = np.array(vertices[a], dtype=float)
        v1 = np.array(vertices[b], dtype=float)
        v2 = np.array(vertices[c], dtype=float)
        n = np.cross(v1 - v0, v2 - v0)
        for i in (a, b, c):
            normals[i][0] += n[0]
            normals[i][1] += n[1]
            normals[i][2] += n[2]
    result = []
    for n in normals:
        length = math.sqrt(n[0]**2 + n[1]**2 + n[2]**2)
        if length > 1e-8:
            result.append((n[0]/length, n[1]/length, n[2]/length))
        else:
            result.append((0.0, 1.0, 0.0))
    return result


def quantize_u16(value: float, bbox_min: float, bbox_extent: float) -> int:
    if abs(bbox_extent) < 1e-10:
        return 0
    t = (value - bbox_min) / bbox_extent
    t = max(0.0, min(1.0, t))
    return min(32767, max(0, round(t * 32767.0)))


def dequantize_u16(quantized: int, bbox_min: float, bbox_extent: float) -> float:
    if abs(bbox_extent) < 1e-10:
        return bbox_min
    return bbox_min + (quantized / 32767.0) * bbox_extent


def pack_normal_10_10_10(normal: Tuple[float, float, float]) -> int:
    def enc(v: float) -> int:
        v = max(-1.0, min(1.0, v))
        return max(0, min(1023, round((v + 1.0) * 511.5)))
    nx, ny, nz = normal
    return enc(nz) | (enc(nx) << 10) | (enc(ny) << 20)


def unpack_normal_10_10_10(packed: int) -> Tuple[float, float, float]:
    nx_raw = (packed >> 0) & 0x3FF
    ny_raw = (packed >> 10) & 0x3FF
    nz_raw = (packed >> 20) & 0x3FF
    nx = ny_raw / 511.5 - 1.0
    ny = nz_raw / 511.5 - 1.0
    nz = nx_raw / 511.5 - 1.0
    return (nx, ny, nz)


def float16_to_bytes(value: float) -> bytes:
    f16 = np.float16(value)
    return struct.pack("<H", np.uint16(f16.view(np.uint16)))


def bytes_to_float16(data: bytes) -> float:
    u16 = struct.unpack("<H", data)[0]
    f16 = np.uint16(u16).view(np.float16)
    return float(f16)


# ── PAR section parsing (aligned with official) ──

def _parse_par_sections(data: bytes) -> List[Dict]:
    if len(data) < 0x50 or data[:4] != PAR_MAGIC:
        return []
    sections = []
    offset = 0x50
    for i in range(8):
        slot_off = 0x10 + i * 8
        comp_size = struct.unpack_from("<I", data, slot_off)[0]
        decomp_size = struct.unpack_from("<I", data, slot_off + 4)[0]
        stored_size = comp_size if comp_size > 0 else decomp_size
        if decomp_size <= 0:
            continue
        if offset + stored_size > len(data):
            return []
        sections.append({"index": i, "offset": offset, "size": decomp_size})
        offset += stored_size
    return sections


# ── PAC descriptor discovery (aligned with official) ──

def _find_pac_descriptors(
    data: bytes,
    sec0_offset: int,
    sec0_size: int,
    n_lods: int,
) -> List[PacDescriptor]:
    region = data[sec0_offset:sec0_offset + sec0_size]
    if not region:
        return []

    found: List[Tuple[int, PacDescriptor]] = []
    seen_starts: set = set()
    pad_len = max(4, n_lods)

    def _find_name_strings(region: bytes, desc_start: int) -> Tuple[str, str]:
        names = []
        cursor = desc_start
        for _ in range(2):
            found_name = False
            for back in range(1, 200):
                pos = cursor - back
                if pos < 0:
                    break
                candidate_len = region[pos]
                if candidate_len == 0 or candidate_len != back - 1:
                    continue
                name_bytes = region[pos + 1:cursor]
                if not name_bytes or not all(32 <= c < 127 for c in name_bytes):
                    continue
                names.append(name_bytes.decode("ascii", "replace"))
                cursor = pos
                found_name = True
                break
            if not found_name:
                names.append(f"unknown_{desc_start:x}")
        names.reverse()
        return names[0], names[1]

    def _append_descriptor(idx: int, stored_lod_count: int, vc_off: int, ic_off: int) -> None:
        desc_start = idx - 35
        if desc_start in seen_starts or desc_start < 0:
            return
        if desc_start + ic_off + stored_lod_count * 4 > len(region):
            return
        if region[desc_start] != 0x01:
            return
        try:
            floats = struct.unpack_from("<8f", region, desc_start + 3)
        except struct.error:
            return
        vert_counts = [
            struct.unpack_from("<H", region, desc_start + vc_off + i * 2)[0]
            for i in range(stored_lod_count)
        ]
        idx_counts = [
            struct.unpack_from("<I", region, desc_start + ic_off + i * 4)[0]
            for i in range(stored_lod_count)
        ]
        if not any(v > 0 for v in vert_counts):
            return
        if any(v > 200000 for v in vert_counts):
            return
        if any(i > 20000000 for i in idx_counts):
            return
        name, material = _find_name_strings(region, desc_start)
        palette = tuple(region[idx + 1:idx + 1 + stored_lod_count])
        padded_vc = vert_counts + [0] * max(0, pad_len - stored_lod_count)
        padded_ic = idx_counts + [0] * max(0, pad_len - stored_lod_count)
        found.append((
            desc_start,
            PacDescriptor(
                name=name,
                material=material,
                bbox_min=(floats[2], floats[3], floats[4]),
                bbox_extent=(floats[5], floats[6], floats[7]),
                vertex_counts=padded_vc,
                index_counts=padded_ic,
                palette=palette,
                descriptor_offset=sec0_offset + desc_start,
                stored_lod_count=stored_lod_count,
            ),
        ))
        seen_starts.add(desc_start)

    pattern_specs = [
        (bytes([0x04, 0x00, 0x01, 0x02, 0x03]), 4, 40, 48,
          lambda idx: True),
        (bytes([0x03, 0x00, 0x01, 0x01, 0x02]), 3, 40, 46,
          lambda idx: True),
        (bytes([0x03, 0x00, 0x01, 0x02]), 3, 40, 46,
          lambda idx: idx < 1 or region[idx - 1] != 0x04),
        (bytes([0x02, 0x00, 0x01]), 2, 40, 44,
          lambda idx: idx < 1 or region[idx - 1] not in (0x03, 0x04)),
    ]

    for pattern, lod_count, vc_off, ic_off, should_accept in pattern_specs:
        pos = 0
        while True:
            idx = region.find(pattern, pos)
            if idx == -1:
                break
            if should_accept(idx):
                _append_descriptor(idx, lod_count, vc_off, ic_off)
            pos = idx + len(pattern)

    found.sort(key=lambda item: item[0])
    return [desc for _, desc in found]


# ── PAC parsing (aligned with official) ──

def parse_pac(data: bytes, path: str = "unknown.pac") -> ParsedMesh:
    if not data or data[:4] != PAR_MAGIC:
        raise ValueError("Not a valid PAC file")

    sections = _parse_par_sections(data)
    if not sections:
        raise ValueError("Failed to parse PAC sections")

    sec_by_idx = {s["index"]: s for s in sections}
    sec0 = sec_by_idx.get(0)
    if not sec0:
        raise ValueError("Missing PAC section 0")

    s0_start = sec0["offset"]
    s0_end = s0_start + sec0["size"]
    flags = struct.unpack_from("<I", data, s0_start)[0]
    n_lods = data[s0_start + 4]
    if n_lods == 0 or n_lods > 10:
        raise ValueError(f"Invalid n_lods: {n_lods}")

    # Read LOD offsets and split offsets
    off = s0_start + 5
    lod_offsets = [struct.unpack_from("<I", data, off + i * 4)[0] for i in range(n_lods)]
    off += n_lods * 4
    split_offsets = [struct.unpack_from("<I", data, off + i * 4)[0] for i in range(n_lods)]
    off += n_lods * 4

    # Compute section boundaries
    sorted_offsets = sorted(lod_offsets)
    boundaries = [80] + sorted_offsets + [len(data)]
    sections_bounds = [(boundaries[i], boundaries[i + 1]) for i in range(len(boundaries) - 1)]

    # Parse submesh descriptors from section 0
    # Actual layout (from hex analysis):
    #   [u8] flag
    #   [u8] pad
    #   [u8] name_len
    #   [name_len] name
    #   [u8] mat_len
    #   [mat_len] material
    #   [u8] flag2
    #   [u16] pad2
    #   [8x float] bbox
    #   [u8] bone_count
    #   [bone_count] bone_palette (u8 each)
    #   [pad to even]
    #   [n_lods x u16] vert_counts
    #   [n_lods x u32] idx_counts
    pac_submeshes = []
    pos = off
    while pos < s0_end:
        # flag + pad
        if pos + 2 >= s0_end:
            break
        pos += 2

        # name
        if pos + 1 >= s0_end:
            break
        name_len = data[pos]
        if name_len == 0 or name_len > 200 or pos + 1 + name_len >= s0_end:
            break
        name = data[pos + 1:pos + 1 + name_len].decode("ascii", "replace")
        pos += 1 + name_len

        # material
        if pos + 1 >= s0_end:
            break
        mat_len = data[pos]
        if pos + 1 + mat_len >= s0_end:
            break
        material = data[pos + 1:pos + 1 + mat_len].decode("ascii", "replace")
        pos += 1 + mat_len

        # flag2 + pad2
        if pos + 3 >= s0_end:
            break
        pos += 3

        # bbox (8 floats)
        if pos + 32 >= s0_end:
            break
        bbox_floats = [struct.unpack_from("<f", data, pos + i * 4)[0] for i in range(8)]
        pos += 32

        # bone palette
        if pos + 1 >= s0_end:
            break
        bone_count = data[pos]; pos += 1
        if pos + bone_count >= s0_end:
            break
        bone_palette = tuple(data[pos:pos + bone_count])
        pos += bone_count
        if bone_count % 2 != 0:
            pos += 1  # pad to even

        # vert counts per LOD
        if pos + n_lods * 2 >= s0_end:
            break
        vert_counts = [struct.unpack_from("<H", data, pos + i * 2)[0] for i in range(n_lods)]
        pos += n_lods * 2

        # index counts per LOD
        if pos + n_lods * 4 >= s0_end:
            break
        idx_counts = [struct.unpack_from("<I", data, pos + i * 4)[0] for i in range(n_lods)]
        pos += n_lods * 4

        # bbox layout: [pad_float, pad_float, bmin_x, bmin_y, bmin_z, extent_x, extent_y, extent_z]
        bmin = (bbox_floats[2], bbox_floats[3], bbox_floats[4])
        extent_from_s0 = (bbox_floats[5], bbox_floats[6], bbox_floats[7])
        bmax = (bmin[0] + extent_from_s0[0],
                bmin[1] + extent_from_s0[1],
                bmin[2] + extent_from_s0[2])

        pac_submeshes.append({
            "name": name,
            "material": material,
            "bmin": bmin,
            "bmax": bmax,
            "vert_counts": vert_counts,
            "idx_counts": idx_counts,
            "bone_palette": bone_palette,
        })

        # If next bytes don't look like flag+pad+name_len, stop
        if pos + 3 >= s0_end:
            break
        # next name_len should be reasonable (allow 0 as "no next descriptor")
        next_name_len = data[pos + 2]
        if next_name_len > 128:
            break

    if not pac_submeshes:
        raise ValueError("No submesh descriptors found in PAC")

    # Use official-style descriptor discovery to align with rebuild logic
    descriptors = _find_pac_descriptors(data, s0_start, sec0["size"], n_lods)
    if not descriptors:
        raise ValueError("No PAC descriptors found via official-style scan")

    # Map descriptors to submeshes by name
    desc_by_name = {}
    for d in descriptors:
        desc_by_name[d.name] = d

    # Use LOD0 section: first LOD offset, and its split offset
    # lod_offsets[0] is where LOD0 section starts
    # split_offsets[0] is where indices start in that section
    if n_lods == 0 or n_lods > 10:
        raise ValueError(f"Invalid n_lods: {n_lods}")

    lod0_sec_start = lod_offsets[0]
    lod0_split = split_offsets[0]
    # Next LOD section start or EOF
    next_lod_start = min(
        (off for off in lod_offsets if off > lod0_sec_start),
        default=len(data)
    )
    lod0_sec_end = next_lod_start

    if lod0_sec_start >= lod0_split or lod0_split >= lod0_sec_end:
        raise ValueError("Invalid LOD0 layout: split not between start and end")

    vert_region_end = lod0_split
    idx_region_end = lod0_sec_end

    # We'll walk descriptors in order and consume vertex/index regions
    vert_cur = lod0_sec_start
    idx_cur = lod0_split

    result = ParsedMesh(path=path, format="pac", submeshes=[])

    for desc in descriptors:
        # Use LOD0 counts
        lod0_idx = 0
        declared_nv = desc.vertex_counts[lod0_idx] if lod0_idx < len(desc.vertex_counts) else 0
        declared_ni = desc.index_counts[lod0_idx] if lod0_idx < len(desc.index_counts) else 0

        if declared_nv == 0:
            continue

        # Try to match with pac_submeshes info by name
        sm_info = next((s for s in pac_submeshes if s["name"] == desc.name), None)
        bmin = sm_info["bmin"] if sm_info else desc.bbox_min
        extent = desc.bbox_extent
        bmax = tuple(bmin[i] + extent[i] for i in range(3))
        bone_palette = sm_info.get("bone_palette", desc.palette) if sm_info else desc.palette

        vert_stride = 40  # default for this engine

        # Ensure we have enough space
        if vert_cur + declared_nv * vert_stride > vert_region_end:
            # If overflow, clamp count
            available = (vert_region_end - vert_cur) // max(vert_stride, 1)
            if available <= 0:
                break
            declared_nv = available

        if idx_cur + declared_ni * 2 > idx_region_end:
            available = (idx_region_end - idx_cur) // 2
            if available <= 0:
                break
            declared_ni = available

        # Read faces as u16
        raw_faces = []
        max_index = -1
        for i in range(0, declared_ni - 2, 3):
            a = struct.unpack_from("<H", data, idx_cur + i * 2)[0]
            b = struct.unpack_from("<H", data, idx_cur + (i + 1) * 2)[0]
            c = struct.unpack_from("<H", data, idx_cur + (i + 2) * 2)[0]
            raw_faces.append((a, b, c))
            if a > max_index:
                max_index = a
            if b > max_index:
                max_index = b
            if c > max_index:
                max_index = c

        # Determine used vertex set
        used_indices = sorted({
            idx for face in raw_faces for idx in face
            if 0 <= idx < declared_nv
        })
        idx_map = {src_idx: dst_idx for dst_idx, src_idx in enumerate(used_indices)}

        verts = []
        uvs = []
        normals = []
        bone_indices = []
        bone_weights = []
        source_offsets = []

        for src_idx in used_indices:
            rec_off = vert_cur + src_idx * vert_stride
            if rec_off + 12 > vert_region_end:
                break

            xu, yu, zu = struct.unpack_from("<HHH", data, rec_off)
            verts.append((
                dequantize_u16(xu, bmin[0], extent[0]),
                dequantize_u16(yu, bmin[1], extent[1]),
                dequantize_u16(zu, bmin[2], extent[2]),
            ))
            source_offsets.append(rec_off)

            # UV (float16)
            uv = (0.0, 0.0)
            if rec_off + 12 <= vert_region_end:
                try:
                    u = struct.unpack_from("<e", data, rec_off + 8)[0]
                    v = struct.unpack_from("<e", data, rec_off + 10)[0]
                    if not (math.isnan(u) or math.isnan(v)):
                        uv = (u, v)
                except Exception:
                    uv = (0.0, 0.0)
            uvs.append(uv)

            # Normal (10_10_10)
            n = (0.0, 1.0, 0.0)
            if rec_off + 20 <= vert_region_end:
                npacked = struct.unpack_from("<I", data, rec_off + 16)[0]
                n = unpack_normal_10_10_10(npacked)
            normals.append(n)

            # Bones
            packed_bones = ()
            packed_weights = ()
            if rec_off + 36 <= vert_region_end:
                raw_slots = struct.unpack_from("<BBBB", data, rec_off + 28)
                raw_weights = struct.unpack_from("<BBBB", data, rec_off + 32)
                mapped_bones = []
                mapped_weights = []
                for slot, weight in zip(raw_slots, raw_weights):
                    if slot == 0xFF or weight == 0:
                        continue
                    mapped_bones.append(bone_palette[slot] if slot < len(bone_palette) else slot)
                    mapped_weights.append(weight / 255.0)
                packed_bones = tuple(mapped_bones)
                packed_weights = tuple(mapped_weights)
            bone_indices.append(packed_bones)
            bone_weights.append(packed_weights)

        faces = []
        for a, b, c in raw_faces:
            if a in idx_map and b in idx_map and c in idx_map:
                faces.append((idx_map[a], idx_map[b], idx_map[c]))

        sm = SubMesh(
            name=desc.name,
            material=desc.material,
            texture="",
            vertices=verts,
            uvs=uvs,
            faces=faces,
            normals=normals,
            bone_indices=bone_indices,
            bone_weights=bone_weights,
            source_vertex_map=list(range(len(verts))),
            vertex_count=len(verts),
            face_count=len(faces),
            source_vertex_offsets=source_offsets,
            source_vertex_stride=vert_stride,
            source_index_offset=idx_cur,
            source_descriptor_offset=desc.descriptor_offset,
            source_lod_count=desc.stored_lod_count,
            source_bbox_min=bmin,
            source_bbox_extent=extent,
        )
        result.submeshes.append(sm)

        if any(bone_indices):
            result.has_bones = True

        # Advance cursors
        used_verts_count = max(declared_nv, max_index + 1) if max_index >= 0 else declared_nv
        vert_cur += used_verts_count * vert_stride
        idx_cur += declared_ni * 2

    # Compute overall stats
    if result.submeshes:
        all_verts = [v for sm in result.submeshes for v in sm.vertices]
        if all_verts:
            xs = [v[0] for v in all_verts]
            ys = [v[1] for v in all_verts]
            zs = [v[2] for v in all_verts]
            result.bbox_min = (min(xs), min(ys), min(zs))
            result.bbox_max = (max(xs), max(ys), max(zs))

    result.total_vertices = sum(len(sm.vertices) for sm in result.submeshes)
    result.total_faces = sum(len(sm.faces) for sm in result.submeshes)
    result.has_uvs = any(sm.uvs for sm in result.submeshes)

    logger.info("Parsed PAC %s: %d submeshes, %d verts, %d faces",
                path, len(result.submeshes), result.total_vertices, result.total_faces)
    return result


# ── PAC rebuild (Round-trip edit) ──

def _pac_needs_full_rebuild(original_mesh: ParsedMesh, working_mesh: ParsedMesh) -> bool:
    if len(original_mesh.submeshes) != len(working_mesh.submeshes):
        return True
    for orig_sm, new_sm in zip(original_mesh.submeshes, working_mesh.submeshes):
        if len(orig_sm.vertices) != len(new_sm.vertices):
            return True
        if len(orig_sm.faces) != len(new_sm.faces):
            return True
        if orig_sm.source_vertex_stride < 12:
            return True
        if len(orig_sm.source_vertex_offsets) != len(orig_sm.vertices):
            return True
        if orig_sm.source_descriptor_offset < 0:
            return True
    return False


def _build_pac_in_place(
    original_mesh: ParsedMesh,
    working_mesh: ParsedMesh,
    original_data: bytes,
) -> bytes:
    result = bytearray(original_data)
    vertex_updates: Dict[int, bytes] = {}
    index_updates: Dict[int, bytes] = {}

    for sm_idx, (orig_sm, new_sm) in enumerate(zip(original_mesh.submeshes, working_mesh.submeshes)):
        if len(orig_sm.vertices) != len(new_sm.vertices):
            raise ValueError(
                f"PAC submesh {sm_idx} changed vertex count "
                f"({len(orig_sm.vertices)} -> {len(new_sm.vertices)}). "
                "Keep the same topology when importing OBJ for PAC meshes."
            )
        if len(orig_sm.faces) != len(new_sm.faces):
            raise ValueError(
                f"PAC submesh {sm_idx} changed face count "
                f"({len(orig_sm.faces)} -> {len(new_sm.faces)}). "
                "Keep the same topology when importing OBJ for PAC meshes."
            )
        if orig_sm.source_vertex_stride < 12:
            raise ValueError(
                f"PAC submesh {sm_idx} is missing source vertex metadata and cannot be rebuilt safely."
            )

        # Always compute bbox from the new vertices to avoid clipping
        # when morphed geometry exceeds the original bounding box.
        bmin, bmax = compute_bbox(new_sm.vertices)
        extent = tuple(bmax[i] - bmin[i] for i in range(3))

        # Patch descriptor bounds if we know its offset
        if orig_sm.source_descriptor_offset >= 0:
            _patch_pac_descriptor_bounds(result, orig_sm.source_descriptor_offset, bmin, extent)

        new_uvs = new_sm.uvs if len(new_sm.uvs) == len(new_sm.vertices) else []

        for vi, rec_off in enumerate(orig_sm.source_vertex_offsets):
            if rec_off < 0 or rec_off + orig_sm.source_vertex_stride > len(result):
                raise ValueError(
                    f"PAC vertex record {vi} for submesh {sm_idx} points outside the file."
                )

            rec = bytearray(result[rec_off:rec_off + orig_sm.source_vertex_stride])
            vx, vy, vz = new_sm.vertices[vi]
            struct.pack_into(
                "<HHH",
                rec,
                0,
                quantize_u16(vx, bmin[0], extent[0]),
                quantize_u16(vy, bmin[1], extent[1]),
                quantize_u16(vz, bmin[2], extent[2]),
            )

            if new_uvs and len(rec) >= 12:
                try:
                    struct.pack_into("<e", rec, 8, new_uvs[vi][0])
                    struct.pack_into("<e", rec, 10, new_uvs[vi][1])
                except (OverflowError, ValueError):
                    struct.pack_into("<e", rec, 8, 0.0)
                    struct.pack_into("<e", rec, 10, 0.0)

            payload = bytes(rec)
            prev = vertex_updates.get(rec_off)
            if prev is not None and prev != payload:
                raise ValueError(
                    "PAC import edited a shared vertex buffer inconsistently across submeshes."
                )
            vertex_updates[rec_off] = payload

        if orig_sm.source_index_offset >= 0:
            for fi, (a, b, c) in enumerate(new_sm.faces):
                if a >= len(new_sm.vertices) or b >= len(new_sm.vertices) or c >= len(new_sm.vertices):
                    raise ValueError(f"PAC face {fi} in submesh {sm_idx} references an out-of-range vertex.")
                face_off = orig_sm.source_index_offset + fi * 6
                if face_off + 6 > len(result):
                    raise ValueError(
                        f"PAC face record {fi} for submesh {sm_idx} points outside the file."
                    )
                payload = struct.pack("<HHH", a, b, c)
                prev = index_updates.get(face_off)
                if prev is not None and prev != payload:
                    raise ValueError(
                        "PAC import edited a shared index buffer inconsistently across submeshes."
                    )
                index_updates[face_off] = payload

    for rec_off, payload in vertex_updates.items():
        result[rec_off:rec_off + len(payload)] = payload
    for face_off, payload in index_updates.items():
        result[face_off:face_off + len(payload)] = payload

    logger.info(
        "Built PAC %s with in-place patching: %d submeshes, %d verts, %d faces",
        working_mesh.path,
        len(working_mesh.submeshes),
        sum(len(sm.vertices) for sm in working_mesh.submeshes),
        sum(len(sm.faces) for sm in working_mesh.submeshes),
    )
    return bytes(result)


def _patch_pac_descriptor_bounds(
    data: bytearray,
    descriptor_offset: int,
    bbox_min: Tuple[float, float, float],
    bbox_extent: Tuple[float, float, float],
) -> None:
    if descriptor_offset < 0 or descriptor_offset + 35 > len(data):
        return
    floats_off = descriptor_offset + 3
    struct.pack_into("<f", data, floats_off + 2 * 4, bbox_min[0])
    struct.pack_into("<f", data, floats_off + 3 * 4, bbox_min[1])
    struct.pack_into("<f", data, floats_off + 4 * 4, bbox_min[2])
    struct.pack_into("<f", data, floats_off + 5 * 4, bbox_extent[0])
    struct.pack_into("<f", data, floats_off + 6 * 4, bbox_extent[1])
    struct.pack_into("<f", data, floats_off + 7 * 4, bbox_extent[2])


def _build_pac_full_rebuild(
    original_mesh: ParsedMesh,
    working_mesh: ParsedMesh,
    original_data: bytes,
) -> bytes:
    sections = _parse_par_sections(original_data)
    sec_by_idx = {sec["index"]: sec for sec in sections}
    sec0 = sec_by_idx.get(0)
    if not sec0:
        raise ValueError("PAC section table is missing section 0.")

    n_lods = original_data[sec0["offset"] + 4] if sec0["size"] >= 5 else 0
    if n_lods <= 0 or n_lods > 10:
        raise ValueError(f"Invalid PAC LOD count: {n_lods}")

    descriptors = _find_pac_descriptors(original_data, sec0["offset"], sec0["size"], n_lods)
    if len(descriptors) < len(working_mesh.submeshes):
        raise ValueError("PAC descriptor count does not match the parsed submesh set.")

    sec0_data = bytearray(original_data[sec0["offset"]:sec0["offset"] + sec0["size"]])
    preserved_sections = {
        sec["index"]: original_data[sec["offset"]:sec["offset"] + sec["size"]]
        for sec in sections
        if sec["index"] > n_lods
    }

    prepared_submeshes = []
    for sm_idx, (orig_sm, new_sm, desc) in enumerate(zip(original_mesh.submeshes, working_mesh.submeshes, descriptors)):
        if not orig_sm.source_vertex_offsets or orig_sm.source_vertex_stride < 12:
            raise ValueError(
                f"PAC submesh {sm_idx} is missing source vertex metadata for a full rebuild."
            )

        donor_records = []
        for rec_off in orig_sm.source_vertex_offsets:
            if rec_off < 0 or rec_off + orig_sm.source_vertex_stride > len(original_data):
                raise ValueError(
                    f"PAC vertex record for submesh {sm_idx} points outside the file."
                )
            donor_records.append(original_data[rec_off:rec_off + orig_sm.source_vertex_stride])

        donor_indices = _choose_pac_donor_indices(orig_sm, new_sm)
        normals = (
            new_sm.normals
            if len(new_sm.normals) == len(new_sm.vertices)
            else compute_smooth_normals(new_sm.vertices, new_sm.faces)
        )
        new_uvs = new_sm.uvs if len(new_sm.uvs) == len(new_sm.vertices) else []
        bmin, bmax = compute_bbox(new_sm.vertices)
        extent = tuple(bmax[i] - bmin[i] for i in range(3))
        stored_lod_count = max(1, min(n_lods, orig_sm.source_lod_count or desc.stored_lod_count or n_lods))

        rel_desc_off = desc.descriptor_offset - sec0["offset"]
        if rel_desc_off < 0 or rel_desc_off + 40 > len(sec0_data):
            raise ValueError(f"PAC descriptor {sm_idx} points outside section 0.")

        _patch_pac_descriptor_bounds(sec0_data, rel_desc_off, bmin, extent)
        vc_off = rel_desc_off + 40
        ic_off = vc_off + desc.stored_lod_count * 2
        new_vert_count = len(new_sm.vertices)
        new_index_count = len(new_sm.faces) * 3
        for lod_idx in range(desc.stored_lod_count):
            struct.pack_into("<H", sec0_data, vc_off + lod_idx * 2, new_vert_count)
            struct.pack_into("<I", sec0_data, ic_off + lod_idx * 4, new_index_count)

        prepared_submeshes.append({
            "submesh": new_sm,
            "donor_records": donor_records,
            "donor_indices": donor_indices,
            "normals": normals,
            "uvs": new_uvs,
            "bbox_min": bmin,
            "bbox_extent": extent,
            "stored_lod_count": stored_lod_count,
        })

    lod_payloads: Dict[int, bytes] = {}
    lod_split_bytes: Dict[int, int] = {}
    for sec_idx in range(1, n_lods + 1):
        lod_idx = n_lods - sec_idx
        verts_buf = bytearray()
        idx_buf = bytearray()

        for sm_idx, prepared in enumerate(prepared_submeshes):
            if lod_idx >= prepared["stored_lod_count"]:
                continue

            sm = prepared["submesh"]
            donor_records = prepared["donor_records"]
            donor_indices = prepared["donor_indices"]
            normals = prepared["normals"]
            new_uvs = prepared["uvs"]
            bbox_min = prepared["bbox_min"]
            bbox_extent = prepared["bbox_extent"]

            for vi, vertex in enumerate(sm.vertices):
                donor_rec = bytearray(donor_records[donor_indices[vi]])
                struct.pack_into(
                    "<HHH",
                    donor_rec,
                    0,
                    quantize_u16(vertex[0], bbox_min[0], bbox_extent[0]),
                    quantize_u16(vertex[1], bbox_min[1], bbox_extent[1]),
                    quantize_u16(vertex[2], bbox_min[2], bbox_extent[2]),
                )

                if len(donor_rec) >= 12:
                    if new_uvs:
                        try:
                            struct.pack_into("<e", donor_rec, 8, new_uvs[vi][0])
                            struct.pack_into("<e", donor_rec, 10, new_uvs[vi][1])
                        except (OverflowError, ValueError):
                            struct.pack_into("<e", donor_rec, 8, 0.0)
                            struct.pack_into("<e", donor_rec, 10, 0.0)

                if len(donor_rec) >= 20:
                    existing_normal = struct.unpack_from("<I", donor_rec, 16)[0]
                    struct.pack_into(
                        "<I",
                        donor_rec,
                        16,
                        _pack_pac_normal(normals[vi], existing_normal),
                    )

                verts_buf.extend(donor_rec)

            for face in sm.faces:
                a, b, c = face
                if a >= len(sm.vertices) or b >= len(sm.vertices) or c >= len(sm.vertices):
                    raise ValueError(f"PAC face in submesh {sm_idx} references an out-of-range vertex.")
                idx_buf.extend(struct.pack("<HHH", a, b, c))

        lod_split_bytes[sec_idx] = len(verts_buf)
        lod_payloads[sec_idx] = bytes(verts_buf + idx_buf)

    section_payloads: Dict[int, bytes] = {0: bytes(sec0_data)}
    section_payloads.update(lod_payloads)
    section_payloads.update(preserved_sections)

    header = bytearray(original_data[:0x50])
    for slot in range(8):
        struct.pack_into("<I", header, 0x10 + slot * 8, 0)
        struct.pack_into("<I", header, 0x10 + slot * 8 + 4, 0)

    section_offsets = {0: 0x50}
    next_offset = 0x50 + len(section_payloads[0])
    for slot in range(1, 8):
        payload = section_payloads.get(slot)
        if payload is None:
            continue
        section_offsets[slot] = next_offset
        next_offset += len(payload)

    off = 5
    for lod_idx in range(n_lods):
        sec_idx = n_lods - lod_idx
        struct.pack_into("<I", sec0_data, off + lod_idx * 4, section_offsets[sec_idx])
    off += n_lods * 4
    for lod_idx in range(n_lods):
        sec_idx = n_lods - lod_idx
        split_abs = section_offsets[sec_idx] + lod_split_bytes.get(sec_idx, 0)
        struct.pack_into("<I", sec0_data, off + lod_idx * 4, split_abs)
    section_payloads[0] = bytes(sec0_data)

    assembled = bytearray(header)
    for slot in range(8):
        payload = section_payloads.get(slot)
        if payload is None:
            continue
        struct.pack_into("<I", assembled, 0x10 + slot * 8, 0)
        struct.pack_into("<I", assembled, 0x10 + slot * 8 + 4, len(payload))
        assembled.extend(payload)

    logger.info(
        "Built PAC %s with full rebuild: %d bytes, %d submeshes, %d verts, %d faces",
        working_mesh.path,
        len(assembled),
        len(working_mesh.submeshes),
        sum(len(sm.vertices) for sm in working_mesh.submeshes),
        sum(len(sm.faces) for sm in working_mesh.submeshes),
    )
    return bytes(assembled)


def _pack_pac_normal(normal: Tuple[float, float, float], existing_packed: int = 0) -> int:
    def _enc(value: float) -> int:
        value = max(-1.0, min(1.0, value))
        return max(0, min(1023, round((value + 1.0) * 511.5)))
    nx, ny, nz = normal
    packed = _enc(nz) | (_enc(nx) << 10) | (_enc(ny) << 20)
    return (existing_packed & 0xC0000000) | packed


def _choose_pac_donor_indices(orig_sm: SubMesh, new_sm: SubMesh) -> List[int]:
    if not orig_sm.vertices:
        return [0] * len(new_sm.vertices)

    exact_map: Dict[Tuple[int, int, int], List[int]] = {}
    for orig_idx, pos in enumerate(orig_sm.vertices):
        key = (round(pos[0] * 100000), round(pos[1] * 100000), round(pos[2] * 100000))
        exact_map.setdefault(key, []).append(orig_idx)

    sidecar_source_map = list(getattr(new_sm, "source_vertex_map", ()) or ())
    donor_indices: List[int] = []
    for vertex_index, new_pos in enumerate(new_sm.vertices):
        if vertex_index < len(sidecar_source_map):
            mapped_index = int(sidecar_source_map[vertex_index])
            if 0 <= mapped_index < len(orig_sm.vertices):
                donor_indices.append(mapped_index)
                continue

        key = (round(new_pos[0] * 100000), round(new_pos[1] * 100000), round(new_pos[2] * 100000))
        exact_hits = exact_map.get(key)
        if exact_hits:
            donor_indices.append(exact_hits[0])
            continue

        best_idx = 0
        best_dist = float("inf")
        for orig_idx, orig_pos in enumerate(orig_sm.vertices):
            dx = new_pos[0] - orig_pos[0]
            dy = new_pos[1] - orig_pos[1]
            dz = new_pos[2] - orig_pos[2]
            dist_sq = dx * dx + dy * dy + dz * dz
            if dist_sq < best_dist:
                best_dist = dist_sq
                best_idx = orig_idx
        donor_indices.append(best_idx)

    return donor_indices


def _align_submesh_order_like_original(original_mesh: ParsedMesh, working_mesh: ParsedMesh):
    """
    Ensure working_mesh submesh order matches original_mesh by name.
    """
    if len(original_mesh.submeshes) != len(working_mesh.submeshes):
        return
    orig_by_name = {sm.name: sm for sm in original_mesh.submeshes}
    reordered = []
    for orig_sm in original_mesh.submeshes:
        found = None
        for sm in working_mesh.submeshes:
            if sm.name == orig_sm.name:
                found = sm
                break
        if found:
            reordered.append(found)
        else:
            # fallback: pick first unmatched
            remaining = [sm for sm in working_mesh.submeshes if sm not in reordered]
            reordered.append(remaining[0] if remaining else orig_sm)
    working_mesh.submeshes = reordered


def build_pac(mesh: ParsedMesh, original_data: bytes) -> bytes:
    """
    Rebuild a PAC binary from a modified mesh using Round-trip edit logic.
    """
    if not original_data or original_data[:4] != PAR_MAGIC:
        raise ValueError("Original PAC data required for rebuild")

    original_mesh = parse_pac(original_data, mesh.path)
    if not original_mesh.submeshes:
        raise ValueError("Original PAC could not be parsed into usable geometry")

    # Store original data reference for rebuild helpers
    original_mesh._original_data = original_data

    working_mesh = copy.deepcopy(mesh)
    _align_submesh_order_like_original(original_mesh, working_mesh)

    if len(original_mesh.submeshes) != len(working_mesh.submeshes):
        raise ValueError(
            "PAC round-trip import failed: submesh count mismatch. "
            "Keep the same object structure when editing OBJ."
        )

    if _pac_needs_full_rebuild(original_mesh, working_mesh):
        return _build_pac_full_rebuild(original_mesh, working_mesh, original_data)
    return _build_pac_in_place(original_mesh, working_mesh, original_data)


class IncrementalPACBuilder:
    """
    基于原始 PAC 的增量构建器（Round-trip 模式）。
    对外接口保持不变，内部使用新的 build_pac。
    """
    def __init__(self, original_pac_path: str):
        with open(original_pac_path, "rb") as f:
            self.original_data = f.read()
        self.original_mesh = parse_pac(self.original_data, original_pac_path)

    def apply_vertex_transform(self, transform_func):
        """
        对每个顶点应用变换：
        transform_func(sm_idx, vi, (x,y,z)) -> (x',y',z')
        并在变换后重新计算每个子网格的 bounding box，
        避免新顶点超出原始 bbox 被量化截断。
        """
        for sm_idx, sm in enumerate(self.original_mesh.submeshes):
            for vi in range(len(sm.vertices)):
                orig_v = sm.vertices[vi]
                new_v = transform_func(sm_idx, vi, orig_v)
                sm.vertices[vi] = new_v

            # 重新计算 bbox
            bmin, bmax = compute_bbox(sm.vertices)
            extent = (
                bmax[0] - bmin[0],
                bmax[1] - bmin[1],
                bmax[2] - bmin[2],
            )
            # 防止零长度
            for i in range(3):
                if extent[i] < 1e-6:
                    # 对称扩展一点
                    center = bmin[i]
                    extent_i = 0.1
                    bmin = list(bmin); bmax = list(bmax)
                    bmin[i] = center - extent_i / 2
                    bmax[i] = center + extent_i / 2
                    extent = list(extent)
                    extent[i] = extent_i
                    bmin = tuple(bmin); bmax = tuple(bmax); extent = tuple(extent)

            sm.source_bbox_min = bmin
            sm.source_bbox_extent = extent

    def build(self, mesh: ParsedMesh = None) -> bytes:
        """
        使用 Round-trip 逻辑重建 PAC。
        如果提供 mesh，则使用该 mesh；否则使用内部修改后的 original_mesh。
        """
        target = mesh or self.original_mesh
        return build_pac(target, self.original_data)


def export_obj_with_metadata(obj_path: str,
                            output_dir: str,
                            mesh_name: str = "modified",
                            material_name: str = "material_0") -> Dict:
    obj_path = Path(obj_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    vertices = []
    uvs = []
    normals = []
    faces = []

    with open(obj_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if not parts:
                continue
            if parts[0] == 'v' and len(parts) >= 4:
                vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif parts[0] == 'vt' and len(parts) >= 3:
                u, v = float(parts[1]), float(parts[2])
                uvs.append((u, v))
            elif parts[0] == 'vn' and len(parts) >= 4:
                normals.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif parts[0] == 'f' and len(parts) >= 4:
                face_verts = []
                for fp in parts[1:]:
                    indices = fp.split('/')
                    vi = int(indices[0]) - 1
                    face_verts.append(vi)
                for i in range(1, len(face_verts) - 1):
                    faces.append((face_verts[0], face_verts[i], face_verts[i+1]))

    metadata = {
        "format": "mesh_roundtrip_manifest_v2",
        "source_path": str(obj_path),
        "source_format": "obj",
        "export_path": "mesh.obj",
        "companion_filename": "mesh.mtl",
        "exported_utc": __import__('datetime').datetime.utcnow().isoformat() + "Z",
        "roundtrip_policy": {
            "primary_workflow": "obj_first",
            "default_import_policy": "auto-fix safe, warn risky"
        },
        "submeshes": [
            {
                "index": 0,
                "name": mesh_name,
                "material": material_name,
                "texture": "",
                "vertex_count": len(vertices),
                "face_count": len(faces),
                "source_vertex_map": list(range(len(vertices)))
            }
        ]
    }

    meta_path = output_dir / "mesh.obj.meta.json"
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    return {
        'vertices': vertices,
        'uvs': uvs if uvs else [(0, 0) for _ in vertices],
        'normals': normals if normals else [(0, 1, 0) for _ in vertices],
        'faces': faces,
        'metadata': metadata,
        'metadata_path': str(meta_path)
    }


def dump_pac_header(pac_path: str, max_bytes: int = 256):
    with open(pac_path, "rb") as f:
        data = f.read()

    print(f"File size: {len(data)}")

    for base in range(0, min(max_bytes, len(data)), 16):
        hex_part = " ".join(f"{b:02X}" for b in data[base:base+16])
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in data[base:base+16])
        print(f"{base:06X}  {hex_part:<48s}  {ascii_part}")

    magic = data[0:4]
    print(f"\nMagic: {magic}")

    if len(data) >= 8:
        version = struct.unpack_from("<I", data, 4)[0]
        print(f"Version (0x4): 0x{version:08X}")

    if len(data) >= 80:
        sizes = []
        for i in range(16):
            off = 16 + i * 4
            sz = struct.unpack_from("<I", data, off)[0]
            sizes.append(sz)
        print(f"Section sizes (offset 16..79): {sizes}")

        off = 80
        offsets = []
        for sz in sizes:
            offsets.append(off)
            off += sz if sz > 0 else 0
        print(f"Section offsets (start=80, sequential): {offsets}")

        for i in range(16):
            if i < len(sizes):
                print(f"Sec {i}: size={sizes[i]}, offset={offsets[i]}")


