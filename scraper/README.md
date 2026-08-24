# The polite scraper

A small scraping pipeline that downloads the first 3 catalogue pages of
[Books to Scrape](https://books.toscrape.com), visits all 60 book detail
pages, and turns the messy HTML into clean, schema-validated JSON —
politely, and with an honest report at the end of every run.

## Target classification

- **Site:** [books.toscrape.com](https://books.toscrape.com)
- **Why this site is appropriate to scrape:** it is a public sandbox built
  specifically for scraping practice. The site's own homepage describes
  itself as "a fictional bookstore that desperately wants to be scraped...
  a safe place for beginners learning web scraping." Every book page
  additionally displays the banner: *"We love being scraped! Warning!
  This is a demo website for web scraping purposes."* This is explicit,
  stated permission from the site owner.
- **Scope:** only the first 3 catalogue pages (60 books total) — never the
  full site.
- **robots.txt result:** `https://books.toscrape.com/robots.txt` returns
  `404 Not Found` — no robots file exists. A missing file is not
  permission by itself; the actual permission here comes from the site's
  explicit "we love being scraped" statement above, not from the absence
  of a robots.txt.
- **Data collected:** book title, price, availability, star rating,
  description, and product URL — all publicly displayed on each page,
  nothing behind a login or paywall.

**I will not reuse this code on another site without checking its rules
and terms first.**

## How to run

```bash
pip install -r requirements.txt
python src/main.py
```

This one command fetches (or reads from cache) 3 catalogue pages and 60
book pages, and writes three files to `output/`:

- `books.json` — 60 valid, schema-checked records
- `errors.json` — any records that failed validation, with a reason
- `run-report.json` — counts and timing for the run

## Record schema

Each record in `books.json` has these fields:

| Field                 | Type            | Notes                                      |
|------------------------|-----------------|---------------------------------------------|
| `title`                | string          | Book title                                   |
| `product_url`          | string (URL)    | Canonical identity — the record's unique key |
| `price_text`           | string          | Raw price as shown on the page, e.g. `£51.77`|
| `price_gbp`            | number          | Cleaned numeric price, e.g. `51.77`          |
| `availability_text`    | string          | Raw availability text                        |
| `in_stock`              | boolean         | Parsed from availability text                |
| `availability_count`    | number \| null  | Parsed count, e.g. `22`                      |
| `rating_text`          | string          | Raw rating word, e.g. `"Three"`              |
| `rating`               | number          | Parsed 1–5                                   |
| `description`          | string \| null  | `null` when the book has no description      |
| `source_page`          | string (URL)    | Where this book was discovered               |
| `fetched_at`           | string (ISO 8601)| When this record was fetched                 |

A record that fails validation never reaches `books.json` — it's written
to `errors.json` with the validation reason instead.

## Politeness rules

- Every real request sends an identifying `User-Agent`:
  `FlyRankInternshipA9/1.0 (+https://github.com/Paolo1207/task-api)`
- Every request has a 10-second timeout — never waits forever
- Waits at least 500ms between real requests to the live site
- Checks the HTTP status code before parsing anything
- Every fetched page is cached to `cache/` (git-ignored) — re-running
  during development reads the saved copy instead of hitting the site
  again
- Retries once on a timeout or `5xx` server error; never retries a `404`
  (the page doesn't exist) or `403` (the site said no)

## Sample run report

A real `run-report.json` from a clean run:

```json
{
  "start_time": "2026-08-24T03:16:15.651088+00:00",
  "end_time": "2026-08-24T03:16:16.180713+00:00",
  "duration_seconds": 0.53,
  "catalogue_pages_visited": 3,
  "books_discovered": 60,
  "unique_urls": 60,
  "pages_fetched_live": 0,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 0,
  "failed_page_details": []
}
```

And from a run with one deliberately broken URL added, proving the
pipeline survives it:

```json
{
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 1,
  "failed_page_details": [
    {
      "url": "https://books.toscrape.com/catalogue/this-book-does-not-exist_9999/index.html",
      "reason": "https://books.toscrape.com/catalogue/this-book-does-not-exist_9999/index.html: status 404"
    }
  ]
}
```

## Why this assignment needed no browser

The data this scraper collects — title, price, availability, rating,
description — is already present in the raw HTML the server sends on
first response. Nothing here is rendered client-side by JavaScript after
the page loads, so `requests` + `BeautifulSoup` sees everything a real
browser would see. A headless browser (Playwright, Selenium) would only
add startup cost, memory overhead, and complexity here without unlocking
any additional data.

## Honest limitation

`source_page` currently records the catalogue's base URL for every book
rather than the specific one of the three catalogue pages (1, 2, or 3)
each book was actually discovered on. The provenance is still accurate
in spirit — every record does carry a real source and fetch timestamp —
but a reader wanting to know exactly which catalogue page listed a given
book would need a small fix to track that per-page instead of globally.

## Ethics note

This scraper only touches a site built and explicitly offered for
scraping practice. In general: prefer an official API when one exists
over scraping; never bypass a login, paywall, CAPTCHA, or explicit block
— those are the site owner saying no, and "no" doesn't become "yes"
just because it's technically possible to work around; collect only the
data actually needed for the task, not everything reachable; and always
identify your scraper honestly via its User-Agent so a site owner can
see who's visiting and why.
