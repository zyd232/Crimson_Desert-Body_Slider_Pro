# Outfit 滑块参数持久化系统 — 重构计划

## 概述

为 outfit 项目创建独立的滑块参数持久化系统，在 `outfit_config/{char_id}.json` 中记录每个 outfit 文件所对应滑块的数值。支持 `is_linked` 状态控制是否使用独立值或同步角色滑块值。

---

## 数据格式设计

### 文件路径

```
{root_dir}/outfit_config/{char_id}.json
```

### JSON 结构

```json
{
  "breast_size_type_01/character/model/1_pc/2_phw/armor/9_upperbody/cd_phw_00_ub_00_0170.pac": {
    "breast_size_type_01": {
      "name": "Breast Size Type 01",
      "min": -50.0,
      "max": 150.0,
      "current_value": 30.0,
      "is_linked": false
    },
    "waist_width_type_02": {
      "name": "Waist Width Type 02",
      "min": -50.0,
      "max": 150.0,
      "current_value": 0.0,
      "is_linked": true
    }
  }
}
```

- **顶层 key**: outfit 文件的 `mod_path`（相对于 `original_outfit/{char_id}` 的路径），如 `"breast_size_type_01/character/model/1_pc/2_phw/armor/9_upperbody/cd_phw_00_ub_00_0170.pac"`
- **二级 key**: 滑块的 `short_id`（如 `"breast_size_type_01"`）
- **滑块属性**:
  - `name`: 显示名称
  - `min`: 最小值
  - `max`: 最大值
  - `current_value`: 当前值（仅在 `is_linked=false` 时有效）
  - `is_linked`: 是否链接到角色滑块（`true` = 同步角色滑块，`false` = 独立值）

### is_linked 语义

| is_linked | min/max/current_value 来源 | 行为 |
|-----------|--------------------------|------|
| `true` | 从角色滑块同步 | 忽略 JSON 中的 min/max/current_value，不向 JSON 写入这些值 |
| `false` | 使用 JSON 中记录的值 | 使用 JSON 中的 min/max/current_value，滑块变化时写入 JSON |

---

## 修改文件清单

### 1. 新建 `core/outfit_config_manager.py`

**职责**: outfit 滑块配置的加载、保存、删除。

```python
class OutfitConfigManager:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.config_dir = os.path.join(root_dir, "outfit_config")
        os.makedirs(self.config_dir, exist_ok=True)

    def _config_path(self, char_id: str) -> str:
        return os.path.join(self.config_dir, f"{char_id}.json")

    def load_config(self, char_id: str) -> Dict[str, Dict[str, Any]]:
        """加载角色的 outfit 配置，返回 {outfit_key: {short_id: slider_info}}"""

    def save_config(self, char_id: str, data: Dict[str, Dict[str, Any]]) -> None:
        """保存角色的 outfit 配置"""

    def save_slider(self, char_id: str, outfit_key: str, short_id: str, slider_info: Dict) -> None:
        """保存单个滑块的配置（加载 -> 修改 -> 保存）"""

    def get_slider(self, char_id: str, outfit_key: str, short_id: str) -> Optional[Dict]:
        """获取单个滑块的配置"""

    def delete_config(self, char_id: str) -> None:
        """删除角色的 outfit 配置文件"""

    def get_all_for_char(self, char_id: str) -> Dict[str, Dict[str, Any]]:
        """获取角色的所有 outfit 配置"""
```

### 2. 修改 `core/body_slider_func.py`

#### 2a. 初始化 OutfitConfigManager

在 `__init__` 中（约第 218 行 `self.outfit_mgr = OutfitManager(self)` 之后）：

```python
from core.outfit_config_manager import OutfitConfigManager
self.outfit_config_mgr = OutfitConfigManager(self.root_dir)
```

#### 2b. `delete_character()` — 删除 outfit_config 文件

在 [`do_delete()`](core/body_slider_func.py:1113) 内部（约第 1140 行 `self.character_sliders.pop(char_id_for_delete, None)` 附近）：

```python
# 删除 outfit_config 文件
self.outfit_config_mgr.delete_config(char_id_for_delete)
```

#### 2c. `reset_all_sliders()` — 删除 outfit_config 文件

在 [`reset_all_sliders()`](core/body_slider_func.py:1245) 内部（约第 1270 行 outfit 目录删除之后）：

```python
# 删除 outfit_config 文件
self.outfit_config_mgr.delete_config(char_id)
```

#### 2d. `_on_outfits_unload_all()` — 删除 outfit_config 文件

在 [`_on_outfits_unload_all()`](core/body_slider_func.py:753) 内部（约第 755 行之后）：

```python
# 删除 outfit_config 文件
self.outfit_config_mgr.delete_config(char_id)
```

