"""Field-extraction tests (synthetic fixtures only)."""

from export import extract_album, extract_artist, extract_track


def _track(**overrides):
    base = {
        "name": "Test Track",
        "artists": [{"name": "Test Artist"}],
        "album": {"name": "Test Album"},
        "duration_ms": 123000,
        "explicit": False,
        "uri": "spotify:track:0000000000000000000001",
    }
    base.update(overrides)
    return base


def test_extract_track_basic():
    result = extract_track({"track": _track()})
    assert result == {
        "name": "Test Track",
        "artists": ["Test Artist"],
        "album": "Test Album",
        "duration_ms": 123000,
        "explicit": False,
        "uri": "spotify:track:0000000000000000000001",
    }


def test_extract_track_added_at_passthrough():
    result = extract_track({"track": _track(), "added_at": "2026-01-01T00:00:00Z"})
    assert result["added_at"] == "2026-01-01T00:00:00Z"


def test_extract_track_is_playable_only_when_false():
    # True should be stripped to minimise diff noise
    assert "is_playable" not in extract_track({"track": _track(is_playable=True)})
    # False should surface
    assert extract_track({"track": _track(is_playable=False)})["is_playable"] is False
    # Missing (no market passed) should also be stripped
    assert "is_playable" not in extract_track({"track": _track()})


def test_extract_track_episode_type():
    result = extract_track({"track": _track(type="episode")})
    assert result["type"] == "episode"


def test_extract_track_returns_none_for_missing_track():
    assert extract_track({}) is None
    assert extract_track({"track": None}) is None


def test_extract_track_item_key_fallback():
    # Some endpoints put the track under "item" instead of "track"
    result = extract_track({"item": _track()})
    assert result["name"] == "Test Track"


def test_extract_album():
    item = {
        "album": {
            "name": "Test Album",
            "artists": [{"name": "Artist A"}, {"name": "Artist B"}],
            "release_date": "2026-01-01",
            "total_tracks": 10,
            "uri": "spotify:album:0000000000000000000001",
        },
        "added_at": "2026-01-01T00:00:00Z",
    }
    result = extract_album(item)
    assert result == {
        "name": "Test Album",
        "artists": ["Artist A", "Artist B"],
        "release_date": "2026-01-01",
        "total_tracks": 10,
        "uri": "spotify:album:0000000000000000000001",
        "added_at": "2026-01-01T00:00:00Z",
    }


def test_extract_artist():
    result = extract_artist(
        {
            "name": "Test Artist",
            "genres": ["genre-a", "genre-b"],
            "uri": "spotify:artist:0000000000000000000001",
        }
    )
    assert result == {
        "name": "Test Artist",
        "genres": ["genre-a", "genre-b"],
        "uri": "spotify:artist:0000000000000000000001",
    }
