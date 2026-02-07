"""
py2app build script for Clipboard Drop.

Usage:
    python setup.py py2app

The .app bundle will be created in the dist/ directory.
"""

from setuptools import setup

APP = ["clipboard_drop.py"]
OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "Clipboard Drop",
        "CFBundleDisplayName": "Clipboard Drop",
        "CFBundleIdentifier": "com.clipboard-drop",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "LSUIElement": True,  # Menu bar app — no Dock icon
    },
    "packages": [
        "rumps",
        "pynput",
        "objc",
        "AppKit",
        "WebKit",
    ],
    "excludes": [
        "setuptools",
        "pip",
        "py2app",
        "altgraph",
        "macholib",
        "modulegraph",
    ],
}

setup(
    name="Clipboard Drop",
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
