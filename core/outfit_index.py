"""
Body Slider Pro - Outfit 索引重建模块

职责：
- 根据 exported_outfit/{char_id}/ 目录中的实际文件结构，从头重建 outfit_index.json
- 备份原有索引为 .bak 文件
- 使用 "app_version" 字段存储当前程序版本号（来自 core/version.txt）

索引结构：
{
  "app_version": "x.y.z",
  "target_body_folders": {
    "target_mesh/{char_id}/{slider_name}.obj": "exported_outfit/{char_id}/{slider_name}",
    ...
  },
  "outfits": {
    "original_outfit 中文件的相对路径": [
      "exported_outfit/{char_id}/{slider_name}/...",
      ...
    ],
    ...
  }
}
"""

import json
import logging
import os
import shutil
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

INDEX_FILENAME = "outfit_index.json"


def read_app_version(root_dir: str) -> str:
    """
    从 core/version.txt 读取程序版本号。
    """
    path = os.path.join(root_dir, "core", "version.txt")
    try:
        with open(path, "r", encoding="utf-8") as f:
            v = f.read().strip()
            if v:
                return v
    except Exception:
        pass
    return "0.0.0"


def _normalize_path(p: str) -> str:
    """
    规范化路径：统一使用正斜杠。
    """
    if not p:
        return p
    return p.replace("\\", "/")


