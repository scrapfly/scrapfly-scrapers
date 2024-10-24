"""
This is an example web scraper for booking.com used in scrapfly blog article:
https://scrapfly.io/blog/how-to-scrape-bookingcom/

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"

For example use instructions see ./run.py
"""
import json
import os
import re
from collections import defaultdict
from typing import Dict, List, Optional, TypedDict
from urllib.parse import urlencode
from uuid import uuid4

from loguru import logger as log
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # Booking.com requires Anti Scraping Protection bypass feature:
    "asp": True,
    "country": "US",
}


class Location(TypedDict):
    b_max_los_data: dict
    b_show_entire_homes_checkbox: bool
    cc1: str
    cjk: bool
    dest_id: str
    dest_type: str
    label: str
    label1: str
    label2: str
    labels: list
    latitude: float
    lc: str
    longitude: float
    nr_homes: int
    nr_hotels: int
    nr_hotels_25: int
    photo_uri: str
    roundtrip: str
    rtl: bool
    value: str


class LocationSuggestions(TypedDict):
    results: List[Location]



async def search_location_suggestions(query: str) -> LocationSuggestions:
    """scrape booking.com location suggestions to find location details for search scraping"""
    result = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url="https://accommodations.booking.com/autocomplete.json",
            method="POST",
            headers={
                "Origin": "https://www.booking.com",
                "Referer": "https://www.booking.com/",
                "Content-Type": "text/plain;charset=UTF-8",
            },
            body=f'{{"query":"{query}","pageview_id":"","aid":800210,"language":"en-us","size":5}}',
        )
    )
    data = json.loads(result.content)
    return data


