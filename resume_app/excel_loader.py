"""Load candidate data and mapping from Excel files."""
from typing import Dict, Any, Optional
import pandas as pd


def load_candidate_sheet(path: str, sheet_name: Optional[str] = None) -> Dict[str, Any]:
    """Load candidate data from an Excel file.

    If the sheet contains columns named `Role` and `BulletPoint` (or similar),
    returns {"bullets": {role: [entries]}}. Otherwise returns a simple mapping 
    of the first row's columns to values.
    """
    try:
        df = pd.read_excel(path, sheet_name=sheet_name)
    except Exception as e:
        raise ValueError(f"Failed to read Excel file: {e}")

    # Handle multiple sheets case
    if isinstance(df, dict):
        first_key = next(iter(df.keys()))
        df = df[first_key]

    if df.empty:
        return {}

    # Check if this is bullet list format
    if _is_bullet_format(df):
        return _parse_bullet_format(df)
    else:
        return _parse_simple_format(df)


def _is_bullet_format(df: pd.DataFrame) -> bool:
    """Check if DataFrame has bullet list format (Role and BulletPoint columns)."""
    cols = [str(c).lower() for c in df.columns]
    has_role = "role" in cols
    has_bullet = any(bullet_col in cols for bullet_col in ["bulletpoint", "bullet point", "bullet"])
    return has_role and has_bullet


def _parse_bullet_format(df: pd.DataFrame) -> Dict[str, Any]:
    """Parse DataFrame in bullet list format."""
    col_map = {c.lower(): c for c in df.columns}
    
    # Map column names
    role_col = col_map.get("role", "Role")
    bullet_col = (col_map.get("bulletpoint") or 
                  col_map.get("bullet point") or 
                  col_map.get("bullet", "BulletPoint"))
    category_col = col_map.get("category")
    keywords_col = col_map.get("keywords")
    lines_col = col_map.get("lines")

    bullets_by_role: Dict[str, Any] = {}
    
    for _, row in df.iterrows():
        role = _safe_str(row[role_col])
        bullet = _safe_str(row[bullet_col])
        
        if not role or not bullet:
            continue
            
        entry = {
            "role": role,
            "bullet": bullet,
            "category": _safe_str(row[category_col]) if category_col else None,
            "keywords": _parse_keywords(row[keywords_col]) if keywords_col else [],
            "lines": _safe_int(row[lines_col]) if lines_col else None
        }

        bullets_by_role.setdefault(role, []).append(entry)

    return {"bullets": bullets_by_role}


def _parse_simple_format(df: pd.DataFrame) -> Dict[str, Any]:
    """Parse DataFrame as simple first-row mapping."""
    first_row = df.iloc[0]
    return {str(col): first_row[col] for col in df.columns}


def _safe_str(value) -> str:
    """Safely convert value to string, handling NaN values."""
    return str(value).strip() if pd.notna(value) else ""


def _safe_int(value) -> int:
    """Safely convert value to int, handling NaN values."""
    if pd.isna(value):
        return 0
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0


def _parse_keywords(value) -> list:
    """Parse keywords from string value."""
    if pd.isna(value):
        return []
    keywords = str(value).split(",")
    return [k.strip() for k in keywords if k.strip()]


def load_skills_sheet(path: str) -> Dict[str, list]:
    """Load skills data from Skills sheet.
    
    Returns:
        Dict mapping skills to their categories
    """
    try:
        df = pd.read_excel(path, sheet_name="Skills")
    except Exception as e:
        raise ValueError(f"Failed to read Skills sheet: {e}")
    
    if df.empty:
        return {}
    
    # Expected columns: Category, Skill
    skills_to_categories = {}
    
    for _, row in df.iterrows():
        skill = _safe_str(row.get("Skill", ""))
        categories_str = _safe_str(row.get("Category", ""))
        
        if skill and categories_str:
            # Parse comma-separated categories
            categories = [cat.strip() for cat in categories_str.split(",") if cat.strip()]
            skills_to_categories[skill] = categories
    
    return skills_to_categories
