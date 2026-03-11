"""
run_agent.py
🤖 AI Job Application Agent — Main Runner
Orchestrates: Resume Parsing → Job Discovery → AI Matching → Auto Apply → Tracking

Usage:
    python run_agent.py                  # Full pipeline
    python run_agent.py --parse-only     # Only parse resume
    python run_agent.py --find-only      # Only discover jobs
    python run_agent.py --match-only     # Only score jobs
    python run_agent.py --apply-only     # Only apply (uses saved apply_list.json)
    python run_agent.py --dashboard      # Launch tracker dashboard only
"""

import sys
import os
import json
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Import config ─────────────────────────────────────────────────────────────
try:
    from config.secrets import (GROQ_API_KEY, JSEARCH_API_KEY,
                                  LINKEDIN_EMAIL, LINKEDIN_PASSWORD,
                                  NAUKRI_EMAIL, NAUKRI_PASSWORD)
    from config.search import SEARCH_CONFIG
    from config.answers import ANSWERS_CONFIG
except ImportError as e:
    print(f"❌ Config error: {e}")
    print("   Please fill in your config/secrets.py before running.")
    sys.exit(1)

# ── Import modules ────────────────────────────────────────────────────────────
from modules.resume_parser import parse_resume, load_profile
from modules.job_finder import discover_jobs, save_jobs
from modules.job_matcher import batch_score_jobs, print_apply_list
from modules.linkedin_applier import run_linkedin_applier
from modules.naukri_applier import run_naukri_applier
from modules.tracker import log_bulk_applications, run_dashboard, get_stats

# ── Paths ─────────────────────────────────────────────────────────────────────
RESUME_PATH = "resumes/resume.pdf"
PROFILE_PATH = "data/profile.json"
DISCOVERED_PATH = "data/discovered_jobs.json"
APPLY_LIST_PATH = "data/apply_list.json"
SKIP_LIST_PATH = "data/skip_list.json"


def banner() -> None:
    print("""
╔══════════════════════════════════════════════════════════════╗
║          🤖  AI JOB APPLICATION AGENT  v1.0                 ║
║          Built by Susmit Roy (Rukai)                        ║
╚══════════════════════════════════════════════════════════════╝
    """)


def check_secrets() -> bool:
    '''
    Validates that required secrets are filled in.
    '''
    required = {
        "GROQ_API_KEY": GROQ_API_KEY,
        "JSEARCH_API_KEY": JSEARCH_API_KEY,
    }
    missing = [k for k, v in required.items() if "your_" in v or not v]
    if missing:
        print(f"❌ Missing required secrets: {', '.join(missing)}")
        print("   Please fill in config/secrets.py")
        return False
    return True


def step_parse_resume() -> dict:
    '''Step 1: Parse resume into structured profile.'''
    print("\n" + "─" * 60)
    print("📄 STEP 1: RESUME PARSING")
    print("─" * 60)

    if os.path.exists(PROFILE_PATH):
        print(f"   Found existing profile at {PROFILE_PATH}")
        choice = input("   Re-parse resume? (y/n, default n): ").strip().lower()
        if choice != "y":
            profile = load_profile(PROFILE_PATH)
            print(f"   ✅ Loaded profile: {profile.get('name')} — {profile.get('current_title')}")
            return profile

    profile = parse_resume(RESUME_PATH, GROQ_API_KEY, PROFILE_PATH)
    print(f"\n   ✅ Parsed: {profile.get('name')} | {profile.get('current_title')}")
    print(f"   Experience: {profile.get('years_of_experience')} years")
    print(f"   Target roles: {', '.join(profile.get('target_roles', [])[:3])}")
    return profile


def step_discover_jobs(profile: dict) -> list[dict]:
    '''Step 2: Discover active job listings.'''
    print("\n" + "─" * 60)
    print("🔍 STEP 2: JOB DISCOVERY")
    print("─" * 60)

    if os.path.exists(DISCOVERED_PATH):
        with open(DISCOVERED_PATH) as f:
            existing = json.load(f)
        print(f"   Found {len(existing)} previously discovered jobs")
        choice = input("   Re-fetch jobs? (y/n, default n): ").strip().lower()
        if choice != "y":
            return existing

    if "your_" in JSEARCH_API_KEY:
        print("   ⚠️  JSearch API key not set — skipping job discovery")
        print("   Please add your RapidAPI key to config/secrets.py")
        return []

    jobs = discover_jobs(profile, SEARCH_CONFIG, JSEARCH_API_KEY)
    save_jobs(jobs, DISCOVERED_PATH)
    return jobs


