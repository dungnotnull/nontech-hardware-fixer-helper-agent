"""RepairClinic symptom and parts scraper."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from loguru import logger


class RepairClinicScraper:
    """Scrape RepairClinic symptom guides using Playwright."""

    BASE_URL = "https://www.repairclinic.com"
    POPULAR_DEVICES = [
        "refrigerator", "washer", "dryer", "dishwasher",
        "microwave", "range", "oven", "freezer",
    ]

    async def crawl(self, max_symptoms: int = 30) -> list[dict[str, Any]]:
        """Crawl symptom pages for popular devices."""
        results: list[dict[str, Any]] = []
        try:
            from playwright.async_api import async_playwright
        except Exception:
            logger.warning("Playwright not available; RepairClinic scraper disabled")
            return results

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent="Mozilla/5.0 (compatible; FixerAgentBot/0.1)")
            for device in self.POPULAR_DEVICES:
                page = await context.new_page()
                try:
                    url = f"{self.BASE_URL}/Shop-For-Parts/?searchText={device}+not+working"
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    cards = await page.query_selector_all(".symptom-card, .symptom-item, [data-testid='symptom']")
                    for card in cards[:5]:
                        title_el = await card.query_selector("h3, .title, .symptom-title")
                        title = await title_el.inner_text() if title_el else ""
                        desc_el = await card.query_selector("p, .description")
                        desc = await desc_el.inner_text() if desc_el else ""
                        link_el = await card.query_selector("a")
                        href = await link_el.get_attribute("href") if link_el else ""
                        results.append({
                            "device": device,
                            "title": title.strip(),
                            "description": desc.strip(),
                            "url": f"{self.BASE_URL}{href}" if href else "",
                            "source": "repairclinic",
                            "crawled_at": datetime.utcnow().isoformat(),
                        })
                except Exception as e:
                    logger.warning(f"RepairClinic scrape failed for {device}: {e}")
                finally:
                    await page.close()
            await browser.close()

        logger.info(f"RepairClinic crawl complete: {len(results)} symptoms")
        return results