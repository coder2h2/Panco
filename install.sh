#!/bin/bash
set -e

# Default to user-level install
PANCO_DIR="$HOME/.pco"
BIN_DIR="$HOME/.local/bin"
USE_SUDO=""

# Parse flags
if [ "$1" = "--global" ] || [ "$1" = "-g" ]; then
    PANCO_DIR="/opt/panco"
    BIN_DIR="/usr/local/bin"
    if [ "$EUID" -ne 0 ]; then
        echo "Note: Installing system-wide requires root privileges. Using sudo..."
        USE_SUDO="sudo"
    fi
fi

echo "Installing Panco interpreter..."

# Verify Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found. Please install python3 first." >&2
    exit 1
fi

# Create target directories
if [ -n "$USE_SUDO" ]; then
    sudo mkdir -p "$PANCO_DIR"
    sudo mkdir -p "$BIN_DIR"
else
    mkdir -p "$PANCO_DIR"
    mkdir -p "$BIN_DIR"
fi

# Copy source files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -n "$USE_SUDO" ]; then
    sudo cp -rf "$SCRIPT_DIR/panco.py" "$PANCO_DIR/panco.py"
    sudo cp -rf "$SCRIPT_DIR/install_gui.py" "$PANCO_DIR/install_gui.py"
    sudo cp -rf "$SCRIPT_DIR/interpreter" "$PANCO_DIR/"
    sudo chmod +x "$PANCO_DIR/panco.py"
    sudo ln -sf "$PANCO_DIR/panco.py" "$BIN_DIR/delta"
else
    cp -rf "$SCRIPT_DIR/panco.py" "$PANCO_DIR/panco.py"
    cp -rf "$SCRIPT_DIR/install_gui.py" "$PANCO_DIR/install_gui.py"
    cp -rf "$SCRIPT_DIR/interpreter" "$PANCO_DIR/"
    chmod +x "$PANCO_DIR/panco.py"
    ln -sf "$PANCO_DIR/panco.py" "$BIN_DIR/delta"
fi

echo "✔ Panco successfully installed to $PANCO_DIR"
echo "✔ Symlink created at $BIN_DIR/delta"
echo ""
echo "To verify the installation, run:"
echo "  delta"
echo ""
if [ -z "$USE_SUDO" ] && [ "$EUID" -ne 0 ]; then
    echo "Note: Make sure $BIN_DIR is in your PATH. If the command 'delta' is not found, add this to your shell config file (~/.bashrc or ~/.zshrc):"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi
