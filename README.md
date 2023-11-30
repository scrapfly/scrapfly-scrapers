# ScrapFly Scrapers 🕷️

This repository contains example scrapers for popular web scraping targets using the [ScrapFly](https://scrapfly.io) web scraping API and Python.  
Most Scrapers use a simple web scraping stack:
- Python version 3.10+
- [Scrapfly's Python SDK](https://github.com/scrapfly/python-scrapfly) for sending HTTP request, bypass blocking and parsing the HTML using the built-in [parsel](https://pypi.org/project/parsel/) selector.
- [asyncio](https://pypi.org/project/asyncio/) for writing concurrent code using the async/await syntax.
- [JMESPath](https://pypi.org/project/jmespath/) and [nested-lookup](https://pypi.org/project/nested-lookup/) for JSON parsing when needed.
- [loguru](https://pypi.org/project/loguru/) for logging.


For full guides on how to scrape these targets (and many others) see the [scrapeguide directory](https://scrapfly.io/blog/tag/scrapeguide/).  

## Setup and Run
1. Install the required libraries:
```shell
$ pip install scrapfly-sdk[all] jmespath loguru nested-lookup  
```
2. Export your ScrapFly API key  
- On Mac:
```shell
$ export SCRAPFLY_KEY="YOUR SCRAPFLY KEY"
```
- On Windows:
```shell
$ setx SCRAPFLY_KEY "YOUR SCRAPFLY KEY"
```
3. cd into the scraper directory and run the code:
```shell
$ cd ./example-scraper
$ python run.py
```

## List of Scrapers
The following is the list of supported websites grouped by type.
### E-Commerce
- [Aliexpress.com](#aliexpress)
- [Amazon.com](#amazon)
- [Ebay.com](#ebay)
- [Leboncoin.fr](#leboncoin)
- [Walmart.com](#walmart)

### Fashion
- [Fashionphile.com](#fashionphile)
- [Goat.com](#goat)
- [Nordstorm.com](#nordstorm)
- [Stockx.com](#stockx)
- [Vestiaire collective.com](#vestiaire-collective)

### Jobs and Companies
- [Crunchbase.com](#crunchbase)
- [Glassdoor.com](#glassdoor)
- [Indeed.com](#indeed)
- [Zoominfo.com](#zoominfo)
- [Wellfound.com](#wellfound)

### Real Estate
- [Domain.com.au](#domain)
- [Idealista.com](#idealista)
- [Homegate.ch](#homegate)
- [Immobilienscout24.de](#immobilienscout24)
- [Immoscout24.ch](#immoscout24)
- [Immowelt.de](#immowelt)
- [Realestate.com](#realestate)
- [Realtor.com](#realtor)
- [Redfin.com](#redfin)
- [Rightmove.co.uk](#rightmove)
- [Seloger.com](#seloger)
- [Zillow.com](#zillow)
- [Zoopla.co.uk](#zoopla)

### Social Media
- [Instagram.com](#instagram)
- [Threads.net](#threads)
- [Twitter.com](#twitterx)

### Travel
- [Booking.com](#booking)
- [Tripadvisor.com](#tripadvisor)

### Other
- [Yellowpages.com](#yellowpages)
- [Yelp.com](#yelp)

------------

### Aliexpress
<p align="left">
  <img width="200" height="100" src="./.github/assets/aliexpress-ar21.svg">
</p>

The [aliexpress.com scraper](./aliexpress-scraper/) can scrape the following data:

- Product pages for a specific product data.
- Search pages for product listing data.
- Product reviews.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Product pages](./aliexpress-scraper/results/product.json)  
  - [Search pages](./aliexpress-scraper/results/search.json)  
  - [Product reviews](./aliexpress-scraper/results/reviews.json) 

</details>  

For the full guide, refer to our blog article [How to Scrape Aliexpress.com (2023 Update)](https://scrapfly.io/blog/how-to-scrape-aliexpress/)

### Amazon
<p align="left">
  <img width="200" height="100" src="./.github/assets/amazon-ar21.svg">
</p>

The [amazon.com scraper](./amazon-scraper/) can scrape the following data:
- Product pages for a specific product data.
- Search pages for product listing data.
- Product reviews.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Product pages](./amazon-scraper/results/product.json)  
  - [Search pages](./amazon-scraper/results/search.json)  
  - [Product reviews](./amazon-scraper/results/reviews.json) 

</details>  

For the full guide, refer to our blog article [How to Scrape Amazon.com Product Data and Reviews](https://scrapfly.io/blog/how-to-scrape-amazon/)

### Booking

<p align="left">
  <img width="200" height="100" src="./.github/assets/booking-ar21.svg">
</p>

The [booking.com scraper](./bookingcom-scraper/) can scrape the following data:
- Hotel pages for a specific hotel data.
- Search pages for hotel listing data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Hotel pages](./bookingcom-scraper/results/hotel.json)  
  - [Search pages](./bookingcom-scraper/results/search.json)  

</details>  

For the full guide, refer to our blog article [How to Scrape Booking.com (2023 Update)](https://scrapfly.io/blog/how-to-scrape-bookingcom/)

### Crunchbase
<p align="left">
  <img width="200" height="100" src="./.github/assets/crunchbase-ar21.svg">
</p>

The [crunchbase.com scraper](./crunchbase-scraper/) can scrape the following data:
- Company pages for a specific company data.
- Investor pages for a specific investor data.
- Search pages for hotel listing data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Company pages](./crunchbase-scraper/results/company.json)  
  - [Investor pages](./crunchbase-scraper/results/person.json)  

</details> 

For the full guide, refer to our blog article [How to Scrape Crunchbase Company and People Data (2023 Update)](https://scrapfly.io/blog/how-to-scrape-crunchbase/)

### Domain
<p align="left">
  <img width="300" height="150" src="./.github/assets/domain-com-au-logo-vector.svg">
</p>

The [domain.com.au scraper](./domaincom-scraper/) can scrape the following data:
- Property pages for a specific real estate property data.
- Search pages for real estate property listings data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Property pages](./domaincom-scraper/results/properties.json)  
  - [Search pages](./domaincom-scraper/results/search.json)  

</details> 

For the full guide, refer to our blog article 

### Ebay
<p align="left">
  <img width="200" height="100" src="./.github/assets/ebay-ar21.svg">
</p>

The [ebay.com scraper](./ebay-scraper/) can scrape the following data:
- Product pages for a specific product data.
- Search pages for product listings data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Product pages](./ebay-scraper/results/product.json)  
  - [Product pages with variant](./ebay-scraper/results/product-with-variants.json)  
  - [Search pages](./ebay-scraper/results/search.json)  

</details> 

For the full guide, refer to our blog article [How to Scrape Ebay using Python](https://scrapfly.io/blog/how-to-scrape-ebay/)

### Fashionphile
<p align="left">
  <img width="300" height="100" src="./.github/assets/fashionphile.svg">
</p>

The [fashionphile.com scraper](./fashionphile-scraper/) can scrape the following data:
- Product pages for product data.
- Search pages for product listing data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Product pages](./fashionphile-scraper/results/products.json)  
  - [Search pages](./fashionphile-scraper/results/search.json)  

</details> 

For the full guide, refer to our blog article [How to Scrape Fashionphile for Second Hand Fashion Data](https://scrapfly.io/blog/how-to-scrape-fashionphile/)

### Glassdoor
<p align="left">
  <img width="300" height="150" src="./.github/assets/glassdoor-ar21.svg">
</p>

The [glassdoor.com scraper](./glassdoor-scraper/) can scrape the following data:
- Company search for company page URLs (overiew, jobs, reviews, salaries).
- Job pages for a specific job data.
- Salary pages for a specific company salaries data.
- Review pages for a specific company reviews data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Job pages](./glassdoor-scraper/results/jobs.json)  
  - [Review pages](./glassdoor-scraper/results/reviews.json)  
  - [Salary pages](./glassdoor-scraper/results/salaries.json)  

</details> 

For the full guide, refer to our blog article [How to Scrape Glassdoor (2023 update)](https://scrapfly.io/blog/how-to-scrape-glassdoor/)

### Goat
<p align="left">
  <img width="250" height="75" src="./.github/assets/goat.svg">
</p>

The [goat.com scraper](./goat-scraper/) can scrape the following data:
- Product pages for product data.
- Search pages for product listing data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Product pages](./goat-scraper/results/products.json)  
  - [Search pages](./goat-scraper/results/search.json)  

</details> 

For the full guide, refer to our blog article [How to Scrape Goat.com for Fashion Apparel Data in Python](https://scrapfly.io/blog/how-to-scrape-goat-com-fashion-apparel/)

### Homegate
<p align="left">
  <img width="300" height="150" src="./.github/assets/Homegate_Logo.svg">
</p>

The [homegate.com scraper](./homegate-scraper/) can scrape the following data:
- Property pages for a specific real estate property data.
- Search pages for real estate property listings data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Property pages](./homegate-scraper/results/properties.json)  
  - [Search pages](./homegate-scraper/results/search.json)  

</details> 

For the full guide, refer to our blog article [How to Scrape Homegate.ch Real Estate Property Data](https://scrapfly.io/blog/how-to-scrape-homegate-ch-real-estate-property-data/)

### Idealista
<p align="left">
  <img width="200" height="100" src="./.github/assets/idealista.svg">
</p>

The [idealista.com scraper](./idealista-scraper/) can scrape the following data:
- Property pages for a specific real estate property data.
- Search pages for real estate property listings data.
- Provinces pages for search pages URLs.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Property pages](./idealista-scraper/results/properties.json)  
  - [Search pages](./idealista-scraper/results/search.json)  
  - [Provinces pages](./idealista-scraper/results/search_URLs.json)

</details> 

For the full guide, refer to our blog article [How to Scrape Idealista.com in Python - Real Estate Property Data](https://scrapfly.io/blog/how-to-scrape-idealista/)

### Immobilienscout24
<p align="left">
  <img width="200" height="100" src="./.github/assets/ImmobilienScout24_logo.svg">
</p>

The [immobilienscout24.de scraper](./immobilienscout24-scraper/) can scrape the following data:
- Property pages for a specific real estate property data.
- Search pages for real estate property listings data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Property pages](./immobilienscout24-scraper/results/properties.json)  
  - [Search pages](./immobilienscout24-scraper/results/search.json)  

</details> 

For the full guide, refer to our blog article [How to Scrape Immobilienscout24.de Real Estate Data](https://scrapfly.io/blog/how-to-scrape-immobillienscout24-real-estate-property-data/)

### Immoscout24
<p align="left">
  <img width="200" height="100" src="./.github/assets/immoscout24.svg">
</p>

The [immoscout24.ch scraper](./immoscout24-scraper/) can scrape the following data:
- Property pages for a specific real estate property data.
- Search pages for real estate property listings data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Property pages](./immoscout24-scraper/results/properties.json)  
  - [Search pages](./immoscout24-scraper/results/search.json)  

</details> 

For the full guide, refer to our blog article [How to Scrape Immoscout24.ch Real Estate Property Data](https://scrapfly.io/blog/how-to-scrape-immoscout24-ch-real-estate-property-data/)

### Immowelt
<p align="left">
  <img width="200" height="50" src="./.github/assets/Immowelt-Logo.svg">
</p>

The [immowelt.de scraper](./immowelt-scraper/) can scrape the following data:
- Property pages for a specific real estate property data.
- Search pages for real estate property listings data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Property pages](./immowelt-scraper/results/properties.json)  
  - [Search pages](./immowelt-scraper/results/search.json)  

</details> 

For the full guide, refer to our blog article

### Indeed
<p align="left">
  <img width="200" height="100" src="./.github/assets/Indeed_logo.svg">
</p>

The [indeed.com scraper](./indeed-scraper/) can scrape the following data:
- Job pages for a specific job data.
- Search pages for job listings data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Job pages](./indeed-scraper/results/jobs.json)  
  - [Search pages](./indeed-scraper/results/search.json)  

</details> 

For the full guide, refer to our blog article [How to Scrape Indeed.com (2023 Update)](https://scrapfly.io/blog/how-to-scrape-indeedcom/)

### Instagram
<p align="left">
  <img width="200" height="100" src="./.github/assets/instagram-ar21.svg">
</p>

The [instagram.com scraper](./instagram-scraper/) can scrape the following data:
- User pages for a specific user data.
- Post Pages for a specific post data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [User](./instagram-scraper/results/user.json)  
  - [All user posts](./instagram-scraper/results/all-user-posts.json)  
  - [Multi image post](./instagram-scraper/results/multi-image-post.json)  
  - [Video Post](./instagram-scraper/results/video-post.json)  

</details> 

For the full guide, refer to our blog article [How to Scrape Instagram](https://scrapfly.io/blog/how-to-scrape-instagram/)

### Leboncoin
<p align="left">
  <img width="200" height="150" src="./.github/assets/leboncoin.svg">
</p>

The [leboncoin.fr scraper](./leboncoin-scraper/) can scrape the following data:
- product pages for a specific product data.
- Search pages for product listing data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Ad pages](./leboncoin-scraper/results/ad.json)  
  - [Search pages](./leboncoin-scraper/results/search.json)  

</details> 

For the full guide, refer to our blog article [How to Web Scrape Leboncoin.fr using Python](https://scrapfly.io/blog/how-to-scrape-leboncoin-marketplace-real-estate/)

### Nordstorm
<p align="left">
  <img width="350" height="40" src="./.github/assets/nordstrom.svg">
</p>

The [nordstorm.com scraper](./nordstorm-scraper/) can scrape the following data:
- Product pages for product data.
- Search pages for product listing data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Product pages](./nordstorm-scraper/results/products.json)  
  - [Search pages](./nordstorm-scraper/results/search.json)  

</details> 

For the full guide, refer to our blog article [How to Scrape Nordstrom Fashion Product Data](https://scrapfly.io/blog/how-to-scrape-nordstrom/)

### Realestate
<p align="left">
  <img width="300" height="150" src="./.github/assets/realestate-com-au-logo-vector-2023.svg">
</p>

The [realestate.com.au scraper](./realestatecom-scraper/) can scrape the following data:
- Property pages for a specific real estate property data.
- Search pages for real estate property listings data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Property pages](./realestatecom-scraper/results/properties.json)  
  - [Search pages](./realestatecom-scraper/results/search.json)  

</details> 

For the full guide, refer to our blog article

### Realtor
<p align="left">
  <img width="200" height="100" src="./.github/assets/realtor.svg">
</p>

The [realtor.com scraper](./realtor-scraper/) can scrape the following data:
- Property pages for a specific real estate property data.
- Search pages for real estate property listings data.
- Feed pages for newly added propery listings data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Property pages](./realtor-scraper/results/properties.json)  
  - [Search pages](./realtor-scraper/results/search.json)  
  - [Feed pages](./realtor-scraper/results/feed.json)  

</details> 

For the full guide, refer to our blog article [How to Scrape Realtor.com - Real Estate Property Data](https://scrapfly.io/blog/how-to-scrape-realtorcom/)

### Redfin
<p align="left">
  <img width="300" height="150" src="./.github/assets/redfin-logo-vector.svg">
</p>

The [redfin.com scraper](./redfin-scraper/) can scrape the following data:
- Property pages for a specific real estate property data.
- Search pages for real estate property listings data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Property pages for sale](./redfin-scraper/results/properties_for_sale.json)  
  - [Property pages for rent](./redfin-scraper/results/properties_for_rent.json)  
  - [Search pages](./redfin-scraper/results/search.json)  

</details> 

For the full guide, refer to our blog article [How to Scrape Redfin Real Estate Property Data in Python](https://scrapfly.io/blog/how-to-scrape-redfin/)

### Rightmove
<p align="left">
  <img width="200" height="50" src="./.github/assets/rightmove.svg">
</p>

The [rightmove.co.uk scraper](./rightmove-scraper/) can scrape the following data:
- Property pages for a specific real estate property data.
- Search pages for real estate property listings data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Property pages](./rightmove-scraper/results/properties.json)  
  - [Search pages](./rightmove-scraper/results/search.json)  

</details> 

For the full guide, refer to our blog article [How to Scrape RightMove Real Estate Property Data with Python](https://scrapfly.io/blog/how-to-scrape-rightmove/)

### Seloger
<p align="left">
  <img width="200" height="100" src="./.github/assets/SeLoger-2017.svg">
</p>

The [seloger.com scraper](./seloger-scraper/) can scrape the following data:
- Property pages for a specific real estate property data.
- Search pages for real estate property listings data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Property pages](./seloger-scraper/results/property.json)  
  - [Search pages](./seloger-scraper/results/search.json)  

</details> 

For the full guide, refer to our blog article [How to Scrape Seloger.com - Real Estate Listing Data](https://scrapfly.io/blog/how-to-scrape-seloger-com-listing-real-estate-ads/)

### Stockx
<p align="left">
  <img width="200" height="100" src="./.github/assets/StockX_logo.svg">
</p>

The [stockx.com scraper](./stockx-scraper/) can scrape the following data:
- Product pages for a specific product data.
- Search pages for product listings data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Property pages](./stockx-scraper/results/product.json)  
  - [Search pages](./stockx-scraper/results/search.json)  

</details> 

For the full guide, refer to our blog article [How to Scrape StockX e-commerce Data with Python](https://scrapfly.io/blog/how-to-scrape-stockx/)

### Threads
<p align="left">
  <img width="100" height="100" src="./.github/assets/threads.svg">
</p>

The [threads.net scraper](./threads-scraper/) can scrape the following data:
- User pages for a specific user data.
- Theads Pages for a specific thread data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Profile pages](./threads-scraper/results/profile.json)  
  - [Thread pages](./threads-scraper/results/thread.json)  

</details> 

For the full guide, refer to our blog article [How to scrape Threads by Meta using Python (2023-08 Update)](https://scrapfly.io/blog/how-to-scrape-threads/)

### Tripadvisor
<p align="left">
  <img width="200" height="150" src="./.github/assets/tripadvisor-ar21.svg">
</p>

The [tripadvisor.com scraper](./tripadvisor-scraper/) can scrape the following data:
- Holtel pages for a specific hotel data.
- Holtes data in a specific location.
- Search pages for hotel listings data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Hotel pages](./tripadvisor-scraper/results/hotels.json)  
  - [Search pages](./tripadvisor-scraper/results/search.json)  
  - [Location pages](./tripadvisor-scraper/results/location.json)  

</details> 

For the full guide, refer to our blog article [How to Scrape TripAdvisor.com (2023 Updated)](https://scrapfly.io/blog/how-to-scrape-tripadvisor/)

### Twitter(X)
<p align="left">
  <img width="100" height="100" src="./.github/assets/x.svg">
</p>

The [twitter.com scraper](./twitter-scraper/) can scrape the following data:
- Twitter tweet pages for a specific tweet data.
- Twitter user pages for a specific user data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Profile pages](./twitter-scraper/results/profile.json)  
  - [Tweet pages](./twitter-scraper/results/tweet.json)  

</details> 

For the full guide, refer to our blog article [How to Scrape X.com (Twitter) using Python (2023-11 Update)](https://scrapfly.io/blog/how-to-scrape-twitter/)

### Vestiaire collective
<p align="left">
  <img width="400" height="125" src="./.github/assets/vestiaire-collective.svg">
</p>

The [vestiairecollective.com scraper](./vestiairecollective-scraper/) can scrape the following data:
- Product pages for product data.
- Search pages for product listing data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Product pages](./vestiairecollective-scraper/results/products.json)  
  - [Search pages](./vestiairecollective-scraper/results/search.json)  

</details> 

For the full guide, refer to our blog article [How to Scrape Vestiaire Collective for Fashion Product Data](https://scrapfly.io/blog/how-to-scrape-vestiairecollective/)

### Walmart
<p align="left">
  <img width="300" height="100" src="./.github/assets/walmart.svg">
</p>

The [walmart.com scraper](./walmart-scraper/) can scrape the following data:
- Product pages for product data.
- Search pages for product listing data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Product pages](./walmart-scraper/results/products.json)  
  - [Search pages](./walmart-scraper/results/search.json)  

</details> 

For the full guide, refer to our blog article [How to Web Scrape Walmart.com (2023 Update)](https://scrapfly.io/blog/how-to-scrape-walmartcom/)

### Wellfound
<p align="left">
  <img width="300" height="100" src="./.github/assets/wellfound.svg">
</p>

The [wellfound.com scraper](./wellfound-scraper/) can scrape the following data:
- Company pages for company data.
- Search pages for job listing data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Company pages](./wellfound-scraper/results/companies.json)  
  - [Search pages](./wellfound-scraper/results/search.json)  

</details> 

For the full guide, refer to our blog article [How to Scrape Wellfound Company Data and Job Listings](https://scrapfly.io/blog/how-to-scrape-wellfound-aka-angellist/)

### Yellowpages
<p align="left">
  <img width="300" height="75" src="./.github/assets/yellowpages.svg">
</p>

The [yellowpages.com scraper](./yellowpages-scraper/) can scrape the following data:
- Business pages for business data.
- Search pages for business listing data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Business pages](./yellowpages-scraper/results/business_pages.json)  
  - [Search pages](./yellowpages-scraper/results/search.json)  

</details> 

For the full guide, refer to our blog article [How to Scrape YellowPages.com Business Data and Reviews (2023 Update)](https://scrapfly.io/blog/how-to-scrape-yellowpages/)

### Yelp
<p align="left">
  <img width="300" height="75" src="./.github/assets/yelp.svg">
</p>

The [yelp.com scraper](./yelp-scraper/) can scrape the following data:
- Business pages for business data.
- Review pages for business data.
- Search pages for business listing data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Business pages](./yelp-scraper/results/business_pages.json)  
  - [Review pages](./yelp-scraper/results/reviews.json)  
  - [Search pages](./yelp-scraper/results/search.json)  

</details> 

For the full guide, refer to our blog article [How to Web Scrape Yelp.com (2023 update)](https://scrapfly.io/blog/how-to-scrape-yelpcom/)

### Zillow
<p align="left">
  <img width="200" height="100" src="./.github/assets/zillow.svg">
</p>

The [zillow.com scraper](./zillow-scraper/) can scrape the following data:
- Zillow property pages for a specific real estate property data.
- Zillow search pages for real estate property listings data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Property pages](./zillow-scraper/results/property.json)  
  - [Search pages](./zillow-scraper/results/search.json)  

</details> 

For the full guide, refer to our blog article [How to Scrape Zillow Real Estate Property Data in Python](https://scrapfly.io/blog/how-to-scrape-zillow/)

### Zoominfo
<p align="left">
  <img width="300" height="100" src="./.github/assets/zoominfo.svg">
</p>

The [zoominfo.com scraper](./zoominfo-scraper/) can scrape the following data:
- Company pages for company data.
- Directory pages for company page URLs.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Company pages](./zoominfo-scraper/results/companies.json)  
  - [Directory pages](./zoominfo-scraper/results/directory.json)  

</details> 

For the full guide, refer to our blog article [How to Scrape Zoominfo Company Data (2023 Update)](https://scrapfly.io/blog/how-to-scrape-zoominfo/)

### Zoopla
<p align="left">
  <img width="200" height="100" src="./.github/assets/zoopla.svg">
</p>

The [zoopla.co.uk scraper](./zoopla-scraper/) can scrape the following data:
- Zoopla property pages for a specific real estate property data.
- Zoopla search pages for real estate property listings data.

<details class="is-code">
  <summary>View sample data</summary>  

  - [Property pages](./zoopla-scraper/results/properties.json)  
  - [Search pages](./zoopla-scraper/results/search.json)  

</details> 

For the full guide, refer to our blog article [How to Scrape Zoopla Real Estate Property Data in Python](https://scrapfly.io/blog/how-to-scrape-zoopla/)