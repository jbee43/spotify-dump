"""Scope-drift detection tests."""

from export import _missing_scopes


def test_all_scopes_granted():
    required = "a b c"
    granted = "a b c"
    assert _missing_scopes(required, granted) == []


def test_granted_superset_is_fine():
    # Extra scopes in the granted set are benign
    assert _missing_scopes("a b", "a b c d") == []


def test_single_missing_scope():
    assert _missing_scopes("a b c", "a b") == ["c"]


def test_multiple_missing_scopes():
    assert _missing_scopes("a b c d", "a") == ["b", "c", "d"]


def test_order_is_stable_sorted():
    assert _missing_scopes("z a m", "") == ["a", "m", "z"]


def test_empty_granted():
    assert _missing_scopes("a b", "") == ["a", "b"]
    assert _missing_scopes("a b", None) == ["a", "b"]


def test_empty_required():
    assert _missing_scopes("", "a b") == []
    assert _missing_scopes(None, "a b") == []


def test_realistic_scope_drift():
    # Simulates the exact case that prompted this feature: adding
    # user-read-recently-played to SCOPES after the token was issued.
    required = (
        "playlist-read-collaborative playlist-read-private user-follow-read "
        "user-library-read user-read-recently-played user-top-read"
    )
    granted = (
        "playlist-read-collaborative playlist-read-private user-follow-read "
        "user-library-read user-top-read"
    )
    assert _missing_scopes(required, granted) == ["user-read-recently-played"]
