"""Review panel for the Resume Builder."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, Any

from .base_panel import BasePanel
from ...templates.template_renderer import render_template
from ...utils.ui_helpers import bind_mouse_wheel


class ReviewPanel(BasePanel):
    """Panel for reviewing selections and generating the resume."""
    
    def _build_ui(self):
        """Build the review panel UI."""
        # Configure frame
        self.frame.configure(padding=20)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(self.frame, text="Review & Generate Resume", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 20), sticky="ew")
        
        # Scrollable review area - takes full width
        review_container = ttk.Frame(self.frame)
        review_container.grid(row=1, column=0, sticky="nsew")
        review_container.columnconfigure(0, weight=1)
        review_container.rowconfigure(0, weight=1)
        
        review_canvas = tk.Canvas(review_container)
        review_scrollbar = ttk.Scrollbar(review_container, orient="vertical", command=review_canvas.yview)
        review_canvas.configure(yscrollcommand=review_scrollbar.set)
        
        self.review_frame = ttk.Frame(review_canvas)
        self.review_frame.columnconfigure(0, weight=1)  # Allow full width expansion
        review_canvas.create_window((0, 0), window=self.review_frame, anchor="nw")
        
        review_canvas.grid(row=0, column=0, sticky="nsew")
        review_scrollbar.grid(row=0, column=1, sticky="ns")
        
        self.review_frame.bind('<Configure>', lambda e: review_canvas.configure(scrollregion=review_canvas.bbox('all')))
        
        # Enable mouse wheel scrolling for review
        bind_mouse_wheel(self.review_frame, review_canvas)
        
        # Generate button
        generate_frame = ttk.Frame(self.frame)
        generate_frame.grid(row=2, column=0, pady=(20, 0))
        
        self.generate_btn = ttk.Button(generate_frame, text="Generate Resume", command=self._generate_resume)
        self.generate_btn.pack()
    
    def load_data(self):
        """Load and display selected bullets and skills for review."""
        # Clear previous review content
        for child in self.review_frame.winfo_children():
            child.destroy()
        
        # Create main container with full width layout
        main_container = ttk.Frame(self.review_frame)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=1)  # Two equal columns
        main_container.rowconfigure(1, weight=1)  # Allow content to expand vertically
        
        # Summary statistics at the top - spanning both columns
        stats_frame = ttk.LabelFrame(main_container, text="Selection Summary", padding=15)
        stats_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        
        # Calculate totals
        total_bullets = sum(len(self.app.selected_bullets.get(role, set())) for role in self.app.selection_requirements.keys())
        total_lines = 0
        for role, selected_indices in self.app.selected_bullets.items():
            bullets = self.app.recs.get(role, [])
            for idx in selected_indices:
                if idx < len(bullets):
                    lines = bullets[idx].get("lines", 0)
                    if isinstance(lines, (int, float)):
                        total_lines += int(lines)
        
        total_skills = len([skill for skill in self.app.selected_skills.values() if skill.strip()])
        
        stats_text = f"Total Bullet Points: {total_bullets} | Total Lines: {total_lines} | Skills Categories: {total_skills}"
        ttk.Label(stats_frame, text=stats_text, font=("Arial", 12, "bold"), foreground="darkgreen").pack()
        
        # Left Column: Bullet Points Section
        bullets_section = ttk.LabelFrame(main_container, text="Selected Bullet Points", padding=15)
        bullets_section.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(0, 20))
        bullets_section.columnconfigure(0, weight=1)
        
        # Roles that need titles
        title_roles = ["Nodelink", "MAMM"]
        
        for role in self.app.selection_requirements.keys():
            selected_indices = self.app.selected_bullets.get(role, set())
            if not selected_indices:
                continue
                
            # Role section with full width
            role_frame = ttk.LabelFrame(bullets_section, text=role, padding=15)
            role_frame.pack(fill="x", padx=5, pady=10)
            role_frame.columnconfigure(1, weight=1)
            
            # Title input for applicable roles
            if role in title_roles:
                ttk.Label(role_frame, text="Job Title:").grid(row=0, column=0, sticky="w", pady=(0, 10))
                title_entry = ttk.Entry(role_frame, width=60)
                title_entry.grid(row=0, column=1, sticky="ew", pady=(0, 10), padx=(10, 0))
                
                # Set default title
                default_titles = {
                    "Nodelink": "Software Engineer",
                    "MAMM": "Research Assistant"
                }
                title_entry.insert(0, default_titles.get(role, ""))
                self.app.role_titles[role] = title_entry
            
            # Selected bullets
            ttk.Label(role_frame, text="Selected Bullets:", font=("Arial", 10, "bold")).grid(
                row=1 if role in title_roles else 0, column=0, columnspan=2, sticky="w", pady=(10, 5))
            
            bullets = self.app.recs.get(role, [])
            for i, bullet_idx in enumerate(sorted(selected_indices)):
                if bullet_idx < len(bullets):
                    bullet = bullets[bullet_idx]
                    bullet_text = bullet.get("bullet", "")
                    lines = bullet.get("lines", "?")
                    
                    bullet_label = ttk.Label(role_frame, text=f"• {bullet_text} (Lines: {lines})", 
                                           wraplength=1200, justify="left", font=("Arial", 9))
                    bullet_label.grid(row=2+i if role in title_roles else 1+i, column=0, 
                                    columnspan=2, sticky="ew", pady=2, padx=(20, 0))
        
        # Right Column: Skills Section
        skills_section = ttk.LabelFrame(main_container, text="Selected Skills", padding=15)
        skills_section.grid(row=1, column=1, sticky="nsew", padx=(10, 0), pady=(0, 20))
        skills_section.columnconfigure(0, weight=1)
        
        # Collect current skills
        self._collect_selected_skills()
        
        if self.app.selected_skills:
            skills_container = ttk.Frame(skills_section)
            skills_container.pack(fill="x")
            skills_container.columnconfigure(0, weight=1)
            
            row = 0
            for skill_key, skill_value in self.app.selected_skills.items():
                if skill_value and skill_value.strip():
                    # Parse skill to show category in bold and skills in normal text
                    skill_frame = ttk.Frame(skills_container)
                    skill_frame.grid(row=row, column=0, sticky="ew", pady=5, padx=10)
                    skill_frame.columnconfigure(1, weight=1)
                    
                    # Skill number
                    ttk.Label(skill_frame, text=f"{skill_key}:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 10))
                    
                    # Skill content with character count
                    char_count = len(skill_value)
                    color = "green" if char_count <= 50 else "red"
                    skill_text = f"{skill_value} ({char_count}/50 chars)"
                    ttk.Label(skill_frame, text=skill_text, font=("Arial", 10), 
                             foreground=color, wraplength=1000).grid(row=0, column=1, sticky="ew")
                    row += 1
        else:
            ttk.Label(skills_section, text="No skills selected", font=("Arial", 10, "italic"), 
                     foreground="gray").pack(pady=10)
    
    def _collect_selected_skills(self):
        """Collect the currently selected skills from the skills panel."""
        # This will be called by the skills panel before navigation
        # Skills are already collected in app.selected_skills
        pass
    
    def _generate_resume(self):
        """Generate the final resume."""
        if not self.app.template_path:
            messagebox.showerror("Error", "No template file selected.")
            return
        
        # Collect template data
        template_data = self._collect_final_template_data()
        
        if not template_data:
            if not messagebox.askyesno("No Data", "No bullets selected. Continue with empty template?"):
                return
        
        # Get save location
        out_path = filedialog.asksaveasfilename(
            defaultextension=".docx",
            filetypes=[("Word Document", "*.docx")],
            title="Save Resume As"
        )
        if not out_path:
            return
        
        try:
            # Debug: Print skill data being passed to template
            print("=== DEBUG: Template Data for Skills ===")
            for key, value in template_data.items():
                if key.startswith("SKILL_"):
                    print(f"{key}: '{value}'")
            print("=======================================")
            
            render_template(self.app.template_path, template_data, out_path)
            messagebox.showinfo("Success", f"Resume generated successfully!\nSaved to: {out_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate resume: {e}")
    
    def _collect_final_template_data(self) -> Dict[str, Any]:
        """Collect final template data from selections."""
        # Role mapping for template placeholders
        role_mapping = {
            "Nodelink": "NODELINK",
            "MAMM": "MAMM", 
            "FactCheckAI": "FACTCHECK",
            "Medical Classifier": "MEDICAL"
        }
        
        template_data = {}
        
        for role in self.app.selection_requirements.keys():
            template_prefix = role_mapping.get(role, role.upper().replace(' ', '').replace('-', ''))
            selected_indices = self.app.selected_bullets.get(role, set())
            
            # Add title if applicable
            if role in ["Nodelink", "MAMM"] and role in self.app.role_titles:
                title_entry = self.app.role_titles[role]
                title = title_entry.get().strip() if hasattr(title_entry, 'get') else ""
                template_data[f"{template_prefix}_TITLE"] = title
            else:
                template_data[f"{template_prefix}_TITLE"] = ""
            
            # Add selected bullets
            bullets = self.app.recs.get(role, [])
            sorted_indices = sorted(selected_indices)
            
            for i, bullet_idx in enumerate(sorted_indices, start=1):
                if bullet_idx < len(bullets):
                    bullet = bullets[bullet_idx]
                    bullet_text = bullet.get("bullet", "")
                    template_data[f"{template_prefix}_P{i}"] = bullet_text
            
            # Clear unused placeholders
            max_bullets = 5
            for i in range(len(sorted_indices) + 1, max_bullets + 1):
                template_data[f"{template_prefix}_P{i}"] = ""
        
        # Add selected skills
        for skill_key, skill_value in self.app.selected_skills.items():
            template_data[skill_key] = skill_value
        
        # Ensure all skill placeholders are filled
        for i in range(1, 5):
            skill_key = f"SKILL_{i}"
            if skill_key not in template_data:
                template_data[skill_key] = ""
        
        return template_data
    
    def validate(self) -> bool:
        """Validate before final generation - always return True for review panel."""
        return True