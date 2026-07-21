"""Mercado Livre reviews scraper.

Uses the public frontend endpoint powering the ML reviews page:
    /noindex/catalog/reviews/{ID}/search?objectId={ID}&siteId=MLB&isItem={bool}

Paginates until reviews list is empty (or duplicates loop back), then writes
one dated CSV plus a `_latest.csv` per product for BI tooling.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
LOG_PATH = ROOT / "logs" / "scraper.log"

MLB_ID_RE = re.compile(r"MLB\d+", re.IGNORECASE)

CSV_COLUMNS = [
    "review_id",
    "product_id",
    "product_type",
    "rating",
    "content",
    "date_relative",
    "date_created",
    "likes",
    "has_comment",
    "picture_count",
    "video_count",
    "position_in_list",
    "site_id",
    "picture_urls",
    "collected_at",
]

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.mercadolivre.com.br/",
}


def setup_logging() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        cfg = json.load(f)
    env_out = os.environ.get("OUTPUT_DIR")
    if env_out:
        cfg["output_dir"] = env_out
    env_ids = os.environ.get("PRODUCT_IDS")
    if env_ids:
        cfg["product_ids"] = [p.strip() for p in env_ids.split(",") if p.strip()]
    return cfg


def normalize_product_id(raw: str) -> str:
    m = MLB_ID_RE.search(raw.replace("-", ""))
    if not m:
        raise ValueError(f"Could not extract MLB ID from: {raw!r}")
    return m.group(0).upper()


def build_session(max_retries: int) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=max_retries,
        backoff_factor=2.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(BROWSER_HEADERS)
    return session


def warm_up_session(session: requests.Session, product_id: str, timeout: int) -> None:
    """Visit the product/review page so ML sets session cookies before we hit the JSON endpoint."""
    for url in (
        f"https://www.mercadolivre.com.br/noindex/catalog/reviews/{product_id}"
        f"?noIndex=true&contextual=true&access=view_all",
        f"https://www.mercadolivre.com.br/p/{product_id}",
    ):
        try:
            session.get(url, timeout=timeout)
        except requests.RequestException:
            pass


def fetch_reviews_page(
    session: requests.Session,
    product_id: str,
    is_item: bool,
    offset: int,
    limit: int,
    timeout: int,
) -> list[dict[str, Any]] | None:
    """Return the reviews list for a single page. `None` means the endpoint refused this ID."""
    url = f"https://www.mercadolivre.com.br/noindex/catalog/reviews/{product_id}/search"
    params = {
        "objectId": product_id,
        "siteId": "MLB",
        "isItem": "true" if is_item else "false",
        "offset": offset,
        "limit": limit,
    }
    resp = session.get(url, params=params, timeout=timeout)
    if resp.status_code == 404:
        return None
    if resp.status_code == 400:
        # ML frontend returns 400 when offset exceeds available reviews
        # (also when rate-limited). Either way, stop pagination cleanly.
        logging.info("HTTP 400 at offset=%d — treating as end of stream.", offset)
        return []
    resp.raise_for_status()
    ctype = resp.headers.get("content-type", "")
    if "json" not in ctype:
        logging.warning("Non-JSON response at offset=%d (ctype=%s). Treating as end.", offset, ctype)
        return []
    data = resp.json()
    return data.get("reviews") or []


def paginate_reviews(
    session: requests.Session,
    product_id: str,
    is_item: bool,
    page_size: int,
    delay: float,
    timeout: int,
) -> Iterable[dict[str, Any]]:
    seen_ids: set[int] = set()
    offset = 0
    consecutive_dup_pages = 0
    while True:
        try:
            page = fetch_reviews_page(session, product_id, is_item, offset, page_size, timeout)
        except requests.RequestException as e:
            logging.warning("Request error at offset=%d: %s. Stopping pagination.", offset, e)
            return
        if page is None:
            logging.info("Endpoint 404 for %s (isItem=%s)", product_id, is_item)
            return
        if not page:
            logging.info("Empty page at offset=%d — done.", offset)
            return
        new = [r for r in page if r.get("id") not in seen_ids]
        for r in page:
            seen_ids.add(r.get("id"))
        logging.info(
            "offset=%d got=%d new=%d cumulative=%d",
            offset, len(page), len(new), len(seen_ids),
        )
        yield from new
        if not new:
            consecutive_dup_pages += 1
            if consecutive_dup_pages >= 2:
                logging.info("Two consecutive dup pages — stopping.")
                return
        else:
            consecutive_dup_pages = 0
        offset += page_size
        time.sleep(delay)


def flatten(review: dict[str, Any], product_id: str, is_item: bool, collected_at: str) -> dict[str, Any]:
    comment = review.get("comment") or {}
    content = ((comment.get("content") or {}).get("text")) or None
    date_relative = comment.get("date")

    track_review = (
        ((review.get("track_show") or {}).get("event_data") or {}).get("review") or {}
    )
    iso_date = track_review.get("created_date")
    likes = track_review.get("count_likes")
    has_comment = track_review.get("comment")
    position = track_review.get("position_in_list")

    media = track_review.get("media") or {}
    pics = (media.get("pictures") or {}).get("total_count") or 0
    vids = (media.get("video") or {}).get("total_count") or 0

    pic_urls: list[str] = []
    for m in review.get("media") or []:
        variations = m.get("variations") or []
        if variations:
            pic_urls.append(variations[0].get("url"))

    return {
        "review_id": review.get("id"),
        "product_id": product_id,
        "product_type": "item" if is_item else "catalog",
        "rating": review.get("rating"),
        "content": content,
        "date_relative": date_relative,
        "date_created": iso_date,
        "likes": likes,
        "has_comment": has_comment,
        "picture_count": pics,
        "video_count": vids,
        "position_in_list": position,
        "site_id": review.get("site_id"),
        "picture_urls": " | ".join(u for u in pic_urls if u),
        "collected_at": collected_at,
    }


def write_csvs(df: pd.DataFrame, product_id: str, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    snapshot = output_dir / f"reviews_{product_id}_{today}.csv"
    latest = output_dir / f"reviews_{product_id}_latest.csv"
    df.to_csv(snapshot, index=False, encoding="utf-8-sig")
    df.to_csv(latest, index=False, encoding="utf-8-sig")
    return snapshot, latest


def scrape_product(
    session: requests.Session,
    product_id: str,
    cfg: dict[str, Any],
) -> int:
    collected_at = datetime.now(timezone.utc).isoformat()
    warm_up_session(session, product_id, cfg.get("timeout_seconds", 20))

    page_size = cfg.get("page_size", 50)
    delay = cfg.get("request_delay_seconds", 0.6)
    timeout = cfg.get("timeout_seconds", 20)

    rows: list[dict[str, Any]] = []
    modes = [("catalog", False), ("item", True)]

    for mode_name, is_item in modes:
        collected = list(
            paginate_reviews(session, product_id, is_item, page_size, delay, timeout)
        )
        if collected:
            logging.info("Product %s matched as %s (%d reviews)", product_id, mode_name, len(collected))
            rows = [flatten(r, product_id, is_item, collected_at) for r in collected]
            break

    df = pd.DataFrame(rows, columns=CSV_COLUMNS)
    output_dir = Path(cfg["output_dir"])
    snapshot, latest = write_csvs(df, product_id, output_dir)
    logging.info(
        "Product %s: %d reviews -> %s (+ %s)",
        product_id, len(df), snapshot.name, latest.name,
    )
    return len(df)


def main() -> int:
    setup_logging()
    started = time.perf_counter()
    try:
        cfg = load_config()
    except FileNotFoundError:
        logging.error("Missing config.json at %s", CONFIG_PATH)
        return 2

    raw_ids = cfg.get("product_ids") or []
    if not raw_ids:
        logging.error("config.json has empty product_ids")
        return 2

    session = build_session(cfg.get("max_retries", 3))

    total = 0
    failures = 0
    for raw in raw_ids:
        try:
            pid = normalize_product_id(raw)
        except ValueError as e:
            logging.error("Skipping invalid product id %r: %s", raw, e)
            failures += 1
            continue
        try:
            total += scrape_product(session, pid, cfg)
        except Exception:
            logging.exception("Failed scraping %s", pid)
            failures += 1

    elapsed = time.perf_counter() - started
    logging.info(
        "Run finished: %d reviews across %d products, %d failures, %.1fs",
        total, len(raw_ids), failures, elapsed,
    )
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
