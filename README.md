# 🤖 hunt-smart — AI Job Application Agent

An intelligent, multi-platform job application agent that parses your resume, finds matching jobs, scores them with AI, and auto-applies on LinkedIn and Naukri.

**Built by Susmit Roy**

---

## ✨ Features

- **📄 Smart Resume Parser** — NVIDIA NIM (Nemotron 49B) extracts skills, experience, target roles, and ATS keywords from your PDF
- **🔍 Multi-source Job Discovery** — Finds active jobs from LinkedIn, Indeed, Glassdoor, Naukri via JSearch API
- **🤖 AI Job Matching** — Nemotron 49B scores each job 0–100 against your profile using guided JSON output (no parse errors)
- **🚀 LinkedIn Easy Apply Bot** — Selenium auto-fills and submits Easy Apply forms
- **🏢 Naukri Auto Apply** — Searches and applies on Naukri.com
- **📊 Application Tracker** — Local Flask dashboard at http://localhost:5000

---

## ⚙️ Setup

### 1. Install dependencies
```bash
pip install pymupdf openai selenium undetected-chromedriver setuptools requests flask
```

### 2. Install Chrome
Download [Google Chrome](https://www.google.com/chrome) and install it.

### 3. Fill in your credentials
Edit `config/secrets.py`:
```python
NVIDIA_API_KEY    = "nvapi-xxxxxxxxxxxx"   # build.nvidia.com (free)
JSEARCH_API_KEY   = "your_rapidapi_key"    # rapidapi.com/letscrape (free)
LINKEDIN_EMAIL    = "your@email.com"
LINKEDIN_PASSWORD = "your_password"
NAUKRI_EMAIL      = "your@email.com"
NAUKRI_PASSWORD   = "your_password"
```

### 4. Add your resume
Replace `resumes/resume.pdf` with your actual resume PDF.

### 5. Configure your search
Edit `config/search.py` — set target roles, locations, apply limits.
Edit `config/answers.py` — pre-fill salary, notice period, cover letter.

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

# Dashboard
python run_agent.py --dashboard
# Open http://localhost:5000
```

---

## 🗂️ Project Structure

```
hunt-smart/
├── run_agent.py
├── resumes/
│   └── resume.pdf              ← replace with your resume
├── config/
│   ├── secrets.py              ← API keys & credentials (never commit)
│   ├── search.py               ← job search preferences
│   └── answers.py              ← pre-filled application answers
├── modules/
│   ├── resume_parser.py        ← PDF → NVIDIA NIM → structured profile
│   ├── job_finder.py           ← JSearch API job discovery
│   ├── job_matcher.py          ← NVIDIA NIM job scoring
│   ├── linkedin_applier.py     ← LinkedIn Easy Apply bot
│   ├── naukri_applier.py       ← Naukri apply bot
│   └── tracker.py              ← SQLite + Flask dashboard
└── data/
    ├── profile.json            ← auto-generated
    ├── discovered_jobs.json    ← auto-generated
    ├── apply_list.json         ← auto-generated
    └── applications.db         ← auto-generated
```

---

## 🔑 API Keys (Free)

| Service | URL | Free Tier |
|---------|-----|-----------|
| NVIDIA NIM | build.nvidia.com | Unlimited (40 req/min) |
| JSearch | rapidapi.com/letscrape | 200 req/month |

---

## ⚠️ Disclaimer

Use responsibly and in accordance with LinkedIn's and Naukri's Terms of Service.
`pause_before_submit: False` by default — set to `True` in `config/search.py`
if you want to manually review every application before it submits.

---

*Built with ❤️ by Susmit Roy — github.com/susmitroy17/Hunt-smart*
