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

# 1. Build and copy standalone compiled binary
if [ ! -f "$PROJECT_DIR/dist/delta" ]; then
    echo "Compiling standalone delta binary using pyinstaller..."
    python3 -m venv "$PROJECT_DIR/venv"
    "$PROJECT_DIR/venv/bin/pip" install pyinstaller
    "$PROJECT_DIR/venv/bin/pyinstaller" --onefile --name delta "$PROJECT_DIR/panco.py"
fi
cp -rf "$PROJECT_DIR/dist/delta" "$APPDIR/usr/bin/delta"
chmod +x "$APPDIR/usr/bin/delta"

# 2. Create entrypoint AppRun script
cat << 'EOF' > "$APPDIR/AppRun"
#!/bin/sh
SELF=$(readlink -f "$0")
HERE=$(dirname "$SELF")

# Run the compiled standalone binary directly
exec "$HERE/usr/bin/delta" "$@"
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

# 4. Generate a blank/invisible transparent icon for AppImage compliance (no logo)
python3 -c "
try:
    from PIL import Image
    img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    img.save('$APPDIR/delta.png')
    print('✔ Generated transparent fallback icon')
except Exception as e:
    print('Error generating fallback icon:', e)
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
