"""In-app self-updater for installed Windows builds.

Reads this repo's **public** GitHub Releases API anonymously (no token ever
ships in the binary), finds the highest-semver release that carries an
installer asset, downloads it behind an integrity gate (exact size + PE "MZ"
magic), then launches the installer silently and elevated so it can upgrade the
Program Files copy in place and relaunch the app.

Only active in a frozen (PyInstaller) build on Windows — from source or on other
platforms every entry point is a safe no-op, so development and tests are
unaffected.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import urllib.request

from game.version import VERSION

REPO = "faisalrasheed442/space-invaders-pygame"
RELEASES_API = f"https://api.github.com/repos/{REPO}/releases"
TIMEOUT = 15
_UA = {"User-Agent": "SpaceAdventure-Updater", "Accept": "application/vnd.github+json"}


def is_supported() -> bool:
    """Self-update only makes sense for an installed Windows build."""
    return sys.platform == "win32" and getattr(sys, "frozen", False)


def current_version() -> str:
    return VERSION


def parse_semver(tag: str | None) -> tuple[int, int, int] | None:
    m = re.match(r"v?(\d+)\.(\d+)\.(\d+)", tag or "")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def _pick_installer(assets: list) -> dict | None:
    """Prefer the installer (…Setup.exe); never the portable zip."""
    for a in assets:
        if a.get("name", "").lower().endswith("setup.exe"):
            return a
    return None


def _fetch_releases(timeout: int) -> list:
    req = urllib.request.Request(RELEASES_API, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def check_for_update(timeout: int = TIMEOUT) -> dict | None:
    """Return {version, url, name, size, notes} for a newer release, else None.

    Picks the highest semver (not GitHub's `latest` flag, which can be set out
    of order) that actually ships an installer. Never raises — any failure
    (offline, rate-limited, malformed) returns None.
    """
    try:
        releases = _fetch_releases(timeout)
    except Exception:
        return None

    current = parse_semver(VERSION) or (0, 0, 0)
    best_ver = current
    best: dict | None = None
    for rel in releases:
        if rel.get("draft") or rel.get("prerelease"):
            continue
        ver = parse_semver(rel.get("tag_name"))
        if not ver or ver <= best_ver:
            continue
        asset = _pick_installer(rel.get("assets", []))
        if not asset:
            continue
        best_ver = ver
        best = {
            "version": ".".join(map(str, ver)),
            "url": asset["browser_download_url"],
            "name": asset["name"],
            "size": int(asset.get("size", 0)),
            "notes": rel.get("body", "") or "",
        }
    return best


def download(info: dict, dest_dir: str | None = None, progress=None, timeout: int = TIMEOUT) -> str:
    """Download the installer with an integrity gate; return the final path.

    Streams to a `.part` file, then refuses to commit it unless the byte count
    matches the release's authoritative size AND the first two bytes are the PE
    magic `MZ`. Only then is it atomically renamed into place — so a truncated
    download is never left where `apply_update` would run it.
    """
    dest_dir = dest_dir or tempfile.gettempdir()
    part = os.path.join(dest_dir, info["name"] + ".part")
    final = os.path.join(dest_dir, info["name"])

    req = urllib.request.Request(info["url"], headers={"User-Agent": _UA["User-Agent"]})
    total = 0
    expected = int(info.get("size", 0))
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(part, "wb") as fh:
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            fh.write(chunk)
            total += len(chunk)
            if progress:
                progress(total, expected)

    try:
        if expected and total != expected:
            raise IOError(f"size mismatch: got {total}, expected {expected}")
        with open(part, "rb") as fh:
            if fh.read(2) != b"MZ":
                raise IOError("downloaded file is not a Windows executable")
    except Exception:
        _safe_remove(part)
        raise

    os.replace(part, final)   # atomic
    return final


def apply_update(installer_path: str) -> bool:
    """Launch the installer elevated + silent. Return True if it started.

    Uses ShellExecuteW "runas" (one UAC prompt — the price of a Program Files
    install). A return value <= 32 means failure *or* the user declined UAC; in
    that case we report False so the caller can keep running instead of quitting
    into a broken state.
    """
    if sys.platform != "win32":
        return False
    import ctypes

    params = "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOCANCEL"
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", installer_path, params, None, 0)  # SW_HIDE
    return int(rc) > 32


def _safe_remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass
