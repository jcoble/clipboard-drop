#!/usr/bin/env python3
"""
Clipboard Drop - macOS Menu Bar Clip Saver
A lightweight menu bar app for saving and retrieving clipboard content.
"""

import rumps
import json
import time
import base64
from pathlib import Path

import AppKit
import WebKit
import objc

CLIPS_DIR = Path(__file__).parent / "clips"
CLIPS_JSON = CLIPS_DIR / "clips.json"
SETTINGS_PATH = Path(__file__).parent / "settings.json"

# Dark mode CSS for preview windows
PREVIEW_CSS = """
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    color: #e6edf3;
    background: #0d1117;
    padding: 24px 32px;
    margin: 0;
    -webkit-font-smoothing: antialiased;
}
pre {
    background: #161b22;
    padding: 16px;
    border-radius: 6px;
    overflow-x: auto;
    line-height: 1.45;
    border: 1px solid #30363d;
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
    font-size: 13px;
    color: #e6edf3;
    white-space: pre-wrap;
    word-wrap: break-word;
}
.image-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 200px;
    padding: 16px;
}
.image-container img {
    max-width: 100%;
    max-height: 80vh;
    border-radius: 6px;
    border: 1px solid #30363d;
}
.clip-meta {
    color: #8b949e;
    font-size: 12px;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #30363d;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.copy-btn {
    background: #21262d;
    color: #8b949e;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 12px;
    cursor: pointer;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    transition: all 0.15s ease;
}
.copy-btn:hover { background: #30363d; color: #e6edf3; }
.copy-btn.copied { background: #238636; border-color: #238636; color: #fff; }
"""


def load_settings():
    if SETTINGS_PATH.exists():
        with open(SETTINGS_PATH) as f:
            return json.load(f)
    return {"max_clips": 50, "window": {"width": 700, "height": 600, "opacity": 0.95}}


def load_clips():
    if CLIPS_JSON.exists():
        with open(CLIPS_JSON) as f:
            return json.load(f)
    return []


def save_clips(clips):
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CLIPS_JSON, "w") as f:
        json.dump(clips, f, indent=2)


def relative_time(timestamp):
    diff = time.time() - timestamp
    if diff < 60:
        return "just now"
    elif diff < 3600:
        mins = int(diff / 60)
        return f"{mins} min ago"
    elif diff < 86400:
        hrs = int(diff / 3600)
        return f"{hrs} hr{'s' if hrs > 1 else ''} ago"
    elif diff < 172800:
        return "yesterday"
    else:
        days = int(diff / 86400)
        return f"{days} days ago"


def read_clipboard():
    """Read clipboard contents. Returns (type, data) where type is 'text' or 'image'."""
    pb = AppKit.NSPasteboard.generalPasteboard()

    # Check for image first (TIFF is macOS native screenshot format)
    image_types = [AppKit.NSPasteboardTypeTIFF, AppKit.NSPasteboardTypePNG]
    for img_type in image_types:
        data = pb.dataForType_(img_type)
        if data:
            # Convert to PNG
            bitmap = AppKit.NSBitmapImageRep.alloc().initWithData_(data)
            if bitmap:
                png_data = bitmap.representationUsingType_properties_(
                    AppKit.NSBitmapImageFileTypePNG, {}
                )
                if png_data:
                    return ("image", bytes(png_data))

    # Check for text
    text = pb.stringForType_(AppKit.NSPasteboardTypeString)
    if text:
        return ("text", text)

    return (None, None)


