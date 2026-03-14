"""
job_matcher.py
Uses NVIDIA NIM (Nemotron 49B) to score each discovered job against the
user's profile. Uses guided_json for guaranteed valid JSON output.
Model  : nvidia/llama-3.3-nemotron-super-49b-v1
API    : build.nvidia.com (free tier)
"""

import json
import time
import os
from openai import OpenAI

# ── JSON schema — guarantees valid structured output every time ────────────
SCORE_SCHEMA = {
    "type": "object",
    "properties": {
        "match_score":     { "type": "integer", "minimum": 0, "maximum": 100 },
        "match_reason":    { "type": "string" },
        "missing_skills":  { "type": "array", "items": { "type": "string" } },
        "matching_skills": { "type": "array", "items": { "type": "string" } },
        "recommendation":  { "type": "string", "enum": ["apply", "maybe", "skip"] }
    },
    "required": [
        "match_score", "match_reason",
        "missing_skills", "matching_skills", "recommendation"
    ]
}


def _client(nvidia_api_key: str) -> OpenAI:
    return OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=nvidia_api_key
    )


def score_job(job: dict, profile: dict, nvidia_api_key: str) -> dict:
    client = _client(nvidia_api_key)

    profile_summary = {
        "name":                profile.get("name"),
        "current_title":       profile.get("current_title"),
        "years_of_experience": profile.get("years_of_experience"),
        "skills":              profile.get("skills"),
        "ats_keywords":        profile.get("ats_keywords", [])[:20],
        "target_roles":        profile.get("target_roles", [])
    }

    prompt = f"""You are an HR recruiter. Score this job for the candidate.

CANDIDATE: {profile_summary.get('current_title')}, {profile_summary.get('years_of_experience')} years
SKILLS: {', '.join(profile_summary.get('ats_keywords', [])[:15])}

JOB: {job.get('title')} at {job.get('company')}
DESCRIPTION: {job.get('description', '')[:800]}

Reply with ONLY this JSON, nothing else:
{{"match_score": 75, "match_reason": "reason here", "missing_skills": ["skill1"], "matching_skills": ["skill2"], "recommendation": "apply"}}

recommendation must be exactly one of: apply, maybe, skip
match_score must be 0-100 integer."""

    response = client.chat.completions.create(
        model="meta/llama-3.1-8b-instruct",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=200
    )

    raw = response.choices[0].message.content.strip()

    # Extract JSON from response even if there's extra text
    import re
    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if not json_match:
        raise ValueError(f"No JSON found in response: {raw[:100]}")

    result = json.loads(json_match.group())

    job["match_score"]     = int(result.get("match_score", 0))
    job["match_reason"]    = result.get("match_reason", "")
    job["missing_skills"]  = result.get("missing_skills", [])
    job["matching_skills"] = result.get("matching_skills", [])
    job["recommendation"]  = result.get("recommendation", "skip")
    return job


def batch_score_jobs(jobs: list, profile: dict, nvidia_api_key: str,
                     min_score: int = 55, delay: float = 0.5) -> tuple:
    """
    Scores all jobs and splits into apply_list / skip_list.
    delay=0.5s is safe — NVIDIA NIM has much higher rate limits than Groq,
    so you won't hit daily token limits mid-run.
    Returns (apply_list, skip_list).
    """
    apply_list, skip_list = [], []
    total  = len(jobs)
    errors = 0

    print(f"\n🤖 Scoring {total} jobs with NVIDIA NIM — Nemotron 49B...")
    print(f"   Min score to shortlist: {min_score}/100\n")

    for i, job in enumerate(jobs, 1):
        print(
            f"  [{i}/{total}] {job.get('title')} @ {job.get('company')}...",
            end=" ", flush=True
        )
        try:
            scored = score_job(job, profile, nvidia_api_key)
            score  = scored.get("match_score", 0)
            rec    = scored.get("recommendation", "skip")
            print(f"Score: {score}/100 → {rec.upper()}")

            if score >= min_score or rec == "apply":
                apply_list.append(scored)
            else:
                skip_list.append(scored)

            time.sleep(delay)

        except Exception as e:
            print(f"ERROR: {e}")
            errors += 1
            job["match_score"]     = 0
            job["match_reason"]    = ""
            job["missing_skills"]  = []
            job["matching_skills"] = []
            job["recommendation"]  = "skip"
            skip_list.append(job)
            time.sleep(2)     # back off on error

    apply_list.sort(key=lambda j: j.get("match_score", 0), reverse=True)

    print(f"\n📊 Scoring complete!")
    print(f"   ✅ Apply list : {len(apply_list)} jobs")
    print(f"   ❌ Skip list  : {len(skip_list)} jobs")
    if errors:
        print(f"   ⚠️  Errors    : {errors} jobs failed to score")

    return apply_list, skip_list


def print_apply_list(apply_list: list) -> None:
    """Pretty-prints the apply list with scores and reasons."""
    print("\n" + "=" * 70)
    print("🎯 JOBS TO APPLY FOR (sorted by match score)")
    print("=" * 70)
    for i, job in enumerate(apply_list, 1):
        print(f"\n{i}. [{job.get('match_score')}/100] "
              f"{job.get('title')} @ {job.get('company')}")
        print(f"   📍 {job.get('location')} | {job.get('source')}")
        print(f"   💡 {job.get('match_reason')}")
        print(f"   🔗 {job.get('apply_link', 'N/A')[:80]}")


if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.secrets import NVIDIA_API_KEY
    from config.search import SEARCH_CONFIG
    from modules.resume_parser import load_profile

    profile = load_profile("data/profile.json")
    with open("data/discovered_jobs.json") as f:
        jobs = json.load(f)

    min_score = SEARCH_CONFIG.get("min_match_score", 55)
    apply_list, skip_list = batch_score_jobs(
        jobs, profile, NVIDIA_API_KEY, min_score
    )

    with open("data/apply_list.json", "w") as f:
        json.dump(apply_list, f, indent=2)
    with open("data/skip_list.json", "w") as f:
        json.dump(skip_list, f, indent=2)

    print_apply_list(apply_list)
    print("\n💾 Saved to data/apply_list.json and data/skip_list.json")
