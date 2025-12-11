#!/usr/bin/env python3
"""Check Immich asset counts: collect asset IDs from albums and unalbummed assets
and compute the unique total to compare with the server UI count.

Usage examples:
  python scripts/check_immich_counts.py --env ~/.immich.env --user-count 25094
  python scripts/check_immich_counts.py --base-url https://old.immich.example.com --api-key ABC

The script tries to be flexible with Immich API shapes: it will tolerate responses that
are lists or objects with `items`/`data`, and it will attempt common album asset endpoints.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# no typing imports needed; using PEP 585 / union (|) annotations

try:
    import requests
except Exception:
    print("Missing dependency: requests. Install with: pip install requests", file=sys.stderr)
    raise


def load_env(path: str) -> dict[str, str]:
    p = Path(path).expanduser()
    if not p.exists():
        return {}
    vals: dict[str, str] = {}
    for ln in p.read_text(encoding="utf-8").splitlines():
        line = ln.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()
    return vals


def extract_list(obj):
    """Return a list from several possible container shapes."""
    if obj is None:
        return []
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for key in ("items", "data", "assets", "results", "rows"):
            if key in obj and isinstance(obj[key], list):
                return obj[key]
        # if dict looks like a single album with 'assets' possibly nested
        # not a list - return empty
    return []


def extract_id(o: dict) -> str | None:
    for k in ("id", "assetId", "uuid", "_id"):
        v = o.get(k)
        if v:
            return str(v)
    return None


def paged_post(
    session: requests.Session,
    url: str,
    json_body: dict,
    items_key: str = "items",
) -> list[dict]:
    all_items: list[dict] = []
    page = 1
    page_size = 1000
    while True:
        body = dict(json_body)
        body.update({"page": page, "size": page_size})
        r = session.post(url, json=body, timeout=30)
        r.raise_for_status()
        data = r.json()
        batch = None
        if isinstance(data, dict):
            # Check for nested structure: {"assets": {"items": [...]}}
            if "assets" in data and isinstance(data["assets"], dict):
                batch = data["assets"].get("items", [])
            else:
                # Try direct extraction
                for k in (items_key, "data", "items", "results"):
                    if k in data and isinstance(data[k], list):
                        batch = data[k]
                        break
        if batch is None:
            batch = data if isinstance(data, list) else []
        if not batch:
            break
        all_items.extend(batch)
        if len(batch) < page_size:
            break
        page += 1
    return all_items


def try_get(session: requests.Session, url: str) -> dict | None:
    r = session.get(url, timeout=30)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=("Verify Immich asset counts by enumerating albums and unalbummed assets")
    )
    p.add_argument(
        "--env",
        default=str(Path.home() / ".immich.env"),
        help=("Path to env file with OLD_IMMICH_SERVER_URL and OLD_IMMICH_API_KEY"),
    )
    p.add_argument("--base-url", default=None, help="Immich server base URL (overrides env)")
    p.add_argument("--api-key", default=None, help="Immich API key (overrides env)")
    p.add_argument(
        "--user-count",
        type=int,
        default=None,
        help="Optional server UI asset count for comparison",
    )
    p.add_argument(
        "--save-json",
        default=None,
        help="Path to save detailed JSON of ids and counts",
    )
    p.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print verbose debug information",
    )
    args = p.parse_args(argv)

    env = load_env(args.env) if args.env else {}
    base = args.base_url or env.get("OLD_IMMICH_SERVER_URL") or env.get("IMMICH_SERVER_URL")
    api_key = args.api_key or env.get("OLD_IMMICH_API_KEY") or env.get("IMMICH_API_KEY")
    if not base or not api_key:
        print("Missing base URL or API key. Provide --base-url/--api-key or a valid env file.")
        return 2
    base = base.rstrip("/")
    headers = {"x-api-key": api_key, "Accept": "application/json"}

    session = requests.Session()
    session.headers.update(headers)

    # 1) list albums
    print("Fetching albums...")
    # Use Immich API prefix
    albums_url = f"{base}/api/albums"
    try:
        r = session.get(albums_url, timeout=30)
        # If non-2xx this will raise
        r.raise_for_status()
        try:
            albums_raw = r.json()
            albums = extract_list(albums_raw)
        except json.JSONDecodeError:
            print("Failed to decode JSON from /api/albums response")
            print(f"Status: {r.status_code}")
            body = r.text or ""
            print("Response preview:")
            print(body[:800])
            return 3
    except Exception as e:
        print(f"Failed to fetch /api/albums: {e}")
        return 3

    print(f"Albums returned: {len(albums)}")

    asset_ids = set()
    sum_album_asset_counts = 0
    album_asset_details = {}
    albums_with_no_assets_fetched = []

    for a in albums:
        # Find album id
        album_id = None
        for k in ("id", "albumId", "uuid", "_id"):
            if isinstance(a, dict) and k in a:
                album_id = a[k]
                break
        if not album_id:
            # skip if no id
            continue
        album_id = str(album_id)
        # try common endpoints for album assets
        tried = False
        for candidate in (
            f"{base}/api/albums/{album_id}/assets",
            f"{base}/api/albums/{album_id}",
        ):
            try:
                j = try_get(session, candidate)
            except Exception:
                j = None
            if j is None:
                continue
            assets = extract_list(j)
            if (
                not assets
                and isinstance(j, dict)
                and "assets" in j
                and isinstance(j["assets"], list)
            ):
                assets = j["assets"]
            if assets:
                tried = True
                album_asset_details[album_id] = [
                    extract_id(it) for it in assets if isinstance(it, dict)
                ]
                sum_album_asset_counts += len(assets)
                for it in assets:
                    aid = extract_id(it) if isinstance(it, dict) else None
                    if aid:
                        asset_ids.add(aid)
                break
        if not tried:
            # album returned but no asset list discovered — continue
            album_asset_details[album_id] = []
            albums_with_no_assets_fetched.append(album_id)

    print(f"Sum of per-album asset counts: {sum_album_asset_counts}")
    print(f"Unique asset IDs found inside albums: {len(asset_ids)}")
    if albums_with_no_assets_fetched:
        print(
            f"WARNING: {len(albums_with_no_assets_fetched)} albums had no assets fetched "
            f"(endpoints returned no data)"
        )
        if args.verbose:
            print(f"  Album IDs: {albums_with_no_assets_fetched[:10]}")

    # 2) unalbummed assets via search/metadata
    print("Fetching unalbummed assets via /api/search/metadata (isNotInAlbum = true)...")
    search_url = f"{base}/api/search/metadata"
    try:
        items = paged_post(session, search_url, {"isNotInAlbum": True}, items_key="items")
    except Exception as e:
        print(f"Paged POST to /search/metadata failed: {e}")
        # fallback: try a single POST
        try:
            r = session.post(search_url, json={"isNotInAlbum": True}, timeout=30)
            r.raise_for_status()
            jr = r.json()
            if args.verbose:
                keys_info = list(jr.keys()) if isinstance(jr, dict) else "not a dict"
                print(f"  Search response keys: {keys_info}")
                if isinstance(jr, dict):
                    for k, v in jr.items():
                        if isinstance(v, list):
                            print(f"    {k}: list with {len(v)} items")
                        elif isinstance(v, dict):
                            print(f"    {k}: dict with keys {list(v.keys())}")
                        else:
                            print(f"    {k}: {type(v).__name__}")
            items = extract_list(jr)
        except Exception as e2:
            print(f"Fallback POST failed: {e2}")
            items = []

    unalbummed_ids = {extract_id(it) for it in items if isinstance(it, dict) and extract_id(it)}
    print(f"Unalbummed assets found: {len(unalbummed_ids)}")

    total_unique = len(asset_ids | unalbummed_ids)
    print(f"Unique assets (albums ∪ unalbummed): {total_unique}")

    if args.user_count is not None:
        diff = args.user_count - total_unique
        print(
            f"Server UI reported: {args.user_count}. "
            f"Difference = {diff} (positive means UI > unique assets)"
        )

    if args.save_json:
        out = {
            "albums_count_returned": len(albums),
            "sum_album_asset_counts": sum_album_asset_counts,
            "unique_album_asset_ids": len(asset_ids),
            "unalbummed_assets_count": len(unalbummed_ids),
            "unique_assets_union": total_unique,
            "album_asset_details_sample": {
                k: v[:20] for k, v in list(album_asset_details.items())[:30]
            },
        }
        Path(args.save_json).write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"Saved JSON summary to {args.save_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
