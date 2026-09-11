"""
This is an example cloud browser scraper for Copilot.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import re
from pathlib import Path
from scrapfly import ScrapflyClient, BrowserConfig
from playwright.sync_api import sync_playwright
from loguru import logger as log
from parsel import Selector
from typing import List, Literal, Optional, TypedDict


BROWSER_CONFIG = BrowserConfig(
        debug=True,
        country="US",
        proxy_pool="residential",
        cache=True,
    )

client = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

CopilotMode = Literal["smart", "reasoning", "study", "search"]

class CopilotSource(TypedDict):
    title: str
    url: str
    snippet: Optional[str]


class CopilotResult(TypedDict):
    query: str
    answer: str
    sources: List[CopilotSource]

COMPOSER_INPUT = 'textarea[data-testid="composer-input"]'
SUBMIT_BUTTON = 'button[data-testid="submit-button"]'
RESPONSE_COMPLETE = 'button[aria-label="Good response"]'
MODE_DROPDOWN = '[data-testid="composer-dropdown-button-menu-contents"]'
MODE_TOGGLE = '[data-testid^="composer-chat-mode-"]'

MODE_LABELS: dict[CopilotMode, str] = {
    "smart": "Smart",
    "reasoning": "Think deeper",
    "study": "Study and learn",
    "search": "Search",
}

LANDING_URL = "https://copilot.microsoft.com/"


def ensure_captcha_solved(cdp, page, *, timeout_s: int = 150) -> None:
    record = None
    for _ in range(timeout_s):
        page.wait_for_timeout(1000)
        records = cdp.send("Antibot.getSolvedCaptchas").get("records", [])
        if not records:
            continue
        record = records[-1]
        if record["status"] == "solved":
            log.success(f"captcha solved: {record.get('type')}")
            return
        if record["status"] == "failed":
            raise RuntimeError(record.get("errorMessage", "captcha failed"))
    if record is None:
        log.warning("no captcha record found")
        return
    raise RuntimeError("captcha not solved within timeout")


def _select_mode(page, mode: CopilotMode) -> None:
    log.debug(f"selecting mode: {mode}")
    toggle = page.locator(MODE_TOGGLE)
    toggle.wait_for(timeout=15000)
    aria_label = toggle.get_attribute("aria-label") or ""
    if MODE_LABELS[mode] in aria_label:
        return
    if toggle.get_attribute("aria-expanded") != "true":
        toggle.click()
        page.wait_for_selector(MODE_DROPDOWN, timeout=5000)
    page.locator(
        f'{MODE_DROPDOWN} button[data-testid="composer-chat-mode-{mode}-button"]'
    ).click()


def parse_copilot_page(html: str, query: str | None = None) -> CopilotResult:
    """Parse a saved Copilot chat page into structured result data."""
    selector = Selector(text=html)
    if query is None:
        query = (selector.css('[data-content="user-message"]::text').get() or "").strip()

    body = selector.css('[data-testid="ai-message-body"]')
    text_nodes = body.xpath(
        './/text()[not(ancestor::span[contains(@class,"sr-only")]) '
        'and not(ancestor::button) '
        'and not(ancestor::span[@data-copy="false"])]'
    ).getall()
    answer = re.sub(r"\s+", " ", "".join(text_nodes)).strip()

    sources: List[CopilotSource] = []
    for block in body.css("span.sr-only span.block"):
        line = (block.xpath("string(.)").get() or "").strip()
        if not line:
            continue
        if ". " in line:
            domain, title = line.split(". ", 1)
        else:
            domain, title = line, line
        sources.append(
            {
                "title": title,
                "url": f"https://{domain}",
                "snippet": None,
            }
        )

    return {
        "query": query,
        "answer": answer,
        "sources": sources,
    }


def fill_query(page, query: str, mode: CopilotMode) -> str:
    """Fill the Copilot composer input and select the response mode."""
    log.debug(f"filling query ({mode}): {query}")
    page.wait_for_selector(COMPOSER_INPUT, timeout=15000)
    _select_mode(page, mode)
    textarea = page.locator(COMPOSER_INPUT)
    textarea.click()
    textarea.fill(query)
    return query


def open_session():
    log.debug("opening cloud browser session")
    if not client.verify:
        os.environ.setdefault("NODE_TLS_REJECT_UNAUTHORIZED", "0")
    p = sync_playwright().start()
    cdp_url = client.cloud_browser(BROWSER_CONFIG)
    browser = p.chromium.connect_over_cdp(cdp_url, timeout=180_000)
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else context.new_page()
    page.set_viewport_size({"width": 1920, "height": 1080})
    return p, browser, page


def scrape_copilot(query: str, mode: CopilotMode) -> CopilotResult:
    """Scrape the Copilot search results for a given query."""
    output = Path(__file__).parent / "results"
    output.mkdir(exist_ok=True)

    p, browser, page = open_session()
    try:
        cdp = page.context.new_cdp_session(page)
        cdp.send("Antibot.captchaEnable")
        log.debug(f"navigating to {LANDING_URL}")
        page.goto(LANDING_URL, wait_until="domcontentloaded", timeout=90_000)
        page.wait_for_selector(MODE_TOGGLE, state="visible", timeout=60_000)
        fill_query(page, query, mode)
        log.debug("submitting query")
        page.locator(SUBMIT_BUTTON).wait_for(state="visible", timeout=15000)
        page.locator(SUBMIT_BUTTON).click()
        ensure_captcha_solved(cdp, page)
        log.debug("waiting for response")
        page.wait_for_timeout(30_000)
        page.wait_for_selector(RESPONSE_COMPLETE, state="visible", timeout=120_000)
        html = page.content()
        return parse_copilot_page(html, query=query)
    finally:
        browser.close()