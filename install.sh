#!/bin/bash
# Clipboard Drop - Install Script
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$APP_DIR/venv"
PLIST_NAME="com.clipboard-drop.plist"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "=== Clipboard Drop Installer ==="
echo "App directory: $APP_DIR"
echo ""

# Create virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists."
fi

# Install dependencies
echo "Installing dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt" --quiet
echo "Dependencies installed."

# Create clips directory
mkdir -p "$APP_DIR/clips"

# Create Launch Agent plist
echo "Creating Launch Agent for auto-start..."
mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_NAME</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_DIR/bin/python3</string>
        <string>$APP_DIR/clipboard_drop.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>$APP_DIR/logs/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$APP_DIR/logs/stderr.log</string>
    <key>WorkingDirectory</key>
    <string>$APP_DIR</string>
</dict>
</plist>
PLIST

mkdir -p "$APP_DIR/logs"
echo "Launch Agent created at: $PLIST_PATH"

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Usage:"
echo "  Start now:     $VENV_DIR/bin/python3 $APP_DIR/clipboard_drop.py"
echo "  Auto-start:    launchctl load $PLIST_PATH"
echo "  Stop:          launchctl unload $PLIST_PATH"
echo ""
echo "The app will appear as 📎 in your menu bar."
echo "Press Cmd+Shift+V anywhere to save clipboard!"
