# https://gist.github.com/scrapfly-dev/680d42cb28a83668e7cfbac5420018b2
import json
import os
import asyncio
import jmespath

from typing import List, Dict
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

BASE_CONFIG = {
    "asp": True,
    "render_js": True,
    "proxy_pool": "public_residential_pool"
}

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

def _reduce_organization_dataset(data: Dict) -> Dict:
    """
    Reduce organization dataset to a smaller subset of the most important fields

    Note that Crunchbase dataset is huge and contains a lot of different fields.
    This example is using jmespath to select most commonly requested fields.
    """
    return jmespath.search(
        """{
        id: properties.identifier.permalink,
        name: properties.title,
        logo: properties.identifier.image_id,
        description: cards.overview_description.description,
        
        linkedin: cards.social_fields.linkedin.value,
        facebook: cards.social_fields.facebook.value,
        twitter: cards.social_fields.twitter.value,
        
        email: cards.contact_fields.contact_email,
        phone: cards.contact_fields.phone_number,

        website: cards.company_about_fields2.website.value,
        ipo_status: cards.company_about_fields2.ipo_status,
        rank_org_company: cards.company_about_fields2.rank_org_company,

        semrush_global_rank: cards.semrush_summary.semrush_global_rank,
        semrush_visits_latest_month: cards.semrush_summary.semrush_visits_latest_month,
        semrush_id: cards.semrush_summary.identifier.permalink,
        
        categories: cards.overview_fields_extended.categories[].value,
        legal_name: cards.overview_fields_extended.legal_name,
        operating_status: cards.overview_fields_extended.operating_status,
        last_funding_type: cards.overview_fields_extended.last_funding_type,
        founded_on: cards.overview_fields_extended.founded_on.value,
        location_groups: cards.overview_fields_extended.location_group_identifiers[].value,
        
        trademarks: cards.ipqwery_summary.ipqwery_num_trademark_registered,
        trademark_popular_class: cards.ipqwery_summary.ipqwery_popular_trademark_class,
        patents: cards.ipqwery_summary.ipqwery_num_patent_granted,
        patent_popular_category: cards.ipqwery_summary.ipqwery_popular_patent_category,

        investments: cards.company_overview_highlights.num_investments,
        investors: cards.company_overview_highlights.num_investors,
        acquisitions: cards.company_overview_highlights.num_acquisitions,
        contacts: cards.company_overview_highlights.num_contacts,
        funding_total_usd: cards.company_overview_highlights.funding_total.value_usd,
        stock_symbol: cards.company_overview_highlights.listed_stock_symbol,
        exits: cards.company_overview_highlights.num_exits,
        similar_orgs: cards.company_overview_highlights.num_org_similarities,
        current_positions: cards.company_overview_highlights.num_current_positions,
        
        investors_lead: cards.company_financials_highlights.num_lead_investors,
        investments_lead: cards.company_financials_highlights.num_lead_investments,
        funding_rounds: cards.company_financials_highlights.num_funding_rounds,

        event_appearances: cards.event_appearances_headline.num_event_appearances,
        advisors: cards.advisors_headline.num_current_advisor_positions,
        buildwith_tech_used: cards.builtwith_summary.builtwith_num_technologies_used,
        
        similar: cards.org_similarity_list[].{
            score: score,
            reasons: reasons,
            id: source.permalink
        },
        timeline: cards.overview_timeline.entities[].{
            title: properties.activity_properties.title,
            author: properties.activity_properties.author,
            publisher: properties.activity_properties.publisher,
            url: properties.activity_properties.url.value,
            thumb: properties.activity_properties.thumbnail_url,
            date: properties.activity_date,
            type: properties.entity_def_id
        },
        events: cards.event_appearances_list[].{
            type: appearance_type,
            event_start_date: event_starts_on,
            name: event_identifier.value
        },
        investments: cards.investments_list[].{
            raised_usd: funding_round_money_raised.value_usd,
            name: funding_round_identifier.value,
            organization: organization_identifier.value,
            announced_on: announced_on,
            is_lead_investor: is_lead_investor
        },
        funding_rounds: cards.funding_rounds_list[].{
            announced_on: announced_on,
            raised_usd: money_raised.value_usd,
            investors: num_investors,
            lead_investors: lead_investor_identifiers[].value
        },
        investors: cards.investors_list[].{
            is_lead_investor: is_lead_investor,
            name: investor_identifier.value
        }
    }""",
        data,
    )


def _reduce_employee_dataset(data: Dict) -> List[Dict]:
    """Reduce employee dataset to a smaller subset of the most important fields"""
    parsed = []
    for person in data["entities"]:
        parsed.append(
            jmespath.search(
                """{
                name: properties.name,    
                linkedin: properties.linkedin,
                job_levels: properties.job_levels,
                job_departments: properties.job_departments
            }""",
                person,
            )
        )
    return parsed

def parse_company(result: ScrapeApiResponse) -> Dict:
    """parse company page for company and employee data"""
    # the app cache data can be in one of two places:
    app_state_data = result.selector.css("script#ng-state::text").get()
    if not app_state_data:
        app_state_data = _unescape_angular(result.selector.css("script#client-app-state::text").get() or "")
    app_state_data = json.loads(app_state_data)
    # there are multiple caches:
    cache_keys = list(app_state_data["HttpState"])
    # Organization data can be found in this cache:
    data_cache_key = next(key for key in cache_keys if "entities/organizations/" in key)
    # Some employee/contact data can be found in this key:
    people_cache_key = next(key for key in cache_keys if "/data/searches/contacts" in key)

    organization = app_state_data["HttpState"][data_cache_key]["data"]
    employees = app_state_data["HttpState"][people_cache_key]["data"]
    return {
        "organization": _reduce_organization_dataset(organization),
        "employees": _reduce_employee_dataset(employees),
    }


async def scrape_company(url: str) -> Dict:
    """scrape crunchbase company page for organization and employee data"""
    # note: we use /people tab because it contains the most data:
    print(f"scraping company: {url}")
    result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    return parse_company(result)


async def main():
    url = "https://www.crunchbase.com/organization/tesla-motors/people"
    company_data = await scrape_company(url)

    # save the results to a json file
    with open("company_data.json", "w", encoding="utf-8") as f:
        json.dump(company_data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())