def step_match_jobs(jobs: list[dict], profile: dict) -> list[dict]:
    '''Step 3: AI-score jobs and filter apply list.'''
    print("\n" + "─" * 60)
    print("🤖 STEP 3: AI JOB MATCHING")
    print("─" * 60)

    if os.path.exists(APPLY_LIST_PATH):
        with open(APPLY_LIST_PATH) as f:
            existing = json.load(f)
        print(f"   Found existing apply list ({len(existing)} jobs)")
        choice = input("   Re-score jobs? (y/n, default n): ").strip().lower()
        if choice != "y":
            print_apply_list(existing[:10])
            return existing

    if not jobs:
        print("   ⚠️  No jobs to score")
        return []

    min_score = SEARCH_CONFIG.get("min_match_score", 55)
    apply_list, skip_list = batch_score_jobs(jobs, profile, GROQ_API_KEY, min_score)

    # Save both
    with open(APPLY_LIST_PATH, "w") as f:
        json.dump(apply_list, f, indent=2)
    with open(SKIP_LIST_PATH, "w") as f:
        json.dump(skip_list, f, indent=2)

    print_apply_list(apply_list[:10])
    return apply_list


def step_apply(apply_list: list[dict], profile: dict) -> None:
    '''Step 4: Apply to jobs on LinkedIn and Naukri.'''
    print("\n" + "─" * 60)
    print("🚀 STEP 4: AUTO APPLY")
    print("─" * 60)

    if not apply_list:
        print("   ⚠️  No jobs in apply list")
        return

    print(f"\n   Apply list contains {len(apply_list)} jobs")
    print("   Platforms: LinkedIn Easy Apply + Naukri")

    secrets = {
        "LINKEDIN_EMAIL": LINKEDIN_EMAIL,
        "LINKEDIN_PASSWORD": LINKEDIN_PASSWORD,
        "NAUKRI_EMAIL": NAUKRI_EMAIL,
        "NAUKRI_PASSWORD": NAUKRI_PASSWORD,
    }

    choice = input("\n   Proceed with auto-apply? (y/n): ").strip().lower()
    if choice != "y":
        print("   Skipped auto-apply.")
        return

    # ── LinkedIn ──────────────────────────────────────────────────────────────
    print("\n  🔗 Starting LinkedIn Easy Apply...")
    apply_list = run_linkedin_applier(
        apply_list=apply_list,
        profile=profile,
        answers_config=ANSWERS_CONFIG,
        secrets=secrets,
        resume_path=RESUME_PATH,
        max_applications=SEARCH_CONFIG.get("max_linkedin_applications", 20),
        pause_before_submit=SEARCH_CONFIG.get("pause_before_submit", True)
    )

    # ── Naukri ────────────────────────────────────────────────────────────────
    print("\n  🏢 Starting Naukri Apply...")
    naukri_apps = run_naukri_applier(
        profile=profile,
        search_config=SEARCH_CONFIG,
        secrets=secrets,
        resume_path=RESUME_PATH,
        max_applications=SEARCH_CONFIG.get("max_naukri_applications", 15),
        pause_before_apply=SEARCH_CONFIG.get("pause_before_submit", True)
    )

    # ── Log all applied jobs to tracker ──────────────────────────────────────
    print("\n  📊 Logging applications to tracker...")
    linkedin_logged = log_bulk_applications(apply_list)
    naukri_logged = log_bulk_applications(naukri_apps)

    print(f"\n  ✅ Logged: {linkedin_logged} LinkedIn + {naukri_logged} Naukri applications")

    stats = get_stats()
    print(f"\n  📈 Total applications in database: {stats.get('total', 0)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Job Application Agent")
    parser.add_argument("--parse-only", action="store_true", help="Only parse resume")
    parser.add_argument("--find-only", action="store_true", help="Only discover jobs")
    parser.add_argument("--match-only", action="store_true", help="Only score jobs")
    parser.add_argument("--apply-only", action="store_true", help="Only apply to jobs")
    parser.add_argument("--dashboard", action="store_true", help="Launch tracker dashboard")
    args = parser.parse_args()

    banner()

    # Dashboard only
    if args.dashboard:
        run_dashboard()
        return

    if not check_secrets():
        return

    # ── Parse only ────────────────────────────────────────────────────────────
    if args.parse_only:
        step_parse_resume()
        return

    # ── Full pipeline or specific steps ──────────────────────────────────────
    profile = step_parse_resume()

    if args.find_only:
        step_discover_jobs(profile)
        return

    jobs = step_discover_jobs(profile)

    if args.match_only:
        if not jobs and os.path.exists(DISCOVERED_PATH):
            with open(DISCOVERED_PATH) as f:
                jobs = json.load(f)
        step_match_jobs(jobs, profile)
        return

    apply_list = step_match_jobs(jobs, profile)

    if not args.apply_only:
        pass  # Already went through all steps

    step_apply(apply_list, profile)

    print("\n" + "═" * 60)
    print("🎉 AGENT RUN COMPLETE")
    print("   Run `python run_agent.py --dashboard` to view tracker")
    print("═" * 60 + "\n")


if __name__ == "__main__":
    main()