#### 2e. `reset_character_to_default()` — 删除 outfit_config 文件

在 [`reset_character_to_default()`](core/body_slider_func.py:1211) 内部（约第 1241 行 `_refresh_3d_preview` 之前）：

```python
# 删除 outfit_config 文件
self.outfit_config_mgr.delete_config(char_id)
```

### 3. 修改 `core/outfit_manager.py`

#### 3a. `OutfitHost` — 新增 outfit_config_mgr 属性

```python
@property
def outfit_config_mgr(self):
    return getattr(self._app, "outfit_config_mgr", None)
```

#### 3b. `unload_all_outfits()` — 删除 outfit_config 文件

在方法末尾（约第 436 行 `h.sync_outfits_panel_for_char(char_id)` 之前）：

```python
# 删除 outfit_config 文件
ocm = h.outfit_config_mgr
if ocm:
    ocm.delete_config(char_id)
```

### 4. 修改 `core/ui_outfits.py` — 核心改动

#### 4a. `load_sliders()` — 从 JSON 加载已保存的配置

在 [`load_sliders()`](core/ui_outfits.py:346) 中，遍历 `outfit_sliders_info` 时：

```python
# 初始化 link states 和 slider values 时，优先使用 JSON 中保存的值
for key, info in outfit_sliders_info.items():
    # 尝试从 outfit_config 加载已保存的配置
    saved = self._load_saved_slider_config(key, info)
    
    if key not in self.main.outfit_link_states:
        self.main.outfit_link_states[key] = saved.get("is_linked", True)
    if key not in self.main.outfit_slider_values:
        # 如果 is_linked=true，使用角色滑块的值
        if not saved.get("is_linked", True) and saved:
            self.main.outfit_slider_values[key] = saved.get("current_value", info.get("current_value", 0.0))
        else:
            self.main.outfit_slider_values[key] = info.get("current_value", 0.0)
    self.main.outfit_slider_mapping[key] = info.get("char_slider_id")
```

#### 4b. `_add_slider_row()` — 加载已保存的 is_linked 和 current_value

在 [`_add_slider_row()`](core/ui_outfits.py:395) 中：

```python
# 从 outfit_config 加载已保存的配置
saved = self._load_saved_slider_config(outfit_key, info)
is_linked = saved.get("is_linked", True) if saved else True
self.main.outfit_link_states[outfit_key] = is_linked

# 确定初始值
if is_linked:
    # 链接状态：使用角色滑块的值
    def_v = float(info.get("current_value", 0))
else:
    # 独立状态：使用 JSON 中保存的值
    def_v = float(saved.get("current_value", info.get("current_value", 0))) if saved else float(info.get("current_value", 0))
```

链接按钮的初始状态也根据 `is_linked` 设置。

#### 4c. `_add_slider_row()` — 滑块值变化时保存

修改 `update_logic` 函数：

```python
def update_logic(v: float, ok=True):
    try:
        info["current_value"] = v
        self.outfitSliderValueChanged.emit(outfit_key, v, char_slider_id)
        
        # 保存配置（仅在未链接状态下保存 current_value）
        linked = self.main.outfit_link_states.get(outfit_key, True)
        if not linked:
            self._save_slider_config(outfit_key, info, v)
    except Exception:
        pass
```

#### 4d. `_toggle_outfit_link()` — 保存 is_linked 状态

在 [`_toggle_outfit_link()`](core/ui_outfits.py:501) 中：

```python
# 切换后保存 is_linked 状态
self._save_slider_link_state(outfit_key, info, new_linked)
```

#### 4e. 新增辅助方法

```python
def _get_outfit_key_from_info(self, info: Dict) -> str:
    """从 slider info 中提取 outfit 文件的 mod_path（需要在 load_sliders 时传入）"""

def _load_saved_slider_config(self, outfit_key: str, info: Dict) -> Optional[Dict]:
    """
    从 outfit_config/{char_id}.json 加载已保存的滑块配置。
    返回 slider_info 字典或 None。
    """
    ocm = getattr(self.main, "outfit_config_mgr", None)
    if not ocm:
        return None
    short_id = info.get("short_id", "")
    return ocm.get_slider(self.char_id, outfit_key, short_id)

def _save_slider_config(self, outfit_key: str, info: Dict, current_value: float):
    """保存滑块的 current_value 到 outfit_config JSON（仅 is_linked=false 时调用）"""
    ocm = getattr(self.main, "outfit_config_mgr", None)
    if not ocm:
        return
    short_id = info.get("short_id", "")
    slider_data = {
        "name": info.get("name", short_id),
        "min": float(info.get("min", -50)),
        "max": float(info.get("max", 150)),
        "current_value": current_value,
        "is_linked": False,
    }
    ocm.save_slider(self.char_id, outfit_key, short_id, slider_data)

def _save_slider_link_state(self, outfit_key: str, info: Dict, is_linked: bool):
    """保存 is_linked 状态切换"""
    ocm = getattr(self.main, "outfit_config_mgr", None)
    if not ocm:
        return
    short_id = info.get("short_id", "")
    # 加载现有配置，只修改 is_linked
    saved = self._load_saved_slider_config(outfit_key, info)
    slider_data = {
        "name": info.get("name", short_id),
        "min": float(info.get("min", -50)),
        "max": float(info.get("max", 150)),
        "current_value": self.main.outfit_slider_values.get(outfit_key, 0.0),
        "is_linked": is_linked,
    }
    if saved and not is_linked:
        # 断开链接时保留之前保存的 current_value
        slider_data["current_value"] = saved.get("current_value", slider_data["current_value"])
    ocm.save_slider(self.char_id, outfit_key, short_id, slider_data)
```