def save_clip(clip_type, data):
    """Save a clip to storage. Returns True if saved, False if duplicate."""
    clips = load_clips()
    settings = load_settings()
    max_clips = settings.get("max_clips", 50)
    ts = int(time.time())

    if clip_type == "text":
        # Duplicate detection against most recent clip
        if clips and clips[0]["type"] == "text" and clips[0]["content"] == data:
            return False

        clip = {
            "id": ts,
            "type": "text",
            "content": data,
            "timestamp": ts,
            "preview": data[:80].replace("\n", " "),
        }
        clips.insert(0, clip)

    elif clip_type == "image":
        # Duplicate detection: skip if most recent is also an image with same size
        if clips and clips[0]["type"] == "image":
            prev_file = CLIPS_DIR / clips[0]["filename"]
            if prev_file.exists() and prev_file.stat().st_size == len(data):
                return False

        filename = f"img_{ts}.png"
        filepath = CLIPS_DIR / filename
        filepath.write_bytes(data)

        # Get image dimensions for preview text
        img_rep = AppKit.NSBitmapImageRep.alloc().initWithData_(
            AppKit.NSData.dataWithBytes_length_(data, len(data))
        )
        if img_rep:
            w, h = int(img_rep.pixelsWide()), int(img_rep.pixelsHigh())
            preview = f"Screenshot ({w}x{h})"
        else:
            preview = "Image"

        clip = {
            "id": ts,
            "type": "image",
            "filename": filename,
            "timestamp": ts,
            "preview": preview,
        }
        clips.insert(0, clip)

    # Auto-prune
    while len(clips) > max_clips:
        removed = clips.pop()
        if removed["type"] == "image":
            img_path = CLIPS_DIR / removed["filename"]
            if img_path.exists():
                img_path.unlink()

    save_clips(clips)
    return True


def clear_all_clips():
    """Remove all clips and image files."""
    clips = load_clips()
    for clip in clips:
        if clip["type"] == "image":
            img_path = CLIPS_DIR / clip["filename"]
            if img_path.exists():
                img_path.unlink()
    save_clips([])


def render_text_preview(text, timestamp):
    """Render text clip as dark-mode HTML."""
    import html as html_mod
    escaped = html_mod.escape(text)
    time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
    return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<style>{PREVIEW_CSS}</style>
</head><body>
<div class="clip-meta">
    <span>Text clip &middot; {time_str}</span>
    <button class="copy-btn" onclick="copyClip(this)">Copy</button>
</div>
<pre>{escaped}</pre>
<script>
function copyClip(btn) {{
    window.webkit.messageHandlers.copyClip.postMessage('copy');
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(() => {{ btn.textContent = 'Copy'; btn.classList.remove('copied'); }}, 1500);
}}
</script>
</body></html>"""


def render_image_preview(filename, timestamp):
    """Render image clip as dark-mode HTML with centered image."""
    filepath = CLIPS_DIR / filename
    if not filepath.exists():
        return f"<html><body><p>Image not found: {filename}</p></body></html>"

    img_data = filepath.read_bytes()
    b64 = base64.b64encode(img_data).decode("ascii")
    time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
    return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<style>{PREVIEW_CSS}</style>
</head><body>
<div class="clip-meta">
    <span>Image clip &middot; {time_str}</span>
    <button class="copy-btn" onclick="copyClip(this)">Copy</button>
</div>
<div class="image-container">
    <img src="data:image/png;base64,{b64}">
</div>
<script>
function copyClip(btn) {{
    window.webkit.messageHandlers.copyClip.postMessage('copy');
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(() => {{ btn.textContent = 'Copy'; btn.classList.remove('copied'); }}, 1500);
}}
</script>
</body></html>"""


