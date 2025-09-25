"""Skills selection panel for the Resume Builder."""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Set

from .base_panel import BasePanel
from ...data.excel_loader import load_skills_sheet
from ...ai.skill_recommender import SkillRecommender, format_skill_for_template
from ...utils.ui_helpers import bind_mouse_wheel


class SkillsSelectionPanel(BasePanel):
    """Panel for selecting skills and categories."""
    
    def _build_ui(self):
        """Build the skills selection UI."""
        # Configure frame
        self.frame.configure(padding=20)
        self.frame.columnconfigure(0, weight=7)  # Skills area takes much more space
        self.frame.columnconfigure(1, weight=2)   # Minimal job description area
        self.frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(self.frame, text="Select Skills", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 20))
        
        # Left side: Skills selection
        skills_main_frame = ttk.LabelFrame(self.frame, text="Skills Selection", padding=15)
        skills_main_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 15))
        skills_main_frame.columnconfigure(0, weight=1)
        skills_main_frame.rowconfigure(1, weight=1)
        
        # Category selection frame
        categories_frame = ttk.LabelFrame(skills_main_frame, text="Select Relevant Categories", padding=10)
        categories_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        categories_frame.columnconfigure(0, weight=1)
        
        self.categories_frame = categories_frame  # Store reference for population
        
        # Skills sections - scrollable
        skills_outer_frame = ttk.Frame(skills_main_frame)
        skills_outer_frame.grid(row=1, column=0, sticky="nsew")
        skills_outer_frame.columnconfigure(0, weight=1)
        skills_outer_frame.rowconfigure(0, weight=1)
        
        # Canvas and scrollbar for skills sections
        skills_canvas = tk.Canvas(skills_outer_frame)
        skills_scrollbar = ttk.Scrollbar(skills_outer_frame, orient="vertical", command=skills_canvas.yview)
        skills_canvas.configure(yscrollcommand=skills_scrollbar.set)
        
        self.skills_content_frame = ttk.Frame(skills_canvas)
        self.skills_content_frame.columnconfigure(0, weight=1)
        self.skills_content_frame.columnconfigure(1, weight=1)  # Two columns for skill sections
        
        # Bind scrolling configuration
        self.skills_content_frame.bind('<Configure>', 
                                     lambda e: skills_canvas.configure(scrollregion=skills_canvas.bbox('all')))
        
        skills_canvas.create_window((0, 0), window=self.skills_content_frame, anchor="nw")
        skills_canvas.grid(row=0, column=0, sticky="nsew")
        skills_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Enable mouse wheel scrolling
        bind_mouse_wheel(self.skills_content_frame, skills_canvas)
        
        # Right side: Job description
        jd_frame = ttk.LabelFrame(self.frame, text="Job Description Reference", padding=15)
        jd_frame.grid(row=1, column=1, sticky="nsew")
        jd_frame.columnconfigure(0, weight=1)
        jd_frame.rowconfigure(1, weight=1)
        
        jd_label = ttk.Label(jd_frame, text="Use this as reference:", font=("Arial", 10, "bold"))
        jd_label.grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        jd_text_frame = ttk.Frame(jd_frame)
        jd_text_frame.grid(row=1, column=0, sticky="nsew")
        jd_text_frame.columnconfigure(0, weight=1)
        jd_text_frame.rowconfigure(0, weight=1)
        
        self.skills_jd_text = tk.Text(jd_text_frame, wrap=tk.WORD, state="disabled", font=("Arial", 9), width=20, height=15)
        jd_scrollbar = ttk.Scrollbar(jd_text_frame, orient="vertical", command=self.skills_jd_text.yview)
        self.skills_jd_text.configure(yscrollcommand=jd_scrollbar.set)
        
        self.skills_jd_text.grid(row=0, column=0, sticky="nsew")
        jd_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Enable mouse wheel scrolling
        def skills_jd_mousewheel(event):
            self.skills_jd_text.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.skills_jd_text.bind("<MouseWheel>", skills_jd_mousewheel)
    
    def load_data(self):
        """Load skills data and generate recommendations."""
        try:
            # Ensure we have an excel path
            if not self.app.excel_path:
                raise ValueError("No Excel file selected")
            
            # Load skills data from Excel
            self.app.skills_data = load_skills_sheet(self.app.excel_path)
            
            if self.app.skills_data:
                # Generate skill recommendations
                skill_recommender = SkillRecommender(self.app.skills_data)
                self.app.skill_recommendations = skill_recommender.recommend_skills(self.app.jd_text, num_categories=4)
            else:
                self.app.skill_recommendations = []
                
            # Populate the skills panel
            self._populate_skills_panel()
            
        except Exception as e:
            error_msg = str(e)
            print(f"ERROR in load_data: {error_msg}")
            print(f"Exception type: {type(e)}")
            print(f"Excel path was: {self.app.excel_path}")
            
            if "Skills sheet not found" in error_msg:
                messagebox.showwarning("Skills Sheet Missing", 
                    f"Your Excel file doesn't contain a 'Skills' sheet.\n\n{error_msg}\n\n"
                    "You can still continue without skills recommendations.")
            else:
                messagebox.showwarning("Skills Warning", f"Could not load skills: {error_msg}")
            self.app.skill_recommendations = []
            self._populate_skills_panel()
    
    def _populate_skills_panel(self):
        """Populate the skills panel with categories and skill sections."""
        # Populate job description text
        if hasattr(self, 'skills_jd_text'):
            self.skills_jd_text.config(state="normal")
            self.skills_jd_text.delete("1.0", tk.END)
            self.skills_jd_text.insert("1.0", self.app.jd_text)
            self.skills_jd_text.config(state="disabled")
        
        # Clear existing content
        for widget in self.categories_frame.winfo_children():
            widget.destroy()
        for widget in self.skills_content_frame.winfo_children():
            widget.destroy()
        
        # Populate category selection checkboxes
        if self.app.skills_data:
            all_categories = set()
            for skill_categories in self.app.skills_data.values():
                all_categories.update(skill_categories)
            all_categories = sorted(list(all_categories))
            
            ttk.Label(self.categories_frame, text="Select relevant categories:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 10))
            
            # Create category checkboxes in an 8-column grid
            categories_grid_frame = ttk.Frame(self.categories_frame)
            categories_grid_frame.pack(fill="x")
            
            self.category_vars = {}
            max_cols = 8
            for i, category in enumerate(all_categories):
                var = tk.BooleanVar()
                checkbox = ttk.Checkbutton(categories_grid_frame, text=category, variable=var, 
                                         command=self._update_filtered_skills)
                row = i // max_cols
                col = i % max_cols
                checkbox.grid(row=row, column=col, sticky="w", padx=8, pady=2)
                self.category_vars[category] = var
            
            # Update filtered skills initially
            self._update_filtered_skills()
        
        # Create 4 skill sections
        self._create_skill_sections()
    
    def _update_filtered_skills(self):
        """Update the filtered skills based on selected categories."""
        self.app.selected_categories = {cat for cat, var in self.category_vars.items() if var.get()}
        
        # Filter skills that belong to at least one selected category
        self.app.filtered_skills = {}
        for skill, categories in self.app.skills_data.items():
            if any(cat in self.app.selected_categories for cat in categories):
                self.app.filtered_skills[skill] = categories
        
        # Update skill sections with filtered skills
        if hasattr(self, 'skill_sections'):
            self._update_skill_sections()
    
    def _create_skill_sections(self):
        """Create the 4 skill sections in 2 columns."""
        # Section header spanning both columns
        header_frame = ttk.Frame(self.skills_content_frame)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        ttk.Label(header_frame, text="Configure Skills for Resume", font=("Arial", 12, "bold")).pack()
        
        # Initialize skill sections storage
        self.skill_sections = {}
        
        for i in range(4):
            section_key = f"SKILL_{i+1}"
            
            # Calculate position in 2-column layout
            row = (i // 2) + 1  # Two sections per row, starting from row 1
            col = i % 2         # Alternate between columns 0 and 1
            
            # Create section frame
            section_frame = ttk.LabelFrame(self.skills_content_frame, text=f"Skill Section {i+1}", padding=15)
            section_frame.grid(row=row, column=col, sticky="ew", pady=10, padx=5)
            section_frame.columnconfigure(1, weight=1)
            
            # Custom category name entry
            ttk.Label(section_frame, text="Category Name for Resume:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 10))
            category_name_var = tk.StringVar()
            category_entry = ttk.Entry(section_frame, textvariable=category_name_var, width=30)
            category_entry.grid(row=0, column=1, sticky="w", pady=5)
            
            # Skills selection area
            ttk.Label(section_frame, text="Select Skills:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="nw", padx=(0, 10), pady=(10, 0))
            
            # Scrollable skills frame
            skills_container = ttk.Frame(section_frame)
            skills_container.grid(row=1, column=1, sticky="ew", pady=10)
            skills_container.columnconfigure(0, weight=1)
            
            # Character count and validation
            char_count_label = ttk.Label(section_frame, text="Characters: 0/50", font=("Arial", 9))
            char_count_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=(5, 0))
            
            # Store section data
            self.skill_sections[section_key] = {
                'frame': section_frame,
                'category_name_var': category_name_var,
                'skills_container': skills_container,
                'char_count_label': char_count_label,
                'skill_vars': {},
                'category_entry': category_entry
            }
            
            # Bind category name changes to update character count
            category_name_var.trace_add("write", lambda *args, key=section_key: self._update_section_char_count(key))
        
        # Initial update of skill sections
        self._update_skill_sections()
    
    def _update_skill_sections(self):
        """Update all skill sections with filtered skills."""
        if not hasattr(self, 'skill_sections'):
            return
        
        for section_key, section_data in self.skill_sections.items():
            # Clear existing skills
            for widget in section_data['skills_container'].winfo_children():
                widget.destroy()
            
            section_data['skill_vars'] = {}
            
            if self.app.filtered_skills:
                # Create checkboxes for filtered skills in a grid
                max_cols = 3
                sorted_skills = sorted(self.app.filtered_skills.keys())
                
                for i, skill in enumerate(sorted_skills):
                    var = tk.BooleanVar()
                    checkbox = ttk.Checkbutton(
                        section_data['skills_container'], 
                        text=skill, 
                        variable=var,
                        command=lambda key=section_key: self._update_section_char_count(key)
                    )
                    row = i // max_cols
                    col = i % max_cols
                    checkbox.grid(row=row, column=col, sticky="w", padx=8, pady=2)
                    section_data['skill_vars'][skill] = var
            else:
                # Show message when no categories selected
                msg_label = ttk.Label(
                    section_data['skills_container'], 
                    text="← Select categories above to see available skills",
                    font=("Arial", 9),
                    foreground="gray"
                )
                msg_label.grid(row=0, column=0, sticky="w", pady=10)
            
            # Update character count
            self._update_section_char_count(section_key)
    
    def _update_section_char_count(self, section_key):
        """Update character count for a specific skill section."""
        if section_key not in self.skill_sections:
            return
        
        section_data = self.skill_sections[section_key]
        category_name = section_data['category_name_var'].get().strip()
        selected_skills = [skill for skill, var in section_data['skill_vars'].items() if var.get()]
        
        if category_name and selected_skills:
            formatted = format_skill_for_template(category_name, selected_skills)
            char_count = len(formatted)
            
            # Update label with color coding
            section_data['char_count_label'].config(text=f"Characters: {char_count}/50")
            if char_count > 50:
                section_data['char_count_label'].config(foreground="red")
            elif char_count > 45:
                section_data['char_count_label'].config(foreground="orange")
            else:
                section_data['char_count_label'].config(foreground="green")
        else:
            section_data['char_count_label'].config(text="Characters: 0/50", foreground="black")
    
    def _collect_selected_skills(self):
        """Collect the currently selected skills from the UI."""
        self.app.selected_skills.clear()
        
        if hasattr(self, 'skill_sections'):
            for skill_key, section_data in self.skill_sections.items():
                category_name = section_data['category_name_var'].get().strip()
                selected_skills = [skill for skill, var in section_data['skill_vars'].items() if var.get()]
                
                if category_name and selected_skills:
                    formatted_skill = format_skill_for_template(category_name, selected_skills)
                    # Only add if within character limit
                    if len(formatted_skill) <= 50:
                        self.app.selected_skills[skill_key] = formatted_skill
    
    def validate(self) -> bool:
        """Validate skills selection."""
        # Collect current selections
        self._collect_selected_skills()
        
        # Check if at least one skill section is filled
        if not self.app.selected_skills:
            messagebox.showwarning("No Skills Selected", "Please select at least one skill category.")
            return False
        
        # Check for character limit violations
        for skill_key, skill_text in self.app.selected_skills.items():
            if len(skill_text) > 50:
                messagebox.showerror("Character Limit Exceeded", 
                    f"Skill section {skill_key} exceeds 50 characters ({len(skill_text)}).\n"
                    "Please reduce the number of skills or shorten the category name.")
                return False
        
        return True