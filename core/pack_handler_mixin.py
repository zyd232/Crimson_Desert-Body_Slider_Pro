"""
PackHandlerMixin:
Handles:
- loading overlay helpers
- character pack export
- character pack import
- on_character_pack_imported callback
- save_model_pac_and_mod (MOD export)

Integrated from:
- body_slider_func.py
- char_pack_export.py
- char_pack_import.py
- pack_handler_mixin.py (previous stub)
"""

import os
import json
import shutil
import zipfile
import tempfile
from typing import Dict, Any, List, Tuple, Set

from core.zip_utils import extract_zip, read_zip_string, create_zip

from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QApplication,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject

from core.ui_components import (
    LoadingOverlay,
    show_critical,
    show_info,
    show_warning,
    show_question,
    show_choice,
    DarkMessageBox,
    CharacterPackSelectDialog,
    CharacterPackLoadDialog,
    PackConflictResolveDialog,
    ModRenameDialog,
    ImportOverwriteSelectDialog,
    ImportRenameCharDialog,
    SliderMergeDialog,
    ExportProgressDialog,
)
from core.ui_dialogs_import_pack import (
    OutfitMergeDialog,
    OutfitImportChoiceDialog,
    MeshMismatchDialog,
)
from core.pack_import_handler import (
    has_outfit_data,
    compare_mesh_data,
    find_outfit_duplicates,
    copy_outfit_files,
    apply_outfit_merge_choices,
    overwrite_outfit_data,
)
from core.outfit_index import rebuild_outfit_index


class ZipExtractWorker(QObject):
    """Worker for extracting ZIP files in a background thread."""
    finished = pyqtSignal(str)  # error_message (empty string = success)

    def __init__(self, zip_path: str, temp_dir: str, long_path_callback):
        super().__init__()
        self.zip_path = zip_path
        self.temp_dir = temp_dir
        self.long_path_callback = long_path_callback

    def run(self):
        try:
            extract_zip(
                self.zip_path,
                self.temp_dir,
                long_path_callback=self.long_path_callback,
            )
            self.finished.emit("")
        except zipfile.BadZipFile:
            self.finished.emit("Invalid ZIP file.")
        except Exception as e:
            self.finished.emit(str(e))


