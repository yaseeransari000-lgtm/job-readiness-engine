"""
skill_matcher.py
-----------------
Ye file resume aur job description compare karke match score nikalti hai.
Logic simple aur readable rakha gaya hai — koi heavy AI model nahi,
sirf smart keyword matching jo accurate results deta hai.
"""

import json
import re
import os

# skills_database.json se saari known skills load karte hain ek baar
SKILLS_FILE = os.path.join(os.path.dirname(__file__), "skills_database.json")

with open(SKILLS_FILE, "r", encoding="utf-8") as f:
    SKILLS_DATA = json.load(f)

ALL_SKILLS = SKILLS_DATA["skills"]


def clean_text(text):
    """Text ko lowercase karke extra spaces/symbols hata dete hain taaki matching accurate ho."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\+\#\.\s]", " ", text)  # special chars hatao (C++ aur C# bachao)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_skills(text):
    """
    Diye gaye text mein se humari skills_database wali skills dhoondta hai.
    Multi-word skills (jaise 'machine learning') bhi sahi se detect hoti hain.
    """
    cleaned = clean_text(text)
    found_skills = set()

    for skill in ALL_SKILLS:
        skill_clean = clean_text(skill)
        # word-boundary check taaki "java" "javascript" ke andar match na ho
        pattern = r"(?<!\w)" + re.escape(skill_clean) + r"(?!\w)"
        if re.search(pattern, cleaned):
            found_skills.add(skill)

    return found_skills


def calculate_match(resume_text, job_description_text):
    """
    Resume aur job description dono se skills nikal kar compare karta hai.
    Return karta hai: match percentage, matched skills, missing skills.
    """
    resume_skills = extract_skills(resume_text)
    job_skills = extract_skills(job_description_text)

    if not job_skills:
        # Agar job description mein koi pehchani hui skill na mile
        return {
            "match_percent": 0,
            "matched_skills": [],
            "missing_skills": [],
            "total_required": 0,
            "warning": "Job description mein koi recognizable skill nahi mili. Thoda detailed JD try karo."
        }

    matched = resume_skills & job_skills          # dono mein common skills
    missing = job_skills - resume_skills           # job mein hai, resume mein nahi

    match_percent = round((len(matched) / len(job_skills)) * 100)

    return {
        "match_percent": match_percent,
        "matched_skills": sorted(matched),
        "missing_skills": sorted(missing),
        "total_required": len(job_skills),
        "warning": None
    }


# Har missing skill ke liye free learning resource suggest karne wala chhota dictionary
LEARNING_RESOURCES = {
    "python": "https://docs.python.org/3/tutorial/",
    "javascript": "https://javascript.info/",
    "react": "https://react.dev/learn",
    "sql": "https://www.w3schools.com/sql/",
    "flask": "https://flask.palletsprojects.com/en/latest/quickstart/",
    "django": "https://docs.djangoproject.com/en/stable/intro/tutorial01/",
    "git": "https://git-scm.com/book/en/v2",
    "docker": "https://docs.docker.com/get-started/",
    "machine learning": "https://www.coursera.org/learn/machine-learning",
    "data analysis": "https://www.kaggle.com/learn/pandas",
}


def get_resource_link(skill):
    """Skill ke liye free resource link deta hai, agar available ho toh."""
    return LEARNING_RESOURCES.get(skill, f"https://www.google.com/search?q=learn+{skill.replace(' ', '+')}+free+course")
