"""
job_finder.py
Discovers active job listings from LinkedIn, Naukri, Indeed, and others
using the JSearch API (RapidAPI), based on the user's parsed profile.
"""

import requests
import json
import time
import os
from datetime import datetime


def build_search_queries(profile: dict, config: dict) -> list[str]:
    '''
    Generates smart search queries from the user's profile and search config.
    Returns a list of query strings to run through JSearch.
    '''
    target_roles = profile.get("target_roles", [])
    current_title = profile.get("current_title", "")
    job_titles = profile.get("job_titles", [])

    # Pull from config overrides or fall back to profile
    roles_to_search = config.get("search_roles") or (target_roles + [current_title])[:5]
    locations = config.get("search_locations", ["India", "Remote"])

    queries = []
    for role in roles_to_search:
        for location in locations:
            queries.append(f"{role} {location}")

    # Deduplicate
    return list(dict.fromkeys(queries))


def fetch_jobs(query: str, jsearch_api_key: str, num_pages: int = 1,
               date_posted: str = "week") -> list[dict]:
    '''
    Fetches job listings from JSearch API for a given query.
    date_posted options: "today", "3days", "week", "month"
    Returns a list of raw job dicts.
    '''
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": jsearch_api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }

    all_jobs = []

    for page in range(1, num_pages + 1):
        params = {
            "query": query,
            "page": str(page),
            "num_pages": "1",
            "date_posted": date_posted,
            "remote_jobs_only": "false",
            "employment_types": "FULLTIME,PARTTIME,CONTRACTOR"
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            jobs = data.get("data", [])
            all_jobs.extend(jobs)
            print(f"  📦 Page {page}: {len(jobs)} jobs for '{query}'")
            time.sleep(0.5)  # be polite to the API

        except requests.exceptions.RequestException as e:
            print(f"  ⚠️  API error for '{query}' page {page}: {e}")
            break

    return all_jobs


def normalize_job(raw_job: dict) -> dict:
    '''
    Normalizes a raw JSearch job dict into a clean standard format.
    '''
    return {
        "job_id": raw_job.get("job_id", ""),
        "title": raw_job.get("job_title", ""),
        "company": raw_job.get("employer_name", ""),
        "location": f"{raw_job.get('job_city', '')} {raw_job.get('job_country', '')}".strip(),
        "is_remote": raw_job.get("job_is_remote", False),
        "employment_type": raw_job.get("job_employment_type", ""),
        "description": raw_job.get("job_description", "")[:3000],  # trim for AI
        "apply_link": raw_job.get("job_apply_link", ""),
        "apply_is_direct": raw_job.get("job_apply_is_direct", False),
        "source": raw_job.get("job_publisher", ""),
        "posted_at": raw_job.get("job_posted_at_datetime_utc", ""),
        "salary_min": raw_job.get("job_min_salary"),
        "salary_max": raw_job.get("job_max_salary"),
        "salary_currency": raw_job.get("job_salary_currency", ""),
        "required_experience": raw_job.get("job_required_experience", {}).get("required_experience_in_months"),
        "required_skills": raw_job.get("job_required_skills") or [],
        "highlights": raw_job.get("job_highlights", {}),
        "employer_logo": raw_job.get("employer_logo", ""),
        "match_score": None,  # filled by matcher
        "status": "discovered",
        "discovered_at": datetime.now().isoformat()
    }


def deduplicate_jobs(jobs: list[dict]) -> list[dict]:
    '''
    Removes duplicate jobs by job_id and by (title + company) pair.
    '''
    seen_ids = set()
    seen_pairs = set()
    unique = []

    for job in jobs:
        jid = job.get("job_id")
        pair = (job.get("title", "").lower(), job.get("company", "").lower())

        if jid and jid in seen_ids:
            continue
        if pair in seen_pairs:
            continue

        seen_ids.add(jid)
        seen_pairs.add(pair)
        unique.append(job)

    return unique


def discover_jobs(profile: dict, config: dict, jsearch_api_key: str) -> list[dict]:
    '''
    Full job discovery pipeline using the user's profile and search config.
    Returns a deduplicated list of normalized job dicts.
    '''
    queries = build_search_queries(profile, config)
    print(f"\n🔍 Running {len(queries)} search queries...")

    all_raw_jobs = []
    for query in queries:
        print(f"\n  🔎 Searching: {query}")
        raw = fetch_jobs(
            query=query,
            jsearch_api_key=jsearch_api_key,
            num_pages=config.get("pages_per_query", 1),
            date_posted=config.get("date_posted", "week")
        )
        all_raw_jobs.extend(raw)

    print(f"\n📥 Total raw jobs fetched: {len(all_raw_jobs)}")

    normalized = [normalize_job(j) for j in all_raw_jobs]
    unique = deduplicate_jobs(normalized)

    print(f"✅ After deduplication: {len(unique)} unique jobs")
    return unique


def save_jobs(jobs: list[dict], output_path: str) -> None:
    '''
    Saves the jobs list as a JSON file.
    '''
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved {len(jobs)} jobs to: {output_path}")


if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.secrets import JSEARCH_API_KEY
    from config.search import SEARCH_CONFIG
    from modules.resume_parser import load_profile

    profile = load_profile("data/profile.json")
    jobs = discover_jobs(profile, SEARCH_CONFIG, JSEARCH_API_KEY)
    save_jobs(jobs, "data/discovered_jobs.json")
