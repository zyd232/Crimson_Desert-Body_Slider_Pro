"""
快速把 PNG 图标转成 Windows 用的高质量 ICO（多尺寸）。
用法：
    python convert_icon.py "D:/My_Projects/Game Mods/Crimson Desert/Body Slider Outfitter/process/icon/icon_body_slider_outfitter_black.png" core/assets/icon.ico
"""
import sys
from PIL import Image


def png_to_ico(png_path: str, ico_path: str):
    img = Image.open(png_path).convert("RGBA")

    # Windows ICO common sizes, from large to small
    sizes = [
        (512, 512),
        (256, 256),
        (128, 128),
        (64, 64),
        (48, 48),
        (32, 32),
        (16, 16),
    ]

    # Generate each size from the original high-res image
    images = [img.resize(s, Image.LANCZOS) for s in sizes]

    # Save as ICO: first image is primary, others appended.
    # Using large-to-small order improves behavior in Windows Explorer.
    images[0].save(
        ico_path,
        format="ICO",
        append_images=images[1:],
        # Do not use 'sizes' parameter to avoid Pillow-specific quirks
    )

    print(f"OK: {ico_path} (sizes: {sizes})")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python convert_icon.py input.png output.ico")
        sys.exit(1)
    png_to_ico(sys.argv[1], sys.argv[2])