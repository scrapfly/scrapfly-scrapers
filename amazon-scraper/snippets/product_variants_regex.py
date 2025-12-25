# https://gist.github.com/scrapfly-dev/bceaae127efc6cbec2e4709e06c3a6b0
import os
import re

from scrapfly import ScrapeConfig, ScrapflyClient

BASE_CONFIG = {
    "asp": True,
    "country": "US",
}

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

response = SCRAPFLY.scrape(ScrapeConfig(
    "https://www.amazon.com/dp/B07F7TLZF4",
    **BASE_CONFIG,
))

# this pattern selects value between curly braces that follow dimensionValeusDsiplayData key:
variant_data = re.findall(r'dimensionValuesDisplayData"\s*:\s* ({.+?}),\n', response.content)
print(variant_data)