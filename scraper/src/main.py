import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

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


def discover_catalogue_pages():
    """Visit catalogue pages 1-3, following the 'next' link, collecting every book URL."""
    all_book_urls = []
    current_url = BASE_URL
    pages_fetched = 0

    while pages_fetched < 3:
        pages_fetched += 1
        cache_name = f"catalogue-page-{pages_fetched}.html"
        html = fetch(current_url, cache_name)
        soup = BeautifulSoup(html, "html.parser")

        # Every book link on this page, turned into an absolute URL
        for article in soup.select("article.product_pod"):
            link = article.select_one("h3 a")
            if link and link.get("href"):
                absolute_url = urljoin(current_url, link["href"])
                all_book_urls.append(absolute_url)

        # Follow the catalogue's own "next" link, if there is one
        next_link = soup.select_one("li.next a")
        if next_link and next_link.get("href") and pages_fetched < 3:
            current_url = urljoin(current_url, next_link["href"])
        else:
            break

    unique_urls = list(dict.fromkeys(all_book_urls))  # dedupe, keep order
    return pages_fetched, len(all_book_urls), unique_urls


def main():
    pages_visited, discovered, unique_urls = discover_catalogue_pages()
    print(f"catalogue_pages={pages_visited}")
    print(f"discovered={discovered}")
    print(f"unique_urls={len(unique_urls)}")


if __name__ == "__main__":
    main()