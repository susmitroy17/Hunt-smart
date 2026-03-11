"""
resume_parser.py
Extracts structured profile data from a PDF resume using Groq AI.
"""

import fitz  # PyMuPDF
import json
import os
from groq import Groq


def extract_text_from_pdf(pdf_path: str) -> str:
    '''
    Extracts raw text from a PDF file using PyMuPDF.
    '''
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()
    return full_text.strip()


def parse_resume_with_ai(resume_text: str, groq_api_key: str) -> dict:
    '''
    Sends resume text to Groq AI and extracts a structured profile as JSON.
    Returns a dict with keys: name, email, phone, location, summary,
    skills, experience, education, certifications, job_titles, keywords.
    '''
    client = Groq(api_key=groq_api_key)

    system_prompt = """You are an expert resume parser. Extract structured information from the resume text provided.
Return ONLY a valid JSON object — no markdown, no explanation, no backticks.

The JSON must follow this exact schema:
{
  "name": "Full Name",
  "email": "email@example.com",
  "phone": "+91-XXXXXXXXXX",
  "location": "City, State, Country",
  "linkedin": "linkedin URL or empty string",
  "github": "github URL or empty string",
  "summary": "2-3 sentence professional summary",
  "current_title": "Most recent job title",
  "years_of_experience": 2.5,
  "job_titles": ["list", "of", "all", "job", "titles", "held"],
  "target_roles": ["roles this person is suited for based on their skills"],
  "skills": {
    "technical": ["list of technical skills"],
    "tools": ["list of tools and software"],
    "domain": ["domain knowledge areas"],
    "soft": ["soft skills inferred from resume"]
  },
  "experience": [
    {
      "company": "Company Name",
      "title": "Job Title",
      "location": "City, Country",
      "duration": "Start – End",
      "highlights": ["bullet point 1", "bullet point 2"]
    }
  ],
  "education": [
    {
      "degree": "Degree name",
      "field": "Field of study",
      "institution": "University name",
      "year": "Year",
      "gpa": "GPA or empty string"
    }
  ],
  "certifications": ["list of certifications"],
  "projects": ["list of project names"],
  "ats_keywords": ["top 30 ATS-optimized keywords from this resume for job matching"],
  "preferred_locations": ["locations mentioned or implied in resume"],
  "work_authorization": "India"
}"""

    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Parse this resume:\n\n{resume_text}"}
        ],
        temperature=0.1,
        max_tokens=2000
    )

    raw = response.choices[0].message.content.strip()

    # Clean any accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    profile = json.loads(raw)
    return profile


def save_profile(profile: dict, output_path: str) -> None:
    '''
    Saves the parsed profile dict as a JSON file.
    '''
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    print(f"✅ Profile saved to: {output_path}")


def load_profile(profile_path: str) -> dict:
    '''
    Loads a saved profile JSON from disk.
    '''
    with open(profile_path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_resume(pdf_path: str, groq_api_key: str, output_path: str = None) -> dict:
    '''
    Full pipeline: PDF → text extraction → AI parsing → structured profile.
    Optionally saves to output_path if provided.
    Returns the profile dict.
    '''
    print(f"📄 Reading resume: {pdf_path}")
    text = extract_text_from_pdf(pdf_path)

    if not text:
        raise ValueError("Could not extract text from PDF. Is it a scanned image PDF?")

    print(f"🤖 Parsing with Groq AI ({len(text)} characters)...")
    profile = parse_resume_with_ai(text, groq_api_key)

    if output_path:
        save_profile(profile, output_path)

    return profile


if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.secrets import GROQ_API_KEY

    profile = parse_resume(
        pdf_path="resumes/resume.pdf",
        groq_api_key=GROQ_API_KEY,
        output_path="data/profile.json"
    )

    print("\n📊 PARSED PROFILE SUMMARY")
    print("=" * 50)
    print(f"Name        : {profile.get('name')}")
    print(f"Title       : {profile.get('current_title')}")
    print(f"Experience  : {profile.get('years_of_experience')} years")
    print(f"Location    : {profile.get('location')}")
    print(f"\nTarget Roles:")
    for role in profile.get("target_roles", []):
        print(f"  → {role}")
    print(f"\nTop Skills  : {', '.join(profile.get('skills', {}).get('technical', [])[:8])}")
    print(f"\nATS Keywords: {', '.join(profile.get('ats_keywords', [])[:10])}...")
