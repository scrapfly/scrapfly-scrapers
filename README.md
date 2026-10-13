# ScrapFly Scrapers 🕷️

This repository contains educational example scrapers for popular web scraping targets using the [ScrapFly](https://scrapfly.io) web scraping API and Python.  
Most Scrapers use a simple web scraping stack:
- Python version 3.10+
- [Scrapfly's Python SDK](https://github.com/scrapfly/python-scrapfly) for sending HTTP request, bypass blocking and parsing the HTML using the built-in [parsel](https://pypi.org/project/parsel/) selector.
- [asyncio](https://pypi.org/project/asyncio/) for writing concurrent code using the async/await syntax.
- [JMESPath](https://pypi.org/project/jmespath/) and [nested-lookup](https://pypi.org/project/nested-lookup/) for JSON parsing when needed.
- [loguru](https://pypi.org/project/loguru/) for logging.

To learn more about web scraping see our full tutorials on how to scrape these targets (and many others) see the [scrapeguide directory](https://scrapfly.io/blog/tag/scrapeguide/).  

## List of Scrapers
Below is the list of available web scrapers for the supported domains along with their scrape guide, sample datasets, and status. 👇

<table>

  <tr>
    <td><strong>Domain</strong></td>
    <td><strong>Guide</strong></td> 
    <td><strong>Sample Datasets</strong></td>
    <td><strong>Status</strong></td>
  </tr>

  <tr>
    <td><a href="/aliexpress-scraper/">Aliexpress.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-aliexpress/">How to Scrape Aliexpress.com (2025 Update)</a></td>    
    <td>
    <ul>
        <li><a href="./aliexpress-scraper/results/product.json">Product pages</a></li>
        <li><a href="./aliexpress-scraper/results/search.json">Search pages</a></li>
        <li><a href="./aliexpress-scraper/results/reviews.json">Product reviews</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/aliexpress-scraper.svg" alt="aliexpress-scraper-status"></td>    
  </tr>

  <tr>
    <td><a href="/amazon-scraper/">Amazon.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-amazon/">How to Scrape Amazon.com Product Data and Reviews</a></td>    
    <td>
    <ul>
        <li><a href="./amazon-scraper/results/product.json">Product pages</a></li>
        <li><a href="./amazon-scraper/results/search.json">Search pages</a></li>
        <li><a href="./amazon-scraper/results/reviews.json">Product reviews</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/amazon-scraper.svg" alt="amazon-scraper-status"></td>
  </tr>

  <tr>
    <td><a href="/bestbuy-scraper/">BestBuy.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-bestbuy-product-offer-and-review-data/">How to Scrape BestBuy Product, Offer and Review Data</a></td>    
    <td>
    <ul>
        <li><a href="./bestbuy-scraper/results/promos.json">Sitemap pages</a></li>
        <li><a href="./bestbuy-scraper/results/products.json">Product pages</a></li>
        <li><a href="./bestbuy-scraper/results/reviews.json">Review pages</a></li>
        <li><a href="./bestbuy-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/bestbuy-scraper.svg" alt="bestbuy-scraper-status"></td>
  </tr>    

  <tr> 
    <td><a href="/bing-scraper/">Bing.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-bing-search-using-python/">How to Scrape Bing Search with Python</a></td>    
    <td>
    <ul>
        <li><a href="./bing-scraper/results/serps.json">SERP data</a></li>
        <li><a href="./bing-scraper/results/keywords.json">Keyword data</a></li>
        <li><a href="./bing-scraper/results/rich_snippets.json">Rich snippet data</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/bing-scraper.svg" alt="bing-scraper-status"></td>
  </tr>    

  <tr>
    <td><a href="/booking-scraper/">Booking.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-bookingcom/">How to Scrape Booking.com (2025 Update)</a></td>    
    <td>
    <ul>
        <li><a href="./bookingcom-scraper/results/hotel.json">Hotel pages</a></li>
        <li><a href="./bookingcom-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/bookingcom-scraper.svg" alt="bookingcom-scraper-status"></td>
  </tr>    

<tr>
    <td><a href="/crunchbase-scraper/">Crunchbase.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-crunchbase/">How to Scrape Crunchbase in 2025</a></td>    
    <td>
    <ul>
        <li><a href="./crunchbase-scraper/results/company.json">Company pages</a></li>
        <li><a href="./crunchbase-scraper/results/person.json">Investor pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/crunchbase-scraper.svg" alt="crunchbase-scraper-status"></td>
</tr>    

<tr>
    <td><a href="/domaincom-scraper/">Domain.com.au</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-domain-com-au-real-estate-property-data/">How to Scrape Domain.com.au Real Estate Property Data</a></td>    
    <td>
    <ul>
        <li><a href="./domaincom-scraper/results/properties.json">Property pages</a></li>
        <li><a href="./domaincom-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/domaincom-scraper.svg" alt="domaincom-scraper-status"></td>
</tr>    

<tr>
    <td><a href="/ebay-scraper/">Ebay.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-ebay/">How to Scrape Ebay Using Python (2025 Update)</a></td>    
    <td>
    <ul>
        <li><a href="./ebay-scraper/results/product.json">Product pages</a></li>
        <li><a href="./ebay-scraper/results/product-with-variants.json">Product pages with variant</a></li>
        <li><a href="./ebay-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/ebay-scraper.svg" alt="ebay-scraper-status"></td>
</tr>    

<tr>
    <td><a href="/etsy-scraper/">Etsy.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-etsy-com-product-review-data/">How to Scrape Etsy.com Product, Shop and Search Data</a></td>    
    <td>
    <ul>
        <li><a href="./etsy-scraper/results/products.json">Product pages</a></li>
        <li><a href="./etsy-scraper/results/shops.json">Shop pages</a></li>
        <li><a href="./etsy-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/etsy-scraper.svg" alt="etsy-scraper-status"></td>
</tr>    

<tr>
    <td><a href="/fashionphile-scraper/">Fashionphile.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-fashionphile/">How to Scrape Fashionphile for Second Hand Fashion Data</a></td>    
    <td>
    <ul>
        <li><a href="./fashionphile-scraper/results/products.json">Product pages</a></li>
        <li><a href="./fashionphile-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/fashionphile-scraper.svg" alt="fashionphile-scraper-status"></td>
</tr>    

<tr>
    <td><a href="/glassdoor-scraper/">Glassdoor.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-glassdoor/">How to Scrape Glassdoor (2025 update)</a></td>
    <td>
    <ul>
        <li><a href="./glassdoor-scraper/results/jobs.json">Job pages</a></li>
        <li><a href="./glassdoor-scraper/results/reviews.json">Review pages</a></li>
        <li><a href="./glassdoor-scraper/results/salaries.json">Salary pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/glassdoor-scraper.svg" alt="glassdoor-scraper-status"></td>
</tr>  

<tr>
    <td><a href="/goat-scraper/">Goat.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-goat-com-fashion-apparel/">How to Scrape Goat.com for Fashion Apparel Data in Python</a></td>
    <td>
    <ul>
        <li><a href="./goat-scraper/results/products.json">Product pages</a></li>
        <li><a href="./goat-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/goat-scraper.svg" alt="goat-scraper-status"></td>
</tr>

<tr>
    <td><a href="/goodreads-scraper/">Goodreads.com</a></td>
    <td></td>
    <td>
    <ul>
        <li><a href="./goodreads-scraper/results/book.json">Book pages</a></li>
        <li><a href="./goodreads-scraper/results/reviews.json">Review pages</a></li>
        <li><a href="./goodreads-scraper/results/list.json">List pages</a></li>
        <li><a href="./goodreads-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/goodreads-scraper.svg" alt="goodreads-scraper-status"></td>
</tr>

<tr>
    <td><a href="/google-scraper/">Google.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-google/">How to Scrape Google Search Results</a> - <a href="https://scrapfly.io/blog/how-to-scrape-google-maps/">How to Scrape Google Maps</a></td>
    <td>
    <ul>
        <li><a href="./google-scraper/results/serp.json">SERP data</a></li>
        <li><a href="./google-scraper/results/keywords.json">Keyword data</a></li>
        <li><a href="./google-scraper/results/google_map_places_urls.json">Google Maps place URLs</a></li>
        <li><a href="./google-scraper/results/google_map_places.json">Google Maps place data</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/goat-scraper.svg" alt="goat-scraper-status"></td>
</tr>

<tr>
    <td><a href="/homegate-scraper/">Homegate.ch</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-homegate-ch-real-estate-property-data/">How to Scrape Homegate.ch Real Estate Property Data</a></td>
    <td>
    <ul>
        <li><a href="./homegate-scraper/results/properties.json">Property pages</a></li>
        <li><a href="./homegate-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/homegate-scraper.svg" alt="homegate-scraper-status"></td>
</tr>

<tr>
    <td><a href="/idealista-scraper/">Idealista.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-idealista/">How to Scrape Idealista.com in Python - Real Estate Property Data</a></td>
    <td>
    <ul>
        <li><a href="./idealista-scraper/results/properties.json">Property pages</a></li>
        <li><a href="./idealista-scraper/results/search_data.json">Search pages</a></li>
        <li><a href="./idealista-scraper/results/search_URLs.json">Provinces pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/idealista-scraper.svg" alt="idealista-scraper-status"></td>
</tr>

<tr>
    <td><a href="/immobilienscout24-scraper/">Immobilienscout24.de</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-immobillienscout24-real-estate-property-data/">How to Scrape Immobilienscout24.de Real Estate Data</a></td>
    <td>
    <ul>
        <li><a href="./immobilienscout24-scraper/results/properties.json">Property pages</a></li>
        <li><a href="./immobilienscout24-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/immobilienscout24-scraper.svg" alt="immobilienscout24-scraper-status"></td>
</tr>

<tr>
    <td><a href="/immoscout24-scraper/">Immoscout24.ch</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-immoscout24-ch-real-estate-property-data/">How to Scrape Immoscout24.ch Real Estate Property Data</a></td>
    <td>
    <ul>
        <li><a href="./immoscout24-scraper/results/properties.json">Property pages</a></li>
        <li><a href="./immoscout24-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/immoscout24-scraper.svg" alt="immoscout24-scraper-status"></td>
</tr>

<tr>
    <td><a href="/immowelt-scraper/">Immowelt.de</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-immowelt-de-real-estate-properties/">How to Scrape Immowelt.de Real Estate Data</a></td>
    <td>
    <ul>
        <li><a href="./immowelt-scraper/results/properties.json">Property pages</a></li>
        <li><a href="./immowelt-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/immowelt-scraper.svg" alt="immowelt-scraper-status"></td>
</tr>

<tr>
    <td><a href="/indeed-scraper/">Indeed.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-indeedcom/">How to Scrape Indeed.com (2025 Update)</a></td>
    <td>
    <ul>
        <li><a href="./indeed-scraper/results/jobs.json">Job pages</a></li>
        <li><a href="./indeed-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/indeed-scraper.svg" alt="indeed-scraper-status"></td>
</tr>

<tr>
    <td><a href="/instagram-scraper/">Instagram.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-instagram/">How to Scrape Instagram in 2025</a></td>
    <td>
    <ul>
        <li><a href="./instagram-scraper/results/user.json">User data</a></li>
        <li><a href="./instagram-scraper/results/all-user-posts.json">All user posts</a></li>
        <li><a href="./instagram-scraper/results/multi-image-post.json">Multi image post</a></li>
        <li><a href="./instagram-scraper/results/video-post.json">Video Post</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/instagram-scraper.svg" alt="instagram-scraper-status"></td>
</tr>

<tr>
    <td><a href="/leboncoin-scraper/">Leboncoin.fr</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-leboncoin-marketplace-real-estate/">How to Web Scrape Leboncoin.fr using Python</a></td>
    <td>
    <ul>
        <li><a href="./leboncoin-scraper/results/ads.json">Ad pages</a></li>
        <li><a href="./leboncoin-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/leboncoin-scraper.svg" alt="leboncoin-scraper-status"></td>
</tr>

<tr>
    <td><a href="/nordstorm-scraper/">Nordstorm.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-nordstrom/">How to Scrape Nordstrom Fashion Product Data</a></td>
    <td>
    <ul>
        <li><a href="./nordstorm-scraper/results/products.json">Product pages</a></li>
        <li><a href="./nordstorm-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/nordstorm-scraper.svg" alt="nordstorm-scraper-status"></td>
</tr>

<tr>
    <td><a href="/realestatecom-scraper/">Realestate.com.au</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-realestate-com-au-property-listing-data/">How to Scrape Realestate.com.au Property Listing Data</a></td>
    <td>
    <ul>
        <li><a href="./realestatecom-scraper/results/properties.json">Property pages</a></li>
        <li><a href="./realestatecom-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/realestatecom-scraper.svg" alt="realestatecom-scraper-status"></td>
</tr>

<tr>
    <td><a href="/realtorcom-scraper/">Realtor.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-realtorcom/">How to Scrape Realtor.com - Real Estate Property Data</a></td>
    <td>
    <ul>
        <li><a href="./realtorcom-scraper/results/property.json">Property pages</a></li>
        <li><a href="./realtorcom-scraper/results/search.json">Search pages</a></li>
        <li><a href="./realtorcom-scraper/results/feed.json">Feed pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/realtorcom-scraper.svg" alt="realtorcom-scraper-status"></td>
</tr>

<tr>
    <td><a href="/reddit-scraper/">Reddit.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-reddit-social-data/">How to Scrape Reddit Posts, Subreddits and Profiles
</a></td>
    <td>
    <ul>
        <li><a href="./reddit-scraper/results/post.json">Post pages</a></li>
        <li><a href="./reddit-scraper/results/subreddit.json">Subreddit pages</a></li>
        <li><a href="./reddit-scraper/results/user_comments.json">User comment pages</a></li>
        <li><a href="./reddit-scraper/results/user_posts.json">User post pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/reddit-scraper.svg" alt="reddit-scraper-status"></td>
</tr>

<tr>
    <td><a href="/redfin-scraper/">Redfin.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-redfin/">How to Scrape Redfin Real Estate Property Data in Python
</a></td>
    <td>
    <ul>
        <li><a href="./redfin-scraper/results/properties_for_sale.json">Property pages for sale</a></li>
        <li><a href="./redfin-scraper/results/properties_for_rent.json">Property pages for rent</a></li>
        <li><a href="./redfin-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/redfin-scraper.svg" alt="redfin-scraper-status"></td>
</tr>

<tr>
    <td><a href="./rightmove-scraper/">Rightmove.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-rightmove/">How to Scrape RightMove Real Estate Property Data with Python</a></td>
    <td>
    <ul>
        <li><a href="./rightmove-scraper/results/properties.json">Property pages</a></li>
        <li><a href="./rightmove-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/rightmove-scraper.svg" alt="rightmove-scraper-status"></td>
</tr>

<tr>
    <td><a href="./seloger-scraper/">Seloger.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-seloger-com-listing-real-estate-ads/">How to Scrape Seloger.com - Real Estate Listing Data</a></td>
    <td>
    <ul>
        <li><a href="./seloger-scraper/results/property.json">Property pages</a></li>
        <li><a href="./seloger-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/seloger-scraper.svg" alt="seloger-scraper-status"></td>
</tr>

<tr>
    <td><a href="./shopify-scraper/">Shopify stores</a></td>
    <td><a href="https://scrapfly.io/blog/posts/how-to-scrape-shopify-stores">How to Scrape Shopify Stores for Products, Prices, and Variants</a></td>
    <td>
    <ul>
        <li><a href="./shopify-scraper/results/preflight.json">Storefront preflight</a></li>
        <li><a href="./shopify-scraper/results/catalog.json">Catalog products.json</a></li>
        <li><a href="./shopify-scraper/results/collection.json">Collection products</a></li>
        <li><a href="./shopify-scraper/results/product_pages.json">Product pages</a></li>
        <li><a href="./shopify-scraper/results/product_urls.json">Sitemap product urls</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/shopify-scraper.svg" alt="shopify-scraper-status"></td>
</tr>

<tr>
    <td><a href="./similarweb-scraper/">Similarweb.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-similarweb/">How to Scrape SimilarWeb Website Traffic Analytics</a></td>
    <td>
    <ul>
        <li><a href="./similarweb-scraper/results/websites.json">Website pages</a></li>
        <li><a href="./similarweb-scraper/results/websites_compare.json">Website compare pages</a></li>
        <li><a href="./similarweb-scraper/results/trends.json">Trend pages</a></li>
        <li><a href="./similarweb-scraper/results/sitemap_urls.json">Sitemaps</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/similarweb-scraper.svg" alt="similarweb-scraper-status"></td>
</tr>

<tr>
    <td><a href="./stockx-scraper/">Stockx.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-stockx/">How to Scrape StockX e-commerce Data with Python</a></td>
    <td>
    <ul>
        <li><a href="./stockx-scraper/results/product.json">Product pages</a></li>
        <li><a href="./stockx-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/stockx-scraper.svg" alt="stockx-scraper-status"></td>
</tr>

<tr>
    <td><a href="./threads-scraper/">Threads.net</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-threads/">How to scrape Threads by Meta using Python (2025 Update)</a></td>
    <td>
    <ul>
        <li><a href="./threads-scraper/results/profile.json">Profile pages</a></li>
        <li><a href="./threads-scraper/results/thread.json">Thread pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/threads-scraper.svg" alt="threads-scraper-status"></td>
</tr>

<tr>
    <td><a href="./tiktok-scraper/">TikTok.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-tiktok-python-json/">How To Scrape TikTok in 2025</a></td>
    <td>
    <ul>
        <li><a href="./tiktok-scraper/results/comments.json">Comment data</a></li>
        <li><a href="./tiktok-scraper/results/posts.json">Post data</a></li>
        <li><a href="./tiktok-scraper/results/profiles.json">Profile data</a></li>
        <li><a href="./tiktok-scraper/results/channel.json">Channel data</a></li>
        <li><a href="./tiktok-scraper/results/search.json">Search data</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/tiktok-scraper.svg" alt="tiktok-scraper-status"></td>
</tr>

<tr>
    <td><a href="./tripadvisor-scraper/">Tripadvisor.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-tripadvisor/">How to Scrape TripAdvisor.com (2025 Updated)</a></td>
    <td>
    <ul>
        <li><a href="./tripadvisor-scraper/results/hotels.json">Hotel pages</a></li>
        <li><a href="./tripadvisor-scraper/results/search.json">Search pages</a></li>
        <li><a href="./tripadvisor-scraper/results/location.json">Location pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/tripadvisor-scraper.svg" alt="tripadvisor-scraper-status"></td>
</tr>

<tr>
    <td><a href="./trustpilot-scraper/">Trustpilot.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-trustpilot-com-reviews/">How to Scrape Trustpilot.com Reviews and Company Data</a></td>
    <td>
    <ul>
        <li><a href="./trustpilot-scraper/results/companies.json">Company pages</a></li>
        <li><a href="./trustpilot-scraper/results/reviews.json">Reviews pages</a></li>
        <li><a href="./trustpilot-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/trustpilot-scraper.svg" alt="trustpilot-scraper-status"></td>
</tr>

<tr>
    <td><a href="./twitter-scraper/">Twitter(X).com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-twitter/">How to Scrape X.com (Twitter) using Python (2025 Update)</a></td>
    <td>
    <ul>
        <li><a href="./twitter-scraper/results/profile.json">Profile pages</a></li>
        <li><a href="./twitter-scraper/results/tweet.json">Tweet pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/twitter-scraper.svg" alt="twitter-scraper-status"></td>
</tr>

<tr>
    <td><a href="./vestiairecollective-scraper/">VestiaireCollective.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-vestiairecollective/">How to Scrape Vestiaire Collective for Fashion Product Data</a></td>
    <td>
    <ul>
        <li><a href="./vestiairecollective-scraper/results/products.json">Product pages</a></li>
        <li><a href="./vestiairecollective-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/vestiairecollective-scraper.svg" alt="vestiairecollective-scraper-status"></td>
</tr>

<tr>
    <td><a href="./g2-scraper/">G2.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-g2-company-data-and-reviews/">How to Scrape G2 Company Data and Reviews</a></td>
    <td>
    <ul>
        <li><a href="./g2-scraper/results/reviews.json">Review pages</a></li>
        <li><a href="./g2-scraper/results/search.json">Search pages</a></li>
        <li><a href="./g2-scraper/results/alternatives.json">Alternatives pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/g2-scraper.svg" alt="g2-scraper-status"></td>
</tr>

<tr>
    <td><a href="/walmart-scraper/">Walmart.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-walmartcom/">How to Scrape Walmart.com Product Data (2025 Update)</a></td>
    <td>
    <ul>
        <li><a href="./walmart-scraper/results/products.json">Product pages</a></li>
        <li><a href="./walmart-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/walmart-scraper.svg" alt="walmart-scraper-status"></td>
</tr>

<tr>
    <td><a href="/wellfound-scraper/">Wellfound.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-wellfound-aka-angellist/">How to Scrape Wellfound Company Data and Job Listings</a></td>
    <td>
    <ul>
        <li><a href="./wellfound-scraper/results/companies.json">Company pages</a></li>
        <li><a href="./wellfound-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/wellfound-scraper.svg" alt="wellfound-scraper-status"></td>
</tr>

<tr>
    <td><a href="/linkedin-scraper/">Linkedin.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-linkedin-person-profile-company-job-data/">How to Scrape LinkedIn in 2025</a></td>
    <td>
    <ul>
        <li><a href="./linkedin-scraper/results/profile.json">Profile pages</a></li>
        <li><a href="./linkedin-scraper/results/company.json">Company pages</a></li>
        <li><a href="./linkedin-scraper/results/job_search.json">Job search pages</a></li>
        <li><a href="./linkedin-scraper/results/jobs.json">Job pages</a></li>
        <li><a href="./linkedin-scraper/results/articles.json">Article pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/linkedin-scraper.svg" alt="linkedin-scraper-status"></td>
</tr>

<tr>
    <td><a href="/yellowpages-scraper/">Yellowpages.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-yellowpages/">How to Scrape YellowPages.com in 2025</a></td>
    <td>
    <ul>
        <li><a href="./yellowpages-scraper/results/business_pages.json">Business pages</a></li>
        <li><a href="./yellowpages-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/yellowpages-scraper.svg" alt="yellowpages-scraper-status"></td>
</tr>

<tr>
    <td><a href="/yelp-scraper/">Yelp.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-yelpcom/">How to Web Scrape Yelp.com (2025 update)</a></td>
    <td>
    <ul>
        <li><a href="./yelp-scraper/results/business_pages.json">Business pages</a></li>
        <li><a href="./yelp-scraper/results/reviews.json">Review pages</a></li>
        <li><a href="./yelp-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/yelp-scraper.svg" alt="yelp-scraper-status"></td>
</tr>

<tr>
    <td><a href="/youtube-scraper/">YouTube.com</a></td></a></td>
    <td><a href="https://scrapfly.io/blog/posts/how-to-scrape-youtube-in-2025">How to Scrape YouTube in 2025</a></td>
    <td>
    <ul>
        <li><a href="./youtube-scraper/results/channel_videos.json">Channel videos</a></li>
        <li><a href="./youtube-scraper/results/channels.json">Channel metadata</a></li>
        <li><a href="./youtube-scraper/results/channel_videos.json">Channel videos</a></li>
        <li><a href="./youtube-scraper/results/videos.json">Video metadata</a></li>
        <li><a href="./youtube-scraper/results/comments.json">Video comments</a></li>
        <li><a href="./youtube-scraper/results/shorts.json">Shorts' metadata</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/youtube-scraper.svg" alt="youtube-scraper-status"></td>
</tr>


<tr>
    <td><a href="/zillow-scraper/">Zillow.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-zillow/">How to Scrape Zillow Real Estate Property Data in Python</a></td>
    <td>
    <ul>
        <li><a href="./zillow-scraper/results/property.json">Property pages</a></li>
        <li><a href="./zillow-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/zillow-scraper.svg" alt="zillow-scraper-status"></td>
</tr>

<tr>
    <td><a href="/zoominfo-scraper/">Zoominfo.com</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-zoominfo/">How to Scrape Zoominfo Company Data (2025 Update)</a></td>
    <td>
    <ul>
        <li><a href="./zoominfo-scraper/results/companies.json">Company pages</a></li>
        <li><a href="./zoominfo-scraper/results/directory.json">Directory pages</a></li>
        <li><a href="./zoominfo-scraper/results/faqs.json">FAQs data</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/zoominfo-scraper.svg" alt="zoominfo-scraper-status"></td>
</tr>

<tr>
    <td><a href="/zoopla-scraper/">Zoopla.co.uk</a></td>
    <td><a href="https://scrapfly.io/blog/how-to-scrape-zoopla/">How to Scrape Zoopla Real Estate Property Data in Python</a></td>
    <td>
    <ul>
        <li><a href="./zoopla-scraper/results/properties.json">Property pages</a></li>
        <li><a href="./zoopla-scraper/results/search.json">Search pages</a></li>
    </ul>
    </td>
    <td><img src="https://github.com/scrapfly/scrapfly-scrapers/raw/ci-status/badges/zoopla-scraper.svg" alt="zoopla-scraper-status"></td>
</tr>
</table>


## Fair Use and Legal Disclaimer

This repository contains _educational_ reference material to illustrate how accessible web scraping can be and the provided programs are not intented to be used in web scraping production. 
That being said, Scrapfly team is constantly updating and improving all of this code for optimal experience. 

Scrapfly does not offer legal advice and as always, consult a lawyer when creating programs that interact with other people's websites though here's a good general intro of what NOT to do:
- Do not store PII (personally identifiable information) of EU citizens who are protected by GDPR.
- Do not scrape and repurpose entire public datasets which can be protected by database protection laws in some countries.
- Do not scrape at rates that could damage the website and scrape only publicly available data.
