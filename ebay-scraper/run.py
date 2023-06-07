"""
This example run script shows how to run the Aliexpress.com scraper defined in ./aliexpress.py
It scrapes product data and product search and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
import ebay
from datetime import datetime
from pathlib import Path

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache for basic use
    ebay.BASE_CONFIG["cache"] = True
    ebay.BASE_CONFIG["country"] = "US"

    print("running Ebay.com scrape and saving results to ./results directory")
    url = "https://www.ebay.com/sch/i.html?_from=R40&_nkw=iphone&_sacat=0&LH_TitleDesc=0&Storage%2520Capacity=16%2520GB&_dcat=9355&_ipg=240&rt=nc&LH_All=1"
    search_results = await ebay.scrape_search(url, max_pages=2)
    output.joinpath("search.json").write_text(json.dumps(search_results, indent=2, cls=DateTimeEncoder))

    single_product_result = await ebay.scrape_product("https://www.ebay.com/itm/332562282948")
    output.joinpath("product.json").write_text(json.dumps(single_product_result, indent=2))

    variant_product_result = await ebay.scrape_product("https://www.ebay.com/itm/393531906094")
    output.joinpath("product-with-variants.json").write_text(json.dumps(variant_product_result, indent=2))



class DateTimeEncoder(json.JSONEncoder):
    """Custom JSONEncoder subclass that knows how to encode datetime values."""

    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()  # Convert datetime objects to ISO-8601 string format
        return super(DateTimeEncoder, self).default(o)  # Default behaviour for other types



if __name__ == "__main__":
    asyncio.run(run())