### 5. 修改 `core/main_window.py`

#### 5a. `_on_outfit_slider_value_changed()` — 集成 is_linked 持久化

在 [`_on_outfit_slider_value_changed()`](core/main_window.py:1223) 中：

当前的 linked/unlinked 分支逻辑基本保持不变。但需要在 unlinked 分支中增加保存 outfit_config 的逻辑：

```python
def _on_outfit_slider_value_changed(self, outfit_key, value, char_slider_id):
    linked = self.outfit_link_states.get(outfit_key, True)
    
    if linked and char_slider_id and char_slider_id in self.sliders_info:
        # 现有逻辑不变
        ...
    else:
        # Unlinked state
        self.outfit_slider_values[outfit_key] = value
        # 保存独立值到 outfit_config
        # （实际保存在 ui_outfits.py 的 update_logic 中触发）
        if hasattr(self, "outfit_mgr") and self.outfit_mgr:
            self.outfit_mgr.update_outfit_morphs()
```

---

## 数据流图

```
                    outfit_config/{char_id}.json
                           │
                           │ 加载
                           ▼
        ┌─────────────────────────────────┐
        │   OutfitConfigManager           │
        │   load_config / save_config     │
        │   save_slider / get_slider      │
        │   delete_config                 │
        └─────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
   load_sliders()   _add_slider_row()   _toggle_outfit_link()
   读取保存的配置    读取 is_linked       保存 is_linked 切换
   初始化 UI        初始化 UI 值        保存 current_value
                                        (当 is_linked=false)
         
         │
         ▼ (滑块值变化)
   update_logic() ──→ 保存 current_value (仅 is_linked=false)
                      emit outfitSliderValueChanged
                      ──→ _on_outfit_slider_value_changed()
                           ──→ update_outfit_morphs()
```

### 删除场景

```
delete_character() ──→ outfit_config_mgr.delete_config(char_id)
reset_all_sliders()  ──→ outfit_config_mgr.delete_config(char_id)
reset_character_to_default() ──→ outfit_config_mgr.delete_config(char_id)
_on_outfits_unload_all() ──→ outfit_config_mgr.delete_config(char_id)
unload_all_outfits() ──→ outfit_config_mgr.delete_config(char_id)
```

---

## 实现顺序

1. **创建 `core/outfit_config_manager.py`** — 纯数据层，无 UI 依赖
2. **修改 `core/body_slider_func.py`** — 初始化 manager，在删除/重置场景中调用 `delete_config`
3. **修改 `core/outfit_manager.py`** — `OutfitHost` 新增属性，`unload_all_outfits` 调用删除
4. **修改 `core/ui_outfits.py`** — 核心改动：加载/保存配置、is_linked 逻辑
5. **修改 `core/main_window.py`** — 微调 `_on_outfit_slider_value_changed`

---

## 注意事项

1. **向后兼容**: 如果 `outfit_config/{char_id}.json` 不存在，使用默认值（`is_linked=true`，`current_value` 从角色滑块读取）
2. **outfit_key 的确定**: 在 `load_sliders()` 中，`outfit_key` 形如 `"outfit_breast_size_type_01"`。需要用当前激活的 outfit 的 `mod_path` 作为顶层 key。需要在 `OutfitSlidersPanel` 中保存当前 outfit 的 `mod_path`。
3. **性能**: 每次滑块值变化都写入 JSON 可能频繁。考虑在 `save_slider` 中不做防抖，因为 JSON 文件较小，写入速度快。
4. **路径字段**: `path` 字段存储对应角色滑块的目标 mesh 路径，用于参考。可以从 `sliders_info[char_slider_id]["path"]` 获取。
