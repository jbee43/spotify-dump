"""history.jsonl append tests (synthetic fixtures only)."""

import json

import export


def test_append_history_writes_line_from_stats(monkeypatch, tmp_path):
    monkeypatch.setattr(export, "DATA_DIR", tmp_path)
    stats = {
        "exported_at": "2026-04-24 09:00:00",
        "liked_songs": 100,
        "saved_albums": 5,
        "followed_artists": 10,
        "recently_played": 42,
        "playlists": 3,
    }
    (tmp_path / "stats.json").write_text(json.dumps(stats), encoding="utf-8")

    export.append_history()

    history = tmp_path / "history.jsonl"
    assert history.exists()
    lines = history.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == stats


def test_append_history_is_append_only(monkeypatch, tmp_path):
    monkeypatch.setattr(export, "DATA_DIR", tmp_path)
    (tmp_path / "stats.json").write_text(
        json.dumps({"exported_at": "2026-04-24 09:00:00", "liked_songs": 1}),
        encoding="utf-8",
    )
    export.append_history()
    export.append_history()

    lines = (
        (tmp_path / "history.jsonl").read_text(encoding="utf-8").strip().splitlines()
    )
    assert len(lines) == 2


def test_append_history_compact_format(monkeypatch, tmp_path):
    # Compact separators keep diffs linear (no pretty-printing)
    monkeypatch.setattr(export, "DATA_DIR", tmp_path)
    (tmp_path / "stats.json").write_text(json.dumps({"a": 1, "b": 2}), encoding="utf-8")
    export.append_history()
    line = (tmp_path / "history.jsonl").read_text(encoding="utf-8").strip()
    assert " " not in line  # no spaces after separators
    assert line == '{"a":1,"b":2}'


def test_append_history_noop_when_stats_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(export, "DATA_DIR", tmp_path)
    export.append_history()
    assert not (tmp_path / "history.jsonl").exists()
