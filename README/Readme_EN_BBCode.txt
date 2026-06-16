[size=5][color=#ffffff][b]Body Slider Pro[/b][/color][/size]
[color=#FFA500]Body & model customization tool for Crimson Desert[/color]

[line]

[size=4][color=#ffffff][b]What is this?[/b][/color][/size]

A slider-based tool to morph [b]any model[/b] in Crimson Desert: bodies, faces, clothes, monsters, props - if it has a .pac file, you can create sliders for it.

[list]
[*][b]Regular users[/b]: Use built-in sliders to adjust body shapes.[/*]
[*][b]Advanced users[/b]: Import other mods' .pac files to create sliders.[/*]
[*][b]Modders[/b]: Edit meshes in 3D software, then generate custom sliders.[/*]
[/list]

[line]

[size=4][color=#ffffff][b]How It Works[/b][/color][/size]

[list]
[*][b]Original Mesh[/b] = base model from the game (.pac)[/*]
[*][b]Target Mesh[/b] = edited model (same topology & UVs)[/*]
[*][b]Slider[/b] = smooth blend between the two[/*]
[/list]

[line]

[size=4][color=#ffffff][b]Quick Start (Regular Users)[/b][/color][/size]

[list]
[*][size=3]Select a character from the top tabs (e.g. Damiane).[/size][/*]
[*][size=3]Drag sliders to adjust your body; preview in the 3D view.[/size][/*]
[*](Optional) To morph toward another mod's body:
 - Find its .pac file.  (e.g. [color=#FFA500]cd_[i]phw_00_nude_00_0001_damian.pac[/i][/color] for Damiane‘s nude body)
 - Click [b]+ Add Custom Slider[/b] → choose that .pac as Target Mesh.
 - Click [b]Export as MOD Folder[/b], then copy the folder from /exported_mod/ into the path where your Mod Manager stores mods.[/*]
[/list]

[line]

[size=4][color=#ffffff][b]For Modders[/b][/color][/size]

[list]
[*][size=3]Add a character: [b]+ Add Character[/b] → set Name, ID, Original PAC, Mod Path.[/size][/*]
[*][size=3]Export OBJ: [b]Export Model (.obj)[/b] → open in Blender (sliders at 0).[/size][/*]
[*][size=3]Edit the mesh: move vertices only. [color=#FFA500]Do NOT change vertex count, topology, or UVs.[/color][/size][/*]
[*][size=3]Export as .obj with the same structure.[/size][/*]
[*][size=3]Create slider: [b]+ Add Custom Slider[/b] → select your edited .obj as Target Mesh → set range.[/size][/*]
[*][size=3][b]Export as MOD Folder[/b] to generate a ready-to-use mod, or [b]Save/Share Character Pack[/b] to share your setup.[/size][/*]
[/list]
[size=3][color=#FFA500]If your mesh is based on another creator's work, get permission before sharing.[/color][/size]

[line]

[size=4][color=#ffffff][b]Notes[/b][/color][/size]

[list]
[*][size=3]Sliders require identical structure between Original PAC and Target Mesh.[/size][/*]
[*][size=3]For crashes, see crash_report/ and attach the log when reporting bugs.[/size][/*]
[/list]

[line]

[size=3][color=#87CEEB][b]Credits[/b][/color]
Inspired by [b]Crimson Desert Mod Workbench[/b]:
[url=https://www.nexusmods.com/crimsondesert/mods/826]https://www.nexusmods.com/crimsondesert/mods/826[/url][/size]