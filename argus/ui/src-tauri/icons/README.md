# ARGUS Tauri Icons

This directory should contain the app icons for the Tauri desktop build.

## Required Icons

Generate these icons from the PWA icons (pwa-512x512.png) in the public directory:

| File | Size | Platform |
|------|------|----------|
| `icon.png` | 512x512 | Tray icon (macOS/Windows/Linux) |
| `32x32.png` | 32x32 | Windows/Linux |
| `128x128.png` | 128x128 | macOS/Windows/Linux |
| `128x128@2x.png` | 256x256 | macOS Retina |
| `icon.icns` | Multi-size | macOS bundle |
| `icon.ico` | Multi-size | Windows bundle |

## Generating Icons

You can use the Tauri CLI to generate icons from a 1024x1024 or 512x512 source:

```bash
# From the ui directory with Tauri CLI installed:
npx tauri icon ../public/pwa-512x512.png
```

Or manually convert using ImageMagick:

```bash
# Install ImageMagick first: brew install imagemagick

# Generate PNG sizes
convert pwa-512x512.png -resize 32x32 32x32.png
convert pwa-512x512.png -resize 128x128 128x128.png
convert pwa-512x512.png -resize 256x256 128x128@2x.png
cp pwa-512x512.png icon.png

# Generate ICO (Windows)
convert pwa-512x512.png -define icon:auto-resize=256,128,64,48,32,16 icon.ico

# Generate ICNS (macOS) - requires iconutil
mkdir icon.iconset
convert pwa-512x512.png -resize 16x16 icon.iconset/icon_16x16.png
convert pwa-512x512.png -resize 32x32 icon.iconset/icon_16x16@2x.png
convert pwa-512x512.png -resize 32x32 icon.iconset/icon_32x32.png
convert pwa-512x512.png -resize 64x64 icon.iconset/icon_32x32@2x.png
convert pwa-512x512.png -resize 128x128 icon.iconset/icon_128x128.png
convert pwa-512x512.png -resize 256x256 icon.iconset/icon_128x128@2x.png
convert pwa-512x512.png -resize 256x256 icon.iconset/icon_256x256.png
convert pwa-512x512.png -resize 512x512 icon.iconset/icon_256x256@2x.png
convert pwa-512x512.png -resize 512x512 icon.iconset/icon_512x512.png
cp pwa-512x512.png icon.iconset/icon_512x512@2x.png
iconutil -c icns icon.iconset
rm -rf icon.iconset
```

## Quick Setup

For quick testing, just copy the PWA icon:

```bash
cp ../public/pwa-512x512.png icon.png
```

The other icons are only needed for distribution builds.
