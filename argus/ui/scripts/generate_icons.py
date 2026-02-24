#!/usr/bin/env python3
"""Generate PWA icons for ARGUS Command Center.

Creates the "A" icon with:
- Background: #0f1117 (argus-bg)
- Letter: #3b82f6 (argus-accent), bold, centered

Sizes generated:
- 192x192, 512x512 (regular)
- 192x192, 512x512 (maskable with safe zone padding)
- 180x180 (apple-touch-icon)
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Colors
BG_COLOR = (15, 17, 23)  # #0f1117
ACCENT_COLOR = (59, 130, 246)  # #3b82f6


def get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Get the best available font at the specified size."""
    # Try system fonts (macOS paths)
    font_paths = [
        "/System/Library/Fonts/SFNSDisplay.ttf",
        "/System/Library/Fonts/SFCompactDisplay.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/Library/Fonts/Arial Bold.ttf",
        "/Library/Fonts/Arial.ttf",
    ]

    for font_path in font_paths:
        if Path(font_path).exists():
            try:
                return ImageFont.truetype(font_path, size)
            except OSError:
                continue

    # Fallback to default font (won't be as nice but works)
    return ImageFont.load_default()


def create_icon(size: int, maskable: bool = False) -> Image.Image:
    """Create an ARGUS icon at the specified size.

    Args:
        size: Icon size in pixels (square).
        maskable: If True, add safe zone padding for maskable icons.

    Returns:
        PIL Image object.
    """
    img = Image.new("RGB", (size, size), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # For maskable icons, the safe zone is 80% of the icon
    # so we need to shrink the content to fit within that
    if maskable:
        content_size = int(size * 0.7)  # Leave more room for various mask shapes
        offset = (size - content_size) // 2
    else:
        content_size = size
        offset = 0

    # Font size relative to content area
    font_size = int(content_size * 0.65)
    font = get_font(font_size)

    # Draw the "A" centered
    text = "A"

    # Get text bounding box for centering
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Calculate center position
    x = offset + (content_size - text_width) // 2 - bbox[0]
    # Adjust y to be visually centered (accounting for baseline)
    y = offset + (content_size - text_height) // 2 - bbox[1] - int(content_size * 0.02)

    draw.text((x, y), text, font=font, fill=ACCENT_COLOR)

    return img


def main() -> None:
    """Generate all required icons."""
    script_dir = Path(__file__).parent
    public_dir = script_dir.parent / "public"
    icons_dir = public_dir / "icons"
    icons_dir.mkdir(exist_ok=True)

    # Regular icons
    print("Generating regular icons...")
    sizes = [192, 512]
    for size in sizes:
        icon = create_icon(size, maskable=False)
        path = icons_dir / f"icon-{size}.png"
        icon.save(path, "PNG")
        print(f"  Created {path.name}")

    # Maskable icons (with safe zone padding)
    print("Generating maskable icons...")
    for size in sizes:
        icon = create_icon(size, maskable=True)
        path = icons_dir / f"icon-maskable-{size}.png"
        icon.save(path, "PNG")
        print(f"  Created {path.name}")

    # Apple touch icon (180x180)
    print("Generating Apple touch icon...")
    apple_icon = create_icon(180, maskable=False)
    apple_path = public_dir / "apple-touch-icon.png"
    apple_icon.save(apple_path, "PNG")
    print(f"  Created {apple_path.name}")

    print("\nAll icons generated successfully!")


if __name__ == "__main__":
    main()
