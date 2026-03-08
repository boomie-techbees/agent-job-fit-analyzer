"""Job board scrapers for We Work Remotely and RemoteOK.

Each scraper returns a list of JobListing objects. Scrapers are async
and handle their own error recovery — a single failed page doesn't
kill the whole run.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Protocol

import httpx
from bs4 import BeautifulSoup

from agent.models import JobListing, JobSource
from config import REQUEST_TIMEOUT, SCRAPE_DELAY, USER_AGENT

logger = logging.getLogger(__name__)


class Scraper(Protocol):
    """Interface that all scrapers implement."""

    async def scrape(self) -> list[JobListing]: ...


# ---------------------------------------------------------------------------
# RemoteOK — JSON API
# ---------------------------------------------------------------------------

class RemoteOKScraper:
    """Scrapes RemoteOK using their public JSON API."""

    API_URL = "https://remoteok.com/api"

    async def scrape(self) -> list[JobListing]:
        logger.info("Scraping RemoteOK...")
        listings: list[JobListing] = []

        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as client:
            try:
                resp = await client.get(self.API_URL)
                resp.raise_for_status()
                data = resp.json()
            except (httpx.HTTPError, ValueError) as exc:
                logger.error("RemoteOK scrape failed: %s", exc)
                return listings

        # First element is a metadata/legal notice object, skip it
        jobs = data[1:] if len(data) > 1 else data

        for entry in jobs:
            try:
                title = entry.get("position", "").strip()
                company = entry.get("company", "").strip()
                if not title or not company:
                    continue

                url = entry.get("url", "")
                if url and not url.startswith("http"):
                    url = f"https://remoteok.com{url}"

                description = entry.get("description", "")
                # RemoteOK descriptions are HTML — extract text
                if description:
                    description = BeautifulSoup(
                        description, "html.parser"
                    ).get_text(separator="\n", strip=True)

                tags = entry.get("tags", []) or []
                location = entry.get("location", "Remote") or "Remote"
                salary = ""
                salary_min = entry.get("salary_min")
                salary_max = entry.get("salary_max")
                if salary_min and salary_max:
                    salary = f"${int(salary_min):,}–${int(salary_max):,}"
                elif salary_min:
                    salary = f"${int(salary_min):,}+"

                listings.append(
                    JobListing(
                        title=title,
                        company=company,
                        url=url,
                        source=JobSource.REMOTE_OK,
                        description=description[:5000],  # cap length
                        location=location,
                        tags=[str(t) for t in tags],
                        posted_date=entry.get("date", ""),
                        salary=salary or None,
                    )
                )
            except Exception as exc:
                logger.warning("Skipping malformed RemoteOK entry: %s", exc)

        logger.info("RemoteOK: found %d listings", len(listings))
        return listings


# ---------------------------------------------------------------------------
# We Work Remotely — HTML scraping
# ---------------------------------------------------------------------------

class WeWorkRemotelyScraper:
    """Scrapes We Work Remotely job listings from category pages."""

    # Category pages (search endpoint returns 403, so we use category browsing)
    CATEGORY_URLS = [
        "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs",
        "https://weworkremotely.com/categories/remote-back-end-programming-jobs",
        "https://weworkremotely.com/categories/remote-full-stack-programming-jobs",
    ]

    async def scrape(self) -> list[JobListing]:
        logger.info("Scraping We Work Remotely...")
        listings: list[JobListing] = []
        seen_urls: set[str] = set()

        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as client:
            for url in self.CATEGORY_URLS:
                try:
                    page_listings = await self._scrape_page(client, url)
                    for listing in page_listings:
                        if listing.url not in seen_urls:
                            seen_urls.add(listing.url)
                            listings.append(listing)
                except Exception as exc:
                    logger.warning("Failed to scrape %s: %s", url, exc)

                await asyncio.sleep(SCRAPE_DELAY)

        logger.info("We Work Remotely: found %d listings", len(listings))
        return listings

    async def _scrape_page(
        self, client: httpx.AsyncClient, url: str
    ) -> list[JobListing]:
        resp = await client.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        listings: list[JobListing] = []

        # WWR 2024+ layout: each job is an <li class="new-listing-container">
        # containing an <a class="listing-link--unlocked"> with structured divs.
        job_items = soup.select("li.new-listing-container")

        for item in job_items:
            try:
                link = item.select_one("a[href*='/remote-jobs/']")
                if not link:
                    continue

                href = link.get("href", "")
                if not href or "/remote-jobs/search" in href:
                    continue

                job_url = href
                if not job_url.startswith("http"):
                    job_url = f"https://weworkremotely.com{href}"

                # Title: h3.new-listing__header__title > span
                title_el = link.select_one(
                    ".new-listing__header__title__text"
                )
                title = title_el.get_text(strip=True) if title_el else ""

                # Company: p.new-listing__company-name
                company_el = link.select_one(".new-listing__company-name")
                company = company_el.get_text(strip=True) if company_el else ""

                # HQ location: p.new-listing__company-headquarters
                hq_el = link.select_one(".new-listing__company-headquarters")
                hq_location = hq_el.get_text(strip=True) if hq_el else ""

                # Categories include region, salary, contract type
                categories = link.select(
                    ".new-listing__categories__category"
                )
                cat_texts = [c.get_text(strip=True) for c in categories]

                # Find the "Anywhere" or region category for location
                location = hq_location or "Remote"
                salary = None
                tags: list[str] = []
                for cat in cat_texts:
                    if cat in ("Featured",):
                        continue
                    if "USD" in cat or "$" in cat:
                        salary = cat
                    elif "Anywhere" in cat or "Region" in cat:
                        location = cat
                    else:
                        tags.append(cat)

                if not title:
                    continue

                listings.append(
                    JobListing(
                        title=title,
                        company=company or "Unknown",
                        url=job_url,
                        source=JobSource.WE_WORK_REMOTELY,
                        location=location,
                        salary=salary,
                        tags=tags,
                    )
                )
            except Exception as exc:
                logger.warning("Skipping malformed WWR entry: %s", exc)

        return listings

    async def enrich_listing(
        self, client: httpx.AsyncClient, listing: JobListing
    ) -> JobListing:
        """Fetch the full job page to get the description."""
        try:
            resp = await client.get(listing.url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Job description is typically in .listing-container
            desc_el = soup.select_one(".listing-container")
            if desc_el:
                listing.description = desc_el.get_text(
                    separator="\n", strip=True
                )[:5000]
        except Exception as exc:
            logger.warning(
                "Failed to enrich WWR listing %s: %s", listing.url, exc
            )

        return listing


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

async def scrape_all() -> list[JobListing]:
    """Run all scrapers concurrently and return combined results."""
    remoteok = RemoteOKScraper()
    wwr = WeWorkRemotelyScraper()

    results = await asyncio.gather(
        remoteok.scrape(),
        wwr.scrape(),
        return_exceptions=True,
    )

    listings: list[JobListing] = []
    for result in results:
        if isinstance(result, Exception):
            logger.error("Scraper failed: %s", result)
        else:
            listings.extend(result)

    logger.info("Total scraped: %d listings", len(listings))
    return listings
