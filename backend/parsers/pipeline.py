"""
StreetEasy + Craigslist Email Ingestion Pipeline
=================================================
Entry-point that ties together both ingestion paths:

  StreetEasy:
    GmailFetcher → StreetEasyEmailParser → ListingScraper (ZenRows) → ListingWriter

  Craigslist:
    GmailFetcher → CraigslistEmailParser → CraigslistScraper (ZenRows) → CraigslistWriter

Fully async — uses your app's async_session_factory (asyncpg) for all DB writes.

Run from the command line (from project root):
    python -m app.parsers.pipeline                              # both sources
    python -m app.parsers.pipeline --source streeteasy          # StreetEasy only
    python -m app.parsers.pipeline --source craigslist          # Craigslist only
    python -m app.parsers.pipeline --eml path/to/test.eml       # parse a local .eml file
    python -m app.parsers.pipeline --after 2026/03/01           # emails after this date
    python -m app.parsers.pipeline --no-scrape                  # skip ZenRows step

Environment variables (in .env or shell):
    GMAIL_CREDENTIALS_PATH   path to credentials.json      (default: credentials.json)
    GMAIL_TOKEN_PATH         path to token.json            (default: token.json)
    ZENROWS_API_KEY          ZenRows API key               (required unless --no-scrape)
    ANTHROPIC_API_KEY        Anthropic API key             (optional, enables Claude gap-fill)
    DATABASE_URL             set in app/database.py via .env
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Sender queries used to find alert emails in Gmail.
_STREETEASY_GMAIL_QUERY = "from:noreply@email.streeteasy.com is:unread"
_CRAIGSLIST_GMAIL_QUERY = "from:alerts@alerts.craigslist.org is:unread"

load_dotenv()

# ---------------------------------------------------------------------------
# Per-source pipeline steps
# ---------------------------------------------------------------------------

async def _run_streeteasy(
    eml_path: str | None,
    after_date: str | None,
    max_results: int,
    scrape: bool,
    zenrows_api_key: str | None,
) -> tuple[int, int]:
    """Fetch → parse → scrape → write for StreetEasy. Returns (created, skipped)."""
    from parsers.streeteasy_email import StreetEasyEmailParser

    email_parser = StreetEasyEmailParser()

    if eml_path:
        logger.info("[StreetEasy] Offline mode — parsing local file: %s", eml_path)
        listings = email_parser.parse_eml_file(eml_path)
    else:
        from parsers.gmail_fetcher import GmailFetcher
        fetcher = GmailFetcher(
            credentials_path=os.environ.get("GMAIL_CREDENTIALS_PATH", "credentials.json"),
            token_path=os.environ.get("GMAIL_TOKEN_PATH", "token.json"),
            query_override=_STREETEASY_GMAIL_QUERY,
        )
        raw_messages = fetcher.fetch_new_messages(
            max_results=max_results, after_date=after_date
        )
        listings = []
        for msg in raw_messages:
            listings.extend(email_parser.parse_gmail_message(msg))

    logger.info("[StreetEasy] Listings from email: %d", len(listings))
    if not listings:
        return 0, 0

    if scrape:
        api_key = zenrows_api_key or os.environ.get("ZENROWS_API_KEY", "")
        if not api_key:
            logger.warning("[StreetEasy] ZENROWS_API_KEY not set — skipping scraping.")
        else:
            from parsers.streeteasy_scraper import ListingScraper
            scraper = ListingScraper(
                zenrows_api_key=api_key,
                anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            )
            logger.info("[StreetEasy] Enriching %d listing(s) via ZenRows...", len(listings))
            listings = await asyncio.to_thread(scraper.enrich_batch, listings)

    from app.database import async_session_factory
    from parsers.streeteasy_db_writer import ListingWriter
    async with async_session_factory() as session:
        writer = ListingWriter(session)
        created, skipped = await writer.upsert_listings(listings)

    logger.info("[StreetEasy] Done. Created=%d Skipped=%d", created, skipped)
    return created, skipped


async def _run_craigslist(
    eml_path: str | None,
    after_date: str | None,
    max_results: int,
    scrape: bool,
    zenrows_api_key: str | None,
) -> tuple[int, int]:
    """Fetch → parse → scrape → write for Craigslist. Returns (created, skipped)."""
    from parsers.craigslist_email import CraigslistEmailParser

    email_parser = CraigslistEmailParser()

    if eml_path:
        logger.info("[Craigslist] Offline mode — parsing local file: %s", eml_path)
        listings = email_parser.parse_eml_file(eml_path)
    else:
        from parsers.gmail_fetcher import GmailFetcher
        fetcher = GmailFetcher(
            credentials_path=os.environ.get("GMAIL_CREDENTIALS_PATH", "credentials.json"),
            token_path=os.environ.get("GMAIL_TOKEN_PATH", "token.json"),
            query_override=_CRAIGSLIST_GMAIL_QUERY,
        )
        raw_messages = fetcher.fetch_new_messages(
            max_results=max_results, after_date=after_date
        )
        listings = []
        for msg in raw_messages:
            listings.extend(email_parser.parse_gmail_message(msg))

    logger.info("[Craigslist] Listings from email: %d", len(listings))
    if not listings:
        return 0, 0

    if scrape:
        api_key = zenrows_api_key or os.environ.get("ZENROWS_API_KEY", "")
        if not api_key:
            logger.warning("[Craigslist] ZENROWS_API_KEY not set — skipping scraping.")
        else:
            from parsers.craigslist_scraper import CraigslistScraper
            scraper = CraigslistScraper(
                zenrows_api_key=api_key,
                anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            )
            logger.info("[Craigslist] Enriching %d listing(s) via ZenRows...", len(listings))
            listings = await asyncio.to_thread(scraper.enrich_batch, listings)

    from app.database import async_session_factory
    from parsers.craigslist_db_writer import CraigslistWriter
    async with async_session_factory() as session:
        writer = CraigslistWriter(session)
        created, skipped = await writer.upsert_listings(listings)

    logger.info("[Craigslist] Done. Created=%d Skipped=%d", created, skipped)
    return created, skipped


# ---------------------------------------------------------------------------
# Main entry-point
# ---------------------------------------------------------------------------

async def run_pipeline(
    source: str = "both",               # "streeteasy" | "craigslist" | "both"
    eml_path: str | None = None,
    after_date: str | None = None,
    max_results: int = 50,
    scrape: bool = True,
    zenrows_api_key: str | None = None,
) -> None:
    """Execute the full ingestion pipeline (async)."""

    if eml_path and source == "both":
        # When a local .eml is supplied, auto-detect the source from the sender.
        with open(eml_path, "rb") as fh:
            header = fh.read(4096).decode("utf-8", errors="ignore")
        if "craigslist" in header.lower():
            source = "craigslist"
            logger.info("Auto-detected Craigslist .eml — running Craigslist parser.")
        else:
            source = "streeteasy"
            logger.info("Auto-detected StreetEasy .eml — running StreetEasy parser.")

    total_created = total_skipped = 0

    if source in ("streeteasy", "both"):
        c, s = await _run_streeteasy(eml_path, after_date, max_results, scrape, zenrows_api_key)
        total_created += c
        total_skipped += s

    if source in ("craigslist", "both"):
        c, s = await _run_craigslist(eml_path, after_date, max_results, scrape, zenrows_api_key)
        total_created += c
        total_skipped += s

    logger.info(
        "Pipeline complete. Total created=%d skipped=%d", total_created, total_skipped
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Ingest StreetEasy and/or Craigslist alert emails into the apartment database."
    )
    p.add_argument(
        "--source",
        choices=["streeteasy", "craigslist", "both"],
        default="both",
        help="Which source to ingest (default: both).",
    )
    p.add_argument("--eml", metavar="PATH",
                   help="Parse a local .eml file instead of calling the Gmail API. "
                        "Source is auto-detected from the sender if --source is not set.")
    p.add_argument("--after", metavar="YYYY/MM/DD",
                   help="Only fetch Gmail messages received after this date.")
    p.add_argument("--max-results", type=int, default=50, metavar="N",
                   help="Maximum number of Gmail messages to fetch per source (default: 50).")
    p.add_argument("--no-scrape", action="store_true",
                   help="Skip the ZenRows scraping step (email data only).")
    p.add_argument("--zenrows-api-key", metavar="KEY",
                   help="ZenRows API key (overrides ZENROWS_API_KEY env var).")
    return p


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    asyncio.run(
        run_pipeline(
            source=args.source,
            eml_path=args.eml,
            after_date=args.after,
            max_results=args.max_results,
            scrape=not args.no_scrape,
            zenrows_api_key=args.zenrows_api_key,
        )
    )