def retrieve_graphql_body(result: ScrapeApiResponse) -> List[Dict]:
    """parse the graphql search query from the HTML and return the full graphql body"""
    selector = result.selector
    script_data = selector.xpath("//script[@data-capla-store-data='apollo']/text()").get()
    json_script_data = json.loads(script_data)
    keys_list = list(json_script_data["ROOT_QUERY"]["searchQueries"].keys())
    second_key = keys_list[1]
    search_query_string = second_key[len("search("):-1]
    input_json_object = json.loads(search_query_string)
    return {
        "operationName": "FullSearch",
        "variables": {
            "input": input_json_object["input"],
            "carouselLowCodeExp": False
        },
        "extensions": {},
        "query": "query FullSearch($input: SearchQueryInput!, $carouselLowCodeExp: Boolean!) {\n  searchQueries {\n    search(input: $input) {\n      ...FullSearchFragment\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment FullSearchFragment on SearchQueryOutput {\n  banners {\n    ...Banner\n    __typename\n  }\n  breadcrumbs {\n    ... on SearchResultsBreadcrumb {\n      ...SearchResultsBreadcrumb\n      __typename\n    }\n    ... on LandingPageBreadcrumb {\n      ...LandingPageBreadcrumb\n      __typename\n    }\n    __typename\n  }\n  carousels {\n    ...Carousel\n    __typename\n  }\n  destinationLocation {\n    ...DestinationLocation\n    __typename\n  }\n  entireHomesSearchEnabled\n  dateFlexibilityOptions {\n    enabled\n    __typename\n  }\n  flexibleDatesConfig {\n    broadDatesCalendar {\n      checkinMonths\n      los\n      startWeekdays\n      losType\n      __typename\n    }\n    dateFlexUseCase\n    dateRangeCalendar {\n      flexWindow\n      checkin\n      checkout\n      __typename\n    }\n    __typename\n  }\n  filters {\n    ...FilterData\n    __typename\n  }\n  filtersTrackOnView {\n    type\n    experimentHash\n    value\n    __typename\n  }\n  appliedFilterOptions {\n    ...FilterOption\n    __typename\n  }\n  recommendedFilterOptions {\n    ...FilterOption\n    __typename\n  }\n  pagination {\n    nbResultsPerPage\n    nbResultsTotal\n    __typename\n  }\n  tripTypes {\n    ...TripTypesData\n    __typename\n  }\n  results {\n    ...BasicPropertyData\n    ...MatchingUnitConfigurations\n    ...PropertyBlocks\n    ...BookerExperienceData\n    priceDisplayInfoIrene {\n      ...PriceDisplayInfoIrene\n      __typename\n    }\n    licenseDetails {\n      nextToHotelName\n      __typename\n    }\n    isTpiExclusiveProperty\n    propertyCribsAvailabilityLabel\n    mlBookingHomeTags\n    trackOnView {\n      experimentTag\n      __typename\n    }\n    __typename\n  }\n  searchMeta {\n    ...SearchMetadata\n    __typename\n  }\n  sorters {\n    option {\n      ...SorterFields\n      __typename\n    }\n    __typename\n  }\n  zeroResultsSection {\n    ...ZeroResultsSection\n    __typename\n  }\n  rocketmilesSearchUuid\n  previousSearches {\n    ...PreviousSearches\n    __typename\n  }\n  frontierThemes {\n    ...FrontierThemes\n    __typename\n  }\n  merchComponents {\n    ...MerchRegionIrene\n    __typename\n  }\n  wishlistData {\n    numProperties\n    __typename\n  }\n  seoThemes {\n    id\n    caption\n    __typename\n  }\n  __typename\n}\n\nfragment BasicPropertyData on SearchResultProperty {\n  acceptsWalletCredit\n  basicPropertyData {\n    accommodationTypeId\n    id\n    isTestProperty\n    location {\n      address\n      city\n      countryCode\n      __typename\n    }\n    pageName\n    ufi\n    photos {\n      main {\n        highResUrl {\n          relativeUrl\n          __typename\n        }\n        lowResUrl {\n          relativeUrl\n          __typename\n        }\n        highResJpegUrl {\n          relativeUrl\n          __typename\n        }\n        lowResJpegUrl {\n          relativeUrl\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    reviewScore: reviews {\n      score: totalScore\n      reviewCount: reviewsCount\n      totalScoreTextTag {\n        translation\n        __typename\n      }\n      showScore\n      secondaryScore\n      secondaryTextTag {\n        translation\n        __typename\n      }\n      showSecondaryScore\n      __typename\n    }\n    externalReviewScore: externalReviews {\n      score: totalScore\n      reviewCount: reviewsCount\n      showScore\n      totalScoreTextTag {\n        translation\n        __typename\n      }\n      __typename\n    }\n    starRating {\n      value\n      symbol\n      caption {\n        translation\n        __typename\n      }\n      tocLink {\n        translation\n        __typename\n      }\n      showAdditionalInfoIcon\n      __typename\n    }\n    isClosed\n    paymentConfig {\n      installments {\n        minPriceFormatted\n        maxAcceptCount\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  badges {\n    caption {\n      translation\n      __typename\n    }\n    closedFacilities {\n      startDate\n      endDate\n      __typename\n    }\n    __typename\n  }\n  customBadges {\n    showSkiToDoor\n    showBhTravelCreditBadge\n    showOnlineCheckinBadge\n    __typename\n  }\n  description {\n    text\n    __typename\n  }\n  displayName {\n    text\n    translationTag {\n      translation\n      __typename\n    }\n    __typename\n  }\n  geniusInfo {\n    benefitsCommunication {\n      header {\n        title\n        __typename\n      }\n      items {\n        title\n        __typename\n      }\n      __typename\n    }\n    geniusBenefits\n    geniusBenefitsData {\n      hotelCardHasFreeBreakfast\n      hotelCardHasFreeRoomUpgrade\n      sortedBenefits\n      __typename\n    }\n    showGeniusRateBadge\n    __typename\n  }\n  location {\n    displayLocation\n    mainDistance\n    publicTransportDistanceDescription\n    skiLiftDistance\n    beachDistance\n    nearbyBeachNames\n    beachWalkingTime\n    geoDistanceMeters\n    __typename\n  }\n  mealPlanIncluded {\n    mealPlanType\n    text\n    __typename\n  }\n  persuasion {\n    autoextended\n    geniusRateAvailable\n    highlighted\n    preferred\n    preferredPlus\n    showNativeAdLabel\n    nativeAdId\n    nativeAdsCpc\n    nativeAdsTracking\n    sponsoredAdsData {\n      isDsaCompliant\n      legalEntityName\n      sponsoredAdsDesign\n      __typename\n    }\n    __typename\n  }\n  policies {\n    showFreeCancellation\n    showNoPrepayment\n    enableJapaneseUsersSpecialCase\n    __typename\n  }\n  ribbon {\n    ribbonType\n    text\n    __typename\n  }\n  recommendedDate {\n    checkin\n    checkout\n    lengthOfStay\n    __typename\n  }\n  showGeniusLoginMessage\n  hostTraderLabel\n  soldOutInfo {\n    isSoldOut\n    messages {\n      text\n      __typename\n    }\n    alternativeDatesMessages {\n      text\n      __typename\n    }\n    __typename\n  }\n  nbWishlists\n  visibilityBoosterEnabled\n  showAdLabel\n  isNewlyOpened\n  propertySustainability {\n    isSustainable\n    tier {\n      type\n      __typename\n    }\n    facilities {\n      id\n      __typename\n    }\n    certifications {\n      name\n      __typename\n    }\n    chainProgrammes {\n      chainName\n      programmeName\n      __typename\n    }\n    levelId\n    __typename\n  }\n  seoThemes {\n    caption\n    __typename\n  }\n  relocationMode {\n    distanceToCityCenterKm\n    distanceToCityCenterMiles\n    distanceToOriginalHotelKm\n    distanceToOriginalHotelMiles\n    phoneNumber\n    __typename\n  }\n  bundleRatesAvailable\n  __typename\n}\n\nfragment Banner on Banner {\n  name\n  type\n  isDismissible\n  showAfterDismissedDuration\n  position\n  requestAlternativeDates\n  merchId\n  title {\n    text\n    __typename\n  }\n  imageUrl\n  paragraphs {\n    text\n    __typename\n  }\n  metadata {\n    key\n    value\n    __typename\n  }\n  pendingReviewInfo {\n    propertyPhoto {\n      lowResUrl {\n        relativeUrl\n        __typename\n      }\n      lowResJpegUrl {\n        relativeUrl\n        __typename\n      }\n      __typename\n    }\n    propertyName\n    urlAccessCode\n    __typename\n  }\n  nbDeals\n  primaryAction {\n    text {\n      text\n      __typename\n    }\n    action {\n      name\n      context {\n        key\n        value\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  secondaryAction {\n    text {\n      text\n      __typename\n    }\n    action {\n      name\n      context {\n        key\n        value\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  iconName\n  flexibleFilterOptions {\n    optionId\n    filterName\n    __typename\n  }\n  trackOnView {\n    type\n    experimentHash\n    value\n    __typename\n  }\n  dateFlexQueryOptions {\n    text {\n      text\n      __typename\n    }\n    action {\n      name\n      context {\n        key\n        value\n        __typename\n      }\n      __typename\n    }\n    isApplied\n    __typename\n  }\n  __typename\n}\n\nfragment Carousel on Carousel {\n  aggregatedCountsByFilterId\n  carouselId\n  position\n  contentType\n  hotelId\n  name\n  soldoutProperties\n  priority\n  themeId\n  frontierThemeIds\n  title {\n    text\n    __typename\n  }\n  slides {\n    captionText {\n      text\n      __typename\n    }\n    name\n    photoUrl\n    subtitle {\n      text\n      __typename\n    }\n    type\n    title {\n      text\n      __typename\n    }\n    action {\n      context {\n        key\n        value\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment DestinationLocation on DestinationLocation {\n  name {\n    text\n    __typename\n  }\n  inName {\n    text\n    __typename\n  }\n  countryCode\n  ufi\n  __typename\n}\n\nfragment FilterData on Filter {\n  trackOnView {\n    type\n    experimentHash\n    value\n    __typename\n  }\n  trackOnClick {\n    type\n    experimentHash\n    value\n    __typename\n  }\n  name\n  field\n  category\n  filterStyle\n  title {\n    text\n    translationTag {\n      translation\n      __typename\n    }\n    __typename\n  }\n  subtitle\n  options {\n    parentId\n    genericId\n    trackOnView {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnClick {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnSelect {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnDeSelect {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnViewPopular {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnClickPopular {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnSelectPopular {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnDeSelectPopular {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    ...FilterOption\n    __typename\n  }\n  filterLayout {\n    isCollapsable\n    collapsedCount\n    __typename\n  }\n  stepperOptions {\n    min\n    max\n    default\n    selected\n    title {\n      text\n      translationTag {\n        translation\n        __typename\n      }\n      __typename\n    }\n    field\n    labels {\n      text\n      translationTag {\n        translation\n        __typename\n      }\n      __typename\n    }\n    trackOnView {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnClick {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnSelect {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnDeSelect {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnClickDecrease {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnClickIncrease {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnDecrease {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnIncrease {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    __typename\n  }\n  sliderOptions {\n    min\n    max\n    minSelected\n    maxSelected\n    minPriceStep\n    minSelectedFormatted\n    currency\n    histogram\n    selectedRange {\n      translation\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment FilterOption on Option {\n  optionId: id\n  count\n  selected\n  urlId\n  source\n  additionalLabel {\n    text\n    translationTag {\n      translation\n      __typename\n    }\n    __typename\n  }\n  value {\n    text\n    translationTag {\n      translation\n      __typename\n    }\n    __typename\n  }\n  starRating {\n    value\n    symbol\n    caption {\n      translation\n      __typename\n    }\n    showAdditionalInfoIcon\n    __typename\n  }\n  __typename\n}\n\nfragment LandingPageBreadcrumb on LandingPageBreadcrumb {\n  destType\n  name\n  urlParts\n  __typename\n}\n\nfragment MatchingUnitConfigurations on SearchResultProperty {\n  matchingUnitConfigurations {\n    commonConfiguration {\n      name\n      unitId\n      bedConfigurations {\n        beds {\n          count\n          type\n          __typename\n        }\n        nbAllBeds\n        __typename\n      }\n      nbAllBeds\n      nbBathrooms\n      nbBedrooms\n      nbKitchens\n      nbLivingrooms\n      nbUnits\n      unitTypeNames {\n        translation\n        __typename\n      }\n      localizedArea {\n        localizedArea\n        unit\n        __typename\n      }\n      __typename\n    }\n    unitConfigurations {\n      name\n      unitId\n      bedConfigurations {\n        beds {\n          count\n          type\n          __typename\n        }\n        nbAllBeds\n        __typename\n      }\n      apartmentRooms {\n        config {\n          roomId: id\n          roomType\n          bedTypeId\n          bedCount: count\n          __typename\n        }\n        roomName: tag {\n          tag\n          translation\n          __typename\n        }\n        __typename\n      }\n      nbAllBeds\n      nbBathrooms\n      nbBedrooms\n      nbKitchens\n      nbLivingrooms\n      nbUnits\n      unitTypeNames {\n        translation\n        __typename\n      }\n      localizedArea {\n        localizedArea\n        unit\n        __typename\n      }\n      unitTypeId\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment PropertyBlocks on SearchResultProperty {\n  blocks {\n    blockId {\n      roomId\n      occupancy\n      policyGroupId\n      packageId\n      mealPlanId\n      bundleId\n      __typename\n    }\n    finalPrice {\n      amount\n      currency\n      __typename\n    }\n    originalPrice {\n      amount\n      currency\n      __typename\n    }\n    onlyXLeftMessage {\n      tag\n      variables {\n        key\n        value\n        __typename\n      }\n      translation\n      __typename\n    }\n    freeCancellationUntil\n    hasCrib\n    blockMatchTags {\n      childStaysForFree\n      __typename\n    }\n    thirdPartyInventoryContext {\n      isTpiBlock\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment PriceDisplayInfoIrene on PriceDisplayInfoIrene {\n  badges {\n    name {\n      translation\n      __typename\n    }\n    tooltip {\n      translation\n      __typename\n    }\n    style\n    identifier\n    __typename\n  }\n  chargesInfo {\n    translation\n    __typename\n  }\n  displayPrice {\n    copy {\n      translation\n      __typename\n    }\n    amountPerStay {\n      amount\n      amountRounded\n      amountUnformatted\n      currency\n      __typename\n    }\n    __typename\n  }\n  priceBeforeDiscount {\n    copy {\n      translation\n      __typename\n    }\n    amountPerStay {\n      amount\n      amountRounded\n      amountUnformatted\n      currency\n      __typename\n    }\n    __typename\n  }\n  rewards {\n    rewardsList {\n      termsAndConditions\n      amountPerStay {\n        amount\n        amountRounded\n        amountUnformatted\n        currency\n        __typename\n      }\n      breakdown {\n        productType\n        amountPerStay {\n          amount\n          amountRounded\n          amountUnformatted\n          currency\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    rewardsAggregated {\n      amountPerStay {\n        amount\n        amountRounded\n        amountUnformatted\n        currency\n        __typename\n      }\n      copy {\n        translation\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  useRoundedAmount\n  discounts {\n    amount {\n      amount\n      amountRounded\n      amountUnformatted\n      currency\n      __typename\n    }\n    name {\n      translation\n      __typename\n    }\n    description {\n      translation\n      __typename\n    }\n    itemType\n    productId\n    __typename\n  }\n  excludedCharges {\n    excludeChargesAggregated {\n      copy {\n        translation\n        __typename\n      }\n      amountPerStay {\n        amount\n        amountRounded\n        amountUnformatted\n        currency\n        __typename\n      }\n      __typename\n    }\n    excludeChargesList {\n      chargeMode\n      chargeInclusion\n      chargeType\n      amountPerStay {\n        amount\n        amountRounded\n        amountUnformatted\n        currency\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  taxExceptions {\n    shortDescription {\n      translation\n      __typename\n    }\n    longDescription {\n      translation\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment BookerExperienceData on SearchResultProperty {\n  bookerExperienceContentUIComponentProps {\n    ... on BookerExperienceContentLoyaltyBadgeListProps {\n      badges {\n        variant\n        key\n        title\n        popover\n        logoSrc\n        logoAlt\n        __typename\n      }\n      __typename\n    }\n    ... on BookerExperienceContentFinancialBadgeProps {\n      paymentMethod\n      backgroundColor\n      hideAccepted\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment SearchMetadata on SearchMeta {\n  availabilityInfo {\n    hasLowAvailability\n    unavailabilityPercent\n    totalAvailableNotAutoextended\n    __typename\n  }\n  boundingBoxes {\n    swLat\n    swLon\n    neLat\n    neLon\n    type\n    __typename\n  }\n  childrenAges\n  dates {\n    checkin\n    checkout\n    lengthOfStayInDays\n    __typename\n  }\n  destId\n  destType\n  guessedLocation {\n    destId\n    destType\n    destName\n    __typename\n  }\n  maxLengthOfStayInDays\n  nbRooms\n  nbAdults\n  nbChildren\n  userHasSelectedFilters\n  customerValueStatus\n  isAffiliateBookingOwned\n  affiliatePartnerChannelId\n  affiliateVerticalType\n  geniusLevel\n  __typename\n}\n\nfragment SearchResultsBreadcrumb on SearchResultsBreadcrumb {\n  destId\n  destType\n  name\n  __typename\n}\n\nfragment SorterFields on SorterOption {\n  type: name\n  captionTranslationTag {\n    translation\n    __typename\n  }\n  tooltipTranslationTag {\n    translation\n    __typename\n  }\n  isSelected: selected\n  __typename\n}\n\nfragment TripTypesData on TripTypes {\n  beach {\n    isBeachUfi\n    isEnabledBeachUfi\n    __typename\n  }\n  ski {\n    isSkiExperience\n    isSkiScaleUfi\n    __typename\n  }\n  __typename\n}\n\nfragment ZeroResultsSection on ZeroResultsSection {\n  title {\n    text\n    __typename\n  }\n  primaryAction {\n    text {\n      text\n      __typename\n    }\n    action {\n      name\n      __typename\n    }\n    __typename\n  }\n  paragraphs {\n    text\n    __typename\n  }\n  type\n  __typename\n}\n\nfragment PreviousSearches on PreviousSearch {\n  childrenAges\n  __typename\n}\n\nfragment FrontierThemes on FrontierTheme {\n  id\n  name\n  selected\n  __typename\n}\n\nfragment MerchRegionIrene on MerchComponentsResultIrene {\n  regions {\n    id\n    components {\n      ... on PromotionalBannerIrene {\n        promotionalBannerCampaignId\n        contentArea {\n          title {\n            ... on PromotionalBannerSimpleTitleIrene {\n              value\n              __typename\n            }\n            __typename\n          }\n          subTitle {\n            ... on PromotionalBannerSimpleSubTitleIrene {\n              value\n              __typename\n            }\n            __typename\n          }\n          caption {\n            ... on PromotionalBannerSimpleCaptionIrene {\n              value\n              __typename\n            }\n            ... on PromotionalBannerCountdownCaptionIrene {\n              campaignEnd\n              __typename\n            }\n            __typename\n          }\n          buttons {\n            variant\n            cta {\n              ariaLabel\n              text\n              targetLanding {\n                ... on OpenContextSheet {\n                  sheet {\n                    ... on WebContextSheet {\n                      title\n                      body {\n                        items {\n                          ... on ContextSheetTextItem {\n                            text\n                            __typename\n                          }\n                          ... on ContextSheetList {\n                            items {\n                              text\n                              __typename\n                            }\n                            __typename\n                          }\n                          __typename\n                        }\n                        __typename\n                      }\n                      buttons {\n                        variant\n                        cta {\n                          text\n                          ariaLabel\n                          targetLanding {\n                            ... on DirectLinkLanding {\n                              urlPath\n                              queryParams {\n                                name\n                                value\n                                __typename\n                              }\n                              __typename\n                            }\n                            ... on LoginLanding {\n                              stub\n                              __typename\n                            }\n                            ... on DeeplinkLanding {\n                              urlPath\n                              queryParams {\n                                name\n                                value\n                                __typename\n                              }\n                              __typename\n                            }\n                            ... on ResolvedLinkLanding {\n                              url\n                              __typename\n                            }\n                            __typename\n                          }\n                          __typename\n                        }\n                        __typename\n                      }\n                      __typename\n                    }\n                    __typename\n                  }\n                  __typename\n                }\n                ... on SearchResultsLandingIrene {\n                  destType\n                  destId\n                  checkin\n                  checkout\n                  nrAdults\n                  nrChildren\n                  childrenAges\n                  nrRooms\n                  filters {\n                    name\n                    value\n                    __typename\n                  }\n                  __typename\n                }\n                ... on DirectLinkLandingIrene {\n                  urlPath\n                  queryParams {\n                    name\n                    value\n                    __typename\n                  }\n                  __typename\n                }\n                ... on LoginLandingIrene {\n                  stub\n                  __typename\n                }\n                ... on DeeplinkLandingIrene {\n                  urlPath\n                  queryParams {\n                    name\n                    value\n                    __typename\n                  }\n                  __typename\n                }\n                ... on SorterLandingIrene {\n                  sorterName\n                  __typename\n                }\n                __typename\n              }\n              __typename\n            }\n            __typename\n          }\n          __typename\n        }\n        designVariant {\n          ... on DesktopPromotionalFullBleedImageIrene {\n            image: image {\n              id\n              url(width: 814, height: 138)\n              alt\n              overlayGradient\n              primaryColorHex\n              __typename\n            }\n            colorScheme\n            signature\n            __typename\n          }\n          ... on DesktopPromotionalImageLeftIrene {\n            imageOpt: image {\n              id\n              url(width: 248, height: 248)\n              alt\n              overlayGradient\n              primaryColorHex\n              __typename\n            }\n            colorScheme\n            signature\n            __typename\n          }\n          ... on DesktopPromotionalImageRightIrene {\n            imageOpt: image {\n              id\n              url(width: 248, height: 248)\n              alt\n              overlayGradient\n              primaryColorHex\n              __typename\n            }\n            colorScheme\n            signature\n            __typename\n          }\n          ... on MdotPromotionalFullBleedImageIrene {\n            image: image {\n              id\n              url(width: 358, height: 136)\n              alt\n              overlayGradient\n              primaryColorHex\n              __typename\n            }\n            colorScheme\n            signature\n            __typename\n          }\n          ... on MdotPromotionalImageLeftIrene {\n            imageOpt: image {\n              id\n              url(width: 128, height: 128)\n              alt\n              overlayGradient\n              primaryColorHex\n              __typename\n            }\n            colorScheme\n            signature\n            __typename\n          }\n          ... on MdotPromotionalImageRightIrene {\n            imageOpt: image {\n              id\n              url(width: 128, height: 128)\n              alt\n              overlayGradient\n              primaryColorHex\n              __typename\n            }\n            colorScheme\n            signature\n            __typename\n          }\n          ... on MdotPromotionalImageTopIrene {\n            imageOpt: image {\n              id\n              url(width: 128, height: 128)\n              alt\n              overlayGradient\n              primaryColorHex\n              __typename\n            }\n            colorScheme\n            signature\n            __typename\n          }\n          ... on MdotPromotionalIllustrationLeftIrene {\n            imageOpt: image {\n              id\n              url(width: 200, height: 200)\n              alt\n              overlayGradient\n              primaryColorHex\n              __typename\n            }\n            colorScheme\n            signature\n            __typename\n          }\n          ... on MdotPromotionalIllustrationRightIrene {\n            imageOpt: image {\n              id\n              url(width: 200, height: 200)\n              alt\n              overlayGradient\n              primaryColorHex\n              __typename\n            }\n            colorScheme\n            signature\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n      ... on MerchCarouselIrene @include(if: $carouselLowCodeExp) {\n        carouselCampaignId\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n"
    }


