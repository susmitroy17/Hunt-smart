# 🤖 AI Job Application Agent

An intelligent, multi-platform job application agent that parses your resume, finds matching jobs, scores them with AI, and auto-applies on LinkedIn and Naukri built by **Susmit Roy**.

---

## ✨ Features

- **📄 Smart Resume Parser** — AI extracts your skills, experience, target roles, and ATS keywords automatically
- **🔍 Multi-source Job Discovery** — Finds active jobs from LinkedIn, Indeed, Glassdoor, Naukri via JSearch API
- **🤖 AI Job Matching** — Groq AI scores each job against your profile (0–100) and filters low-match jobs
- **🚀 LinkedIn Easy Apply Bot** — Selenium auto-fills and submits Easy Apply forms
- **🏢 Naukri Auto Apply** — Searches and applies on Naukri.com
- **📊 Application Tracker** — Local Flask dashboard showing all applications, statuses, and match scores

---

## ⚙️ Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Install Chrome + ChromeDriver
Download [Google Chrome](https://www.google.com/chrome) and install it.

### 3. Fill in your credentials
Edit `config/secrets.py`:
```python
GROQ_API_KEY = "your_groq_key"         # console.groq.com (free)
JSEARCH_API_KEY = "your_rapidapi_key"  # rapidapi.com/letscrape (free tier)
LINKEDIN_EMAIL = "your@email.com"
LINKEDIN_PASSWORD = "your_password"
NAUKRI_EMAIL = "your@email.com"
NAUKRI_PASSWORD = "your_password"
```

### 4. Add your resume
Replace `resumes/resume.pdf` with your actual resume PDF.

### 5. Configure your search
Edit `config/search.py` to set your target roles, locations, and apply limits.
Edit `config/answers.py` to pre-fill your application answers.

---

## 🚀 Usage

```bash
# Full pipeline (parse → find → match → apply)
python run_agent.py

# Individual steps
python run_agent.py --parse-only     # Parse resume only
python run_agent.py --find-only      # Discover jobs only
python run_agent.py --match-only     # AI scoring only
python run_agent.py --apply-only     # Apply using saved apply_list.json

# View application tracker dashboard
python run_agent.py --dashboard
# Open http://localhost:5000 in your browser
```

---

## 🗂️ Project Structure

```
job_agent/
├── run_agent.py              # Main orchestrator
├── requirements.txt
├── resumes/
│   └── resume.pdf            # Your resume (replace this)
├── config/
│   ├── secrets.py            # API keys & credentials (⚠️ never commit)
│   ├── search.py             # Job search preferences
│   └── answers.py            # Pre-filled application answers
├── modules/
│   ├── resume_parser.py      # PDF → AI structured profile
│   ├── job_finder.py         # JSearch API job discovery
│   ├── job_matcher.py        # Groq AI job scoring
│   ├── linkedin_applier.py   # LinkedIn Easy Apply bot
│   ├── naukri_applier.py     # Naukri apply bot
│   └── tracker.py            # SQLite + Flask dashboard
└── data/
    ├── profile.json           # Parsed resume profile (auto-generated)
    ├── discovered_jobs.json   # Raw job listings (auto-generated)
    ├── apply_list.json        # High-match jobs to apply (auto-generated)
    └── applications.db        # SQLite application tracker (auto-generated)
```

---

## 🔑 API Keys (Free Tiers)

| Service | URL | Free Tier |
|---------|-----|-----------|
| Groq AI | console.groq.com | 14,400 req/day |
| JSearch (RapidAPI) | rapidapi.com/letscrape-6bfcfaeece9f-6bfcfaeece9f/api/jsearch | 200 req/month |

---

## ⚠️ Disclaimer

This tool is for personal job search automation. Use responsibly and in accordance with LinkedIn's and Naukri's Terms of Service. `pause_before_submit: True` (default) ensures you review every application before it's submitted.

---

## 📊 Dashboard Preview

Run `python run_agent.py --dashboard` and open `http://localhost:5000` to see:
- Total applications, interviews, offers
- Match scores per job
- Filter by source, status, company
- Direct links to job postings

---

*Built with ❤️ by Susmit Roy — inspired by [Auto_job_applier_linkedIn](https://github.com/GodsScion/Auto_job_applier_linkedIn)*
