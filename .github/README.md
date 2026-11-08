# Body Slider Pro - User Manual

> **Crimson Desert** body & model customization tool.  
> Simple to use, powerful for modders.

---

## What is Body Slider Pro?

Body Slider Pro is a sliding-control tool for **Crimson Desert** models.

Although "Body" is in the name, it can create sliders for **any model** in the game:
- Character body shapes
- Face shapes
- Clothing
- Monsters
- Props and items

If you can find its `.pac` file, you can create sliders for it.

This means:
- **Regular users** can adjust built-in sliders to customize body shapes.
- **Advanced users** can import other mods' `.pac` files to create sliders based on them.
- **Modders** can edit models in 3D software, then build custom sliders from the edited meshes.

---

## How It Works (Brief)

1. The tool extracts the game's original mesh (called **Original Mesh**) from a `.pac` file.
2. You edit the mesh (without changing its topology or UVs). The edited mesh is the **Target Mesh**.
3. Because the topology is unchanged, Body Slider Pro builds a **Vertex Deformer** between the Original Mesh and Target Mesh to create sliders.
4. Because the UVs are unchanged, no texture modifications are required.

In short:
- Original Mesh = base model
- Target Mesh = modified model (same structure)
- Slider = blends between them

---

## Interface Overview

When you open Body Slider Pro, you will see:

- **Left panel**: 3D model preview.
- **Right panel**: Character tabs, sliders, and controls.
- **Far right** (optional): Outfit panel area, including Outfit file tree, Outfit Default Sliders, and Outfit Custom Sliders panels.
- **Top bar**: Language selector, character tabs, character actions, and global buttons.

### Key Buttons

| Button | Description |
|---|---|
| **+ Add Character** | Add a new character to manage. |
| **⇋ Sort Characters** | Drag to reorder character tabs. |
| **Edit Properties** (per character) | Edit that character's properties: Name, ID, Original PAC, Mod Path. |
| **× Delete** (per character) | Delete the character and its related files. |
| **Reset** | Reset all slider values for the current character to 0. |
| **Reset All** | Reset all character settings and sliders to default. |
| **+ Add Custom Slider** | Create a new custom slider using a Target Mesh. |
| **Export Model (.obj)** | Export the current model as `.obj` for editing in 3D software. |
| **Export as MOD Folder** | Package the current sliders into a ready-to-use MOD. |
| **Reset Camera** | Reset the 3D view to default. |
| **Wireframe** | Toggle wireframe overlay on the 3D model. |
| **▶/◀ Show/Hide Outfits Panel** | Toggle the outfit panel area on the right (only appears when outfit data exists). |
| **Unload All Outfits** | Delete all outfit data for the current character. |
| **+ Add Outfit Custom Slider** | Create an independent custom slider for the currently activated outfit. |
| **Export Outfit Model (.obj)** | Export the currently activated outfit as `.obj` file. |
| **Save/Share Character Pack** | Export your character configuration (and sliders) as a `.zip` pack. |
| **Load Character Pack** | Import a character pack (your own or from others; may include outfit data). |

---

## Quick Start (For Regular Users)

You just want to adjust your body shape. No modding knowledge required.

### Step 1: Select a Character

- Use the character tabs on the top bar to switch characters.
- Default character (e.g. **Damiane**) is ready to use.

### Step 2: Adjust Sliders

- Drag sliders under **Default Sliders** to adjust your body.
- Preview changes in the 3D view on the left.

### Step 3: Use Someone Else's Body MOD (Optional)

If you like another modder's body shape and want sliders for it:

1. Find that mod's `.pac` file (e.g. `phw_00_nude_00_0001_damian.pac` for Damiane; older game versions used `cd_phw_00_nude_00_0001_damian.pac`).
   - Important: It must be the **same character/item** as your Original PAC.
2. In Body Slider Pro:
    - Click **+ Add Custom Slider**.
    - Enter a slider name.
    - For **Target Mesh**, choose that `.pac` file.
3. Adjust the new slider to blend between default and that mod's shape.
4. Click **Export as MOD Folder**.
5. Copy the folder from `/exported_mod/` into your Mod Manager's MODs directory and enable it.

Done.

---

## Outfits System

Body Slider Pro supports loading and managing outfits for characters. Outfit data is imported via the **Load Character Pack** feature, and once loaded, outfits will deform in sync with body sliders.

Three outfit-related panels appear on the right side (from left to right):
- **Outfits Panel**: File tree displaying available outfit files (`.pac` / `.obj`).
- **Outfit Default Sliders Panel**: Outfit deformation sliders corresponding to character default sliders.
- **Outfit Custom Sliders Panel**: Deformation controls for character custom sliders + independent outfit custom sliders.

### How to Get Outfits

Outfit data is provided by mod authors packaged in character packs (`.zip`). Simply use the **Load Character Pack** feature to import a character pack that includes outfit data.

