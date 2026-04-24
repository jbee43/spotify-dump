"""Playlist URI-diff tests (synthetic fixtures only)."""

from export import _diff_track_uris


def _t(uri):
    return {"uri": uri}


def test_no_changes():
    old = [_t("u1"), _t("u2")]
    new = [_t("u1"), _t("u2")]
    added, removed = _diff_track_uris(old, new)
    assert added == []
    assert removed == []


def test_track_added():
    old = [_t("u1")]
    new = [_t("u1"), _t("u2")]
    added, removed = _diff_track_uris(old, new)
    assert added == ["u2"]
    assert removed == []


def test_track_removed():
    old = [_t("u1"), _t("u2")]
    new = [_t("u1")]
    added, removed = _diff_track_uris(old, new)
    assert added == []
    assert removed == ["u2"]


def test_track_added_and_removed():
    old = [_t("u1"), _t("u2")]
    new = [_t("u1"), _t("u3")]
    added, removed = _diff_track_uris(old, new)
    assert added == ["u3"]
    assert removed == ["u2"]


def test_empty_old_all_added():
    added, removed = _diff_track_uris([], [_t("u1"), _t("u2")])
    assert added == ["u1", "u2"]
    assert removed == []


def test_empty_new_all_removed():
    added, removed = _diff_track_uris([_t("u1"), _t("u2")], [])
    assert added == []
    assert removed == ["u1", "u2"]


def test_tracks_without_uri_ignored():
    old = [_t("u1"), {"name": "no uri"}]
    new = [_t("u1"), {"uri": None}]
    added, removed = _diff_track_uris(old, new)
    assert added == []
    assert removed == []


def test_reorder_is_not_a_change():
    added, removed = _diff_track_uris(
        [_t("u1"), _t("u2"), _t("u3")],
        [_t("u3"), _t("u1"), _t("u2")],
    )
    assert added == []
    assert removed == []


def test_sorted_output():
    # Adding in random insertion order should produce sorted output
    added, removed = _diff_track_uris([], [_t("u_z"), _t("u_a"), _t("u_m")])
    assert added == ["u_a", "u_m", "u_z"]
