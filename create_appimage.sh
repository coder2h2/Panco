#!/bin/bash
set -e

# Directories
PROJECT_DIR="/home/ip-ascii/panco"
APPDIR="$PROJECT_DIR/delta.AppDir"
BUILD_DIR="$PROJECT_DIR/build_appimage"

echo "Creating AppImage build structure..."
rm -rf "$APPDIR" "$BUILD_DIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$BUILD_DIR"

# 1. Copy script and interpreter source code
cp -rf "$PROJECT_DIR/panco.py" "$APPDIR/usr/bin/panco.py"
cp -rf "$PROJECT_DIR/interpreter" "$APPDIR/usr/bin/"
chmod +x "$APPDIR/usr/bin/panco.py"

# 2. Create entrypoint AppRun script
cat << 'EOF' > "$APPDIR/AppRun"
#!/bin/sh
SELF=$(readlink -f "$0")
HERE=$(dirname "$SELF")

# Run the python interpreter targeting the bundled script
exec python3 "$HERE/usr/bin/panco.py" "$@"
EOF
chmod +x "$APPDIR/AppRun"

# 3. Create desktop entry file
cat << 'EOF' > "$APPDIR/delta.desktop"
[Desktop Entry]
Type=Application
Name=delta
Exec=delta %F
Icon=delta
Comment=Panco interpreted programming language interpreter
Terminal=true
Categories=Development;
EOF

# 4. Copy and convert Panco Logo to PNG format
LOGO_SRC="/home/ip-ascii/.gemini/antigravity-cli/brain/59d4b6d5-0019-4b9c-bd18-befab5812de0/panco_logo_1781991923899.jpg"
python3 -c "
import shutil
src = '$LOGO_SRC'
dest = '$APPDIR/delta.png'
try:
    from PIL import Image
    img = Image.open(src)
    img.save(dest)
    print('✔ Logo converted successfully to PNG')
except ImportError:
    shutil.copy(src, dest)
    print('✔ Logo copied to target (Pillow not installed)')
"

# 5. Download appimagetool
APPIMAGE_TOOL="$BUILD_DIR/appimagetool-x86_64.AppImage"
echo "Downloading appimagetool..."
curl -sL -o "$APPIMAGE_TOOL" "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
chmod +x "$APPIMAGE_TOOL"

# 6. Execute appimagetool to bundle AppImage
echo "Packaging AppImage..."
# Disable sandbox for appimagetool as it may require it depending on the environment
export ARCH=x86_64
"$APPIMAGE_TOOL" --appimage-extract-and-run "$APPDIR" "$PROJECT_DIR/delta.AppImage"

# Clean up
rm -rf "$BUILD_DIR"
echo "✔ Panco AppImage built successfully at: $PROJECT_DIR/delta.AppImage"
