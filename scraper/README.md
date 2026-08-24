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

Outputs `output/books.json`, `output/errors.json`, and
`output/run-report.json`.

## Politeness rules

- Identifies itself with a clear `User-Agent` header
- Sets a request timeout — never waits forever
- Checks the HTTP status code before parsing anything
- Waits at least 500ms between real requests to the site
- Caches every fetched page to `cache/` so re-running during development
  never re-hits the live site
