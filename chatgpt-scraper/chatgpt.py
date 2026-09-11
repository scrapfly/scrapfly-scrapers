"""
This is an example web scraper for chatgpt.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
from pathlib import Path
from urllib.parse import quote_plus

from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient


SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "proxy_pool": "public_residential_pool",
    "country": "US",
    "debug": True,
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


js_scenario = [
    {
        "click": {
            "ignore_if_not_visible": True,
            "selector": "#credentials-picker-container #close",
            "multiple": False,
            "ignore": True,
        }
    },
    {
        "click": {
            "ignore": True,
            "ignore_if_not_visible": True,
            "selector": "div[aria-live='polite'] button:first-of-type",
            "multiple": False,
        }
    },
    {
        "wait_for_selector": {
            "selector": "button[data-composer-submit]",
            "timeout": 15000,
        }
    },
    {
        "condition": {
            "selector": "button[data-composer-submit]",
            "selector_state": "not_existing",
            "action": "exit_failed",
        }
    },
    {
        "click": {
            "selector": "button[data-composer-submit]",
            "ignore_if_not_visible": False,
            "multiple": False,
        }
    },
    {"wait": 10000},
    {
        "condition": {
            "selector": "button[data-composer-submit]",
            "selector_state": "existing",
            "action": "exit_success",
        }
    },
    {"wait": 10000},
]


async def scrape_conversation(prompt: str) -> str:
    url = f"https://chatgpt.com/?prompt={quote_plus(prompt)}"
    log.info("scraping conversation for prompt: {}", prompt)
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url=url,
            format="markdown",
            format_options=["only_content"],
            render_js=True,
            js_scenario=js_scenario,
            rendering_wait=5000,
            **BASE_CONFIG,
        )
    )
    log.success("finished scraping ChatGPT for the prompt: {}", prompt)
    return response.content
