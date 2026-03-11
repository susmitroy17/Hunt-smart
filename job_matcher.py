"""
job_matcher.py
Uses Groq AI to score each discovered job against the user's profile.
Filters out low-match jobs so the bot only applies to relevant ones.
"""

import json
import time
import os
from groq import Groq


def score_job(job: dict, profile: dict, groq_api_key: str) -> dict:
    '''
    Asks Groq to score a job against the user's profile.
    Returns the job dict with match_score (0-100) and match_reason added.
    '''
    client = Groq(api_key=groq_api_key)

    profile_summary = {
        "name": profile.get("name"),
        "current_title": profile.get("current_title"),
        "years_of_experience": profile.get("years_of_experience"),
        "skills": profile.get("skills"),
        "ats_keywords": profile.get("ats_keywords", [])[:20],
        "target_roles": profile.get("target_roles", [])
    }

    prompt = f"""You are an expert HR recruiter scoring job-candidate fit.

CANDIDATE PROFILE:
{json.dumps(profile_summary, indent=2)}

JOB POSTING:
Title: {job.get('title')}
Company: {job.get('company')}
Location: {job.get('location')}
Description: {job.get('description', '')[:1500]}
Required Skills: {job.get('required_skills', [])}

Score this job's fit for the candidate from 0 to 100.
Return ONLY a JSON object with no markdown:
{{
  "match_score": <integer 0-100>,
  "match_reason": "<one sentence why>",
  "missing_skills": ["skill1", "skill2"],
  "matching_skills": ["skill1", "skill2"],
  "recommendation": "apply" | "skip" | "maybe"
}}

Scoring guide:
- 80-100: Strong match, apply immediately
- 60-79: Good match, worth applying  
- 40-59: Partial match, apply with tailored cover letter
- Below 40: Poor match, skip
"""

    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=400
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    result = json.loads(raw)
    job["match_score"] = result.get("match_score", 0)
    job["match_reason"] = result.get("match_reason", "")
    job["missing_skills"] = result.get("missing_skills", [])
    job["matching_skills"] = result.get("matching_skills", [])
    job["recommendation"] = result.get("recommendation", "skip")

    return job


def batch_score_jobs(jobs: list[dict], profile: dict, groq_api_key: str,
                     min_score: int = 50, delay: float = 0.8) -> tuple[list, list]:
    '''
    Scores all jobs and splits them into apply_list and skip_list.
    Returns (apply_list, skip_list).
    delay: seconds between API calls to avoid rate limiting.
    '''
    apply_list = []
    skip_list = []
    total = len(jobs)

    print(f"\n🤖 Scoring {total} jobs against your profile...")
    print(f"   Min score to apply: {min_score}/100\n")

    for i, job in enumerate(jobs, 1):
        print(f"  [{i}/{total}] {job.get('title')} @ {job.get('company')}...", end=" ")

        try:
            scored = score_job(job, profile, groq_api_key)
            score = scored.get("match_score", 0)
            rec = scored.get("recommendation", "skip")
            print(f"Score: {score}/100 → {rec.upper()}")

            if score >= min_score or rec == "apply":
                apply_list.append(scored)
            else:
                skip_list.append(scored)

            time.sleep(delay)

        except Exception as e:
            print(f"ERROR: {e}")
            job["match_score"] = 0
            job["recommendation"] = "skip"
            skip_list.append(job)

    # Sort apply list by score descending
    apply_list.sort(key=lambda j: j.get("match_score", 0), reverse=True)

    print(f"\n📊 Scoring complete!")
    print(f"   ✅ Apply list : {len(apply_list)} jobs")
    print(f"   ❌ Skip list  : {len(skip_list)} jobs")

    return apply_list, skip_list


def print_apply_list(apply_list: list[dict]) -> None:
    '''
    Pretty-prints the apply list with scores and reasons.
    '''
    print("\n" + "=" * 70)
    print("🎯 JOBS TO APPLY FOR (sorted by match score)")
    print("=" * 70)
    for i, job in enumerate(apply_list, 1):
        print(f"\n{i}. [{job.get('match_score')}/100] {job.get('title')} @ {job.get('company')}")
        print(f"   📍 {job.get('location')} | {job.get('source')}")
        print(f"   💡 {job.get('match_reason')}")
        print(f"   🔗 {job.get('apply_link', 'N/A')[:80]}")


if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.secrets import GROQ_API_KEY
    from config.search import SEARCH_CONFIG
    from modules.resume_parser import load_profile

    profile = load_profile("data/profile.json")

    with open("data/discovered_jobs.json") as f:
        jobs = json.load(f)

    min_score = SEARCH_CONFIG.get("min_match_score", 55)
    apply_list, skip_list = batch_score_jobs(jobs, profile, GROQ_API_KEY, min_score)

    # Save both lists
    with open("data/apply_list.json", "w") as f:
        json.dump(apply_list, f, indent=2)

    with open("data/skip_list.json", "w") as f:
        json.dump(skip_list, f, indent=2)

    print_apply_list(apply_list)
    print(f"\n💾 Saved to data/apply_list.json and data/skip_list.json")
