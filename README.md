# Clipboard Drop

macOS menu bar app for saving clipboard content (text and screenshots) for quick retrieval later. Like a long-term clipboard.

## How It Works

Click the **📎** icon in your menu bar to save and browse clips.

- **Save Clipboard** (or press `Cmd+Shift+V` anywhere) — grabs clipboard content and saves it
- **Click a clip** — opens a dark-mode floating preview with a **Copy** button to put it back on your clipboard
- **Escape** — closes the preview
- Text shown in monospace, images shown centered
- Max 50 clips, oldest auto-pruned, duplicates skipped

## Install

```bash
git clone https://github.com/jcoble/clipboard-drop.git
cd clipboard-drop
bash install.sh
```

## Run

```bash
./venv/bin/python3 clipboard_drop.py
```

Auto-start on login:
```bash
launchctl load ~/Library/LaunchAgents/com.clipboard-drop.plist
```

## Stack

- `rumps` — menu bar
- `pyobjc` — NSPanel + WKWebView preview, NSPasteboard clipboard access
- `pynput` — global hotkey