def generate_graphql_request(url_params: str, body: Dict, offset: int):
    """create a scrape config for the search graphql request"""
    body["variables"]["input"]["pagination"]["offset"] = offset
    return ScrapeConfig(
        "https://www.booking.com/dml/graphql?" + url_params,
            headers={
                "accept":"*/*",
                "cache-control":"no-cache",
                "content-type": "application/json",
                "origin":"https://www.booking.com",
                "pragma":"no-cache",
                "priority":"u=1, i",
                "referer":"https://www.booking.com/searchresults.en-gb.html?" + url_params,
            },
        data=body,
        method="POST",
        asp=True
    )


def parse_graphql_response(response: ScrapeApiResponse) -> List[Dict]:
    """parse the search results from the graphql response"""
    data = json.loads(response.content)
    parsed_data = data["data"]["searchQueries"]["search"]["results"]
    return parsed_data


async def scrape_search(
    query,
    checkin: str = "",  # e.g. 2023-05-30
    checkout: str = "",  # e.g. 2023-06-26
    number_of_rooms=1,
    max_pages: Optional[int] = None,
) -> List[Dict]:
    """Scrape booking.com search"""
    log.info(f"scraping search for {query} {checkin}-{checkout}")
    # first we must find destination details from provided query
    # for that scrape suggestions from booking.com autocomplete and take the first one
    location_suggestions = await search_location_suggestions(query)
    destination = location_suggestions["results"][0]
    url_params = urlencode(
        {
            "ss": destination["value"],
            "ssne": destination["value"],
            "ssne_untouched": destination["value"],
            "checkin": checkin,
            "checkout": checkout,
            "no_rooms": number_of_rooms,
            "dest_id": destination["dest_id"],
            "dest_type": destination["dest_type"],
            "efdco": 1,
            "group_adults": 1,
            "group_children": 0,
            "lang": "en-gb",
            "sb": 1,
            "sb_travel_purpose": "leisure",
            "src": "index",
            "src_elem": "sb",
        }
    )
    search_url = "https://www.booking.com/searchresults.en-gb.html?" + url_params
    # first scrape the first page and find total amount of pages
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(search_url, **BASE_CONFIG))
    _total_results = int(first_page.selector.css("h1").re(r"([\d,]+) properties found")[0].replace(",", ""))
    _max_scrape_results = max_pages * 25
    if _max_scrape_results and _max_scrape_results < _total_results:
        _total_results = _max_scrape_results

    data = []
    body = retrieve_graphql_body(first_page)
    to_scrape = [
        generate_graphql_request(url_params, body, offset)
        for offset in range(0, _total_results, 25)
    ]
    log.info(f"scraping search results from the graphql api: {len(to_scrape)} pages to request")
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        try:
            data.extend(parse_graphql_response(response))
        except Exception as e:
            log.error("Failed to parse search results: {}", e)
    log.success(f"scraped {len(data)} results from search pages")
    return data
       