class FloatingWindow:
    """Native macOS floating window with WKWebView for rendering HTML."""

    def __init__(self):
        self._panel = None
        self._webview = None
        self._current_clip_id = None
        self._current_clip = None
        self._copy_handler = None

    def _ensure_panel(self):
        if self._panel is not None:
            return

        settings = load_settings()
        win_cfg = settings.get("window", {})
        width = win_cfg.get("width", 700)
        height = win_cfg.get("height", 600)
        opacity = win_cfg.get("opacity", 0.95)

        screen = AppKit.NSScreen.mainScreen().frame()
        x = (screen.size.width - width) / 2
        y = (screen.size.height - height) / 2
        frame = AppKit.NSMakeRect(x, y, width, height)

        style = (
            AppKit.NSTitledWindowMask
            | AppKit.NSClosableWindowMask
            | AppKit.NSResizableWindowMask
            | AppKit.NSUtilityWindowMask
        )
        self._panel = AppKit.NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            frame, style, AppKit.NSBackingStoreBuffered, False
        )
        self._panel.setLevel_(AppKit.NSFloatingWindowLevel)
        self._panel.setAlphaValue_(opacity)
        self._panel.setReleasedWhenClosed_(False)
        self._panel.setHidesOnDeactivate_(False)
        self._panel.setDelegate_(_ClipPanelDelegate.alloc().initWithWindow_(self))

        # Set up WKWebView with copy message handler
        config = WebKit.WKWebViewConfiguration.alloc().init()
        self._copy_handler = _CopyMessageHandler.alloc().initWithWindow_(self)
        config.userContentController().addScriptMessageHandler_name_(
            self._copy_handler, "copyClip"
        )
        self._webview = WebKit.WKWebView.alloc().initWithFrame_configuration_(
            AppKit.NSMakeRect(0, 0, width, height), config
        )
        self._webview.setAutoresizingMask_(
            AppKit.NSViewWidthSizable | AppKit.NSViewHeightSizable
        )
        self._panel.contentView().addSubview_(self._webview)

    def show_clip(self, clip):
        self._ensure_panel()
        self._current_clip_id = clip["id"]
        self._current_clip = clip

        if clip["type"] == "text":
            html = render_text_preview(clip["content"], clip["timestamp"])
            title = clip["preview"][:50]
        else:
            html = render_image_preview(clip["filename"], clip["timestamp"])
            title = clip["preview"]

        self._webview.loadHTMLString_baseURL_(html, None)
        self._panel.setTitle_(title)
        self._panel.makeKeyAndOrderFront_(None)
        AppKit.NSApp.activateIgnoringOtherApps_(True)

    def hide(self):
        if self._panel:
            self._panel.orderOut_(None)

    def toggle_clip(self, clip):
        if self._panel and self._panel.isVisible() and self._current_clip_id == clip["id"]:
            self.hide()
        else:
            self.show_clip(clip)


class _ClipPanelDelegate(AppKit.NSObject):
    _floating_window = None

    def initWithWindow_(self, floating_window):
        self = objc.super(_ClipPanelDelegate, self).init()
        if self is not None:
            self._floating_window = floating_window
        return self

    def cancelOperation_(self, sender):
        if self._floating_window:
            self._floating_window.hide()

    def windowWillClose_(self, notification):
        pass


class _CopyMessageHandler(AppKit.NSObject):
    """WKScriptMessageHandler that copies clip content to system clipboard."""
    _floating_window = None

    def initWithWindow_(self, floating_window):
        self = objc.super(_CopyMessageHandler, self).init()
        if self is not None:
            self._floating_window = floating_window
        return self

    def userContentController_didReceiveScriptMessage_(self, controller, message):
        if not self._floating_window or not self._floating_window._current_clip:
            return
        clip = self._floating_window._current_clip
        pb = AppKit.NSPasteboard.generalPasteboard()
        pb.clearContents()
        if clip["type"] == "text":
            pb.setString_forType_(clip["content"], AppKit.NSPasteboardTypeString)
        elif clip["type"] == "image":
            img_path = CLIPS_DIR / clip["filename"]
            if img_path.exists():
                img_data = AppKit.NSData.dataWithContentsOfFile_(str(img_path))
                pb.setData_forType_(img_data, AppKit.NSPasteboardTypePNG)


