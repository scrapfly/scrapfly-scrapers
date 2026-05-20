"""
This is an example web scraper for perplexity.ai.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
from pathlib import Path
from typing import List, TypedDict
from loguru import logger as log
from urllib.parse import quote_plus
from scrapfly import ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "country": "US",
    "proxy_pool": "public_residential_pool",
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)

EXTRACTION_PROMPT = (
    "Extract a JSON object from this Perplexity result page with the fields below. "
    "Ignore the left sidebar navigation, history list, cookie banner, sign-in modal, "
    "and the follow-up composer at the bottom.\n"
    "Fields:\n"
    "- query: original question above the answer\n"
    "- answer_markdown: the AI answer text only, with paragraph breaks\n"
    "- cited_domains: array of unique source domain strings cited under the answer. "
    "Include domains from inline source labels, inline anchor URLs, and from "
    "\"domain=...\" parameters in favicon image URLs near the source list. "
    "Return bare domain only (no protocol, no path).\n"
    "- source_count: integer from the \"N sources\" label\n"
    "- follow_ups: array of strings under the Follow-ups heading\n"
    "Return only the JSON object."
)

JS_SCENARIO = [
    {
        "wait_for_selector": {
            "selector": "button[aria-label='Helpful']",
            "state": "visible",
            "timeout": 10000,
        }
    },
    {
        "wait": 10000
    }
]

class PerplexityAnswer(TypedDict):
    query: str
    answer_markdown: str
    cited_domains: List[str]
    source_count: int
    follow_ups: List[str]


async def scrape_answer(prompt: str) -> PerplexityAnswer:
    """Single-turn: submit one prompt, return Scrapfly `extracted_data.data` unchanged (JSON payload)."""
    url = f"https://www.perplexity.ai/search?q={quote_plus(prompt)}"
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url,
            render_js=True,
            rendering_wait=15000,
            extraction_prompt=EXTRACTION_PROMPT,
            js_scenario=JS_SCENARIO,
            **BASE_CONFIG,
        )
    )
    scrape_result = response.scrape_result or {}
    extracted = scrape_result.get("extracted_data") or {}
    data = extracted.get("data")
    if data is None:
        log_url = scrape_result.get("log_url")
        raise KeyError(
            f"missing extracted_data.data in scrape result (see log: {log_url})"
        )
    log.success(f"scraped perplexity answer for the prompt: {prompt}")
    return data