class PriceData(TypedDict):
    checkin: str
    min_length_of_stay: int
    avg_price_pretty: str
    available: int
    avg_price_raw: float
    length_of_stay: int
    price_pretty: str
    price: float


class Hotel(TypedDict):
    url: str
    id: str
    description: str
    address: str
    images: List[str]
    lat: str
    lng: str
    features: Dict[str, List[str]]
    price: List[PriceData]


def parse_hotel(result: ScrapeApiResponse) -> Hotel:
    log.debug("parsing hotel page: {}", result.context["url"])
    sel = result.selector

    features = defaultdict(list)
    for box in sel.xpath('//div[@data-testid="property-section--content"]/div[2]/div'):
        type_ = box.xpath('.//span[contains(@data-testid, "facility-group-icon")]/../text()').get()
        feats = [f.strip() for f in box.css("li ::text").getall() if f.strip()]
        features[type_] = feats

    css = lambda selector, sep="": sep.join(sel.css(selector).getall()).strip()
    lat, lng = sel.css(".show_map_hp_link::attr(data-atlas-latlng)").get("0,0").split(",")
    id = re.findall(r"b_hotel_id:\s*'(.+?)'", result.content)
    data = {
        "url": result.context["url"],
        "id": id[0] if id else None,
        "title": sel.css("h2::text").get(),
        "description": css("div#property_description_content ::text", "\n"),
        "address": css(".hp_address_subtitle::text"),
        "images": sel.css("a.bh-photo-grid-item>img::attr(src)").getall(),
        "lat": lat,
        "lng": lng,
        "features": dict(features),
    }
    return data


