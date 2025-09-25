"""Parse job descriptions into structured requirements and keywords.

This module provides a simple interface to extract useful data from a
job description text that can later be used to prioritize resume sections
or tailor bullet points.
"""
from typing import Dict, List


def parse_job_description(text: str) -> Dict[str, List[str]]:
    """Parse a job description text and return extracted keywords and sections.

    Returns a dict with keys like 'skills', 'responsibilities', and 'keywords'.
    This is a stub — extend with NLP or regex-based extraction as needed.
    """
    # Simple placeholder: split on lines and common separators
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    keywords = set()
    skills = []
    responsibilities = []

    for line in lines:
        lower = line.lower()
        if any(tok in lower for tok in ("skill", "experience with", "proficient in")):
            skills.append(line)
        elif any(tok in lower for tok in ("responsibl", "responsibility", "you will")):
            responsibilities.append(line)
        else:
            # naive keyword collection: split words longer than 3 chars
            for w in line.split():
                if len(w) > 3:
                    keywords.add(w.strip(',:;.()'))

    return {
        "skills": skills,
        "responsibilities": responsibilities,
        "keywords": sorted(keywords),
    }