def rebuild_outfit_index(root_dir: str, char_id: str) -> Optional[Dict]:
    """
    根据文件系统重建 exported_outfit/{char_id}/outfit_index.json。

    流程：
    1. 备份原有 outfit_index.json 为 .bak
    2. 扫描 target_mesh/{char_id}/ 目录，获取所有滑块目标文件
    3. 扫描 exported_outfit/{char_id}/ 目录，重建 target_body_folders 和 outfits 映射
    4. 写入新的 outfit_index.json

    返回重建后的索引字典，失败返回 None。
    """
    root_dir = os.path.abspath(root_dir)
    
    # 关键路径
    exported_outfit_dir = os.path.join(root_dir, "exported_outfit", char_id)
    original_outfit_dir = os.path.join(root_dir, "original_outfit", char_id)
    target_mesh_dir = os.path.join(root_dir, "target_mesh", char_id)
    index_path = os.path.join(exported_outfit_dir, INDEX_FILENAME)
    bak_path = index_path + ".bak"

    # 确保 exported_outfit 目录存在
    if not os.path.isdir(exported_outfit_dir):
        logger.warning("exported_outfit dir does not exist: %s", exported_outfit_dir)
        return None

    # ---- 备份原有索引 ----
    if os.path.exists(index_path):
        try:
            shutil.copy2(index_path, bak_path)
            logger.info("Backed up outfit_index.json to .bak")
        except Exception as e:
            logger.warning("Failed to backup outfit_index.json: %s", e)

    # ---- 初始化新索引 ----
    new_index: Dict = {
        "app_version": read_app_version(root_dir),
        "target_body_folders": {},
        "outfits": {},
    }

    # ---- 1) 构建 target_body_folders 映射 ----
    # 扫描 exported_outfit/{char_id}/ 下的一级目录，每个目录名对应一个滑块
    # 然后在 target_mesh/{char_id}/ 中寻找对应的目标文件
    try:
        for first_level_name in os.listdir(exported_outfit_dir):
            first_level_path = os.path.join(exported_outfit_dir, first_level_name)
            if not os.path.isdir(first_level_path):
                continue

            # 在 target_mesh/{char_id}/ 中寻找匹配的文件
            # 文件名可能是 {first_level_name}.obj 或 {first_level_name}.pac
            tb_file_found = None
            tb_file_abs = os.path.join(target_mesh_dir, first_level_name)
            
            if os.path.isfile(tb_file_abs):
                tb_file_found = tb_file_abs
            else:
                for ext in (".obj", ".pac"):
                    candidate = tb_file_abs + ext
                    if os.path.isfile(candidate):
                        tb_file_found = candidate
                        break

            if tb_file_found:
                target_body_file_rel = _normalize_path(
                    os.path.relpath(tb_file_found, root_dir)
                )
                output_folder_rel = _normalize_path(
                    os.path.relpath(first_level_path, root_dir)
                )
                new_index["target_body_folders"][target_body_file_rel] = output_folder_rel
    except Exception as e:
        logger.error("Error scanning target_body_folders: %s", e, exc_info=True)

    # ---- 2) 构建 outfits 映射 ----
    # 扫描 exported_outfit/{char_id}/{slider_name}/ 下的所有 .obj/.pac 文件
    # 对于每个导出文件，尝试在 original_outfit/{char_id}/ 中找到对应的原始文件
    # 建立 original_rel -> [exported_rel, ...] 的映射
    try:
        for root, dirs, files in os.walk(exported_outfit_dir):
            # 跳过索引文件本身
            outfit_files = []
            for fname in files:
                if not fname.lower().endswith((".obj", ".pac")):
                    continue
                if fname.lower() == INDEX_FILENAME.lower():
                    continue
                outfit_files.append(fname)

            # 处理每个 outfit 文件
            for fname in outfit_files:
                fpath = os.path.join(root, fname)
                rel_from_exported = os.path.relpath(fpath, exported_outfit_dir)
                rel_parts = rel_from_exported.replace("\\", "/").split("/")

                if len(rel_parts) < 2:
                    continue

                # rel_parts[0] 是 slider_name, rel_parts[1:] 是 outfit 文件的相对路径
                outfit_rel = _normalize_path("/".join(rel_parts[1:]))

                # 在 original_outfit 中寻找对应的原始文件（不考虑扩展名）
                orig_base, _ = os.path.splitext(outfit_rel)
                orig_found = False
                original_outfit_rel = None

                for orig_ext in (".pac", ".obj"):
                    candidate_rel = orig_base + orig_ext
                    orig_candidate = os.path.join(original_outfit_dir, candidate_rel)
                    if os.path.isfile(orig_candidate):
                        orig_found = True
                        original_outfit_rel = _normalize_path(candidate_rel)
                        break

                if not orig_found:
                    # original_outfit 中没有对应文件，跳过
                    continue

                # 计算导出文件的相对于 root_dir 的路径
                exported_rel = _normalize_path(os.path.relpath(fpath, root_dir))

                # 添加到 outfits 映射
                if original_outfit_rel not in new_index["outfits"]:
                    new_index["outfits"][original_outfit_rel] = []
                
                if exported_rel not in new_index["outfits"][original_outfit_rel]:
                    new_index["outfits"][original_outfit_rel].append(exported_rel)

    except Exception as e:
        logger.error("Error scanning outfits: %s", e, exc_info=True)

    # ---- 3) 写入新索引 ----
    try:
        os.makedirs(os.path.dirname(index_path) or ".", exist_ok=True)
        with open(index_path, "w", encoding="utf-8-sig") as f:
            json.dump(new_index, f, ensure_ascii=False, indent=2)
        logger.info("Rebuilt outfit_index.json for char_id=%s", char_id)
    except Exception as e:
        # 写入失败时尝试恢复备份
        if os.path.exists(bak_path):
            try:
                shutil.copy2(bak_path, index_path)
                logger.error("Failed to save outfit_index.json, restored from backup")
            except Exception:
                pass
        logger.error("Failed to write outfit_index.json: %s", e, exc_info=True)
        return None

    return new_index


def rebuild_outfit_indices_for_chars(root_dir: str, char_ids: List[str]) -> Dict[str, bool]:
    """
    为多个角色批量重建 outfit 索引。

    返回 {char_id: success_bool} 字典。
    """
    results = {}
    for cid in char_ids:
        try:
            result = rebuild_outfit_index(root_dir, cid)
            results[cid] = result is not None
        except Exception as e:
            logger.error("Failed to rebuild outfit index for %s: %s", cid, e, exc_info=True)
            results[cid] = False
    return results