async def scrape_hotel(url: str, checkin: str, price_n_days=61) -> Hotel:
    """
    Scrape Booking.com hotel data and pricing information.
    """
    # first scrape hotel info details
    # note: we are using scrapfly session here as both info and pricing requests
    #       have to be from the same IP address/session
    if BASE_CONFIG.get("cache"):
        raise Exception("scrapfly cache cannot be used with sessions when scraping hotel data")
    log.info(f"scraping hotel {url} {checkin} with {price_n_days} days of pricing data")
    session = str(uuid4()).replace("-", "")
    result = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url,
            session=session,
            **BASE_CONFIG,
        )
    )
    hotel = parse_hotel(result)

    # To scrape price we'll be calling Booking.com's graphql service
    # in particular we'll be calling AvailabilityCalendar query
    # first, extract hotel variables:
    _hotel_country = re.findall(r'hotelCountry:\s*"(.+?)"', result.content)[0]
    _hotel_name = re.findall(r'hotelName:\s*"(.+?)"', result.content)[0]
    _csrf_token = re.findall(r"b_csrf_token:\s*'(.+?)'", result.content)[0]
    # then create graphql query
    gql_body = json.dumps(
        {
            "operationName": "AvailabilityCalendar",
            # hotel varialbes go here
            # you can adjust number of adults, room number etc.
            "variables": {
                "input": {
                    "travelPurpose": 2,
                    "pagenameDetails": {
                        "countryCode": _hotel_country,
                        "pagename": _hotel_name,
                    },
                    "searchConfig": {
                        "searchConfigDate": {
                            "startDate": checkin,
                            "amountOfDays": price_n_days,
                        },
                        "nbAdults": 2,
                        "nbRooms": 1,
                    },
                }
            },
            "extensions": {},
            # this is the query itself, don't alter it
            "query": "query AvailabilityCalendar($input: AvailabilityCalendarQueryInput!) {\n  availabilityCalendar(input: $input) {\n    ... on AvailabilityCalendarQueryResult {\n      hotelId\n      days {\n        available\n        avgPriceFormatted\n        checkin\n        minLengthOfStay\n        __typename\n      }\n      __typename\n    }\n    ... on AvailabilityCalendarQueryError {\n      message\n      __typename\n    }\n    __typename\n  }\n}\n",
        },
        # note: this removes unnecessary whitespace in JSON output
        separators=(",", ":"),
    )
    # scrape booking graphql
    result_price = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            "https://www.booking.com/dml/graphql?lang=en-gb",
            method="POST",
            body=gql_body,
            session=session,
            # note that we need to set headers to avoid being blocked
            headers={
                "content-type": "application/json",
                "x-booking-csrf-token": _csrf_token,
                "referer": result.context["url"],
                "origin": "https://www.booking.com",
            },
            **BASE_CONFIG,
        )
    )
    price_data = json.loads(result_price.content)
    hotel["price"] = price_data["data"]["availabilityCalendar"]["days"]
    return hotel
