#!/usr/bin/env bash
set -e

REPO_URL="https://github.com/pangzhe/qcode.git"
INSTALL_DIR="${QCODE_DIR:-$HOME/.qcode-install}"

echo ""
echo "  ╔══════════════════════════════════╗"
echo "  ║      Qcode Installer             ║"
echo "  ╚══════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "  Error: python3 is required but not found."
    echo "  Install Python 3.10+ first."
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo "  Error: Python 3.10+ required, found $PYTHON_VERSION"
    exit 1
fi
echo "  Python: $PYTHON_VERSION ✓"

# Check pip
if ! python3 -m pip --version &>/dev/null; then
    echo "  Error: pip is required. Install it with:"
    echo "    python3 -m ensurepip --upgrade"
    exit 1
fi
echo "  pip: ✓"

# Clone or update
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "  Updating existing installation..."
    cd "$INSTALL_DIR"
    git pull --quiet 2>/dev/null || true
else
    echo "  Cloning to $INSTALL_DIR ..."
    git clone --quiet "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Install
echo "  Installing qcode..."
python3 -m pip install -e "$INSTALL_DIR" --quiet --break-system-packages 2>/dev/null \
    || python3 -m pip install -e "$INSTALL_DIR" --quiet 2>/dev/null \
    || python3 -m pip install -e "$INSTALL_DIR" --quiet --user

echo ""
echo "  ✓ qcode installed!"
echo ""

# Run setup if no config
CONFIG_FILE="$HOME/.qcode/config.toml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "  No configuration found. Running setup..."
    echo ""
    qcode --setup
else
    echo "  Configuration found at $CONFIG_FILE"
    echo "  Run 'qcode' to start!"
fi

echo ""
