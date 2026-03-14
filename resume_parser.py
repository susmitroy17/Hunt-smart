"""
resume_parser.py
Extracts structured profile data from a PDF resume using NVIDIA NIM.
Model  : meta/llama-3.1-8b-instruct
API    : build.nvidia.com (free tier)
"""

import fitz  # PyMuPDF
import json
import os
from openai import OpenAI

# ── JSON schema — guarantees valid structured output every time ────────────
PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "name":                { "type": "string" },
        "email":               { "type": "string" },
        "phone":               { "type": "string" },
        "location":            { "type": "string" },
        "linkedin":            { "type": "string" },
        "github":              { "type": "string" },
        "summary":             { "type": "string" },
        "current_title":       { "type": "string" },
        "years_of_experience": { "type": "number" },
        "job_titles":          { "type": "array",  "items": { "type": "string" } },
        "target_roles":        { "type": "array",  "items": { "type": "string" } },
        "skills": {
            "type": "object",
            "properties": {
                "technical": { "type": "array", "items": { "type": "string" } },
                "tools":     { "type": "array", "items": { "type": "string" } },
                "domain":    { "type": "array", "items": { "type": "string" } },
                "soft":      { "type": "array", "items": { "type": "string" } }
            }
        },
        "experience": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "company":    { "type": "string" },
                    "title":      { "type": "string" },
                    "location":   { "type": "string" },
                    "duration":   { "type": "string" },
                    "highlights": { "type": "array", "items": { "type": "string" } }
                }
            }
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "degree":      { "type": "string" },
                    "field":       { "type": "string" },
                    "institution": { "type": "string" },
                    "year":        { "type": "string" },
                    "gpa":         { "type": "string" }
                }
            }
        },
        "certifications":      { "type": "array", "items": { "type": "string" } },
        "projects":            { "type": "array", "items": { "type": "string" } },
        "ats_keywords":        { "type": "array", "items": { "type": "string" } },
        "preferred_locations": { "type": "array", "items": { "type": "string" } },
        "work_authorization":  { "type": "string" }
    },
    "required": [
        "name", "email", "phone", "location", "summary",
        "current_title", "years_of_experience", "skills",
        "target_roles", "ats_keywords"
    ]
}


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts raw text from a PDF file using PyMuPDF."""
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()
    return full_text.strip()


def parse_resume_with_ai(resume_text: str, nvidia_api_key: str) -> dict:
    """
    Sends resume text to NVIDIA NIM Nemotron 49B and returns a structured
    profile dict. Uses guided_json to guarantee valid JSON — no markdown
    fences, no parse errors.
    """
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=nvidia_api_key
    )

    system_prompt = (
        "You are an expert resume parser. "
        "Extract structured information from the resume text provided. "
        "Return ONLY a valid JSON object matching the schema exactly. "
        "No markdown, no explanation, no backticks — raw JSON only."
    )

    user_prompt = (
        f"Parse this resume and extract all information:\n\n{resume_text}\n\n"
        "Return a complete JSON profile with: name, email, phone, location, "
        "linkedin, github, summary, current_title, years_of_experience, "
        "job_titles, target_roles, skills (technical/tools/domain/soft), "
        "experience, education, certifications, projects, "
        "ats_keywords (top 30), preferred_locations, work_authorization."
    )

    response = client.chat.completions.create(
        model="meta/llama-3.1-8b-instruct",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        temperature=0.1,
        max_tokens=2000,
        extra_body={"nvext": {"guided_json": PROFILE_SCHEMA}}
    )

    raw = response.choices[0].message.content.strip()

    # Safety strip — remove any accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)


def save_profile(profile: dict, output_path: str) -> None:
    """Saves the parsed profile dict as a JSON file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    print(f"✅ Profile saved to: {output_path}")


def load_profile(profile_path: str) -> dict:
    """Loads a saved profile JSON from disk."""
    with open(profile_path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_resume(pdf_path: str, nvidia_api_key: str,
                 output_path: str = None) -> dict:
    """
    Full pipeline: PDF → text extraction → NVIDIA NIM → structured profile.
    Saves to output_path if provided. Returns the profile dict.
    """
    print(f"📄 Reading resume: {pdf_path}")
    text = extract_text_from_pdf(pdf_path)

    if not text:
        raise ValueError(
            "Could not extract text from PDF. Is it a scanned image PDF?"
        )

    print(f"🤖 Parsing with NVIDIA NIM — Nemotron 49B ({len(text)} chars)...")
    profile = parse_resume_with_ai(text, nvidia_api_key)

    if output_path:
        save_profile(profile, output_path)

    return profile


if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.secrets import NVIDIA_API_KEY

    profile = parse_resume(
        pdf_path="resumes/resume.pdf",
        nvidia_api_key=NVIDIA_API_KEY,
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
