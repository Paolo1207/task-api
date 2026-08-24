import time
from pathlib import Path

import requests

BASE_URL = "https://books.toscrape.com/"
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/Paolo1207/task-api)"
TIMEOUT_SECONDS = 10
DELAY_SECONDS = 0.5

CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)


def fetch(url: str, cache_name: str) -> str:
    """Fetch a URL, using a cached copy on disk if we already have one."""
    cache_path = CACHE_DIR / cache_name

    if cache_path.exists():
        print(f"CACHE HIT  {cache_name}  ({cache_path.stat().st_size} bytes)")
        return cache_path.read_text(encoding="utf-8")

    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)

    if response.status_code != 200:
        raise RuntimeError(f"Fetch failed for {url}: status {response.status_code}")

    cache_path.write_text(response.text, encoding="utf-8")
    print(f"FETCH      {cache_name}  ({len(response.text)} bytes)")

    time.sleep(DELAY_SECONDS)
    return response.text


def main():
    html = fetch(BASE_URL, "catalogue-page-1.html")
    print(f"Got {len(html)} characters of HTML.")


if __name__ == "__main__":
    main()