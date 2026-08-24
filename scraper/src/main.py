import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError, HttpUrl

BASE_URL = "https://books.toscrape.com/"
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/Paolo1207/task-api)"
TIMEOUT_SECONDS = 10
DELAY_SECONDS = 0.5

SCRAPER_ROOT = Path(__file__).parent.parent
CACHE_DIR = SCRAPER_ROOT / "cache"
OUTPUT_DIR = SCRAPER_ROOT / "output"
CACHE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


def fetch(url: str, cache_name: str) -> str:
    """Fetch a URL, using a cached copy on disk if we already have one."""
    cache_path = CACHE_DIR / cache_name

    if cache_path.exists():
        print(f"CACHE HIT  {cache_name}  ({cache_path.stat().st_size} bytes)")
        return cache_path.read_text(encoding="utf-8")

    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
    response.encoding = "utf-8"

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

        for article in soup.select("article.product_pod"):
            link = article.select_one("h3 a")
            if link and link.get("href"):
                absolute_url = urljoin(current_url, link["href"])
                all_book_urls.append(absolute_url)

        next_link = soup.select_one("li.next a")
        if next_link and next_link.get("href") and pages_fetched < 3:
            current_url = urljoin(current_url, next_link["href"])
        else:
            break

    unique_urls = list(dict.fromkeys(all_book_urls))
    return pages_fetched, len(all_book_urls), unique_urls


def url_to_cache_name(url: str) -> str:
    """Turn a book URL into a safe, unique cache filename."""
    slug = url.rstrip("/").split("/")[-2]
    return f"book-{slug}.html"


def extract_book(url: str, source_page: str) -> dict:
    """Fetch one book detail page and pull out the raw fields."""
    cache_name = url_to_cache_name(url)
    html = fetch(url, cache_name)
    soup = BeautifulSoup(html, "html.parser")

    product_main = soup.select_one("div.product_main")

    title = product_main.select_one("h1").get_text(strip=True)

    price_el = product_main.select_one("p.price_color")
    price_text = price_el.get_text(strip=True) if price_el else None

    availability_el = product_main.select_one("p.availability")
    availability_text = availability_el.get_text(strip=True) if availability_el else None

    rating_el = product_main.select_one("p.star-rating")
    rating_text = None
    if rating_el:
        classes = rating_el.get("class", [])
        rating_text = next((c for c in classes if c != "star-rating"), None)

    description_heading = soup.select_one("#product_description")
    description = None
    if description_heading:
        description_p = description_heading.find_next_sibling("p")
        if description_p:
            description = description_p.get_text(strip=True)

    return {
        "title": title,
        "product_url": url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def normalize_record(raw: dict) -> dict:
    """Turn raw scraped strings into clean, typed values, keeping the originals too."""
    price_gbp = None
    if raw["price_text"]:
        match = re.search(r"[\d.]+", raw["price_text"])
        if match:
            price_gbp = float(match.group())

    availability_count = None
    in_stock = False
    if raw["availability_text"]:
        in_stock = "in stock" in raw["availability_text"].lower()
        match = re.search(r"\((\d+) available\)", raw["availability_text"])
        if match:
            availability_count = int(match.group(1))

    rating = RATING_WORDS.get(raw["rating_text"])

    return {
        **raw,
        "price_gbp": price_gbp,
        "in_stock": in_stock,
        "availability_count": availability_count,
        "rating": rating,
    }


class BookRecord(BaseModel):
    title: str
    product_url: HttpUrl
    price_text: str
    price_gbp: float
    availability_text: str
    in_stock: bool
    availability_count: int | None = None
    rating_text: str
    rating: int
    description: str | None = None
    source_page: HttpUrl
    fetched_at: str


def main():
    pages_visited, discovered, unique_urls = discover_catalogue_pages()
    print(f"catalogue_pages={pages_visited}")
    print(f"discovered={discovered}")
    print(f"unique_urls={len(unique_urls)}")

    valid_records = []
    invalid_records = []
    seen_urls = set()

    for url in unique_urls:
        raw = extract_book(url, source_page=BASE_URL)
        normalized = normalize_record(raw)

        # canonical identity: the product URL. Skip if we've already stored this one.
        if normalized["product_url"] in seen_urls:
            continue

        try:
            validated = BookRecord(**normalized)
            valid_records.append(json.loads(validated.model_dump_json()))
            seen_urls.add(normalized["product_url"])
        except ValidationError as e:
            invalid_records.append({"url": url, "reason": str(e)})

    (OUTPUT_DIR / "books.json").write_text(
        json.dumps(valid_records, indent=2), encoding="utf-8"
    )
    (OUTPUT_DIR / "errors.json").write_text(
        json.dumps(invalid_records, indent=2), encoding="utf-8"
    )

    print(f"\nvalid_records={len(valid_records)}")
    print(f"invalid_records={len(invalid_records)}")
    print("Wrote output/books.json and output/errors.json")


if __name__ == "__main__":
    main()