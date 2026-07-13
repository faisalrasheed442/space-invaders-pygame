"""Tests for the self-updater logic (network fully mocked)."""

import io

import pytest

from game import updater


# --------------------------------------------------------------------------- #
# Version parsing / installer selection
# --------------------------------------------------------------------------- #
def test_parse_semver():
    assert updater.parse_semver("v1.2.3") == (1, 2, 3)
    assert updater.parse_semver("1.2.3") == (1, 2, 3)
    assert updater.parse_semver("1.2") is None
    assert updater.parse_semver(None) is None
    assert updater.parse_semver("garbage") is None


def test_pick_installer_prefers_setup_exe():
    assets = [
        {"name": "SpaceAdventure-portable-win64.zip"},
        {"name": "SpaceAdventureSetup.exe"},
    ]
    assert updater._pick_installer(assets)["name"] == "SpaceAdventureSetup.exe"
    assert updater._pick_installer([{"name": "only.zip"}]) is None


def test_is_supported_false_in_test_env():
    # Not a frozen build under pytest.
    assert updater.is_supported() is False


# --------------------------------------------------------------------------- #
# check_for_update
# --------------------------------------------------------------------------- #
def _release(tag, assets, draft=False, prerelease=False):
    return {"tag_name": tag, "draft": draft, "prerelease": prerelease,
            "assets": assets, "body": f"notes for {tag}"}


SETUP_ASSET = [{"name": "SpaceAdventureSetup.exe",
                "browser_download_url": "https://example/Setup.exe", "size": 999}]


def test_check_for_update_returns_newer(monkeypatch):
    monkeypatch.setattr(updater, "VERSION", "1.0.0")
    monkeypatch.setattr(updater, "_fetch_releases", lambda timeout: [
        _release("v1.2.0", SETUP_ASSET),
        _release("v1.1.0", SETUP_ASSET),
    ])
    info = updater.check_for_update()
    assert info is not None
    assert info["version"] == "1.2.0"          # highest semver, not first in list
    assert info["url"].endswith("Setup.exe")
    assert info["size"] == 999


def test_check_for_update_none_when_not_newer(monkeypatch):
    monkeypatch.setattr(updater, "VERSION", "2.0.0")
    monkeypatch.setattr(updater, "_fetch_releases", lambda timeout: [
        _release("v1.9.0", SETUP_ASSET),
    ])
    assert updater.check_for_update() is None


def test_check_for_update_ignores_release_without_installer(monkeypatch):
    monkeypatch.setattr(updater, "VERSION", "1.0.0")
    monkeypatch.setattr(updater, "_fetch_releases", lambda timeout: [
        _release("v2.0.0", [{"name": "SpaceAdventure-portable.zip"}]),
    ])
    assert updater.check_for_update() is None


def test_check_for_update_ignores_drafts_and_prereleases(monkeypatch):
    monkeypatch.setattr(updater, "VERSION", "1.0.0")
    monkeypatch.setattr(updater, "_fetch_releases", lambda timeout: [
        _release("v3.0.0", SETUP_ASSET, draft=True),
        _release("v2.5.0", SETUP_ASSET, prerelease=True),
    ])
    assert updater.check_for_update() is None


def test_check_for_update_swallows_network_errors(monkeypatch):
    def boom(timeout):
        raise OSError("offline")
    monkeypatch.setattr(updater, "_fetch_releases", boom)
    assert updater.check_for_update() is None      # never raises


# --------------------------------------------------------------------------- #
# download integrity gate
# --------------------------------------------------------------------------- #
class _FakeResponse:
    def __init__(self, data):
        self._buf = io.BytesIO(data)

    def read(self, n):
        return self._buf.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _mock_urlopen(data):
    def _open(req, timeout=None):
        return _FakeResponse(data)
    return _open


def test_download_success(monkeypatch, tmp_path):
    payload = b"MZ" + b"\x00" * 500
    monkeypatch.setattr(updater.urllib.request, "urlopen", _mock_urlopen(payload))
    info = {"name": "SpaceAdventureSetup.exe", "url": "https://x/Setup.exe", "size": len(payload)}
    path = updater.download(info, dest_dir=str(tmp_path))
    assert path.endswith("SpaceAdventureSetup.exe")
    with open(path, "rb") as fh:
        assert fh.read(2) == b"MZ"


def test_download_rejects_size_mismatch(monkeypatch, tmp_path):
    payload = b"MZ" + b"\x00" * 10
    monkeypatch.setattr(updater.urllib.request, "urlopen", _mock_urlopen(payload))
    info = {"name": "s.exe", "url": "https://x", "size": 9999}   # wrong size
    with pytest.raises(IOError):
        updater.download(info, dest_dir=str(tmp_path))
    assert not (tmp_path / "s.exe").exists()
    assert not (tmp_path / "s.exe.part").exists()               # cleaned up


def test_download_rejects_non_executable(monkeypatch, tmp_path):
    payload = b"XX not an exe"
    monkeypatch.setattr(updater.urllib.request, "urlopen", _mock_urlopen(payload))
    info = {"name": "s.exe", "url": "https://x", "size": len(payload)}
    with pytest.raises(IOError):
        updater.download(info, dest_dir=str(tmp_path))
    assert not (tmp_path / "s.exe").exists()
