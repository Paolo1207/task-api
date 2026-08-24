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
RETRY_WAIT_SECONDS = 2

SCRAPER_ROOT = Path(__file__).parent.parent
CACHE_DIR = SCRAPER_ROOT / "cache"
OUTPUT_DIR = SCRAPER_ROOT / "output"
CACHE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Set to a fake URL to test failure handling on purpose. Leave as None for a normal run.
INJECT_FAKE_URL = None

stats = {
    "pages_fetched": 0,
    "cache_hits": 0,
    "failed_pages": 0,
}


class FetchError(Exception):
    """Raised when a page could not be fetched, after retries where appropriate."""
    pass


def fetch(url: str, cache_name: str) -> str:
    """Fetch a URL, using a cached copy on disk if we already have one.
    Retries once on timeout or 5xx. Does not retry on 404 or 403."""
    cache_path = CACHE_DIR / cache_name

    if cache_path.exists():
        stats["cache_hits"] += 1
        print(f"CACHE HIT  {cache_name}  ({cache_path.stat().st_size} bytes)")
        return cache_path.read_text(encoding="utf-8")

    headers = {"User-Agent": USER_AGENT}
    attempts = 0
    max_attempts = 2

    while attempts < max_attempts:
        attempts += 1
        try:
            response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
        except requests.exceptions.Timeout:
            if attempts < max_attempts:
                print(f"TIMEOUT    {cache_name}  retrying in {RETRY_WAIT_SECONDS}s...")
                time.sleep(RETRY_WAIT_SECONDS)
                continue
            raise FetchError(f"{url}: timed out after {max_attempts} attempts")

        if response.status_code == 200:
            response.encoding = "utf-8"
            cache_path.write_text(response.text, encoding="utf-8")
            stats["pages_fetched"] += 1
            print(f"FETCH      {cache_name}  ({len(response.text)} bytes)")
            time.sleep(DELAY_SECONDS)
            return response.text

        if response.status_code in (404, 403):
            # Do not retry: the page doesn't exist, or we were told no.
            raise FetchError(f"{url}: status {response.status_code}")

        if 500 <= response.status_code < 600 and attempts < max_attempts:
            print(f"SERVER ERR {cache_name}  status {response.status_code}, retrying...")
            time.sleep(RETRY_WAIT_SECONDS)
            continue

        raise FetchError(f"{url}: status {response.status_code}")

    raise FetchError(f"{url}: failed after {max_attempts} attempts")


def discover_catalogue_pages():
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

    if INJECT_FAKE_URL:
        unique_urls.append(INJECT_FAKE_URL)

    return pages_fetched, len(all_book_urls), unique_urls


def url_to_cache_name(url: str) -> str:
    slug = url.rstrip("/").split("/")[-2]
    return f"book-{slug}.html"


def extract_book(url: str, source_page: str) -> dict:
    cache_name = url_to_cache_name(url)
    html = fetch(url, cache_name)
    soup = BeautifulSoup(html, "html.parser")

    product_main = soup.select_one("div.product_main")
    if product_main is None:
        raise FetchError(f"{url}: page fetched but product content not found")

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
    start_time = datetime.now(timezone.utc)

    pages_visited, discovered, unique_urls = discover_catalogue_pages()
    print(f"catalogue_pages={pages_visited}")
    print(f"discovered={discovered}")
    print(f"unique_urls={len(unique_urls)}")

    valid_records = []
    invalid_records = []
    failed_pages = []
    seen_urls = set()

    for url in unique_urls:
        try:
            raw = extract_book(url, source_page=BASE_URL)
        except FetchError as e:
            print(f"FAILED     {url}  ({e})")
            failed_pages.append({"url": url, "reason": str(e)})
            stats["failed_pages"] += 1
            continue

        normalized = normalize_record(raw)

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

    end_time = datetime.now(timezone.utc)
    report = {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": round((end_time - start_time).total_seconds(), 2),
        "catalogue_pages_visited": pages_visited,
        "books_discovered": discovered,
        "unique_urls": len(unique_urls),
        "pages_fetched_live": stats["pages_fetched"],
        "cache_hits": stats["cache_hits"],
        "valid_records": len(valid_records),
        "invalid_records": len(invalid_records),
        "failed_pages": stats["failed_pages"],
        "failed_page_details": failed_pages,
    }
    (OUTPUT_DIR / "run-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    print(f"\nvalid_records={len(valid_records)}")
    print(f"invalid_records={len(invalid_records)}")
    print(f"failed_pages={stats['failed_pages']}")
    print("Wrote output/books.json, output/errors.json, output/run-report.json")


if __name__ == "__main__":
    main()