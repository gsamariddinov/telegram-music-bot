"""
Music search and download engine for Tunova Bot.
Provides high-speed, direct MP3 catalog search without YouTube datacenter blocks.
"""
import os
import re
import json
import uuid
import logging
import urllib.request
import urllib.parse

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,uz;q=0.7",
}

# In-memory track cache for quick access by track ID
_TRACK_CACHE = {}


def cache_track(track: dict) -> None:
    if track and "id" in track:
        _TRACK_CACHE[track["id"]] = track


def get_cached_track(track_id: str) -> dict:
    return _TRACK_CACHE.get(track_id)


def search_hitmo(query: str, max_results: int = 5) -> list:
    """Search music on Hitmo direct MP3 catalog."""
    domains = [
        "https://rus.hitmotop.com",
        "https://eu.hitmotop.com",
        "https://ru.hitmoz.org",
    ]

    encoded_q = urllib.parse.quote(query.strip())

    for base_domain in domains:
        try:
            url = f"{base_domain}/search?q={encoded_q}"
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            pattern = r'<li\s+class="[^"]*track[^"]*"[^>]*data-musmeta=\'([^\']+)\'.*?<div class="track__fulltime">([^<]+)</div>'
            matches = re.findall(pattern, html, re.DOTALL)

            if not matches:
                # Fallback pattern without duration div
                matches_meta = re.findall(r"data-musmeta='([^']+)'", html)
                matches = [(m, "03:00") for m in matches_meta]

            tracks = []
            for meta_str, dur_str in matches:
                if len(tracks) >= max_results:
                    break
                try:
                    meta = json.loads(meta_str)
                    dl_url = meta.get("url", "")
                    if not dl_url:
                        continue
                    if dl_url.startswith("/"):
                        dl_url = base_domain + dl_url

                    dur_parts = str(dur_str).strip().split(":")
                    if len(dur_parts) == 2:
                        duration_sec = int(dur_parts[0]) * 60 + int(dur_parts[1])
                    elif len(dur_parts) == 3:
                        duration_sec = int(dur_parts[0]) * 3600 + int(dur_parts[1]) * 60 + int(dur_parts[2])
                    else:
                        duration_sec = 0

                    raw_id = str(meta.get("id") or "").replace("track-id-", "").strip()
                    if not raw_id:
                        raw_id = uuid.uuid4().hex[:10]

                    track_id = f"hm_{raw_id}"

                    track = {
                        "id": track_id,
                        "title": meta.get("title", "Unknown").strip(),
                        "uploader": meta.get("artist", "Unknown").strip(),
                        "duration": duration_sec,
                        "thumbnail": meta.get("img") or "",
                        "url": dl_url,
                    }
                    cache_track(track)
                    tracks.append(track)
                except Exception as ex:
                    logger.debug(f"Error parsing track item: {ex}")
                    continue

            if tracks:
                return tracks

        except Exception as e:
            logger.warning(f"Error searching {base_domain}: {e}")
            continue

    return []


def search_music(query: str, max_results: int = 5) -> list:
    """Primary music search entrypoint."""
    tracks = search_hitmo(query, max_results)
    if tracks:
        return tracks
    return []


def download_direct_mp3(url: str, output_dir: str) -> tuple:
    """Download MP3 directly via streaming HTTP request."""
    out_path = os.path.join(output_dir, "audio.mp3")
    parsed = urllib.parse.urlparse(url)
    referer = f"{parsed.scheme}://{parsed.netloc}/"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": HEADERS["User-Agent"],
            "Referer": referer,
            "Accept": "*/*",
        }
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        with open(out_path, "wb") as out_file:
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                out_file.write(chunk)

    if os.path.exists(out_path) and os.path.getsize(out_path) > 5000:
        return out_path, "mp3"

    return None, None
