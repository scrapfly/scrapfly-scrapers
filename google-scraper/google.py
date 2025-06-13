"""
This is an example web scraper for google.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import operator

from urllib.parse import quote
from loguru import logger as log
from typing import Dict, List
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse


SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass Google web scraping blocking
    "asp": True,
    # set the poxy location to US
    "country": "US",
}


class NoResults(Exception):
    "Raised when requesting pagination without results"
    pass


def parse_place(response: ScrapeApiResponse) -> Dict:
    """parse Google Maps place"""

    def aria_with_label(label):
        """gets aria element as is"""
        return selector.css(f"*[aria-label*='{label}']::attr(aria-label)")

    def aria_no_label(label):
        """gets aria element as text with label stripped off"""
        text = aria_with_label(label).get("")
        return text.split(label, 1)[1].strip()

    selector = response.selector
    result = {
        "name": "".join(selector.css("h1::text").getall()).strip(),
        "category": selector.xpath(
            "//button[contains(@jsaction, 'category')]/text()"
        ).get(),
        # most of the data can be extracted through accessibility labels:
        "address": aria_no_label("Address: "),
        "website": aria_no_label("Website: "),
        "phone": aria_no_label("Phone: "),
        "review_count": aria_with_label(" reviews").get(),
        # to extract star numbers from text we can use regex pattern for numbers: "\d+"
        "stars": aria_with_label(" stars").re("\d+.*\d+")[0],
        "5_stars": aria_with_label("5 stars").re(r"(\d+) review")[0],
        "4_stars": aria_with_label("4 stars").re(r"(\d+) review")[0],
        "3_stars": aria_with_label("3 stars").re(r"(\d+) review")[0],
        "2_stars": aria_with_label("2 stars").re(r"(\d+) review")[0],
        "1_stars": aria_with_label("1 stars").re(r"(\d+) review")[0],
    }
    return result


async def scrape_google_map_places(urls: List[str]) -> List[Dict]:
    """scrape google map place pages"""
    data = []
    to_scrape = [
        ScrapeConfig(
            url=url,
            **BASE_CONFIG,
            render_js=True,
            wait_for_selector="//button[contains(@jsaction, 'reviewlegaldisclosure')]",
        )
        for url in urls
    ]
    log.info(f"scraping {len(to_scrape)} google map place pages")
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        data.append(parse_place(response))
    return data


async def find_google_map_places(query: str) -> List[Dict]:
    script = """
        function waitCss(selector, n=1, require=false, timeout=5000) {
        console.log(selector, n, require, timeout);
        var start = Date.now();
        while (Date.now() - start < timeout){
            if (document.querySelectorAll(selector).length >= n){
            return document.querySelectorAll(selector);
            }
        }
        if (require){
            throw new Error(`selector "${selector}" timed out in ${Date.now() - start} ms`);
        } else {
            return document.querySelectorAll(selector);
        }
        }

        var results = waitCss("div.Nv2PK a, div.tH5CWc a, div.THOPZb a", n=10, require=false);
        return Array.from(results).map((el) => el.getAttribute("href"))
    """
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url=f"https://www.google.com/maps/search/{query.replace(' ', '+')}/?hl=en",
            render_js=True,
            js=script,
            country="US",
        )
    )
    urls = response.scrape_result["browser_data"]["javascript_evaluation_result"]
    return urls


def parse_rich_snippets(response: ScrapeApiResponse):
    selector = response.selector
    snippet = selector.xpath(
        "//h2[re:test(.,'complementary results','i')]/following-sibling::div[1]"
    )
    data = {
        "title": snippet.xpath(".//*[@data-attrid='title']//text()").get(),
        "subtitle": snippet.xpath(".//*[@data-attrid='subtitle']//text()").get(),
        "website": snippet.xpath(
            ".//a[@data-attrid='visit_official_site']/@href"
        ).get(),
        "description": snippet.xpath(
            ".//div[@data-attrid='description']//span//text()"
        ).get(),
        "description_more_link": snippet.xpath(
            ".//div[@data-attrid='description']//@href"
        ).get(),
    }
    # get summary info rows
    data["info"] = {}
    for row in snippet.xpath(".//div[@data-md]/div/div/div[span]"):
        label = row.xpath(".//span/text()").get()
        value = row.xpath(".//a/text()").get()
        data["info"][label] = value
    # get social media links
    data["socials"] = {}
    for profile in snippet.xpath(
        ".//div[@data-attrid='kc:/common/topic:social media presence']//g-link/a"
    ):
        label = profile.xpath(".//text()").get()
        url = profile.xpath(".//@href").get()
        data["socials"][label] = url
    return data


def parse_keywords(response: ScrapeApiResponse) -> List[str]:
    """parse keywords from google search pages"""
    selector = response.selector
    related_search = []
    for suggestion in selector.xpath(
        "//div[div/div/span[contains(text(), 'search for')]]/following-sibling::div//a"
    ):
        related_search.append("".join(suggestion.xpath(".//text()").getall()))
    people_ask_for = selector.css(".related-question-pair span::text").getall()
    return {"related_search": related_search, "people_ask_for": people_ask_for}


async def scrape_keywords(query: str) -> List[str]:
    """request google search page for keyword data"""
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            f"https://www.google.com/search?hl=en&q={quote(query)}", **BASE_CONFIG, render_js=True
        )
    )
    data = parse_keywords(response)
    log.success(
        f"scraped {len(data['related_search'])} related search kws and {len(data['people_ask_for'])} FAQs"
    )
    return data


def parse_serp(response: ScrapeApiResponse) -> List[Dict]:
    """parse search results from google search page"""
    results = []
    selector = response.selector
    has_data = selector.xpath("//h1[contains(text(),'Search Results')]").get()
    if not has_data:
        raise NoResults("No search results found")

    if "start" not in response.context["url"]:
        position = 0
    else:
        position = int(response.context["url"].split("start=")[-1])

    for box in selector.xpath(
        "//h1[contains(text(),'Search Results')]/following-sibling::div[1]/div"
    ):
        title = box.xpath(".//h3/text()").get()
        url = box.xpath(".//h3/../@href").get()
        description = "".join(box.xpath(".//div[@data-sncf]//text()").getall())
        if not title or not url:
            continue
        position += 1
        results.append(
            {
                "position": position,
                "title": title,
                "url": url,
                "origin": box.xpath(".//div[*[cite]]/div/span/text()").get(),
                "domain": url.split("https://")[-1].split("/")[0].replace("www.", ""),
                "description": description.split(" — ")[-1] if description else None,
                "date": box.xpath(".//span[contains(text(),' —')]/span/text()").get(),
            }
        )
    results.sort(key=lambda x: x["position"])
    return results


async def scrape_serp(query: str, max_pages: int = None) -> List[Dict]:
    """query google search for serp results"""
    results = []
    results_per_page = 10
    offset = 0 if not max_pages else max_pages * results_per_page  # 10 results per page
    to_scrape = [
        ScrapeConfig(
            f"https://www.google.com/search?hl=en&q={quote(query)}&start={cursor}",
            **BASE_CONFIG,
        )
        for cursor in range(0, offset, 10)
    ]

    log.info(f"scraping {len(to_scrape)} search pages for the query: {query}")
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        try:
            data = parse_serp(response)
            results.extend(data)
        except NoResults as e:  # catch any exception
            log.warning(f"Encouterned search page without results")
            continue
        except Exception as e:
            log.error(f"Error occured: {e}")
            continue
    log.success(f"scraped {len(results)} SERP results of the query: {query}")
    results.sort(key=operator.itemgetter("position"))
    return results
