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
- **Far right** (optional): Outfits panel, displayed when the current character has outfit data.
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
| **▶/◀ Show/Hide Outfits Panel** | Toggle the outfits panel on the right (only appears when outfit data exists). |
| **Unload All Outfits** | Delete all outfit data for the current character. |
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

1. Find that mod's `.pac` file (e.g. `cd_phw_00_nude_00_0001_damian.pac` for Damiane).
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

Body Slider Pro supports loading and managing outfits for characters. Outfit data is imported via **Character Packs**, and once loaded, outfits will deform in sync with body sliders.

### How to Get Outfits

Outfit data is provided by mod authors packaged in character packs (`.zip`). Simply use the **Load Character Pack** feature to import a character pack that includes outfit data.

### How to Use Outfits

1. After importing a character pack with outfit data, a **▶/◀ button** will appear on the right side of the interface.
2. Click the button to expand the **Outfits Panel**, which displays available outfit files (`.pac` / `.obj`) in a file tree.
3. **Click** an outfit file to **activate** it. The outfit will appear in the 3D preview and deform in sync with the current slider values.
4. **Click again** on an activated outfit to **deactivate** it.
5. Click **Unload All Outfits** to delete all outfit data for the current character.

### Notes

- The Outfits panel only appears when the current character has outfit data.
- Activated outfits deform in real-time with all body sliders.
- When exporting a MOD, configured outfit data is included in the package.

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
| `crash_report/` | Automatic crash logs. Include these when reporting bugs. |

---

## Common Tips

- **Accurate preview**: Use **Wireframe** and **Reset Camera** to inspect the model.
- **Reset sliders**: Use **Reset** to return all sliders for the current character to 0.
- **Multiple characters**: Manage different characters (or outfits) with separate tabs.
- **Character sorting**: Use **⇋ Sort Characters** to drag and reorder character tabs.
- **Sharing**: Use **Save/Share Character Pack** to back up or share your setups (including outfit data).
- **Outfit management**: Use the right-side Outfits panel to quickly switch and preview different outfits.

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