class PackHandlerMixin:
    """
    Mixin for BodySlider.
    Expects: self.T, self.characters, self.root_dir, self.char_config_dir, self.app_version,
             plus UI/config helpers on the host class.
    """

    # ---------- loading helpers ----------

    def _show_loading(self, text: str = "Loading..."):
        return LoadingOverlay(self, text)

    def _hide_loading(self, overlay, on_ready_callback=None):
        if not overlay:
            return
        try:
            overlay.close(on_ready_callback)
        except Exception:
            pass

    # ---------- export character pack ----------

    def export_character_pack(self):
        if not self.characters:
            show_info(
                self,
                self.T.get("msg_error", "Error"),
                self.T.get("pack_empty_char_error", "No character data to export."),
            )
            return

        dlg = CharacterPackSelectDialog(
            characters=self.characters,
            active_char_id=getattr(self, "active_char_id", None),
            T=self.T,
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        selected_ids = dlg.get_selected_ids()
        if not selected_ids:
            return

        # Step 2: Check which selected characters have outfit data
        # and show outfit selection dialog if any do
        characters_with_outfit = []
        for cid in selected_ids:
            original_outfit_dir = os.path.join(self.root_dir, "original_outfit", cid)
            if os.path.isdir(original_outfit_dir):
                try:
                    for _, _, files in os.walk(original_outfit_dir):
                        if files:
                            characters_with_outfit.append(cid)
                            break
                except OSError:
                    pass

        outfit_char_ids: List[str] = []
        if characters_with_outfit:
            from core.ui_dialogs import OutfitSelectDialog
            outfit_dlg = OutfitSelectDialog(
                characters_with_outfit=characters_with_outfit,
                T=self.T,
                root_dir=self.root_dir,
                parent=self,
            )
            if outfit_dlg.exec() != QDialog.DialogCode.Accepted:
                return
            outfit_char_ids = outfit_dlg.get_selected_ids()

        if len(selected_ids) == 1:
            default_name = f"{selected_ids[0]}_character_pack.zip"
        else:
            default_name = "multi_character_pack.zip"

        out_path, _ = QFileDialog.getSaveFileName(
            self,
            self.T.get("pack_save_title", "Save Character Pack"),
            default_name,
            self.T.get("pack_file_filter", "ZIP Files (*.zip)"),
        )
        if not out_path:
            return

        if not out_path.lower().endswith(".zip"):
            out_path += ".zip"

        # Collect all files to be compressed
        file_list: List[Tuple[str, str]] = []  # (src_path, arc_path)

        for char_id in selected_ids:
            config_path = os.path.join(self.char_config_dir, f"{char_id}.json")
            if not os.path.exists(config_path):
                continue

            original_dir = self.cm.char_original_mesh_dir(char_id)
            target_dir = self.cm.char_target_mesh_dir(char_id)

            # char_config
            file_list.append((config_path, f"char_config/{char_id}.json"))

            # original_mesh
            if os.path.isdir(original_dir):
                for dirpath, _, filenames in os.walk(original_dir):
                    for fn in filenames:
                        src = os.path.join(dirpath, fn)
                        rel = os.path.relpath(src, self.root_dir)
                        rel = self._norm_path(rel)
                        arc = rel.replace("\\", "/")
                        file_list.append((src, arc))

            # target_mesh
            if os.path.isdir(target_dir):
                for dirpath, _, filenames in os.walk(target_dir):
                    for fn in filenames:
                        src = os.path.join(dirpath, fn)
                        rel = os.path.relpath(src, self.root_dir)
                        rel = self._norm_path(rel)
                        arc = rel.replace("\\", "/")
                        file_list.append((src, arc))

            # outfit data
            if char_id in outfit_char_ids:
                for outfit_dir_name in ("original_outfit", "exported_outfit"):
                    outfit_char_dir = os.path.join(self.root_dir, outfit_dir_name, char_id)
                    if os.path.isdir(outfit_char_dir):
                        for dirpath, _, filenames in os.walk(outfit_char_dir):
                            for fn in filenames:
                                src = os.path.join(dirpath, fn)
                                rel = os.path.relpath(src, self.root_dir)
                                rel = self._norm_path(rel)
                                arc = rel.replace("\\", "/")
                                file_list.append((src, arc))

        # Write pack_info.json to a temp file so it can be included in the ZIP
        pack_info_tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        entries = [fp for _, fp in file_list]
        pack_info = {
            "app_version": self.app_version,
            "character_ids": selected_ids,
            "entries": entries,
        }
        json.dump(pack_info, pack_info_tmp, indent=2, ensure_ascii=False)
        pack_info_tmp.flush()
        pack_info_path = pack_info_tmp.name
        pack_info_tmp.close()

        # Add pack_info.json to the file list
        full_file_list = list(file_list) + [(pack_info_path, "pack_info.json")]

        # Show progress dialog
        progress = ExportProgressDialog(self.T, self)
        progress.set_total(len(full_file_list))
        progress.set_status(self.T.get("export_progress_status_compressing", "Compressing files..."))
        progress.show()
        QApplication.processEvents()

        def _progress_cb(current, total, filename):
            progress.advance_file(filename)
            QApplication.processEvents()

        try:
            # Use create_zip which auto-selects Zstd (Method 93) when available
            create_zip(
                output_path=out_path,
                file_list=full_file_list,
                progress_callback=_progress_cb,
                use_zstd=True,
                zstd_level=3,
            )

            progress.set_status(self.T.get("export_progress_status_finale", "Finalizing archive..."))
            progress.mark_complete(output_path=out_path)
            QApplication.processEvents()
            progress.exec()
        except Exception as e:
            progress.close()
            show_critical(
                self,
                self.T.get("export_error_title", "Export Failed"),
                self.T.get("export_error_msg", "Error exporting character pack: {error}").format(error=str(e)),
            )
        finally:
            # Clean up temp pack_info.json
            if os.path.exists(pack_info_path):
                try:
                    os.unlink(pack_info_path)
                except Exception:
                    pass

    # ---------- import character pack (with merge support) ----------

    def import_character_pack(self):
        # 读取角色包前：保存镜头并写入 config.json
        self._save_camera_and_config()

        # 在 load_config() 之前保存当前镜头和 wireframe 状态（内存中）
        viewer = self._plotter
        saved_camera = None
        saved_wireframe_enabled = bool(getattr(viewer, "_wireframe_enabled", False)) if viewer else False
        if viewer is not None:
            cam = self._get_camera_position()
            if cam:
                saved_camera = cam

        zip_path, _ = QFileDialog.getOpenFileName(
            self,
            self.T.get("pack_load_title", "Load Character Pack"),
            "",
            self.T.get("pack_file_filter", "ZIP Files (*.zip)"),
        )
        if not zip_path:
            return

        # Step 1: Read pack_info.json
        pack_info = None
        pack_char_ids: List[str] = []
        pack_char_names: Dict[str, str] = {}
        pack_version = "0.0.0"
        pack_type = "app"  # "app" or "outfitter"
        pack_outfit_char_ids: Set[str] = set()  # chars with outfit data in ZIP

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                try:
                    info_bytes = read_zip_string(zip_path, zf, "pack_info.json")
                except KeyError:
                    show_info(
                        self,
                        self.T.get("msg_error", "Error"),
                        self.T.get("pack_invalid_file_error", "Invalid character pack file."),
                    )
                    return

                # Use utf-8-sig to handle BOM (common on Windows)
                try:
                    pack_info = json.loads(info_bytes.decode("utf-8-sig"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    pack_info = json.loads(
                        info_bytes.decode("utf-8", errors="ignore")
                    )

                # Determine pack type: outfitter pack has BOTH original_outfit AND exported_outfit directories
                has_original_outfit = any(info.filename.startswith("original_outfit/") for info in zf.infolist())
                has_exported_outfit = any(info.filename.startswith("exported_outfit/") for info in zf.infolist())

                if has_original_outfit and has_exported_outfit:
                    pack_type = "outfitter"
                else:
                    pack_type = "app"

                pack_version = str(pack_info.get("app_version", "0.0.0"))

                char_ids = pack_info.get("character_ids", None)
                if isinstance(char_ids, list) and len(char_ids) > 0:
                    pack_char_ids = [str(c) for c in char_ids]
                else:
                    legacy_id = str(pack_info.get("character_id", ""))
                    if legacy_id:
                        pack_char_ids = [legacy_id]
                    else:
                        show_info(
                            self,
                            self.T.get("msg_error", "Error"),
                            self.T.get("pack_invalid_file_error", "Invalid character pack file."),
                        )
                        return

                per_char_infos = pack_info.get("characters", {})
                if isinstance(per_char_infos, dict):
                    for cid, cinfo in per_char_infos.items():
                        if isinstance(cinfo, dict):
                            pack_char_names[cid] = cinfo.get("name", cid)
                        else:
                            pack_char_names[cid] = str(cid)
                for cid in pack_char_ids:
                    pack_char_names.setdefault(cid, cid)

                # Check which characters have outfit data in the ZIP
                # (original_outfit/{char_id}/ or exported_outfit/{char_id}/)
                all_filenames = {info.filename for info in zf.infolist()}
                for cid in pack_char_ids:
                    has_original_outfit = any(
                        fn.startswith(f"original_outfit/{cid}/") for fn in all_filenames
                    )
                    has_exported_outfit = any(
                        fn.startswith(f"exported_outfit/{cid}/") for fn in all_filenames
                    )
                    if has_original_outfit or has_exported_outfit:
                        pack_outfit_char_ids.add(cid)

        except Exception as e:
            import traceback
            tb_text = traceback.format_exc()
            # Print full traceback to console for debugging
            print("=== pack_info read error ===")
            print(tb_text)
            # Show a concise but real error instead of a generic message
            err_short = str(e).split("\n")[0]
            show_critical(
                self,
                self.T.get("msg_error", "Error"),
                self.T.get("pack_import_error", "Failed to import character pack: {error}").format(error=err_short),
            )
            return

        # Step 2: Version warning (only for app-type packs)
        if pack_type == "app":
            pack_ver_tuple = self._parse_version(pack_version)
            app_ver_tuple = self._parse_version(self.app_version)
            if pack_ver_tuple > app_ver_tuple:
                msg = self.T.get(
                    "pack_version_warn_msg",
                    "The pack's version ({pack_ver}) is higher than the current app version ({app_ver}). "
                    "There may be incompatibilities.\n\nDo you want to continue importing?",
                ).format(pack_ver=pack_version, app_ver=self.app_version)
                title = self.T.get("pack_version_warn_title", "Version Mismatch Warning")
                if not show_question(self, title, msg):
                    return

        # Step 3: Show character selection dialog
        existing_ids = set(self.characters.keys())
        load_dialog = CharacterPackLoadDialog(
            pack_char_ids=pack_char_ids,
            pack_char_names=pack_char_names,
            existing_char_ids=existing_ids,
            T=self.T,
            parent=self,
            pack_outfit_char_ids=pack_outfit_char_ids,
        )
        if load_dialog.exec() != 1:
            return

        selected_ids = load_dialog.get_selected_ids()
        if not selected_ids:
            return

        # Classify selected characters
        duplicates = [cid for cid in selected_ids if cid in existing_ids]
        new_ids = [cid for cid in selected_ids if cid not in existing_ids]

        # Step 4: Classify duplicate characters by outfit status
        # ========================================
        # Flow:
        # - Pack has no outfit data -> ImportOverwriteSelectDialog (existing logic)
        # - Pack has outfit, existing has no outfit -> direct overwrite
        # - Pack has outfit, existing has outfit -> outfit_choice_pending (new flow)
        # ========================================
        overwrite_ids: Set[str] = set()
        merge_ids: List[str] = []
        outfit_choice_pending_ids: List[str] = []  # Both have outfit, need outfit-aware flow

        if duplicates:
            # First, classify each duplicate
            dialog_candidates: List[str] = []  # chars that go to ImportOverwriteSelectDialog
            direct_overwrite: Set[str] = set()  # pack has outfit, existing doesn't
            outfit_conflict: List[str] = []  # both have outfit data

            for cid in duplicates:
                pack_has_outfit = cid in pack_outfit_char_ids
                existing_has_outfit = has_outfit_data(self.root_dir, cid)

                if not pack_has_outfit and not existing_has_outfit:
                    # Neither has outfit -> show dialog
                    dialog_candidates.append(cid)
                elif pack_has_outfit and not existing_has_outfit:
                    # Pack has outfit, existing doesn't -> direct overwrite
                    direct_overwrite.add(cid)
                elif not pack_has_outfit and existing_has_outfit:
                    # Existing has outfit, pack doesn't -> show dialog (slider merge only)
                    dialog_candidates.append(cid)
                else:
                    # Both have outfit -> outfit-aware flow
                    outfit_conflict.append(cid)

            outfit_choice_pending_ids = outfit_conflict
            overwrite_ids = set(direct_overwrite)

            # Only show ImportOverwriteSelectDialog for chars without outfit conflicts
            if dialog_candidates:
                # Also check if outfitter pack shortcut applies to dialog candidates
                all_dialog_have_outfit = all(
                    cid in pack_outfit_char_ids for cid in dialog_candidates
                )
                if pack_type == "outfitter" and all_dialog_have_outfit:
                    overwrite_ids.update(dialog_candidates)
                else:
                    dup_info_list: List[Dict[str, str]] = []
                    for cid in dialog_candidates:
                        ex_char = self.characters.get(cid, {})
                        dup_info_list.append({
                            "char_id": cid,
                            "pack_name": pack_char_names.get(cid, cid),
                            "existing_name": ex_char.get("name", cid),
                        })

                    dlg = ImportOverwriteSelectDialog(
                        duplicate_chars=dup_info_list,
                        T=self.T,
                        parent=self,
                    )
                    if dlg.exec() != 1:
                        return
                    dlg_overwrite_ids = dlg.get_overwrite_ids()
                    overwrite_ids.update(dlg_overwrite_ids)
                    merge_ids = [cid for cid in dialog_candidates if cid not in dlg_overwrite_ids]

        # Step 5: Prepare temp directory for extraction
        try:
            drive = os.path.splitdrive(os.path.abspath(self.root_dir))[0] or "C:\\"
        except Exception:
            drive = "C:\\"

        # Use a minimal base path to leave more room for long file paths
        temp_dir = os.path.join(drive, "bs")
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
        os.makedirs(temp_dir, exist_ok=True)

        # Helper to get a long-path-safe absolute path on Windows
        def long_path(p: str) -> str:
            ap = os.path.abspath(p)
            # Use NT-style prefix to bypass 260-char limit
            if len(ap) > 150:
                return "\\\\?\\" + ap
            return ap

        # --- Show loading BEFORE ZIP extraction ---
        # Extract ZIP in a background thread so the loading overlay renders immediately.
        extract_loading = self._show_loading(
            self.T.get("pack_loading_text", "Loading character pack...")
        )
        QApplication.processEvents()

        # Store as instance attributes to prevent garbage collection while thread is running
        self._extract_thread = QThread()
        self._extract_worker = ZipExtractWorker(zip_path, temp_dir, long_path)
        self._extract_worker.moveToThread(self._extract_thread)

        def on_extract_finished(error_msg: str):
            self._hide_loading(extract_loading)
            self._extract_thread.quit()
            self._extract_thread.wait()
            self._extract_thread.deleteLater()
            self._extract_worker.deleteLater()
            # Clear references after cleanup
            self._extract_thread = None
            self._extract_worker = None

            if error_msg:
                full_msg = self.T.get(
                    "pack_read_error",
                    "Failed to read character pack: {error}",
                ).format(error=str(error_msg))
                import traceback
                traceback.print_exc()
                show_critical(self, self.T.get("msg_error", "Error"), full_msg)
                if os.path.exists(temp_dir):
                    try:
                        shutil.rmtree(temp_dir)
                    except Exception:
                        pass
                return

            # --- Continue with post-extraction flow ---
            self._continue_pack_import(
                selected_ids, pack_char_configs={}, pack_char_sliders={},
                temp_dir=temp_dir, pack_char_names=pack_char_names,
                merge_ids=merge_ids, new_ids=new_ids, overwrite_ids=overwrite_ids,
                outfit_choice_pending_ids=outfit_choice_pending_ids,
                pack_type=pack_type, saved_camera=saved_camera,
                saved_wireframe_enabled=saved_wireframe_enabled,
            )

        self._extract_worker.finished.connect(on_extract_finished)
        self._extract_thread.started.connect(self._extract_worker.run)
        self._extract_thread.start()

    # ---------- continue pack import after ZIP extraction ----------

    def _continue_pack_import(
        self,
        selected_ids,
        pack_char_configs,
        pack_char_sliders,
        temp_dir,
        pack_char_names,
        merge_ids,
        new_ids,
        overwrite_ids,
        outfit_choice_pending_ids,
        pack_type,
        saved_camera,
        saved_wireframe_enabled,
    ):
        """Continue pack import flow after ZIP extraction completes."""
        root_dir = self.root_dir
        char_config_dir = self.char_config_dir
        T = self.T

        # Build pack char configs from extracted files
        pack_char_configs: Dict[str, Dict[str, Any]] = {}
        pack_char_sliders: Dict[str, Dict[str, Any]] = {}
        for cid in selected_ids:
            cfg_path = os.path.join(temp_dir, "char_config", f"{cid}.json")
            sliders_cfg: Dict[str, Any] = {}
            if os.path.exists(cfg_path):
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    pack_char_configs[cid] = data
                    sliders_cfg = data.get("sliders", {}) or {}
                except Exception:
                    pack_char_configs[cid] = {}
            pack_char_sliders[cid] = sliders_cfg

        # ================================================================
        # NEW OUTFIT-AWARE IMPORT FLOW
        # ================================================================
        # For each existing character with outfit data in pack, apply new logic:
        # 1. Compare mesh files (original_mesh + target_mesh)
        # 2. If meshes differ -> warn user, delete & import on confirmation
        # 3. If meshes match -> ask: overwrite outfits or merge outfits
        # 4. If merge -> check for file duplicates, show merge dialog if needed
        # ================================================================

        # Classify characters by outfit handling strategy
        # outfit_overwrite_ids: chars that will do full overwrite (including outfits)
        # outfit_merge_ids: chars that need outfit merge logic
        # outfit_mesh_mismatch_ids: chars with mesh mismatch needing user confirmation
        outfit_overwrite_ids: Set[str] = set(overwrite_ids)
        outfit_merge_ids: List[str] = []
        outfit_mesh_mismatch_ids: List[str] = []

        for cid in selected_ids:
            if cid in overwrite_ids:
                continue
            if cid not in self.characters:
                continue  # New char, no conflict

            # Check if pack has outfit data for this char
            pack_has_outfit = (
                os.path.isdir(os.path.join(temp_dir, "original_outfit", cid)) or
                os.path.isdir(os.path.join(temp_dir, "exported_outfit", cid))
            )
            existing_has_outfit = has_outfit_data(root_dir, cid)

            if not pack_has_outfit and not existing_has_outfit:
                # Neither has outfit - use original merge/overwrite flow
                continue
            if pack_has_outfit and not existing_has_outfit:
                # Pack has outfit, existing doesn't -> overwrite
                outfit_overwrite_ids.add(cid)
                continue
            if not pack_has_outfit and existing_has_outfit:
                # Existing has outfit, pack doesn't -> merge sliders only
                continue

            # Both have outfit data - compare mesh files
            meshes_match, diff_details = compare_mesh_data(temp_dir, root_dir, cid)
            if not meshes_match:
                outfit_mesh_mismatch_ids.append(cid)
            else:
                outfit_merge_ids.append(cid)

        # Handle mesh mismatch cases
        for cid in outfit_mesh_mismatch_ids:
            diff_msg = T.get(
                "mesh_mismatch_msg",
                "The character model files in the imported pack differ from your existing model files.\n\n{details}\n\nYou must delete the existing character data before importing the new data.",
            ).format(details=diff_details)
            title = T.get("mesh_mismatch_title", "Model Mismatch Detected")

            pack_cfg = pack_char_configs.get(cid, {})
            pack_char_name = pack_char_names.get(cid, pack_cfg.get("character", {}).get("name", cid))
            dlg = MeshMismatchDialog(
                char_name=pack_char_name,
                diff_summary=diff_details,
                T=T,
                parent=self,
            )
            if dlg.exec() != 1:
                # User canceled -> abort
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                return
            # User confirmed -> move to overwrite
            outfit_overwrite_ids.add(cid)

        # Handle outfit choice cases (overwrite vs merge)
        for cid in outfit_merge_ids:
            pack_cfg = pack_char_configs.get(cid, {})
            pack_char_name = pack_char_names.get(cid, pack_cfg.get("character", {}).get("name", cid))
            dlg = OutfitImportChoiceDialog(
                char_name=pack_char_name,
                T=T,
                parent=self,
            )
            if dlg.exec() != 1:
                # User canceled -> abort
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                return
            if dlg.choice() == "overwrite":
                outfit_overwrite_ids.add(cid)
            # else: stays in merge flow

        # Now handle outfit merge characters - check for file duplicates
        outfit_merge_results: Dict[str, Dict[str, Any]] = {}
        for cid in outfit_merge_ids:
            if cid in outfit_overwrite_ids:
                continue  # User chose overwrite

            dup_groups, unique_files = find_outfit_duplicates(temp_dir, root_dir, cid)

            if dup_groups:
                # Show merge dialog for duplicates
                dlg = OutfitMergeDialog(
                    duplicate_groups=dup_groups,
                    T=T,
                    parent=self,
                )
                if dlg.exec() != 1:
                    # User canceled -> abort
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                    return
                choices = dlg.get_choices()
                outfit_merge_results[cid] = {
                    "choices": choices,
                    "unique_files": unique_files,
                    "dup_groups": dup_groups,
                }
            else:
                # No duplicates - just copy unique files + merge index
                outfit_merge_results[cid] = {
                    "choices": {},
                    "unique_files": unique_files,
                    "dup_groups": [],
                }

        # ================================================================
        # END NEW OUTFIT-AWARE IMPORT FLOW
        # ================================================================

        # For merge_ids (slider merge), if incompatible original_mesh, require rename
        rename_map: Dict[str, str] = {}  # old_cid -> new_cid

        for cid in merge_ids:
            ex_char = self.characters.get(cid, {})
            pack_cfg = pack_char_configs.get(cid, {})
            pack_char = pack_cfg.get("character", {})

            ex_pac = ex_char.get("original_pac_path", "") or ""
            new_pac = pack_char.get("original_pac_path", "") or ""

            # Normalize to absolute paths
            if new_pac and not os.path.isabs(new_pac):
                new_pac = os.path.abspath(os.path.join(self.root_dir, new_pac))

            # Simple heuristic: if both have PAC and their filenames differ, consider incompatible
            if ex_pac and new_pac:
                ex_base = os.path.basename(ex_pac)
                new_base = os.path.basename(new_pac)
                if ex_base != new_base:
                    # Incompatible -> force rename
                    dlg = ImportRenameCharDialog(
                        original_id=cid,
                        existing_ids=set(list(self.characters.keys()) + list(rename_map.values())),
                        T=self.T,
                        parent=self,
                    )
                    if dlg.exec() != 1:
                        # User canceled -> abort entire import
                        if os.path.exists(temp_dir):
                            shutil.rmtree(temp_dir)
                        return
                    new_cid = dlg.get_new_id()
                    if not new_cid:
                        if os.path.exists(temp_dir):
                            shutil.rmtree(temp_dir)
                        return
                    rename_map[cid] = new_cid
                    continue

        def get_effective_cid(cid: str) -> str:
            return rename_map.get(cid, cid)

        # Step 6: For merge_ids, show SliderMergeDialog
        merge_choices_map: Dict[str, Dict[str, Any]] = {}
        if merge_ids:
            merge_chars_data: List[Dict[str, Any]] = []

            for cid in merge_ids:
                effective_cid = get_effective_cid(cid)
                ex_char = self.characters.get(cid, {})
                pack_cfg = pack_char_configs.get(cid, {})
                pack_char = pack_cfg.get("character", {})
                ex_sliders_cfg = self.character_sliders.get(cid, {}) or {}
                new_sliders_cfg = pack_char_sliders.get(cid, {}) or {}

                # Build conflict groups
                conflict_groups: List[Dict[str, Any]] = []
                new_only_sliders: List[Dict[str, Any]] = []

                all_local_ids = set(list(ex_sliders_cfg.keys()) + list(new_sliders_cfg.keys()))
                for lid in all_local_ids:
                    ex = ex_sliders_cfg.get(lid)
                    nw = new_sliders_cfg.get(lid)
                    if isinstance(ex, dict) and isinstance(nw, dict):
                        # conflict
                        conflict_groups.append({
                            "slider_local_id": lid,
                            "existing_slider": ex,
                            "new_slider": nw,
                        })
                    elif isinstance(nw, dict) and not isinstance(ex, dict):
                        # new only
                        new_only_sliders.append({
                            "slider_local_id": lid,
                            "name": nw.get("name", lid),
                        })

                merge_chars_data.append({
                    "char_id": effective_cid,
                    "char_name": pack_char_names.get(cid, ex_char.get("name", cid)),
                    "conflict_groups": conflict_groups,
                    "new_only_sliders": new_only_sliders,
                })

            dlg = SliderMergeDialog(
                merge_chars=merge_chars_data,
                T=self.T,
                parent=self,
            )
            if dlg.exec() != 1:
                # Cancel -> abort
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                return

            choices = dlg.get_merge_choices()
            for cid in merge_ids:
                effective_cid = get_effective_cid(cid)
                merge_choices_map[effective_cid] = choices.get(effective_cid, {})

        # Step 7: Show loading before heavy import
        loading = self._show_loading(
            self.T.get("pack_loading_text", "Loading character pack...")
        )

        # Step 8: Perform import in background via QTimer
        characters = self.characters

        def do_import():
            QApplication.processEvents()

            def do_heavy_import():
                try:
                    # We already extracted to temp_dir.

                    # For outfit merge characters (not overwrite), preserve existing outfit data
                    # Only delete outfit data for overwrite characters
                    for cid in selected_ids:
                        effective_cid = get_effective_cid(cid)
                        if cid in outfit_overwrite_ids:
                            for outfit_dir_name in ("original_outfit", "exported_outfit"):
                                existing_outfit_path = os.path.join(root_dir, outfit_dir_name, effective_cid)
                                if os.path.exists(existing_outfit_path):
                                    try:
                                        shutil.rmtree(existing_outfit_path)
                                    except Exception:
                                        pass

                    # If outfitter pack, extract outfit data for overwrite characters
                    if pack_type == "outfitter":
                        effective_ids = set(get_effective_cid(cid) for cid in outfit_overwrite_ids)
                        for src_folder in ("exported_outfit", "original_outfit"):
                            src_base = os.path.join(temp_dir, src_folder)
                            if not os.path.isdir(src_base):
                                continue
                            dst_base = os.path.join(root_dir, src_folder)
                            os.makedirs(dst_base, exist_ok=True)
                            for item in os.listdir(src_base):
                                if item not in effective_ids:
                                    continue
                                sp = os.path.join(src_base, item)
                                dp = os.path.join(dst_base, item)
                                if os.path.isdir(sp):
                                    if os.path.exists(dp):
                                        shutil.rmtree(dp)
                                    shutil.copytree(sp, dp)
                                else:
                                    shutil.copy2(sp, dp)

                    # Collect character IDs that have outfit changes (for index rebuild later)
                    outfit_changed_ids: Set[str] = set()
                    
                    # Handle outfit merge characters
                    for cid in outfit_merge_ids:
                        if cid in outfit_overwrite_ids:
                            continue  # Already handled as overwrite
                        merge_result = outfit_merge_results.get(cid, {})
                        choices = merge_result.get("choices", {})
                        unique_files = merge_result.get("unique_files", [])
                        dup_groups = merge_result.get("dup_groups", [])
                        effective_cid = get_effective_cid(cid)

                        # Apply merge choices for duplicates
                        if dup_groups and choices:
                            apply_outfit_merge_choices(
                                dup_groups, choices, root_dir, effective_cid
                            )

                        # Copy unique files
                        if unique_files:
                            copy_outfit_files(unique_files, root_dir, effective_cid)

                        # Track for index rebuild
                        outfit_changed_ids.add(effective_cid)
                    
                    # Also track overwrite characters that had outfit data
                    for cid in outfit_overwrite_ids:
                        effective_cid = get_effective_cid(cid)
                        outfit_changed_ids.add(effective_cid)

                    imported_ids: List[str] = []

                    for cid in selected_ids:
                        effective_cid = get_effective_cid(cid)
                        is_merge = cid in merge_ids

                        src_cfg = os.path.join(temp_dir, "char_config", f"{cid}.json")
                        src_orig = os.path.join(temp_dir, "original_mesh", cid)
                        src_tgt = os.path.join(temp_dir, "target_mesh", cid)

                        # original_mesh
                        dst_orig_base = self.cm.char_original_mesh_dir(effective_cid)
                        if os.path.exists(src_orig):
                            if os.path.exists(dst_orig_base):
                                shutil.rmtree(dst_orig_base)
                            os.makedirs(os.path.dirname(dst_orig_base), exist_ok=True)
                            shutil.move(src_orig, dst_orig_base)

                        # target_mesh handling depends on mode
                        if is_merge:
                            # Don't fully overwrite target_mesh; we will merge sliders later
                            dst_tgt_base = self.cm.char_target_mesh_dir(effective_cid)
                            if os.path.exists(src_tgt):
                                def merge_dir_into(s: str, d: str):
                                    if not os.path.isdir(s):
                                        return
                                    os.makedirs(d, exist_ok=True)
                                    for item in os.listdir(s):
                                        sp = os.path.join(s, item)
                                        dp = os.path.join(d, item)
                                        if os.path.isdir(sp):
                                            merge_dir_into(sp, dp)
                                        else:
                                            shutil.copy2(sp, dp)
                                merge_dir_into(src_tgt, dst_tgt_base)
                        else:
                            # overwrite or new
                            dst_tgt_base = self.cm.char_target_mesh_dir(effective_cid)
                            if os.path.exists(src_tgt):
                                if os.path.exists(dst_tgt_base):
                                    shutil.rmtree(dst_tgt_base)
                                os.makedirs(os.path.dirname(dst_tgt_base), exist_ok=True)
                                shutil.move(src_tgt, dst_tgt_base)

                        # char_config: for merge, we will rewrite it after merging sliders
                        if not is_merge:
                            if os.path.exists(src_cfg):
                                dst_cfg = os.path.join(char_config_dir, f"{effective_cid}.json")
                                os.makedirs(os.path.dirname(dst_cfg), exist_ok=True)
                                shutil.move(src_cfg, dst_cfg)

                        imported_ids.append(effective_cid)

                    # Now handle merge characters: merge sliders and write configs
                    for cid in merge_ids:
                        effective_cid = get_effective_cid(cid)
                        merge_choices = merge_choices_map.get(effective_cid, {})
                        ex_sliders_cfg = self.character_sliders.get(cid, {}) or {}
                        # Read new sliders from temp config
                        src_cfg = os.path.join(temp_dir, "char_config", f"{cid}.json")
                        new_sliders_cfg: Dict[str, Any] = {}
                        pack_char_data: Dict[str, Any] = {}
                        if os.path.exists(src_cfg):
                            try:
                                with open(src_cfg, "r", encoding="utf-8") as f:
                                    pack_char_data = json.load(f)
                                new_sliders_cfg = pack_char_data.get("sliders", {}) or {}
                            except Exception:
                                pass

                        # Use CustomSliderManager to merge
                        merged_sliders = self.custom_slider_mgr.merge_sliders_for_import(
                            char_id=effective_cid,
                            existing_sliders=ex_sliders_cfg,
                            new_sliders=new_sliders_cfg,
                            merge_choices=merge_choices,
                        )

                        # Build final character config
                        ex_char = self.characters.get(cid, {})
                        pack_char = pack_char_data.get("character", {}) if isinstance(pack_char_data, dict) else {}

                        # For merge: keep existing character info, but allow pack to fill missing fields
                        final_char_info = ex_char.copy()

                        # Normalize paths
                        pac = pack_char.get("original_pac_path", final_char_info.get("original_pac_path", ""))
                        if pac and not os.path.isabs(pac):
                            pac = os.path.abspath(os.path.join(root_dir, pac))
                        final_char_info["original_pac_path"] = pac

                        # Save merged config
                        dst_cfg = os.path.join(char_config_dir, f"{effective_cid}.json")
                        os.makedirs(os.path.dirname(dst_cfg), exist_ok=True)
                        char_data_to_save = {
                            "character": final_char_info,
                            "sliders": merged_sliders,
                        }
                        with open(dst_cfg, "w", encoding="utf-8") as f:
                            json.dump(char_data_to_save, f, indent=4, ensure_ascii=False)

                    # Clean up temp
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)

                    if hasattr(self, "on_character_pack_imported"):
                        self.on_character_pack_imported(
                            imported_ids, saved_camera, saved_wireframe_enabled, loading,
                            outfit_changed_ids
                        )
                    else:
                        self._hide_loading(loading)

                except zipfile.BadZipFile:
                    err_msg = T.get(
                        "pack_read_error",
                        "Failed to read character pack: {error}",
                    ).format(error="Invalid ZIP file.")
                    show_critical(self, T.get("msg_error", "Error"), err_msg)
                except Exception as e:
                    import traceback
                    tb_text = traceback.format_exc()
                    err_msg = T.get(
                        "pack_read_error",
                        "Failed to read character pack: {error}",
                    ).format(error=str(e))
                    # Log full traceback to console as well
                    print(tb_text)
                    # Show a truncated but useful version in dialog
                    short_tb = "\n".join(tb_text.strip().split("\n")[-20:])
                    show_critical(self, T.get("msg_error", "Error"), err_msg + "\n\n" + short_tb)

            QTimer.singleShot(80, do_heavy_import)

        QTimer.singleShot(50, do_import)

    # ---------- import post-processing callback ----------

    def on_character_pack_imported(self, imported_ids, saved_camera, saved_wireframe_enabled, loading=None, outfit_changed_ids=None):
        # loading is provided by import_character_pack; if not, create one
        self_imported = loading is None
        if self_imported:
            loading = self._show_loading(self.T.get("pack_loading_text", "Loading character pack..."))

        try:
            # 1) Reload from disk so newly imported char_config files are picked up
            self.cm.load_config()

            # Refresh character tabs so newly imported characters appear in the tab bar
            self.refresh_char_tabs()

            # 2) Rebuild outfit indices for characters with outfit changes
            if outfit_changed_ids:
                for cid in outfit_changed_ids:
                    try:
                        rebuild_outfit_index(self.root_dir, cid)
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).warning(
                            "Failed to rebuild outfit index for %s: %s", cid, e
                        )

            # 3) Choose which character to activate
            target_active = None
            for cid in imported_ids:
                if cid in self.characters:
                    target_active = cid
                    break
            if not target_active and self.characters:
                target_active = next(iter(self.characters))

            # 4) Fully reload model + sliders + UI
            if target_active:
                # Temporarily set camera / wireframe so refresh can restore them
                if saved_camera:
                    self.camera_positions["global"] = saved_camera
                self.wireframe_enabled = saved_wireframe_enabled

                # If target is different from current active, use switch_character
                # If same (e.g., overwriting current active char), use _refresh_3d_preview
                # because switch_character returns early when char_id == active_char_id.
                if target_active != self.active_char_id:
                    self.switch_character(target_active)
                else:
                    # Same character (overwrite case): refresh 3D preview + sliders UI
                    self._refresh_3d_preview(refresh_sliders_ui=True)

                # Hide the loading overlay after refresh is done
                self._hide_loading(loading)

                def on_ready_after_import():
                    try:
                        current_viewer = self._plotter
                        # Restore camera and wireframe AFTER switch_character / refresh
                        # so they are not overwritten by default behavior.
                        if current_viewer and saved_camera:
                            current_viewer.set_camera_position(saved_camera)
                        if current_viewer:
                            current_viewer.set_wireframe(saved_wireframe_enabled)
                            self._sync_wireframe_button(saved_wireframe_enabled)
                        self.update_all_morphs()
                    except Exception:
                        pass

                QTimer.singleShot(200, on_ready_after_import)
            else:
                self._hide_loading(loading)

        except Exception as e:
            self._hide_loading(loading)
            show_critical(self, self.T.get("msg_error", "Error"), str(e))


    # ---------- save_model_pac_and_mod (MOD export) ----------

    def save_model_pac_and_mod(self):
        import numpy as np
        import subprocess
        from core.pac_builder import parse_pac, IncrementalPACBuilder

        if not self.btn_mod:
            return

        self.btn_mod.setText(self.T["processing"])
        self.btn_mod.setEnabled(False)
        QApplication.processEvents()

        try:
            # Step 1: Show character selection dialog
            dlg = CharacterPackSelectDialog(
                characters=self.characters,
                active_char_id=self.active_char_id,
                T=self.T,
                parent=self,
            )
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            selected_char_ids = dlg.get_selected_ids()
            if not selected_char_ids:
                return

            # Step 2: Detect conflicts by (pac_filename, mod_path)
            conflict_map: Dict[str, List[Tuple[str, str]]] = {}
            for cid in selected_char_ids:
                char = self.characters.get(cid)
                if not char:
                    continue
                pac_path = char.get("original_pac_path", "")
                mod_path = char.get("mod_path", "")
                if not pac_path:
                    continue
                pac_filename = os.path.basename(pac_path)
                key = f"{pac_filename}|{mod_path}"
                conflict_map.setdefault(key, []).append((cid, char.get("name", cid)))

            conflict_groups: Dict[str, List[Tuple[str, str]]] = {
                k: v for k, v in conflict_map.items() if len(v) > 1
            }

            # Step 3: If conflicts, show conflict resolution dialog
            final_char_ids: Set[str] = set()
            if conflict_groups:
                resolve_dlg = PackConflictResolveDialog(
                    conflict_groups=conflict_groups,
                    T=self.T,
                    parent=self,
                )
                if resolve_dlg.exec() != QDialog.DialogCode.Accepted:
                    return
                conflict_choices = resolve_dlg.get_selection()
                for key, chosen_cid in conflict_choices.items():
                    final_char_ids.add(chosen_cid)
            else:
                final_char_ids = set(selected_char_ids)

            for key, chars in conflict_map.items():
                if len(chars) == 1:
                    final_char_ids.add(chars[0][0])

            # Step 4: Build MOD
            packed_names: List[str] = []
            mod_dir = os.path.join(self.root_dir, "exported_mod")
            os.makedirs(mod_dir, exist_ok=True)

            DEFAULT_MOD_PATH = "models/human"
            default_mod_folder_name = "Body_Slider_Mod"
            mod_subdir = os.path.join(mod_dir, default_mod_folder_name)

            if os.path.exists(mod_subdir):
                reply = show_choice(
                    self,
                    self.T.get("mod_folder_exists_title", "Folder Already Exists"),
                    self.T.get(
                        "mod_folder_exists",
                        "The folder '{folder}' already exists in exported_mod.\n"
                        "Do you want to:\n"
                        "- Delete: remove the existing folder and export again\n"
                        "- Rename: create a new folder with a custom name",
                    ).format(folder=default_mod_folder_name),
                    [
                        self.T.get("mod_action_delete", "Delete"),
                        self.T.get("mod_action_rename", "Rename"),
                        self.T.get("btn_cancel", "Cancel"),
                    ],
                )

                if reply is None or reply == self.T.get("btn_cancel", "Cancel"):
                    return

                if reply == self.T.get("mod_action_rename", "Rename"):
                    mod_folder_name = None
                    while mod_folder_name is None:
                        rename_dlg = ModRenameDialog(
                            T=self.T,
                            parent=self,
                            title=self.T.get("mod_rename_title", "Rename MOD Folder"),
                            prompt=self.T.get(
                                "mod_rename_prompt",
                                "Enter a new folder name (max 64 characters, must follow Windows naming rules):",
                            ),
                            text=default_mod_folder_name,
                        )
                        if rename_dlg.exec() != QDialog.DialogCode.Accepted:
                            return

                        candidate = rename_dlg.text()
                        if not candidate:
                            show_warning(
                                self,
                                self.T.get("msg_error", "Error"),
                                self.T.get(
                                    "mod_rename_required",
                                    "Folder name is required. Please enter a name.",
                                ),
                            )
                            continue

                        if len(candidate) > 64:
                            show_warning(
                                self,
                                self.T.get("msg_error", "Error"),
                                self.T.get(
                                    "mod_rename_too_long",
                                    "Folder name is too long. Maximum 64 characters allowed.",
                                ),
                            )
                            continue

                        invalid_chars = r'<>:"/\|?*'
                        if any(c in invalid_chars for c in candidate):
                            show_warning(
                                self,
                                self.T.get("msg_error", "Error"),
                                self.T.get(
                                    "mod_rename_invalid_chars",
                                    "Invalid characters in folder name.\nDo not use: < > : \" / \\ | ? *",
                                ),
                            )
                            continue

                        reserved = {
                            "CON", "PRN", "AUX", "NUL",
                            "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
                            "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
                        }
                        if candidate.upper().rstrip() in reserved:
                            show_warning(
                                self,
                                self.T.get("msg_error", "Error"),
                                self.T.get(
                                    "mod_rename_reserved",
                                    "This name is reserved by Windows and cannot be used.",
                                ),
                            )
                            continue

                        if candidate.strip().isspace():
                            show_warning(
                                self,
                                self.T.get("msg_error", "Error"),
                                self.T.get(
                                    "mod_rename_blank",
                                    "Folder name cannot be only spaces.",
                                ),
                            )
                            continue

                        candidate_subdir = os.path.join(mod_dir, candidate)
                        if os.path.exists(candidate_subdir):
                            show_warning(
                                self,
                                self.T.get("msg_error", "Error"),
                                self.T.get(
                                    "mod_rename_exists",
                                    "A folder with that name already exists. Please choose another.",
                                ),
                            )
                            continue

                        mod_folder_name = candidate

                    mod_subdir = os.path.join(mod_dir, mod_folder_name)
                else:
                    # Delete chosen
                    mod_folder_name = default_mod_folder_name
                    mod_subdir = os.path.join(mod_dir, mod_folder_name)
                    try:
                        shutil.rmtree(mod_subdir)
                    except Exception:
                        pass
            else:
                mod_folder_name = default_mod_folder_name

            os.makedirs(mod_subdir, exist_ok=True)

            previous_active_char_id = self.active_char_id

            # Save current slider values (from UI) before they are overwritten.
            # This ensures we export using the actual slider positions.
            saved_sliders_info: Dict[str, Any] = {}
            for sid, info in self.sliders_info.items():
                s = info.copy()
                saved_sliders_info[sid] = s

            for pack_cid in final_char_ids:
                char = self.characters.get(pack_cid)
                if not char:
                    continue

                original_pac = char.get("original_pac_path", "")
                mod_path = char.get("mod_path", "")

                if not original_pac or not os.path.exists(original_pac):
                    continue

                # For the currently active character, use in-memory slider values (UI).
                # For others, reload from config so we have correct slider definitions.
                if pack_cid == previous_active_char_id:
                    # Restore saved slider values in-place to keep reference with ConfigManager
                    self.sliders_info.clear()
                    self.sliders_info.update(saved_sliders_info)
                else:
                    self.cm._load_sliders_for_character(pack_cid)

                try:
                    with open(original_pac, "rb") as f:
                        pac_bytes = f.read()
                    char_pac_mesh = parse_pac(pac_bytes, original_pac)
                except Exception:
                    continue

                char_original_points: Dict[str, np.ndarray] = {}
                for sm in char_pac_mesh.submeshes:
                    if sm.vertices:
                        char_original_points[sm.name] = np.array(sm.vertices, dtype=np.float32)

                # Use compute_morph_delta (same as UI preview) so OBJ/PAC morphs
                # are calculated identically to what the user sees in 3D.
                from core.mesh_processor import compute_morph_delta

                char_morph_data: Dict[str, Dict[str, np.ndarray]] = {}
                for sid, info in self.sliders_info.items():
                    target_path = info.get("path", "")
                    if not target_path or not os.path.exists(target_path):
                        continue
                    try:
                        compute_morph_delta(
                            char_morph_data, sid, target_path, char_original_points
                        )
                    except Exception:
                        pass

                new_positions: Dict[str, np.ndarray] = {}
                for name, orig in char_original_points.items():
                    morphed = orig.copy()
                    for sid, info in self.sliders_info.items():
                        md = char_morph_data.get(sid)
                        cv = info.get("current_value", 0.0)
                        if md is not None and name in md:
                            morphed += md[name] * (cv / 100.0)
                    new_positions[name] = morphed

                inc = IncrementalPACBuilder(original_pac)
                pac_sm_names = [sm.name for sm in inc.original_mesh.submeshes]

                def transform_func(
                    sm_idx,
                    vi,
                    orig_v,
                    new_positions=new_positions,
                    char_original_points=char_original_points,
                    pac_sm_names=pac_sm_names,
                ):
                    pac_name = pac_sm_names[sm_idx] if sm_idx < len(pac_sm_names) else None
                    if not pac_name or pac_name not in new_positions:
                        return orig_v
                    if pac_name not in char_original_points:
                        return orig_v
                    orig_verts = char_original_points[pac_name]
                    morphed_verts = new_positions[pac_name]
                    if vi >= len(orig_verts):
                        return orig_v
                    ov = orig_verts[vi]
                    mv = morphed_verts[vi]
                    return (
                        float(orig_v[0] + mv[0] - ov[0]),
                        float(orig_v[1] + mv[1] - ov[1]),
                        float(orig_v[2] + mv[2] - ov[2]),
                    )

                inc.apply_vertex_transform(transform_func)
                pac_data = inc.build()

                if mod_path:
                    game_rel_dir = os.path.join(mod_subdir, "files", mod_path)
                else:
                    game_rel_dir = os.path.join(mod_subdir, "files", DEFAULT_MOD_PATH)
                os.makedirs(game_rel_dir, exist_ok=True)

                pac_filename = os.path.basename(original_pac)
                mod_pac_path = os.path.join(game_rel_dir, pac_filename)
                with open(mod_pac_path, "wb") as f:
                    f.write(pac_data)

                packed_names.append(char.get("name", pack_cid))

            # Restore previous active character and fully refresh UI + 3D.
            # Use force_refresh because char_id == active_char_id, otherwise
            # switch_character would return early and sliders/3D would not update.
            # IMPORTANT: Restore sliders_info BEFORE switch_character so that
            # _sync_sliders_to_config and _load_sliders_for_character use correct values.
            self.sliders_info.clear()
            self.sliders_info.update(saved_sliders_info)
            self.active_char_id = previous_active_char_id
            if previous_active_char_id and previous_active_char_id in self.characters:
                self.switch_character(previous_active_char_id, loading=None, force_refresh=True)

            # Write mod.json
            names_list = ", ".join(packed_names) if packed_names else "Body Slider MOD"
            mod_json = {
                "modinfo": {
                    "title": f"Body Slider MOD - {names_list}",
                    "name": f"Body Slider MOD - {names_list}",
                    "author": "Body Slider Pro - by zyd232",
                    "version": "1.0.0",
                    "description": f"Model modifications for {names_list}",
                    "generator": "Body Slider Pro",
                    "nexus_url": "https://www.nexusmods.com/crimsondesert/mods/2727",
                },
                "files_dir": "files",
            }

            with open(os.path.join(mod_subdir, "mod.json"), "w", encoding="utf-8") as f:
                json.dump(mod_json, f, indent=2, ensure_ascii=False)

            # Show success message
            success_msg = self.T["mod_exported_title"] + ":\n\n"
            success_msg += f"{self.T['mod_folder']} {mod_dir}\n\n"
            success_msg += self.T.get(
                "mod_usage_folder",
                "You can use the '{folder}' folder as a MOD package.",
            ).format(folder=mod_folder_name)

            msg = DarkMessageBox(self)
            msg.setWindowTitle(self.T["msg_success"])
            msg.setText(success_msg)
            msg.setIcon(QMessageBox.Icon.Information)

            ok_btn = msg.addButton(self.T["btn_ok"], QMessageBox.ButtonRole.AcceptRole)
            open_btn = msg.addButton(self.T["btn_open_folder"], QMessageBox.ButtonRole.ActionRole)

            ok_btn.clicked.connect(lambda: setattr(msg, "_clicked_button", ok_btn))
            open_btn.clicked.connect(lambda: setattr(msg, "_clicked_button", open_btn))

            msg.exec()
            if msg.clickedButton() is open_btn:
                subprocess.Popen(["explorer", mod_dir])

        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n\n{traceback.format_exc()}"
            show_critical(self, self.T["msg_error"], error_msg)
        finally:
            self.btn_mod.setText(self.T["btn_export_mod"])
            self.btn_mod.setEnabled(True)

    # ---------- import version helper ----------

    @staticmethod
    def _parse_version(version_str: str) -> tuple:
        parts = []
        for p in str(version_str).split("."):
            try:
                parts.append(int(p))
            except ValueError:
                parts.append(0)
        return tuple(parts)