class ClipboardDropApp(rumps.App):
    """Menu bar clipboard saver application."""

    def __init__(self):
        super().__init__("ClipboardDrop", title="📎", quit_button=None)
        self._floating_window = FloatingWindow()
        self._hotkey_listener = None
        self._build_menu()
        self._start_hotkey_listener()

    def _build_menu(self):
        self.menu.clear()

        # Save action
        save_item = rumps.MenuItem("Save Clipboard   ⌘⇧V", callback=self._on_save_clipboard)
        self.menu.add(save_item)
        self.menu.add(None)  # separator

        # Clips list
        clips = load_clips()
        if clips:
            for clip in clips:
                preview = clip["preview"]
                if len(preview) > 40:
                    preview = preview[:37] + "..."
                time_ago = relative_time(clip["timestamp"])
                label = f"{preview}  ·  {time_ago}"
                item = rumps.MenuItem(label, callback=self._on_clip_click)
                item._clip_data = clip
                self.menu.add(item)
        else:
            self.menu.add(rumps.MenuItem("No clips saved", callback=None))

        self.menu.add(None)
        self.menu.add(rumps.MenuItem("Clear All", callback=self._on_clear_all))
        self.menu.add(None)

        self._login_item = rumps.MenuItem("Start at Login", callback=self._toggle_login)
        self._login_item.state = self._is_launch_agent_loaded()
        self.menu.add(self._login_item)
        self.menu.add(rumps.MenuItem("Quit", callback=self._quit))

    def _on_save_clipboard(self, _=None):
        clip_type, data = read_clipboard()
        if clip_type is None:
            rumps.notification("Clipboard Drop", "", "Clipboard is empty")
            return

        saved = save_clip(clip_type, data)
        if saved:
            clips = load_clips()
            preview = clips[0]["preview"] if clips else ""
            rumps.notification("Clipboard Drop", "Saved", preview[:60])
        else:
            rumps.notification("Clipboard Drop", "", "Duplicate — already saved")

        self._build_menu()

    def _on_clip_click(self, sender):
        clip = getattr(sender, "_clip_data", None)
        if clip:
            self._floating_window.toggle_clip(clip)

    def _on_clear_all(self, _):
        clear_all_clips()
        self._floating_window.hide()
        self._build_menu()
        rumps.notification("Clipboard Drop", "", "All clips cleared")

    def _start_hotkey_listener(self):
        try:
            from pynput import keyboard

            def on_save():
                self._on_save_clipboard()

            hotkey_map = {"<cmd>+<shift>+v": on_save}
            self._hotkey_listener = keyboard.GlobalHotKeys(hotkey_map)
            self._hotkey_listener.daemon = True
            self._hotkey_listener.start()
        except ImportError:
            print("pynput not installed, global hotkey disabled")
        except Exception as e:
            print(f"Hotkey listener error: {e}")

    @staticmethod
    def _plist_path():
        return Path.home() / "Library/LaunchAgents/com.clipboard-drop.plist"

    def _is_launch_agent_loaded(self):
        import subprocess
        try:
            result = subprocess.run(
                ["launchctl", "list", "com.clipboard-drop.plist"],
                capture_output=True, text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def _toggle_login(self, sender):
        import subprocess
        plist = self._plist_path()
        if not plist.exists():
            rumps.notification("Clipboard Drop", "Error",
                               "Launch Agent plist not found. Run install.sh first.")
            return

        if sender.state:
            subprocess.run(["launchctl", "unload", str(plist)], capture_output=True)
            sender.state = False
            rumps.notification("Clipboard Drop", "Disabled", "Will not start at login.")
        else:
            subprocess.run(["launchctl", "load", str(plist)], capture_output=True)
            sender.state = True
            rumps.notification("Clipboard Drop", "Enabled", "Will start at login.")

    def _quit(self, _):
        if self._hotkey_listener:
            self._hotkey_listener.stop()
        rumps.quit_application()


def main():
    print("Starting Clipboard Drop...")
    print(f"Clips directory: {CLIPS_DIR}")
    print("Global hotkey: Cmd+Shift+V")
    print("Press Ctrl+C to stop")
    app = ClipboardDropApp()
    app.run()


if __name__ == "__main__":
    main()
