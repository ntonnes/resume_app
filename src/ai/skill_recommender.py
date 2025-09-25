"""Skill recommendation and categorization system."""
from typing import Dict, List, Tuple, Set
import re
from collections import defaultdict, Counter


class SkillRecommender:
    """Recommends and categorizes skills based on job descriptions."""
    
    def __init__(self, skills_to_categories: Dict[str, List[str]]):
        """Initialize with skills mapping.
        
        Args:
            skills_to_categories: Dict mapping skill names to list of categories
        """
        self.skills_to_categories = skills_to_categories
        self.categories_to_skills = self._build_category_index()
    
    def _build_category_index(self) -> Dict[str, List[str]]:
        """Build reverse index: categories -> skills."""
        categories_to_skills = defaultdict(list)
        for skill, categories in self.skills_to_categories.items():
            for category in categories:
                categories_to_skills[category].append(skill)
        return dict(categories_to_skills)
    
    def recommend_skills(self, job_description: str, num_categories: int = 4) -> List[Tuple[str, List[str]]]:
        """Recommend skill categories and specific skills based on job description.
        
        Args:
            job_description: The job posting text
            num_categories: Number of skill categories to return (default 4)
            
        Returns:
            List of (category, [skills]) tuples, ordered by relevance
        """
        # Score skills based on job description
        skill_scores = self._score_skills(job_description)
        
        # Score categories based on their skills
        category_scores = self._score_categories(skill_scores)
        
        # Select top categories
        top_categories = self._select_top_categories(category_scores, num_categories)
        
        # For each category, select relevant skills
        result = []
        for category in top_categories:
            category_skills = self.categories_to_skills.get(category, [])
            # Sort skills by their relevance score
            relevant_skills = sorted(
                [skill for skill in category_skills if skill in skill_scores],
                key=lambda s: skill_scores[s],
                reverse=True
            )[:4]  # Max 4 skills per category
            
            if relevant_skills:
                result.append((category, relevant_skills))
        
        return result
    
    def _score_skills(self, job_description: str) -> Dict[str, float]:
        """Score skills based on their relevance to the job description."""
        job_text = job_description.lower()
        skill_scores = {}
        
        for skill in self.skills_to_categories.keys():
            score = self._calculate_skill_relevance(skill, job_text)
            if score > 0:
                skill_scores[skill] = score
        
        return skill_scores
    
    def _calculate_skill_relevance(self, skill: str, job_text: str) -> float:
        """Calculate relevance score for a skill against job description."""
        skill_lower = skill.lower()
        score = 0.0
        
        # Direct mention (highest score)
        if skill_lower in job_text:
            score += 10.0
            
        # Word boundary matches (medium score)
        if re.search(r'\b' + re.escape(skill_lower) + r'\b', job_text):
            score += 5.0
            
        # Partial matches and synonyms (lower score)
        score += self._calculate_semantic_score(skill_lower, job_text)
        
        return score
    
    def _calculate_semantic_score(self, skill: str, job_text: str) -> float:
        """Calculate semantic relevance score."""
        # Common technology synonyms and related terms
        synonyms = {
            'python': ['django', 'flask', 'pandas', 'numpy', 'scikit'],
            'javascript': ['js', 'react', 'angular', 'vue', 'node'],
            'java': ['spring', 'maven', 'gradle'],
            'sql': ['database', 'mysql', 'postgresql', 'oracle'],
            'cloud': ['aws', 'azure', 'gcp', 'kubernetes', 'docker'],
            'machine learning': ['ml', 'ai', 'neural', 'tensorflow', 'pytorch'],
            'frontend': ['react', 'angular', 'vue', 'css', 'html'],
            'backend': ['api', 'server', 'database', 'microservices'],
            'devops': ['ci/cd', 'deployment', 'automation', 'infrastructure']
        }
        
        score = 0.0
        skill_words = skill.split()
        
        for word in skill_words:
            if word in job_text:
                score += 1.0
        
        # Check for synonyms
        for base_skill, related_terms in synonyms.items():
            if base_skill in skill.lower():
                for term in related_terms:
                    if term in job_text:
                        score += 0.5
        
        return score
    
    def _score_categories(self, skill_scores: Dict[str, float]) -> Dict[str, float]:
        """Score categories based on their skills' relevance."""
        category_scores = defaultdict(float)
        
        for skill, score in skill_scores.items():
            categories = self.skills_to_categories.get(skill, [])
            for category in categories:
                category_scores[category] += score
        
        return dict(category_scores)
    
    def _select_top_categories(self, category_scores: Dict[str, float], num_categories: int) -> List[str]:
        """Select top categories ensuring diversity."""
        # Sort categories by score
        sorted_categories = sorted(
            category_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        selected = []
        category_types = set()
        
        # First pass: select diverse category types
        for category, score in sorted_categories:
            if len(selected) >= num_categories:
                break
                
            category_type = self._get_category_type(category)
            if category_type not in category_types or len(selected) < 2:
                selected.append(category)
                category_types.add(category_type)
        
        # Second pass: fill remaining slots with highest scoring
        if len(selected) < num_categories:
            for category, score in sorted_categories:
                if len(selected) >= num_categories:
                    break
                if category not in selected:
                    selected.append(category)
        
        return selected[:num_categories]
    
    def _get_category_type(self, category: str) -> str:
        """Get the general type of a category for diversity."""
        category_lower = category.lower()
        
        if any(term in category_lower for term in ['programming', 'language', 'framework']):
            return 'programming'
        elif any(term in category_lower for term in ['cloud', 'infrastructure', 'devops']):
            return 'infrastructure'
        elif any(term in category_lower for term in ['data', 'analytics', 'machine learning', 'ai']):
            return 'data'
        elif any(term in category_lower for term in ['tool', 'software', 'platform']):
            return 'tools'
        else:
            return 'other'


def format_skill_for_template(category: str, skills: List[str]) -> str:
    """Format a skill category and skills for template insertion.
    
    Args:
        category: The category name
        skills: List of skills in the category
        
    Returns:
        Formatted string like "Category [Skill, Skill, Skill]"
    """
    skills_str = ", ".join(skills)
    return f"{category} [{skills_str}]"