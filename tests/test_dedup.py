"""Duplicate-grouping tests (synthetic fixtures only)."""

from export import _group_duplicates


def _t(name, artist, uri):
    return {"name": name, "artists": [artist], "uri": uri}


def test_no_duplicates():
    tracks = [
        _t("Song A", "Artist 1", "spotify:track:0000000000000000000001"),
        _t("Song B", "Artist 2", "spotify:track:0000000000000000000002"),
    ]
    assert _group_duplicates(tracks) == []


def test_exact_match_duplicate():
    tracks = [
        _t("Song A", "Artist 1", "spotify:track:0000000000000000000001"),
        _t("Song A", "Artist 1", "spotify:track:0000000000000000000002"),
    ]
    groups = _group_duplicates(tracks)
    assert len(groups) == 1
    assert len(groups[0]) == 2


def test_case_insensitive():
    tracks = [
        _t("Song A", "Artist 1", "spotify:track:0000000000000000000001"),
        _t("SONG A", "ARTIST 1", "spotify:track:0000000000000000000002"),
    ]
    groups = _group_duplicates(tracks)
    assert len(groups) == 1


def test_whitespace_tolerance():
    tracks = [
        _t("  Song A  ", "Artist 1", "spotify:track:0000000000000000000001"),
        _t("Song A", "  Artist 1", "spotify:track:0000000000000000000002"),
    ]
    groups = _group_duplicates(tracks)
    assert len(groups) == 1


def test_different_artist_not_duplicate():
    tracks = [
        _t("Song A", "Artist 1", "spotify:track:0000000000000000000001"),
        _t("Song A", "Artist 2", "spotify:track:0000000000000000000002"),
    ]
    assert _group_duplicates(tracks) == []


def test_empty_artists_list():
    tracks = [
        {"name": "Song A", "artists": [], "uri": "spotify:track:000001"},
        {"name": "Song A", "artists": [], "uri": "spotify:track:000002"},
    ]
    groups = _group_duplicates(tracks)
    assert len(groups) == 1


def test_multiple_duplicate_groups():
    tracks = [
        _t("Song A", "Artist 1", "u1"),
        _t("Song A", "Artist 1", "u2"),
        _t("Song B", "Artist 2", "u3"),
        _t("Song B", "Artist 2", "u4"),
        _t("Song C", "Artist 3", "u5"),
    ]
    groups = _group_duplicates(tracks)
    assert len(groups) == 2
