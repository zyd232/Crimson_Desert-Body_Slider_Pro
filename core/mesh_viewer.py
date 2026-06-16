"""
Minimal 3D mesh viewer using QOpenGLWidget + PyOpenGL.
Replaces pyvistaqt to dramatically reduce package size.
"""

import sys
import numpy as np
from typing import Dict, List, Tuple, Optional

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent, QWheelEvent
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

from OpenGL.GL import (
    glClearColor, glEnable, glDisable, glClear, glViewport,
    glMatrixMode, glLoadIdentity,
    glCullFace, glLightfv, glLightModelfv,
    glMaterialfv, glMaterialf,
    glEnableClientState, glDisableClientState,
    glVertexPointer, glNormalPointer,
    glDrawElements,
    glLoadMatrixf,
    glPolygonMode,
    glColor3f,
    glLineWidth,
    glShadeModel,
    GL_DEPTH_TEST, GL_CULL_FACE, GL_BACK,
    GL_LIGHTING, GL_LIGHT0, GL_LIGHT1, GL_LIGHT2,
    GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT,
    GL_PROJECTION, GL_MODELVIEW,
    GL_POSITION, GL_DIFFUSE, GL_SPECULAR,
    GL_LIGHT_MODEL_AMBIENT,
    GL_FRONT_AND_BACK, GL_SHININESS,
    GL_VERTEX_ARRAY, GL_NORMAL_ARRAY,
    GL_FLOAT, GL_UNSIGNED_INT,
    GL_TRIANGLES, GL_FILL, GL_LINE,
    GL_SMOOTH
)

from core.ui_constants import (
    MESH_COLOR_BEIGE_RGB,
    MESH_COLOR_WHITE_RGB,
    MESH_COLOR_ACCENT_RGB,
)


