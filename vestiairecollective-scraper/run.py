"""
This example run script shows how to run the vestiairecollective.com scraper defined in ./vestiairecollective.py
It scrapes product data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import asyncio
import json
from pathlib import Path
import vestiairecollective

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache for basic use
    vestiairecollective.BASE_CONFIG["cache"] = False

    print(
        "running Vestiairecollective scrape and saving results to ./results directory"
    )

    products_data = await vestiairecollective.scrape_products(
        urls=[
            "https://www.vestiairecollective.com/men-clothing/polo-shirts/louis-vuitton/blue-cotton-louis-vuitton-polo-shirt-72570253.shtml",
            "https://www.vestiairecollective.com/men-clothing/knitwear-sweatshirts/louis-vuitton/black-wool-louis-vuitton-knitwear-sweatshirt-72612965.shtml",
            "https://www.vestiairecollective.com/women-clothing/dresses/louis-vuitton/multicolour-cotton-louis-vuitton-dress-72644779.shtml",
        ]
    )
    with open(output.joinpath("products.json"), "w", encoding="utf-8") as file:
        json.dump(products_data, file, indent=2, ensure_ascii=False)

    products_data = await vestiairecollective.scrape_search(
        url="https://www.vestiairecollective.com/search/?q=louis+vuitton", max_pages=2
    )
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(products_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