When importing, if a character with the same ID already exists and has outfit data, you will be prompted to choose:
- **Overwrite**: Replace all existing outfit data with the imported data.
- **Merge**: Merge outfit data, resolving conflicts for duplicate files one by one.

### How to Use Outfits

1. After importing a character pack with outfit data, a **▶/◀ button** will appear on the right side of the interface.
2. Click the button to expand the outfit panel area, showing the outfit file tree and slider panels.
3. **Click** an outfit file to **activate** it. The outfit will appear in the 3D preview (displayed in orange) and deform in sync with the current slider values.
4. **Click again** on an activated outfit to **deactivate** it.
5. Click **Unload All Outfits** to delete all outfit data for the current character (including `original_outfit/{char_id}` and `exported_outfit/{char_id}` directories).

### Outfit File Tree Controls

The outfit file tree provides the following toolbar buttons:
- **Expand All / Collapse All**: Quickly expand or collapse all folders.
- **Refresh**: Rescan outfit files from disk.
- **Select All / Deselect All**: Batch check or uncheck all outfit files (checkbox marks do not represent activation).

### Outfit Slider System

After activating an outfit, two panels — **Outfit Default Sliders** and **Outfit Custom Sliders** — appear on the right, allowing you to control how much the outfit deforms with body shape changes.

#### Outfit Default Sliders

One-to-one correspondence with character default sliders (such as breast size, waist, hips, etc.). Each slider is **linked** (synced) to the character slider by default, meaning dragging the character slider will automatically move the outfit slider.

#### Outfit Custom Sliders

Contains two types:
1. **Outfit sliders for character custom sliders** — Corresponding to custom sliders you created in the character panel.
2. **Independent outfit custom sliders** — Sliders created specifically for the outfit, independent of character sliders (see below).

#### Link / Unlink

Each outfit slider has a **link button** on the left side:
- **🔗 (Linked)**: The outfit slider value syncs with the corresponding character slider. Dragging the character slider will automatically deform the outfit.
- **⛓️‍💥 (Unlinked)**: The outfit slider value is independent of the character slider, allowing you to adjust the outfit deformation separately without affecting the character body.

Click the button to toggle between the two states. When unlinked, the slider value is saved to the `outfit_config/` directory and will be restored on next launch.

Each slider also has a **Reset** button to return that slider's value to 0.

### Independent Outfit Custom Sliders

In addition to following character sliders, you can **create custom sliders specifically for the currently activated outfit**, allowing deformation effects that only affect the outfit without affecting the character body.

#### Adding Independent Outfit Custom Sliders

1. Make sure an outfit is activated.
2. Click the **"+ Add Outfit Custom Slider"** button.
3. Enter a slider name and ID (letters, numbers, underscores only).
4. Select a target mesh file (`.obj` or `.pac`) — this is your edited outfit model.
5. Set the range (e.g. `-50,150`).

The created slider will appear in the **Outfit Custom Sliders** panel and will **not** show a link button (because it is independent).

#### Editing and Deleting

Each independent outfit custom slider has:
- **Edit** button: Modify the slider name, ID, or replace the target mesh file.
- **× (Delete)** button: Delete this slider and all related data.

#### Notes

- Target mesh files for independent outfit custom sliders are deployed in the `exported_outfit/{char_id}/custom/{slider_id}/` directory.
- Slider IDs must be unique within the same character.
- When editing models, keep the vertex count and topology consistent with the original outfit.

### Exporting Outfit Model

Click the **"Export Outfit Model (.obj)"** button to export the currently activated outfit as an `.obj` file, which can be edited in Blender or other 3D modeling software. The edited model can then be used to create independent outfit custom sliders.

### Notes

- The Outfits panel only appears when the current character has outfit data.
- Activated outfits deform in real-time with all body sliders.
- When exporting a MOD, configured outfit data is included in the package.
- Some operations (such as deleting a character) are restricted when the character has outfit data. Please **Unload All Outfits** first before performing these operations.

---

## For Modders (Creating Custom Sliders with 3D Software)

This workflow is for creating your own morphs (body, face, clothing, etc.) and sharing them as sliders.

### Step 1: Prepare the Original PAC

1. Use a tool like **Crimson Desert Mod Workbench** to extract the `.pac` file for the model you want to modify.
   - **Important: Do not rename this original PAC file at any step in the workflow.**
2. In Body Slider Pro:
    - Click **+ Add Character**.
    - Fill in:
      - **Character Name**: Display name (e.g. "My Custom Body").
      - **Character ID**: Letters, numbers, underscore only (e.g. `my_body_01`).
      - **Original PAC**: Select the extracted `.pac` file.
      - **Mod Path**: Path relative to the `files` folder (e.g. `character\model\1_pc\2_phw\nude`).

### Step 2: Export OBJ

1. In the character's tab, click **Export Model (.obj)**.
    - Tip: Reset all sliders to 0 before exporting, so the OBJ matches the original model.
