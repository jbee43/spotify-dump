#!/usr/bin/env python3
"""Export Spotify library data to JSON files."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import spotipy
from spotipy.oauth2 import SpotifyOAuth

SCOPES = " ".join(
    [
        "playlist-read-collaborative",
        "playlist-read-private",
        "user-follow-read",
        "user-library-read",
        "user-read-recently-played",
        "user-top-read",
    ]
)

DATA_DIR = Path(__file__).parent / "data"
PLAYLISTS_DIR = DATA_DIR / "playlists"
REDIRECT_URI = "http://127.0.0.1:8888/callback"
CACHE_PATH = Path(__file__).parent / ".cache"


def build_auth_manager():
    return SpotifyOAuth(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=REDIRECT_URI,
        scope=SCOPES,
        cache_path=str(CACHE_PATH),
    )


def seed_cache_from_env():
    """In CI, create a cache file from the SPOTIFY_REFRESH_TOKEN env var."""
    refresh_token = os.environ.get("SPOTIFY_REFRESH_TOKEN")
    if not refresh_token or CACHE_PATH.exists():
        return
    cache_data = {
        "access_token": "",
        "token_type": "Bearer",
        "expires_in": 0,
        "refresh_token": refresh_token,
        "scope": SCOPES,
        "expires_at": 0,
    }
    CACHE_PATH.write_text(json.dumps(cache_data))


def get_client():
    seed_cache_from_env()
    return spotipy.Spotify(auth_manager=build_auth_manager())


# --- Field extraction ---


def extract_track(item):
    """Extract useful fields from a saved-track or playlist-track item."""
    track = item.get("track") or item.get("item")
    if not track:
        return None
    result = {
        "name": track["name"],
        "artists": [a["name"] for a in track.get("artists", [])],
        "album": track.get("album", {}).get("name"),
        "duration_ms": track.get("duration_ms"),
        "explicit": track.get("explicit"),
        "uri": track.get("uri"),
    }
    if item.get("added_at"):
        result["added_at"] = item["added_at"]
    if track.get("is_playable") is False:
        result["is_playable"] = False
    episode = track.get("type") == "episode"
    if episode:
        result["type"] = "episode"
    return result


def extract_album(item):
    album = item.get("album", item)
    return {
        "name": album["name"],
        "artists": [a["name"] for a in album.get("artists", [])],
        "release_date": album.get("release_date"),
        "total_tracks": album.get("total_tracks"),
        "uri": album.get("uri"),
        "added_at": item.get("added_at"),
    }


def extract_artist(artist):
    return {
        "name": artist["name"],
        "genres": artist.get("genres", []),
        "uri": artist.get("uri"),
    }


# --- Helpers ---


def _dt_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _load_json_if_exists(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _append_jsonl(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _group_duplicates(tracks):
    """Group tracks by (lowercased name, lowercased first artist); return groups with >1 member."""
    groups = {}
    for t in tracks:
        name = (t.get("name") or "").strip().lower()
        artists = t.get("artists") or []
        first = (artists[0] if artists else "").strip().lower()
        key = (name, first)
        groups.setdefault(key, []).append(t)
    return [g for g in groups.values() if len(g) > 1]


def _diff_track_uris(old_tracks, new_tracks):
    """Return (added, removed) URI lists by comparing two track lists."""
    old = {t.get("uri") for t in old_tracks if t.get("uri")}
    new = {t.get("uri") for t in new_tracks if t.get("uri")}
    return sorted(new - old), sorted(old - new)


def _missing_scopes(required, granted):
    """Return sorted list of scopes declared in `required` but absent from `granted`.

    Both inputs are space-separated scope strings (same format spotipy stores in its cache).
    """
    req = set((required or "").split())
    got = set((granted or "").split())
    return sorted(req - got)


# --- Pagination ---


def fetch_all_paged(sp, first_page):
    """Paginate through standard offset-based endpoints."""
    items = list(first_page.get("items", []))
    page = first_page
    while page.get("next"):
        page = sp.next(page)
        items.extend(page.get("items", []))
    return items


def fetch_all_followed_artists(sp):
    """Followed artists use cursor-based pagination."""
    artists = []
    results = sp.current_user_followed_artists(limit=50)
    while True:
        batch = results["artists"]["items"]
        artists.extend(batch)
        after = results["artists"].get("cursors", {}).get("after")
        if not after:
            break
        results = sp.current_user_followed_artists(limit=50, after=after)
    return artists


# --- Export functions ---


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def export_liked_songs(sp):
    print("Exporting liked songs...")
    items = fetch_all_paged(
        sp, sp.current_user_saved_tracks(limit=50, market="from_token")
    )
    tracks = [t for t in (extract_track(i) for i in items) if t]
    save_json(DATA_DIR / "liked_songs.json", {"total": len(tracks), "tracks": tracks})
    print(f"  {len(tracks)} liked songs")


def export_saved_albums(sp):
    print("Exporting saved albums...")
    items = fetch_all_paged(sp, sp.current_user_saved_albums(limit=50))
    albums = [extract_album(i) for i in items]
    save_json(DATA_DIR / "saved_albums.json", {"total": len(albums), "albums": albums})
    print(f"  {len(albums)} saved albums")


def export_followed_artists(sp):
    print("Exporting followed artists...")
    items = fetch_all_followed_artists(sp)
    artists = [extract_artist(a) for a in items]
    artists.sort(key=lambda a: a["name"].lower())
    save_json(
        DATA_DIR / "followed_artists.json", {"total": len(artists), "artists": artists}
    )
    print(f"  {len(artists)} followed artists")


def export_playlists(sp):
    print("Exporting playlists...")
    playlists = fetch_all_paged(sp, sp.current_user_playlists(limit=50))

    seen_files = set()
    exported_count = 0
    skipped_count = 0

    changelog_path = DATA_DIR / "playlist_changes.jsonl"

    for pl in playlists:
        playlist_id = pl["id"]
        name = pl.get("name", "Unnamed")

        filepath = PLAYLISTS_DIR / f"{playlist_id}.json"
        seen_files.add(filepath.name)

        prev = _load_json_if_exists(filepath) or {}
        prev_snapshot = prev.get("snapshot_id")
        prev_tracks = prev.get("tracks", [])

        try:
            items = fetch_all_paged(
                sp, sp.playlist_items(playlist_id, limit=100, market="from_token")
            )
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status != 403:
                print(f"  {name}: skipped ({e.http_status} {e.reason})")
                skipped_count += 1
                continue
            # spotipy still hits deprecated /tracks; try /items directly
            try:
                first_page = sp._get(
                    f"playlists/{playlist_id}/items",
                    limit=100,
                    additional_types="track,episode",
                    market="from_token",
                )
                items = fetch_all_paged(sp, first_page)
            except Exception:
                print(f"  {name}: skipped (both /tracks and /items failed)")
                skipped_count += 1
                continue
        tracks = [t for t in (extract_track(i) for i in items) if t]

        new_snapshot = pl.get("snapshot_id")
        if prev_snapshot != new_snapshot:
            added, removed = _diff_track_uris(prev_tracks, tracks)
            if added or removed or prev_snapshot is None:
                _append_jsonl(
                    changelog_path,
                    {
                        "exported_at": _dt_now(),
                        "playlist_id": playlist_id,
                        "playlist_name": name,
                        "old_snapshot": prev_snapshot,
                        "new_snapshot": new_snapshot,
                        "added": added,
                        "removed": removed,
                    },
                )

        data = {
            "id": playlist_id,
            "name": name,
            "description": pl.get("description", ""),
            "owner": pl.get("owner", {}).get("display_name"),
            "public": pl.get("public"),
            "snapshot_id": new_snapshot,
            "total_tracks": len(tracks),
            "tracks": tracks,
        }

        save_json(filepath, data)
        exported_count += 1
        print(f"  {name}: {len(tracks)} tracks")

    # Only remove files for playlists no longer in the user's library
    if PLAYLISTS_DIR.exists():
        for old_file in PLAYLISTS_DIR.glob("*.json"):
            if old_file.name not in seen_files:
                prev = _load_json_if_exists(old_file)
                if prev:
                    removed_uris = sorted(
                        t.get("uri") for t in prev.get("tracks", []) if t.get("uri")
                    )
                    _append_jsonl(
                        changelog_path,
                        {
                            "exported_at": _dt_now(),
                            "playlist_id": prev.get("id"),
                            "playlist_name": prev.get("name"),
                            "old_snapshot": prev.get("snapshot_id"),
                            "new_snapshot": None,
                            "added": [],
                            "removed": removed_uris,
                        },
                    )
                old_file.unlink()
                print(f"  Removed stale: {old_file.name}")

    print(
        f"  {len(playlists)} playlists total ({exported_count} exported, {skipped_count} skipped)"
    )


def export_top_items(sp):
    print("Exporting top artists and tracks...")
    time_ranges = ["short_term", "medium_term", "long_term"]

    top_artists = {}
    top_tracks = {}
    for tr in time_ranges:
        artists = fetch_all_paged(
            sp, sp.current_user_top_artists(limit=50, time_range=tr)
        )
        top_artists[tr] = [extract_artist(a) for a in artists]

        tracks = fetch_all_paged(
            sp, sp.current_user_top_tracks(limit=50, time_range=tr)
        )
        top_tracks[tr] = [extract_track({"track": t}) for t in tracks]

    save_json(DATA_DIR / "top_artists.json", top_artists)
    save_json(DATA_DIR / "top_tracks.json", top_tracks)
    print(f"  Done ({', '.join(time_ranges)})")


def export_recently_played(sp):
    """Fetch last 50 plays, merge with existing history deduplicated by played_at."""
    print("Exporting recently played...")
    try:
        results = sp.current_user_recently_played(limit=50)
    except spotipy.exceptions.SpotifyException as e:
        if e.http_status == 403:
            print(
                "  Skipped: missing 'user-read-recently-played' scope "
                "(re-run --setup locally and update SPOTIFY_REFRESH_TOKEN)"
            )
            return
        raise

    filepath = DATA_DIR / "recently_played.json"
    existing = _load_json_if_exists(filepath) or {}
    existing_plays = existing.get("plays", [])
    seen = {p.get("played_at") for p in existing_plays if p.get("played_at")}

    fetched = 0
    added = 0
    merged = list(existing_plays)
    for item in results.get("items", []):
        fetched += 1
        track = extract_track({"track": item["track"]})
        if not track:
            continue
        played_at = item.get("played_at")
        if not played_at or played_at in seen:
            continue
        track["played_at"] = played_at
        merged.append(track)
        seen.add(played_at)
        added += 1

    merged.sort(key=lambda p: p.get("played_at", ""), reverse=True)
    save_json(filepath, {"total": len(merged), "plays": merged})
    print(f"  {fetched} fetched, {added} new, {len(merged)} total")


def export_stats():
    """Write data/stats.json with counts and export timestamp."""
    stats = {"exported_at": _dt_now()}
    for filename, count_key in [
        ("liked_songs.json", "total"),
        ("saved_albums.json", "total"),
        ("followed_artists.json", "total"),
        ("recently_played.json", "total"),
    ]:
        filepath = DATA_DIR / filename
        if filepath.exists():
            data = json.loads(filepath.read_text(encoding="utf-8"))
            stats[filename.replace(".json", "")] = data.get(count_key, 0)
    stats["playlists"] = (
        len(list(PLAYLISTS_DIR.glob("*.json"))) if PLAYLISTS_DIR.exists() else 0
    )
    save_json(DATA_DIR / "stats.json", stats)
    print(
        f"Stats: {json.dumps({k: v for k, v in stats.items() if k != 'exported_at'})}"
    )


def validate_exports():
    """Validate that exported JSON files are present and well-formed."""
    required = {
        "liked_songs.json": "tracks",
        "saved_albums.json": "albums",
        "followed_artists.json": "artists",
        "top_artists.json": None,
        "top_tracks.json": None,
    }
    # Optional files are validated only if present (e.g. recently_played
    # needs the user-read-recently-played scope; may be absent until re-setup).
    optional = {
        "recently_played.json": "plays",
    }
    errors = []
    for filename, list_key in required.items():
        filepath = DATA_DIR / filename
        if not filepath.exists():
            errors.append(f"Missing: {filename}")
            continue
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exception:
            errors.append(f"Invalid JSON: {filename} ({exception})")
            continue
        if list_key and not isinstance(data.get(list_key), list):
            errors.append(
                f"Invalid structure: {filename} (missing or invalid '{list_key}')"
            )

    for filename, list_key in optional.items():
        filepath = DATA_DIR / filename
        if not filepath.exists():
            continue
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exception:
            errors.append(f"Invalid JSON: {filename} ({exception})")
            continue
        if list_key and not isinstance(data.get(list_key), list):
            errors.append(
                f"Invalid structure: {filename} (missing or invalid '{list_key}')"
            )

    if PLAYLISTS_DIR.exists():
        for pf in PLAYLISTS_DIR.glob("*.json"):
            try:
                json.loads(pf.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exception:
                errors.append(f"Invalid JSON: playlists/{pf.name} ({exception})")

    if errors:
        print("Validation FAILED:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    print("Validation passed.")


# --- History & report ---


def append_history():
    """Append one compact JSONL line to data/history.jsonl using stats.json fields."""
    stats_path = DATA_DIR / "stats.json"
    stats = _load_json_if_exists(stats_path)
    if not stats:
        return
    _append_jsonl(DATA_DIR / "history.jsonl", stats)


def run_report():
    """Generate data/report.json listing duplicate liked tracks and unavailable tracks."""
    liked_path = DATA_DIR / "liked_songs.json"
    liked = _load_json_if_exists(liked_path) or {}
    liked_tracks = liked.get("tracks", [])

    duplicates = _group_duplicates(liked_tracks)

    unavailable = []
    for t in liked_tracks:
        if t.get("is_playable") is False:
            entry = dict(t)
            entry["source"] = "liked_songs"
            unavailable.append(entry)

    if PLAYLISTS_DIR.exists():
        for pf in sorted(PLAYLISTS_DIR.glob("*.json")):
            pl = _load_json_if_exists(pf) or {}
            for t in pl.get("tracks", []):
                if t.get("is_playable") is False:
                    entry = dict(t)
                    entry["source"] = f"playlist:{pl.get('name')}"
                    unavailable.append(entry)

    report = {
        "generated_at": _dt_now(),
        "duplicate_groups": len(duplicates),
        "unavailable_count": len(unavailable),
        "duplicates": duplicates,
        "unavailable": unavailable,
    }
    save_json(DATA_DIR / "report.json", report)
    print(
        f"Report: {len(duplicates)} duplicate group(s), "
        f"{len(unavailable)} unavailable track(s) -> data/report.json"
    )


# --- Setup ---


def run_setup():
    """Interactive OAuth setup — prints the refresh token for CI use."""
    auth_manager = build_auth_manager()
    sp = spotipy.Spotify(auth_manager=auth_manager)
    user = sp.current_user()

    token_info = auth_manager.get_cached_token()

    print(f"\nAuthenticated as: {user['display_name']} ({user['id']})")
    print("\nRefresh token (save as SPOTIFY_REFRESH_TOKEN in your CI/CD secrets):\n")
    print(token_info["refresh_token"])
    print()


def run_check():
    """Quick auth check — verifies the token works and covers the current SCOPES."""
    sp = get_client()
    user = sp.current_user()
    print(f"Auth OK: {user['display_name']} ({user['id']})")

    # After current_user(), spotipy has refreshed the token and written the
    # Spotify-reported scope back to CACHE_PATH — that's what we compare against.
    token_info = sp.auth_manager.get_cached_token() or {}
    granted = token_info.get("scope", "")
    missing = _missing_scopes(SCOPES, granted)
    if missing:
        print("Scope check FAILED — refresh token is missing scope(s):")
        for s in missing:
            print(f"  - {s}")
        print(
            "\nRe-run 'python export.py --setup' locally and update "
            "SPOTIFY_REFRESH_TOKEN in Gitea secrets."
        )
        sys.exit(1)

    print(f"Scope check OK: {len(granted.split())} scope(s) granted")


# --- Main ---


def main():
    parser = argparse.ArgumentParser(description="Export Spotify library data to JSON.")
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Interactive OAuth setup (prints refresh token)",
    )
    parser.add_argument(
        "--check", action="store_true", help="Quick auth check (no export)"
    )
    parser.add_argument(
        "--validate", action="store_true", help="Validate exported JSON files"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate data/report.json with duplicate and unavailable tracks",
    )
    args = parser.parse_args()

    if args.setup:
        run_setup()
        return

    if args.check:
        run_check()
        return

    if args.validate:
        validate_exports()
        return

    if args.report:
        run_report()
        return

    sp = get_client()
    export_liked_songs(sp)
    export_saved_albums(sp)
    export_followed_artists(sp)
    export_playlists(sp)
    export_top_items(sp)
    export_recently_played(sp)
    export_stats()
    validate_exports()
    append_history()
    print("\nExport complete.")


if __name__ == "__main__":
    main()
