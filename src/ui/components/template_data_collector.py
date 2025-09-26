"""Template data collector for final resume generation."""
from typing import Dict, Any


class TemplateDataCollector:
    """Collects and formats data for template generation."""
    
    def __init__(self, app: Any):
        """Initialize with application instance.
        
        Args:
            app: Application instance containing data
        """
        self.app = app
    
    def collect_final_template_data(self) -> Dict[str, Any]:
        """Collect final template data using ordered data structures."""
        # Role mapping for template placeholders
        role_mapping = {
            "Nodelink": "NODELINK",
            "MAMM": "MAMM", 
            "FactCheckAI": "FACTCHECK",
            "Medical Classifier": "MEDICAL"
        }
        
        template_data = {}
        
        # Use ordered bullets data
        for role, bullets_data in self.app.ordered_bullets.items():
            template_prefix = role_mapping.get(role, role.upper().replace(' ', '').replace('-', ''))
            
            # Add title if applicable
            if role in ["Nodelink", "MAMM"] and hasattr(self.app, 'role_titles') and role in self.app.role_titles:
                title_entry = self.app.role_titles[role]
                title = title_entry.get().strip() if hasattr(title_entry, 'get') else ""
                template_data[f"{template_prefix}_TITLE"] = title
            else:
                template_data[f"{template_prefix}_TITLE"] = ""
            
            # Add bullets in their current order
            for i, bullet_data in enumerate(bullets_data, start=1):
                template_data[f"{template_prefix}_P{i}"] = bullet_data['bullet']
            
            # Clear unused placeholders
            max_bullets = 5
            for i in range(len(bullets_data) + 1, max_bullets + 1):
                template_data[f"{template_prefix}_P{i}"] = ""
        
        # Add skills in their current order - use both original key and numbered order
        skill_number = 1
        print("Template data - skill ordering:")
        for skill_data in self.app.ordered_skills:
            # Use original key for template compatibility
            template_data[skill_data['key']] = skill_data['value']
            print(f"  {skill_data['key']}: {skill_data['value']}")
            
            # Also use numbered order for templates that expect SKILL_1, SKILL_2, etc.
            if skill_number <= 4:  # Limit to 4 skills as per template
                template_data[f"SKILL_{skill_number}"] = skill_data['value']
                print(f"  SKILL_{skill_number}: {skill_data['value']}")
                skill_number += 1
        
        # Ensure all numbered skill placeholders are filled
        for i in range(skill_number, 5):
            template_data[f"SKILL_{i}"] = ""
        
        return template_data
    
    def calculate_selection_stats(self) -> Dict[str, Any]:
        """Calculate statistics about current selections."""
        total_bullets = sum(len(bullets) for bullets in self.app.ordered_bullets.values())
        total_lines = sum(
            sum(bullet['lines'] if isinstance(bullet['lines'], (int, float)) else 0 
                for bullet in bullets) 
            for bullets in self.app.ordered_bullets.values()
        )
        total_skills = len(self.app.ordered_skills)
        
        return {
            'total_bullets': total_bullets,
            'total_lines': total_lines,
            'total_skills': total_skills
        }