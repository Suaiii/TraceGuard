"""Stitch stable/degraded/conflict single-role figures into one combined tall figure.

Only the bottom-most image keeps the "数据来源" footer.
"""

from pathlib import Path

from PIL import Image

ROLES = ["stable", "degraded", "conflict"]
SRC_DIR = Path("docs/figures/socialmedia")
OUT_BASE = SRC_DIR / "socialmedia_case_combined"


def main():
    images = []
    for role in ROLES:
        path = SRC_DIR / f"socialmedia_case_{role}.png"
        images.append(Image.open(path).convert("RGBA"))

    # All images share the same width; footer occupies ~73 px at the bottom.
    # We keep the footer only on the last (conflict) image.
    footer_height = 80
    w = images[0].width

    cropped_parts = []
    for i, img in enumerate(images):
        if i < len(images) - 1:
            # Crop off the footer area
            cropped = img.crop((0, 0, w, img.height - footer_height))
            cropped_parts.append(cropped)
        else:
            cropped_parts.append(img)  # keep footer on last image

    total_height = sum(im.height for im in cropped_parts)
    combined = Image.new("RGBA", (w, total_height), (255, 255, 255, 255))

    y_offset = 0
    for im in cropped_parts:
        combined.paste(im, (0, y_offset))
        y_offset += im.height

    # Save
    for ext, kwargs in ((".png", {}), (".svg", {}), (".pdf", {})):
        out = Path(str(OUT_BASE) + ext)
        out.parent.mkdir(parents=True, exist_ok=True)
        if ext == ".png":
            combined.save(out, dpi=(300, 300))
        elif ext == ".pdf":
            combined.convert("RGB").save(out)
        else:
            # SVG not directly supported by PIL; skip raster-based SVG
            pass

    # Also save PNG as final combined
    png_path = Path(str(OUT_BASE) + ".png")
    combined.save(png_path, dpi=(300, 300))
    print(f"Saved: {png_path}  ({w}×{total_height})")

    # Close
    for img in images:
        img.close()


if __name__ == "__main__":
    main()