2. Open the exported `.obj` in your 3D modeling software (Blender, etc.).

### Step 3: Edit the Model

When editing:

- DO NOT:
  - Change vertex count
  - Change topology (edge flow)
  - Change UV layout
- YOU CAN:
  - Move vertices to reshape the model.

Keep the structure identical; only change positions.

**Recommended UV-preserving workflow (Blender example):**

1. Duplicate the original object as a backup before editing.
2. Add a **Data Transfer** modifier to the object you will edit.
3. In Data Transfer settings:
    - Set **Source** to the duplicated backup object.
    - Enable **Face Corner Data** → check **UVs**, Mapping: **Topology**.
    - Enable **Face Data**, Mapping: **Topology**.
4. Edit the mesh in Edit Mode while avoiding structural UV changes (e.g., splitting faces, rearranging islands).
5. Tip: Avoid Sculpt Mode unless you are sure it will not alter the UV layout.

### Step 4: Export Edited Model

- Export your edited model as `.obj`.
- Ensure:
  - Object count and names match the original OBJ.
  - Same vertex count and structure.

### Step 5: Create a Custom Slider

1. In Body Slider Pro, go to your character's tab.
2. Click **+ Add Custom Slider**.
3. Fill in:
    - **Slider Name**: e.g. "My Custom Bust".
    - **Target Mesh**: Select your edited `.obj` file.
    - **Range**: Min and Max (e.g. `-50,150`).
4. Adjust the slider to confirm the morph looks correct.

### Step 6: Package or Share

You have two options:

- **Export as MOD Folder**:
  - Creates a ready-to-use MOD in `/exported_mod/`.
  - Copy it to your Mod Manager to enable.

- **Save/Share Character Pack**:
  - Exports a `.zip` containing your character config and sliders (including the Target Mesh).
  - Others can import it using **Load Character Pack**.

Important:
- If your Target Mesh is based on another creator's work, **get permission** before sharing.

---

## Folder Structure (Important Directories)

| Folder | Purpose |
|---|---|
| `original_mesh/` | Stores original `.pac`-based meshes per character. |
| `target_mesh/` | Stores target meshes used by sliders. |
| `exported_mesh/` | Folder for exported OBJ files. |
| `exported_mod/` | Generated MOD folders (ready for Mod Manager). |
| `char_config/` | Character and slider configuration files (`.json`). |
| `original_outfit/` | Stores original outfit data per character (imported via character packs). |
| `exported_outfit/` | Stores processed outfit data (deforms with sliders). |
| `outfit_config/` | Stores independent outfit slider configurations (link states, unlinked values, etc.). |
| `crash_report/` | Automatic crash logs. Include these when reporting bugs. |

---

## Common Tips

- **Accurate preview**: Use **Wireframe** and **Reset Camera** to inspect the model.
- **Reset sliders**: Use **Reset** to return all sliders for the current character to 0.
- **Multiple characters**: Manage different characters (or outfits) with separate tabs.
- **Character sorting**: Use **⇋ Sort Characters** to drag and reorder character tabs.
- **Sharing**: Use **Save/Share Character Pack** to back up or share your setups (including outfit data).
- **Outfit management**: Use the right-side Outfits panel to quickly switch and preview different outfits.
- **Show/Hide outfits**: Use **▶/◀ Show/Hide Outfits Panel** to toggle the outfit panel area.
- **Independent outfit deformation**: Unlink outfit sliders from character sliders to adjust outfit deformation independently.
- **Outfit custom sliders**: Create independent deformation effects for outfits without affecting the character body.

---

## Bug Reports

If Body Slider Pro crashes or behaves unexpectedly:

1. Open the `crash_report/` folder.
2. Find the log file matching the time of the issue (by timestamp).
3. When reporting the bug, attach that log file.

---

## Notes

- Sliders only work when the Original PAC and Target Mesh share the same structure (same submesh count, names, and vertex counts).
- If you see "Mesh Incompatible," check that both meshes come from the same base model.

---

## How to Add a Language Translation

If you want to add a new language to Body Slider Pro:

1. In the `language/` folder, copy an existing file, such as `en.json`.
2. Name the new file with the target language code, e.g. `ja.json` (Japanese), `fr.json` (French).
3. Open it in a text editor:
    - Change `"lang_name"` to the display name of that language (e.g. `"Japanese"`).
    - Translate all values (the text on the right side of each `:`) into the target language.
    - Do NOT change the keys (text on the left), commas, or braces.
4. Save the file, restart Body Slider Pro, and select the new language from the top language selector.

If something looks wrong, compare your file with `en.json` to ensure no keys were missed or altered.

---

## Credits

The `.pac` unpacking/packing and incremental mesh editing in this tool were inspired by:

- **Crimson Desert Mod Workbench**
  - Nexus Mods: https://www.nexusmods.com/crimsondesert/mods/826
  - GitHub: https://github.com/Ratty123/crimson-desert-mod-workbench