class MeshViewer(QOpenGLWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAutoFillBackground(False)

        self._orbit_angle_x = 0.0
        self._orbit_angle_y = 0.0
        self._target = np.array([0.0, 1.5, 0.0], dtype=np.float32)
        self._distance = 3.5
        self._up = np.array([0.0, 1.0, 0.0], dtype=np.float32)

        self._mouse_button = None
        self._last_mouse = None

        self._meshes: Dict[str, Dict] = {}

        # Wireframe overlay control (default: OFF)
        self._wireframe_enabled = False

        # Outfits panel presence (controls color logic)
        self._has_outfits_panel = False

    # ------------ Public API ------------

    def add_mesh(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        color: str = "beige",
        name: str = "",
        mesh_type: str = "character",
    ):
        """
        Add a mesh to the viewer.

        mesh_type:
            - "character": base character model
            - "outfit": outfit model (activated via Outfits panel)
        """
        if len(vertices) == 0:
            return

        faces = self._normalize_faces(faces)
        c = self._color_from_str(color)

        self._meshes[name] = {
            "vertices": vertices.astype(np.float32),
            "indices": faces.astype(np.uint32),
            "color": c,
            "mesh_type": mesh_type,
        }
        self.update()

    def update_mesh_vertices(self, name: str, vertices: np.ndarray):
        mesh = self._meshes.get(name)
        if mesh is None:
            return
        mesh["vertices"] = vertices.astype(np.float32)
        self.update()

    def remove_mesh(self, name: str):
        self._meshes.pop(name, None)
        self.update()

    def clear(self):
        self._meshes.clear()
        self.update()

    def set_wireframe(self, enabled: bool):
        """Enable or disable wireframe overlay."""
        self._wireframe_enabled = bool(enabled)
        self.update()

    def set_has_outfits_panel(self, enabled: bool):
        """
        Set whether the Outfits panel is present for the current character.
        Used to decide mesh render colors.
        """
        self._has_outfits_panel = bool(enabled)
        self.update()

    def reset_camera(self):
        self._orbit_angle_x = 0.0
        self._orbit_angle_y = 0.0
        self._target = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self._distance = 6.0
        self.update()

    def set_view_target(self, target: List[float]):
        """Set orbit center (e.g., to model mid-height)."""
        self._target = np.array(target, dtype=np.float32)
        self.update()

    def set_distance(self, distance: float):
        """Set camera distance from target."""
        self._distance = float(np.clip(distance, 0.5, 100.0))
        self.update()

    def view_vector(self, direction: Tuple, up_vec: Tuple):
        d = np.array(direction, dtype=np.float32)
        up = np.array(up_vec, dtype=np.float32)
        norm_d = np.linalg.norm(d)
        if norm_d < 1e-9:
            return
        d = d / norm_d
        self._up = up / (np.linalg.norm(up) + 1e-9)
        self._orbit_angle_x = 0.0
        self._orbit_angle_y = 0.0
        self.update()

    @property
    def camera_position(self):
        """Return [eye, target] for save/restore (global camera)."""
        eye = self._camera_position()
        target = self._target
        return [
            [float(eye[0]), float(eye[1]), float(eye[2])],
            [float(target[0]), float(target[1]), float(target[2])],
        ]

    def set_camera_position(self, position: List[float]):
        """Restore camera from [eye, target] stored by camera_position."""
        if not position or len(position) < 2:
            return
        eye = np.array(position[0], dtype=np.float32)
        target = np.array(position[1], dtype=np.float32)
        self._target = target
        diff = eye - target
        self._distance = float(np.linalg.norm(diff) + 1e-9)

        # Derive orbit angles from direction so camera angle is fully restored
        dir_norm = diff / self._distance
        dx, dy, dz = float(dir_norm[0]), float(dir_norm[1]), float(dir_norm[2])

        # From forward vector back to orbit angles:
        # dx = -sin(phi)
        # dy = cos(phi)*sin(theta)
        # dz = -cos(phi)*cos(theta)
        phi = float(np.arcsin(np.clip(-dx, -1.0, 1.0)))
        cos_phi = np.cos(phi)
        if abs(cos_phi) > 1e-6:
            theta = float(np.arctan2(dy, -dz))
        else:
            theta = 0.0

        self._orbit_angle_x = phi
        self._orbit_angle_y = float(np.clip(theta, -1.5, 1.5))
        self.update()

    # ------------ Mouse events ------------

    def mousePressEvent(self, e: QMouseEvent):
        self._last_mouse = e.position()
        if e.button() == Qt.MouseButton.LeftButton:
            self._mouse_button = "orbit"
        elif e.button() in (Qt.MouseButton.RightButton, Qt.MouseButton.MiddleButton):
            self._mouse_button = "pan"
        else:
            self._mouse_button = None

    def mouseMoveEvent(self, e: QMouseEvent):
        if self._last_mouse is None:
            self._last_mouse = e.position()
            return

        dx = e.position().x() - self._last_mouse.x()
        dy = e.position().y() - self._last_mouse.y()
        self._last_mouse = e.position()

        if self._mouse_button == "orbit":
            self._orbit_angle_x += dx * 0.005
            self._orbit_angle_y += dy * 0.005
            self._orbit_angle_y = float(np.clip(self._orbit_angle_y, -1.5, 1.5))
            self.update()

        elif self._mouse_button == "pan":
            right = self._camera_right()
            up = self._camera_up()
            scale = self._distance * 0.001
            self._target = self._target + right * dx * scale + up * dy * scale
            self.update()

    def mouseReleaseEvent(self, e: QMouseEvent):
        self._mouse_button = None

    def wheelEvent(self, e: QWheelEvent):
        dy = e.angleDelta().y()
        if dy > 0:
            self._distance *= 0.95
        else:
            self._distance *= 1.05
        self._distance = float(np.clip(self._distance, 0.5, 100.0))
        self.update()

    # ------------ OpenGL ------------

    def initializeGL(self):
        glClearColor(33 / 255.0, 24 / 255.0, 20 / 255.0, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)
        glShadeModel(GL_SMOOTH)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        w = self.width()
        h = self.height()
        if w == 0 or h == 0:
            return

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = float(w) / float(h)
        self._glPerspective(45.0, aspect, 0.01, 200.0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        cam_pos = self._camera_position()
        target = self._target
        up = self._camera_up()

        self._glLookAt(
            cam_pos[0], cam_pos[1], cam_pos[2],
            target[0], target[1], target[2],
            up[0], up[1], up[2],
        )

        # Lighting:
        # - Front key light (LIGHT0): 80%
        # - Back fill light (LIGHT1): 80%
        # - Bottom fill light (LIGHT2): 50%
        glEnable(GL_LIGHTING)

        glLightModelfv(GL_LIGHT_MODEL_AMBIENT,
                       np.array([0.25, 0.25, 0.25, 1.0], dtype=np.float32))

        # Front key light (LIGHT0): 80% intensity
        glEnable(GL_LIGHT0)
        front_dir = np.array([0.0, 1.5, -2.5], dtype=np.float32)
        glLightfv(GL_LIGHT0, GL_POSITION,
                  np.array([front_dir[0], front_dir[1], front_dir[2], 0.0], dtype=np.float32))

        glLightfv(GL_LIGHT0, GL_DIFFUSE,
                  np.array([0.8, 0.8, 0.8, 1.0], dtype=np.float32))
        glLightfv(GL_LIGHT0, GL_SPECULAR,
                  np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32))

        # Back fill light (LIGHT1): 80% intensity
        glEnable(GL_LIGHT1)
        back_dir = np.array([0.0, 1.5, 2.5], dtype=np.float32)
        glLightfv(GL_LIGHT1, GL_POSITION,
                  np.array([back_dir[0], back_dir[1], back_dir[2], 0.0], dtype=np.float32))

        glLightfv(GL_LIGHT1, GL_DIFFUSE,
                  np.array([0.8, 0.8, 0.8, 1.0], dtype=np.float32))
        glLightfv(GL_LIGHT1, GL_SPECULAR,
                  np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32))

        # Bottom fill light (LIGHT2): 50% intensity
        glEnable(GL_LIGHT2)
        bottom_dir = np.array([0.0, -2.0, 0.0], dtype=np.float32)
        glLightfv(GL_LIGHT2, GL_POSITION,
                  np.array([bottom_dir[0], bottom_dir[1], bottom_dir[2], 0.0], dtype=np.float32))

        glLightfv(GL_LIGHT2, GL_DIFFUSE,
                  np.array([0.5, 0.5, 0.5, 1.0], dtype=np.float32))
        glLightfv(GL_LIGHT2, GL_SPECULAR,
                  np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32))

        for mesh in self._meshes.values():
            verts = mesh["vertices"]
            idx = mesh["indices"]

            if len(verts) == 0 or len(idx) == 0:
                continue

            mesh_type = mesh.get("mesh_type", "character")

            # Decide render mode and color based on:
            # - wireframe_enabled
            # - has_outfits_panel
            # - mesh_type
            use_wireframe = bool(self._wireframe_enabled)
            has_outfits = bool(self._has_outfits_panel)

            if use_wireframe:
                # Wireframe mode: no lighting, colored lines
                if has_outfits:
                    # With Outfits panel:
                    # - character base -> white
                    # - outfit -> orange
                    if mesh_type == "outfit":
                        r, g, b = MESH_COLOR_ACCENT_RGB
                    else:
                        r, g, b = MESH_COLOR_WHITE_RGB
                else:
                    # No Outfits panel -> keep original orange
                    r, g, b = MESH_COLOR_ACCENT_RGB
            else:
                # Filled mode with lighting
                if has_outfits and mesh_type == "outfit":
                    # Outfit mesh in fill mode: orange (flat color, no lighting)
                    r, g, b = MESH_COLOR_ACCENT_RGB
                else:
                    # Character base: white clay (lit)
                    r, g, b = MESH_COLOR_WHITE_RGB

            # Smooth normals for even, clay-like shading
            normals = self._compute_smooth_normals(verts, idx)

            flat = idx.ravel()

            if use_wireframe:
                # Wireframe mode: no lighting, colored edges
                glDisable(GL_LIGHTING)
                glColor3f(r, g, b)
                glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
                glLineWidth(1)

                glEnableClientState(GL_VERTEX_ARRAY)
                glVertexPointer(3, GL_FLOAT, 0, verts)

                glDrawElements(
                    GL_TRIANGLES,
                    flat.shape[0],
                    GL_UNSIGNED_INT,
                    flat.astype(np.uint32),
                )

                glDisableClientState(GL_VERTEX_ARRAY)

                # Restore for next mesh
                glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            else:
                # For both outfit and character in fill mode: use lit material.
                # - character base: white diffuse
                # - outfit: orange diffuse (from r,g,b)
                # This ensures outfit meshes have lighting like the base model.

                # Enable lighting for fill mode
                glEnable(GL_LIGHTING)

                diffuse_r, diffuse_g, diffuse_b = float(r), float(g), float(b)
                mat_diffuse = np.array(
                    [diffuse_r, diffuse_g, diffuse_b, 1.0],
                    dtype=np.float32,
                )
                mat_specular = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)

                glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, mat_diffuse)
                glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, mat_specular)
                glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 0.0)

                glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

                glEnableClientState(GL_VERTEX_ARRAY)
                glEnableClientState(GL_NORMAL_ARRAY)
                glVertexPointer(3, GL_FLOAT, 0, verts)
                glNormalPointer(GL_FLOAT, 0, normals)

                glDrawElements(
                    GL_TRIANGLES,
                    flat.shape[0],
                    GL_UNSIGNED_INT,
                    flat.astype(np.uint32),
                )

                glDisableClientState(GL_VERTEX_ARRAY)
                glDisableClientState(GL_NORMAL_ARRAY)

    # ------------ Helpers ------------

    @staticmethod
    def _normalize_faces(faces: np.ndarray) -> np.ndarray:
        f = np.asarray(faces, dtype=np.intp)
        if f.ndim == 1:
            if f.shape[0] % 4 == 0 and all(
                f[i] == 3 for i in range(0, f.shape[0], 4)
            ):
                t = f[1:].reshape(-1, 3)
                return t
            return np.zeros((0, 3), dtype=np.intp)
        if f.ndim == 2 and f.shape[1] == 3:
            return f
        return f.reshape(-1, 3)

    @staticmethod
    def _compute_face_normals(
        verts: np.ndarray,
        faces: np.ndarray,
    ) -> np.ndarray:
        v0 = verts[faces[:, 0]]
        v1 = verts[faces[:, 1]]
        v2 = verts[faces[:, 2]]
        e1 = v1 - v0
        e2 = v2 - v0
        n = np.cross(e1, e2)
        length = np.linalg.norm(n, axis=1, keepdims=True)
        length = np.maximum(length, 1e-9)
        n = n / length
        n_flat = np.repeat(n, 3, axis=0)
        return n_flat.astype(np.float32)

    @staticmethod
    def _compute_smooth_normals(
        verts: np.ndarray,
        faces: np.ndarray,
    ) -> np.ndarray:
        """Smooth (Gouraud) shading: average face normals per vertex."""
        v0 = verts[faces[:, 0]]
        v1 = verts[faces[:, 1]]
        v2 = verts[faces[:, 2]]
        e1 = v1 - v0
        e2 = v2 - v0
        face_normals = np.cross(e1, e2)

        # Normalize face normals
        length = np.linalg.norm(face_normals, axis=1, keepdims=True)
        length = np.maximum(length, 1e-9)
        face_normals = face_normals / length

        # Accumulate per-vertex normals
        N = verts.shape[0]
        vert_normals = np.zeros((N, 3), dtype=np.float32)

        # Add each face's normal to its 3 vertices
        for c in range(3):
            idx = faces[:, c]  # shape (F,)
            np.add.at(vert_normals, idx, face_normals)

        # Normalize per-vertex normals
        norms = np.linalg.norm(vert_normals, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-9)
        vert_normals = vert_normals / norms

        # Return per-vertex normals directly to match verts array (N x 3)
        return vert_normals.astype(np.float32)

    @staticmethod
    def _color_from_str(c: str) -> Tuple[float, float, float]:
        c = c.lower()
        named = {
            "beige": (0.96, 0.87, 0.70),
            "white": (1.0, 1.0, 1.0),
            "gray": (0.5, 0.5, 0.5),
            "darkgray": (0.3, 0.3, 0.3),
            "black": (0.0, 0.0, 0.0),
        }
        if c in named:
            return named[c]
        if c.startswith("#"):
            c = c.lstrip("#")
            if len(c) == 6:
                r = int(c[0:2], 16) / 255.0
                g = int(c[2:4], 16) / 255.0
                b = int(c[4:6], 16) / 255.0
                return (r, g, b)
        return (0.96, 0.87, 0.70)

    def _camera_position(self) -> np.ndarray:
        phi = self._orbit_angle_x
        theta = self._orbit_angle_y
        d = self._distance

        dx, dy, dz = 0.0, 0.0, -1.0

        c1 = np.cos(phi)
        s1 = np.sin(phi)
        x1 = dx * c1 + dz * s1
        z1 = -dx * s1 + dz * c1
        dx, dz = x1, z1

        c2 = np.cos(theta)
        s2 = np.sin(theta)
        y2 = dy * c2 - dz * s2
        z2 = dy * s2 + dz * c2
        dy, dz = y2, z2

        return self._target + np.array([dx, dy, dz], dtype=np.float32) * d

    def _camera_right(self) -> np.ndarray:
        phi = self._orbit_angle_x
        c1 = np.cos(phi)
        s1 = np.sin(phi)
        dx, dy, dz = 1.0, 0.0, 0.0
        x1 = dx * c1 + dz * s1
        z1 = -dx * s1 + dz * c1
        return np.array([x1, dy, z1], dtype=np.float32)

    def _camera_up(self) -> np.ndarray:
        theta = self._orbit_angle_y
        c2 = np.cos(theta)
        s2 = np.sin(theta)
        return np.array([0.0, c2, s2], dtype=np.float32)

    def _glPerspective(self, fovy, aspect, znear, zfar):
        f = 1.0 / np.tan(fovy * 0.5 * np.pi / 180.0)
        m = np.zeros((4, 4), dtype=np.float32)
        m[0, 0] = f / aspect
        m[1, 1] = f
        m[2, 2] = (znear + zfar) / (znear - zfar)
        m[2, 3] = (2.0 * znear * zfar) / (znear - zfar)
        m[3, 2] = -1.0
        glLoadMatrixf(m.T)

    def _glLookAt(self, eye_x, eye_y, eye_z,
                  center_x, center_y, center_z,
                  up_x, up_y, up_z):
        f = np.array([center_x - eye_x, center_y - eye_y, center_z - eye_z], dtype=np.float32)
        f = f / (np.linalg.norm(f) + 1e-9)
        s = np.cross(f, np.array([up_x, up_y, up_z], dtype=np.float32))
        s = s / (np.linalg.norm(s) + 1e-9)
        u = np.cross(s, f)

        m = np.zeros((4, 4), dtype=np.float32)
        m[0, 0] = s[0]
        m[1, 0] = s[1]
        m[2, 0] = s[2]
        m[0, 1] = u[0]
        m[1, 1] = u[1]
        m[2, 1] = u[2]
        m[0, 2] = -f[0]
        m[1, 2] = -f[1]
        m[2, 2] = -f[2]
        m[3, 3] = 1.0

        m[0, 3] = -np.dot(s, [eye_x, eye_y, eye_z])
        m[1, 3] = -np.dot(u, [eye_x, eye_y, eye_z])
        m[2, 3] = np.dot(f, [eye_x, eye_y, eye_z])

        glLoadMatrixf(m.T)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    w = QWidget()
    lay = QVBoxLayout(w)
    viewer = MeshViewer()

    verts = np.array([
        [-1, -1, -1],
        [ 1, -1, -1],
        [ 1,  1, -1],
        [-1,  1, -1],
        [-1, -1,  1],
        [ 1, -1,  1],
        [ 1,  1,  1],
        [-1,  1,  1],
    ], dtype=np.float32)

    faces = np.array([
        [0,1,2], [0,2,3],
        [5,4,7], [5,7,6],
        [4,0,3], [4,3,7],
        [1,5,6], [1,6,2],
        [4,5,1], [4,1,0],
        [3,2,6], [3,6,7],
    ], dtype=np.uint32)

    viewer.add_mesh(verts, faces, color="beige", name="cube")

    lay.addWidget(viewer)
    w.resize(600, 500)
    w.show()
    sys.exit(app.exec())