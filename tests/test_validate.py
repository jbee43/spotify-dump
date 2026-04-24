"""validate_exports tests (synthetic fixtures only)."""

import json

import pytest

import export


def _write_valid_fixtures(root):
    (root / "liked_songs.json").write_text(
        json.dumps({"total": 0, "tracks": []}), encoding="utf-8"
    )
    (root / "saved_albums.json").write_text(
        json.dumps({"total": 0, "albums": []}), encoding="utf-8"
    )
    (root / "followed_artists.json").write_text(
        json.dumps({"total": 0, "artists": []}), encoding="utf-8"
    )
    (root / "top_artists.json").write_text(
        json.dumps({"short_term": [], "medium_term": [], "long_term": []}),
        encoding="utf-8",
    )
    (root / "top_tracks.json").write_text(
        json.dumps({"short_term": [], "medium_term": [], "long_term": []}),
        encoding="utf-8",
    )


def test_validate_passes_with_good_fixtures(monkeypatch, tmp_path, capsys):
    playlists = tmp_path / "playlists"
    playlists.mkdir()
    monkeypatch.setattr(export, "DATA_DIR", tmp_path)
    monkeypatch.setattr(export, "PLAYLISTS_DIR", playlists)
    _write_valid_fixtures(tmp_path)

    # Should not raise / sys.exit
    export.validate_exports()
    assert "Validation passed" in capsys.readouterr().out


def test_validate_fails_on_missing_file(monkeypatch, tmp_path):
    playlists = tmp_path / "playlists"
    playlists.mkdir()
    monkeypatch.setattr(export, "DATA_DIR", tmp_path)
    monkeypatch.setattr(export, "PLAYLISTS_DIR", playlists)
    _write_valid_fixtures(tmp_path)
    (tmp_path / "liked_songs.json").unlink()

    with pytest.raises(SystemExit) as exc:
        export.validate_exports()
    assert exc.value.code == 1


def test_validate_fails_on_invalid_json(monkeypatch, tmp_path):
    playlists = tmp_path / "playlists"
    playlists.mkdir()
    monkeypatch.setattr(export, "DATA_DIR", tmp_path)
    monkeypatch.setattr(export, "PLAYLISTS_DIR", playlists)
    _write_valid_fixtures(tmp_path)
    (tmp_path / "saved_albums.json").write_text("{ not json", encoding="utf-8")

    with pytest.raises(SystemExit):
        export.validate_exports()


def test_validate_fails_on_invalid_structure(monkeypatch, tmp_path):
    playlists = tmp_path / "playlists"
    playlists.mkdir()
    monkeypatch.setattr(export, "DATA_DIR", tmp_path)
    monkeypatch.setattr(export, "PLAYLISTS_DIR", playlists)
    _write_valid_fixtures(tmp_path)
    # Missing the "tracks" list key
    (tmp_path / "liked_songs.json").write_text(
        json.dumps({"total": 0}), encoding="utf-8"
    )

    with pytest.raises(SystemExit):
        export.validate_exports()


def test_validate_tolerates_missing_recently_played(monkeypatch, tmp_path):
    # recently_played.json is optional (needs user-read-recently-played scope)
    playlists = tmp_path / "playlists"
    playlists.mkdir()
    monkeypatch.setattr(export, "DATA_DIR", tmp_path)
    monkeypatch.setattr(export, "PLAYLISTS_DIR", playlists)
    _write_valid_fixtures(tmp_path)

    # No recently_played.json — should still pass
    export.validate_exports()


def test_validate_checks_recently_played_when_present(monkeypatch, tmp_path):
    playlists = tmp_path / "playlists"
    playlists.mkdir()
    monkeypatch.setattr(export, "DATA_DIR", tmp_path)
    monkeypatch.setattr(export, "PLAYLISTS_DIR", playlists)
    _write_valid_fixtures(tmp_path)
    (tmp_path / "recently_played.json").write_text(
        json.dumps({"total": 0}),
        encoding="utf-8",  # missing "plays" key
    )

    with pytest.raises(SystemExit):
        export.validate_exports()


def test_validate_detects_corrupt_playlist_json(monkeypatch, tmp_path):
    playlists = tmp_path / "playlists"
    playlists.mkdir()
    monkeypatch.setattr(export, "DATA_DIR", tmp_path)
    monkeypatch.setattr(export, "PLAYLISTS_DIR", playlists)
    _write_valid_fixtures(tmp_path)
    (playlists / "bogus.json").write_text("{ bad json", encoding="utf-8")

    with pytest.raises(SystemExit):
        export.validate_exports()
