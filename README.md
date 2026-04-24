# spotify-dump

## TLDR

Automated export of Spotify library data (playlists, liked songs, albums, artists, top items, recently-played) to JSON via CI/CD. Git-versioned history plus append-only JSONL logs let you track listening history, playlist changes and library growth over time

## How to use

To run your own instance, fork this repo and follow the steps below

### 1. Create a Spotify Developer App

1. Go to <https://developer.spotify.com/dashboard>
2. Create an app (any name/description)
3. In settings, add redirect URI `http://127.0.0.1:8888/callback`
   - **Important**: use `127.0.0.1`, not `localhost` — Spotify [blocked `localhost` in Nov 2025](https://developer.spotify.com/blog/2025-02-12-increasing-the-security-requirements-for-integrating-with-spotify), HTTP is only allowed for loopback IPs (`127.0.0.1` / `[::1]`)
4. Note the **Client ID** and **Client Secret**

### 2. Initial authentication (one-time, local)

```bash
git clone <your-fork-url> && cd spotify-dump
pip install -r requirements.txt

export SPOTIFY_CLIENT_ID="your_client_id"
export SPOTIFY_CLIENT_SECRET="your_client_secret"

python export.py --setup
```

A browser window opens for Spotify authorization

After approving, Spotipy captures the callback automatically and the script prints a **refresh token**; save it for the next step

### 3. Configure GitHub Secrets

In your repo, go to **Settings > Secrets and variables > Actions** and add:

| Secret                  | Value                     |
| ----------------------- | ------------------------- |
| `SPOTIFY_CLIENT_ID`     | Client ID from step 1     |
| `SPOTIFY_CLIENT_SECRET` | Client Secret from step 1 |
| `SPOTIFY_REFRESH_TOKEN` | Refresh token from step 2 |

### 4. CI/CD

All workflows are in `.github/workflows/` and pre-configured for GitHub Actions:

| Workflow          | Trigger   | Purpose                                                            |
| ----------------- | --------- | ------------------------------------------------------------------ |
| `ci.yml`          | Push / PR | Lint (`ruff`), security audit (`pip-audit`), data validation       |
| `export.yml`      | Manual    | Export Spotify data, commit to repo, optional webhook notification |
| `token-check.yml` | Manual    | Verify Spotify auth is still valid                                 |
| `deps-check.yml`  | Manual    | Check for outdated pinned dependencies                             |

Scheduled triggers are stripped from this mirror; add your own cron schedules after configuring secrets

All workflows support optional notifications via a `NOTIFICATION_WEBHOOK_URL` secret

### 5. (Optional) Run locally

```bash
export SPOTIFY_CLIENT_ID="your_client_id"
export SPOTIFY_CLIENT_SECRET="your_client_secret"

python export.py
```

After the initial `--setup`, Spotipy caches the token locally in `.cache` (gitignored)

## Exported data

All output goes to `data/` directory:

| File                     | Contents                                                                  |
| ------------------------ | ------------------------------------------------------------------------- |
| `liked_songs.json`       | All liked/saved songs                                                     |
| `saved_albums.json`      | Saved albums                                                              |
| `followed_artists.json`  | Followed artists (sorted alphabetically)                                  |
| `top_artists.json`       | Top artists (short, medium, long term)                                    |
| `top_tracks.json`        | Top tracks (short, medium, long term)                                     |
| `recently_played.json`   | Rolling listening history (appended each run, deduped by `played_at`)     |
| `playlists/{id}.json`    | One file per playlist with full track listing and `snapshot_id`           |
| `stats.json`             | Counts and timestamp from last export                                     |
| `history.jsonl`          | Append-only log: one compact JSONL line per export for long-term trending |
| `playlist_changes.jsonl` | Append-only log: one line per playlist whose `snapshot_id` changed        |

Each track includes name, artists, album, duration, explicit flag, URI and added date (where available); tracks unavailable in your market are tagged with `"is_playable": false`

Recently-played is inherently lossy: Spotify only returns the last 50 plays per call, so on a daily cron any plays beyond ~50 per day are lost

## CLI flags

| Flag         | Purpose                                                         |
| ------------ | --------------------------------------------------------------- |
| `--setup`    | Interactive OAuth setup (prints refresh token)                  |
| `--check`    | Auth check + scope-drift detection (fails if SCOPES changed)    |
| `--validate` | Validate exported JSON files without running an export          |
| `--report`   | Generate `data/report.json` with duplicate + unavailable tracks |

`--report` output is gitignored; it's a local investigation tool, not auto-committed

## Running tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Token refresh

The Spotify refresh token is long-lived but can expire if unused for extended periods or if you revoke app access

If exports start failing, re-run `python export.py --setup` locally to get a new refresh token and update the secret

Scope changes also invalidate tokens; if you see `Skipped: missing 'user-read-recently-played' scope` in the export log, your refresh token was issued before the scope was added — re-run `--setup` to reissue it

## References

- [Spotify Web API docs](https://developer.spotify.com/documentation/web-api)
- [Spotipy library](https://spotipy.readthedocs.io)

> **Read-only mirror**: this repository is automatically synced from a private Gitea instance
