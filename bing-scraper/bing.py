"""
This is an example web scraper for bing.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import re
import os
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse
from typing import Dict, List
from urllib.parse import urlencode
from loguru import logger as log

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass Bing web scraping blocking
    "asp": True,
    # set the poxy location to US to get the result in English
    "country": "US",
}


def parse_serps(response: ScrapeApiResponse) -> List[Dict]:
    """parse SERPs from bing search pages"""
    selector = response.selector
    data = []
    if "first" not in response.context["url"]:
        position = 0
    else:
        position = int(response.context["url"].split("first=")[-1])
    for result in selector.xpath("//li[@class='b_algo']"):
        url = result.xpath(".//h2/a/@href").get()
        description = result.xpath("normalize-space(.//div/p)").extract_first()
        date = description.split("·")[0].strip().replace("Web", "").strip()
        # date can be in different format
        if len(date) > 12:
            date_pattern = re.compile(r"\b\d{2}-\d{2}-\d{4}\b")
            date_pattern.findall(description)
            dates = date_pattern.findall(date)
            date = dates[0] if dates else None
        position += 1
        data.append(
            {
                "position": position,
                "title": "".join(result.xpath(".//h2/a//text()").extract()),
                "url": url,
                "origin": result.xpath(".//div[@class='tptt']/text()").get(),
                "domain": url.split("https://")[-1].split("/")[0].replace("www.", "")
                if url
                else None,
                "description": description,
                "date": date,
            }
        )
    return data


def parse_keywords(response: ScrapeApiResponse) -> Dict:
    """parse FAQs and popular keywords on bing search pages"""
    selector = response.selector
    faqs = []
    for faq in selector.xpath("//div[@class='b_slidebar']/div/div[contains(@data-tag, 'QnA')]"):
        url = faq.xpath(".//h2/a/@href").get()
        faqs.append(
            {
                "query": faq.xpath("./@data-query").get(),
                "answer": faq.xpath(".//span[contains(@data-tag, 'QnA')]/text()").get(),
                "title": "".join(faq.xpath(".//div[@class='b_algo']/h2/a//text()").extract()),
                "domain": url.split("https://")[-1].split("/")[0].replace("www.", "")if url else None,
                "url": url,
            }
        )
    related_keywords = []
    for keyword in selector.xpath(".//li[@class='b_ans']/div/ul/li"):
        related_keywords.append("".join(keyword.xpath(".//a/div//text()").extract()))

    return {"FAQs": faqs, "related_keywords": related_keywords}


def parse_rich_snippet(response: ScrapeApiResponse) -> Dict:
    """parse rich snippets from Bing search"""
    selector = response.selector
    data = {}
    data["title"] = selector.xpath("//span[contains(@class, 'txt_heros')]/a/@title").get()
    data["link"] = selector.xpath("//span[contains(@class, 'txt_heros')]/a/@href").get()
    data["heading"] = selector.xpath("//div[contains(@class, 'header_txt')]/a/text()").get()
    data["links"] = {}
    for item in selector.xpath("//div[contains(@class, 'webicons')]/div"):
        name = item.xpath(".//a/@title").get()
        link = item.xpath(".//a/@href").get()
        data["links"][name] = link

    data["info"] = {}
    for row in selector.xpath("//div[contains(@class, 'expansion')]/div[contains(@class, 'row')]"):
        key = row.xpath(".//div/div/a[1]/text()").get().strip()
        value = row.xpath("string(.//div[not(contains(@class, 'title'))])").get().strip().replace(key, "")
        data["info"][key] = value

    all_text = ""
    for div_element in selector.xpath("//div[@class='lite-entcard-blk l_ecrd_bkg_hlt']"):
        div_text = div_element.xpath("string(.)").get().strip()
        all_text += div_text + "\n"
    data["descrption"] = all_text
    return data


async def scrape_search(query: str, max_pages: int = None):
    """scrape bing search pages"""
    url = f"https://www.bing.com/search?{urlencode({'q': query})}"
    log.info("scraping the first search page")
    response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    serp_data = parse_serps(response)

    log.info(f"scraping search pagination ({max_pages - 1} more pages)")
    total_results = (max_pages - 1) * 10  # each page contains 10 results
    other_pages = [
        ScrapeConfig(url + f"&first={start}", **BASE_CONFIG)
        for start in range(10, total_results + 10, 10)
    ]

    # scrape the remaining search pages concurrently
    async for response in SCRAPFLY.concurrent_scrape(other_pages):
        data = parse_serps(response)
        serp_data.extend(data)
    log.success(f"scraped {len(serp_data)} search results from Bing search")
    return serp_data


async def scrape_keywords(query: str):
    """scrape bing search pages for keyword data"""
    url = f"https://www.bing.com/search?{urlencode({'q': query})}"
    log.info("scraping Bing search for keyword data")
    response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    keyword_data = parse_keywords(response)
    log.success(
        f"scraped {len(keyword_data['related_keywords'])} keywords and {len(keyword_data['FAQs'])} FAQs from Bing search"
    )
    return keyword_data


async def scrape_rich_snippets(query: str):
    """scrape bing search pages for keyword data"""
    url = f"https://www.bing.com/search?{urlencode({'q': query})}"
    log.info("scraping Bing search for keyword data")
    response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG, render_js=True))
    rich_snippet_data = parse_rich_snippet(response)
    log.success(f"scraped from Bing rich snippets")
    return rich_snippet_data
