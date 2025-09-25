"""Coordinate data sources and produce a tailored resume file."""
from typing import Dict, Optional
from ..data.job_parser import parse_job_description
from ..data.excel_loader import load_candidate_sheet, load_skills_sheet
from ..templates.template_renderer import render_template
from ..ai.recommender import recommend
from ..ai.skill_recommender import SkillRecommender, format_skill_for_template


DEFAULT_COUNTS = {
    "Nodelink": 5,
    "MAMM": 5,
    "FactCheck": 2,
    "Medical Classifier": 1,
}


def generate_resume(job_description_path: str, excel_path: str, template_path: str, output_path: str, sheet_name: Optional[str] = None) -> Dict[str, str]:
    """High-level pipeline to generate a resume.

    Steps (stubbed):
    - Read job description
    - Parse job description for keywords
    - Load candidate data from Excel
    - Merge data and render template

    Returns a dict with metadata (paths, status).
    """
    # Read job description
    with open(job_description_path, "r", encoding="utf-8") as f:
        jd_text = f.read()

    jd = parse_job_description(jd_text)
    candidate = load_candidate_sheet(excel_path, sheet_name=sheet_name)

    bullets_by_role = candidate.get("bullets") if isinstance(candidate, dict) else None

    # Default interactive path: if called directly, fall back to interactive selection
    selections = {}

    if bullets_by_role:
        for role, count in DEFAULT_COUNTS.items():
            bullets = bullets_by_role.get(role, [])
            if not bullets:
                continue

            # default to top-N picks
            recs = recommend(bullets, jd_text, top_n=min(count, len(bullets)))
            selections[role] = [b for b, _ in recs]

    # Load skills data
    skills_data = {}
    try:
        skills_data = load_skills_sheet(excel_path)
    except Exception as e:
        print(f"Warning: Could not load skills sheet: {e}")
    
    # Generate skill recommendations
    skill_recommendations = {}
    if skills_data:
        skill_recommender = SkillRecommender(skills_data)
        recommended_skills = skill_recommender.recommend_skills(jd_text, num_categories=4)
        
        for i, (category, skills) in enumerate(recommended_skills, start=1):
            skill_key = f"SKILL_{i}"
            skill_recommendations[skill_key] = format_skill_for_template(category, skills)
    
    # Prepare data mapping for template placeholders like {NODELINK_1}
    # Flatten selections into keys
    template_data = {}
    for role, items in selections.items():
        keybase = role.upper().replace(' ', '').replace('-', '')
        for i, item in enumerate(items, start=1):
            template_data[f"{keybase}_{i}"] = item['bullet']

    # Merge other candidate fields, jd summary, and skill recommendations
    other_fields = {k: v for k, v in (candidate.items() if isinstance(candidate, dict) else []) if k != 'bullets'}
    data = {**jd, **other_fields, **template_data, **skill_recommendations}

    out = render_template(template_path, data, output_path)

    return {"output_path": out, "status": "ok"}


def recommend_for_roles(jd_text: str, excel_path: str, sheet_name: Optional[str] = None, top_k: int = 10) -> Dict[str, list]:
    """Return recommended bullets per role (not interactive).

    Returns dict role -> list of bullet dicts (top_k).
    """
    candidate = load_candidate_sheet(excel_path, sheet_name=sheet_name)
    bullets_by_role = candidate.get("bullets") if isinstance(candidate, dict) else {}
    if bullets_by_role is None:
        bullets_by_role = {}

    results = {}
    for role, bullets in bullets_by_role.items():
        recs = recommend(bullets, jd_text, top_n=min(top_k, len(bullets)))
        results[role] = [b for b, _ in recs]

    return results
