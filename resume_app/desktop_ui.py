"""Multi-panel wizard UI for the resume builder using Tkinter."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, Any, Set
import os

from .generator import DEFAULT_COUNTS
from .template_renderer import render_template
from .recommender import recommend_with_matches, extract_skills_from_jd
from .excel_loader import load_skills_sheet
from .skill_recommender import SkillRecommender, format_skill_for_template


class ResumeBuilderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Resume Builder Wizard")
        root.state('zoomed')  # Launch in fullscreen on Windows
        root.minsize(1200, 700)
        
        # Application state
        self.current_panel = 0
        self.excel_path = self._check_default_file(os.getcwd(), 'candidate.xlsx')
        self.template_path = self._check_default_file(os.getcwd(), 'resume.docx')
        self.job_path = None
        self.jd_text = ""
        self.recs: Dict[str, list] = {}
        self.selected_bullets: Dict[str, Set[int]] = {}
        self.role_titles: Dict[str, ttk.Entry] = {}
        self.skills_data: Dict[str, list] = {}
        self.skill_recommendations: list = []
        self.selected_skills: Dict[str, str] = {}
        # New refactored skill selection variables
        self.selected_categories: Set[str] = set()  # Categories selected by user
        self.filtered_skills: Dict[str, list] = {}  # Skills filtered by selected categories
        self.skill_sections: Dict[str, Dict] = {}  # Store data for each of 4 skill sections
        
        # Selection requirements (role -> count)
        self.selection_requirements = {
            "Nodelink": 5,
            "MAMM": 5, 
            "FactCheckAI": 2,
            "Medical Classifier": 1
        }
        
        self._build_ui()
    
    def _check_default_file(self, directory: str, filename: str):
        """Check if default file exists and return path or None."""
        path = os.path.join(directory, filename)
        return path if os.path.exists(path) else None

    def _bind_mouse_wheel(self, widget, canvas):
        """Bind mouse wheel scrolling to a widget and its canvas."""
        def _on_mousewheel(event):
            # Only scroll if the canvas has a scrollable region
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        # Bind to the widget and all its children recursively
        def bind_to_widget(w):
            w.bind("<MouseWheel>", _on_mousewheel)
            for child in w.winfo_children():
                bind_to_widget(child)
        
        bind_to_widget(widget)
        # Also bind to the canvas itself
        canvas.bind("<MouseWheel>", _on_mousewheel)

    def _build_ui(self):
        """Build the main UI with notebook for panels."""
        # Main container
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure root grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Create notebook for panels
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky="nsew")
        
        # Create panels
        self.panel1 = self._create_file_selection_panel()
        self.panel2 = self._create_recommendations_panel()
        self.panel3 = self._create_skills_selection_panel()
        self.panel4 = self._create_review_panel()
        
        # Add panels to notebook
        self.notebook.add(self.panel1, text="1. File Selection")
        self.notebook.add(self.panel2, text="2. Select Bullets")
        self.notebook.add(self.panel3, text="3. Select Skills")
        self.notebook.add(self.panel4, text="4. Review & Generate")
        
        # Disable tab switching (force wizard flow)
        self.notebook.bind("<Button-1>", self._prevent_tab_click)
        
        # Add keyboard shortcuts
        self.root.bind("<Control-Right>", lambda e: self._go_next())
        self.root.bind("<Control-Left>", lambda e: self._go_back())
        self.root.bind("<F1>", self._show_help)
        
        # Navigation frame with improved styling
        nav_frame = ttk.Frame(main_frame)
        nav_frame.grid(row=1, column=0, sticky="ew", pady=(15, 0))
        nav_frame.columnconfigure(1, weight=1)
        
        self.back_btn = ttk.Button(nav_frame, text="← Back", command=self._go_back, state="disabled")
        self.back_btn.grid(row=0, column=0, padx=(0, 10))
        
        # Add help info in the middle
        help_label = ttk.Label(nav_frame, text="Use Ctrl+← Ctrl+→ to navigate or F1 for help", 
                              font=("Arial", 8), foreground="gray")
        help_label.grid(row=0, column=1, padx=10)
        
        self.next_btn = ttk.Button(nav_frame, text="Next →", command=self._go_next)
        self.next_btn.grid(row=0, column=2, padx=(10, 0))
        
        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=2, column=0, sticky="ew", pady=(5, 0))
        status_frame.columnconfigure(1, weight=1)
        
        self.status_label = ttk.Label(status_frame, text="Step 1 of 4: File Selection", 
                                     font=("Arial", 9), foreground="blue")
        self.status_label.grid(row=0, column=0, sticky="w")
        
        self.progress_label = ttk.Label(status_frame, text="Ready to begin", 
                                       font=("Arial", 9), foreground="green")
        self.progress_label.grid(row=0, column=1, sticky="e")
        
        # Initialize navigation state
        self._update_navigation()
    
    def _show_help(self, event=None):
        """Show help dialog."""
        help_text = """Resume Builder Help

Navigation:
• Ctrl+← : Go to previous step
• Ctrl+→ : Go to next step
• F1 : Show this help

Steps:
1. File Selection: Choose your Excel file, Word template, and enter job description
2. Select Bullets: Choose the best bullet points for each role
3. Select Skills: Pick skills and categories (max 50 characters each)
4. Review & Generate: Review selections and create your resume

Tips:
• Skills are automatically recommended based on your job description
• Character counts are shown to keep within resume limits
• Mouse wheel scrolling works anywhere in scrollable areas"""
        
        messagebox.showinfo("Help", help_text)
    
    def _prevent_tab_click(self, event):
        """Prevent manual tab switching."""
        return "break"
    
    def _create_file_selection_panel(self) -> ttk.Frame:
        """Create the file selection panel."""
        panel = ttk.Frame(self.notebook, padding=20)
        
        # Title
        title_label = ttk.Label(panel, text="Resume Builder Setup", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 30))
        
        # Instructions
        instruction_text = "Select your files to begin generating your tailored resume:"
        instruction_label = ttk.Label(panel, text=instruction_text, font=("Arial", 10))
        instruction_label.grid(row=1, column=0, columnspan=3, pady=(0, 20))
        
        # File selection section
        file_frame = ttk.LabelFrame(panel, text="Required Files", padding=15)
        file_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=10)
        file_frame.columnconfigure(1, weight=1)
        
        # Excel file
        ttk.Label(file_frame, text="Candidate Data (Excel):").grid(row=0, column=0, sticky="w", pady=5)
        self.excel_label = ttk.Label(file_frame, text=os.path.basename(self.excel_path) if self.excel_path else "(none selected)")
        self.excel_label.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=5)
        ttk.Button(file_frame, text="Browse...", command=self._select_excel).grid(row=0, column=2, padx=(10, 0), pady=5)
        
        # Template file
        ttk.Label(file_frame, text="Word Template:").grid(row=1, column=0, sticky="w", pady=5)
        self.template_label = ttk.Label(file_frame, text=os.path.basename(self.template_path) if self.template_path else "(none selected)")
        self.template_label.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=5)
        ttk.Button(file_frame, text="Browse...", command=self._select_template).grid(row=1, column=2, padx=(10, 0), pady=5)
        
        # Job description section
        jd_frame = ttk.LabelFrame(panel, text="Job Description", padding=15)
        jd_frame.grid(row=3, column=0, columnspan=3, sticky="nsew", pady=10)
        jd_frame.columnconfigure(0, weight=1)
        jd_frame.rowconfigure(1, weight=1)
        
        ttk.Label(jd_frame, text="Paste the job description below:").grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        # Text widget with scrollbar
        text_frame = ttk.Frame(jd_frame)
        text_frame.grid(row=1, column=0, sticky="nsew")
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        self.jd_text_widget = tk.Text(text_frame, height=10, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.jd_text_widget.yview)
        self.jd_text_widget.configure(yscrollcommand=scrollbar.set)
        
        self.jd_text_widget.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Enable mouse wheel scrolling for text widget
        def text_mousewheel(event):
            self.jd_text_widget.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.jd_text_widget.bind("<MouseWheel>", text_mousewheel)
        
        # Configure panel grid weights
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(3, weight=1)
        
        return panel
    
    def _create_recommendations_panel(self) -> ttk.Frame:
        """Create the recommendations panel."""
        panel = ttk.Frame(self.notebook, padding=10)
        panel.columnconfigure(0, weight=7)  # Much more space for bullets
        panel.columnconfigure(1, weight=3)   # Minimal space for job description
        panel.rowconfigure(0, weight=1)
        
        # Left side - bullet recommendations
        left_frame = ttk.Frame(panel)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)
        
        # Title and instructions
        title_label = ttk.Label(left_frame, text="Select Your Best Bullet Points", font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 10), sticky="w")
        
        instruction_text = f"Required selections: {self.selection_requirements['Nodelink']} Nodelink, {self.selection_requirements['MAMM']} MAMM, {self.selection_requirements['FactCheckAI']} FactCheckAI, {self.selection_requirements['Medical Classifier']} Medical"
        instruction_label = ttk.Label(left_frame, text=instruction_text, font=("Arial", 9), foreground="blue")
        instruction_label.grid(row=0, column=0, pady=(20, 5), sticky="w")
        
        # Line count status
        self.line_count_label = ttk.Label(left_frame, text="Total Lines: 0/21", font=("Arial", 10, "bold"))
        self.line_count_label.grid(row=0, column=0, pady=(45, 10), sticky="w")
        
        # Scrollable frame for recommendations
        self.recs_canvas = tk.Canvas(left_frame)
        recs_scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=self.recs_canvas.yview)
        self.recs_canvas.configure(yscrollcommand=recs_scrollbar.set)
        
        self.recs_frame = ttk.Frame(self.recs_canvas)
        self.recs_canvas.create_window((0, 0), window=self.recs_frame, anchor="nw")
        
        self.recs_canvas.grid(row=1, column=0, sticky="nsew")
        recs_scrollbar.grid(row=1, column=1, sticky="ns")
        
        self.recs_frame.bind('<Configure>', lambda e: self.recs_canvas.configure(scrollregion=self.recs_canvas.bbox('all')))
        
        # Enable mouse wheel scrolling for recommendations
        self._bind_mouse_wheel(self.recs_frame, self.recs_canvas)
        
        # Right side - job description
        right_frame = ttk.LabelFrame(panel, text="Job Description", padding=10)
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        
        self.jd_display = tk.Text(right_frame, wrap=tk.WORD, state="disabled", width=15, height=10)
        self.jd_display.configure(font=("Arial", 8))  # Smaller font to fit more in less space
        jd_scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=self.jd_display.yview)
        self.jd_display.configure(yscrollcommand=jd_scrollbar.set)
        
        self.jd_display.grid(row=0, column=0, sticky="nsew", ipadx=0, ipady=0)
        jd_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Enable mouse wheel scrolling for job description display
        def jd_mousewheel(event):
            self.jd_display.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.jd_display.bind("<MouseWheel>", jd_mousewheel)
        
        return panel
    
    def _load_recommendations(self):
        """Load and display bullet recommendations."""
        try:
            # Clear previous recommendations
            for child in self.recs_frame.winfo_children():
                child.destroy()
            
            # Initialize selected bullets dict
            for role in self.selection_requirements.keys():
                self.selected_bullets[role] = set()
            
            # Load candidate data and compute recommendations
            if not self.excel_path:
                return
                
            from .excel_loader import load_candidate_sheet
            candidate = load_candidate_sheet(self.excel_path)
            bullets_by_role = candidate.get("bullets", {}) if isinstance(candidate, dict) else {}
            
            self.recs = {}
            for role in self.selection_requirements.keys():
                bullets = bullets_by_role.get(role, [])
                if not bullets:
                    continue
                scored = recommend_with_matches(bullets, self.jd_text, top_n=len(bullets))
                self.recs[role] = [{**b, "score": s, "matches": m} for (b, s, m) in scored]
            
            # Display recommendations for each role
            self._display_role_recommendations()
            
            # Display job description in right panel
            self.jd_display.config(state="normal")
            self.jd_display.delete("1.0", tk.END)
            self.jd_display.insert("1.0", self.jd_text)
            self.jd_display.config(state="disabled")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load recommendations: {e}")
    
    def _display_role_recommendations(self):
        """Display recommendations for all roles."""
        for role, items in self.recs.items():
            if not items:
                continue
                
            # Role frame with enhanced styling and more prominent separation
            role_frame = ttk.LabelFrame(self.recs_frame, text="", padding=20, relief="solid", borderwidth=2)
            role_frame.pack(fill="x", padx=10, pady=15)
            role_frame.columnconfigure(0, weight=1)
            
            # Add prominent role title
            role_title = ttk.Label(role_frame, text=f"{role}", font=("Arial", 16, "bold"), foreground="darkblue")
            role_title.grid(row=0, column=0, sticky="w", pady=(0, 5))
            
            # Add selection requirement subtitle
            requirement_label = ttk.Label(role_frame, text=f"Select {self.selection_requirements[role]} bullet points", 
                                        font=("Arial", 10, "italic"), foreground="gray")
            requirement_label.grid(row=1, column=0, sticky="w", pady=(0, 15))
            
            # Pre-select first x bullets for each role
            required_count = self.selection_requirements[role]
            
            # Create bullet checkboxes (starting from row 2 after title and subtitle)
            for idx, item in enumerate(items):
                # Enhanced bullet frame with border
                bullet_frame = ttk.Frame(role_frame, relief="solid", borderwidth=1)
                bullet_frame.grid(row=idx+2, column=0, sticky="ew", pady=3, padx=2)
                bullet_frame.columnconfigure(2, weight=1)
                
                # Checkbox - pre-select first required bullets
                var = tk.BooleanVar(value=(idx < required_count))
                checkbox = ttk.Checkbutton(bullet_frame, variable=var, 
                    command=lambda r=role, i=idx, v=var: self._on_bullet_selection(r, i, v))
                checkbox.grid(row=0, column=0, sticky="w", padx=(5, 0), pady=5)
                
                # Pre-select the bullet
                if idx < required_count:
                    self.selected_bullets.setdefault(role, set()).add(idx)
                
                # Score and lines info
                score = item.get("score", 0)
                lines = item.get("lines", "?")
                info_text = f"[Score: {score:.0f}, Lines: {lines}]"
                info_label = ttk.Label(bullet_frame, text=info_text, font=("Arial", 8, "bold"), foreground="darkblue")
                info_label.grid(row=0, column=1, sticky="w", padx=(10, 5), pady=5)
                
                # Bullet text with better styling
                bullet_text = item.get("bullet", "")
                bullet_label = ttk.Label(bullet_frame, text=bullet_text, wraplength=900, justify="left", 
                                       font=("Arial", 9), background="white", relief="flat", padding=5)
                bullet_label.grid(row=1, column=0, columnspan=3, sticky="ew", padx=5, pady=(0, 5))
                
                # Color coding based on score
                self._apply_bullet_color_coding(bullet_label, score, items)
        
        # Update line count after pre-selection
        self._update_line_count()
    
    def _apply_bullet_color_coding(self, label, score, all_items):
        """Apply color coding to bullet based on score."""
        scores = [item.get("score", 0) for item in all_items]
        max_score = max(scores) if scores else 1
        min_score = min(scores) if scores else 0
        
        if max_score == min_score:
            frac = 1.0
        else:
            frac = (score - min_score) / (max_score - min_score)
        
        # Color gradient: high score = green, low score = red
        if frac > 0.7:
            color = "#2d5a2d"  # Dark green
        elif frac > 0.4:
            color = "#5a5a2d"  # Yellow-green
        else:
            color = "#5a2d2d"  # Dark red
            
        label.config(foreground=color)
    
    def _on_bullet_selection(self, role: str, bullet_idx: int, var: tk.BooleanVar):
        """Handle bullet selection/deselection."""
        required_count = self.selection_requirements[role]
        selected_set = self.selected_bullets[role]
        
        if var.get():  # Selected
            if len(selected_set) >= required_count:
                # Too many selected, deselect this one
                var.set(False)
                messagebox.showwarning("Selection Limit", f"You can only select {required_count} bullets for {role}")
            else:
                selected_set.add(bullet_idx)
        else:  # Deselected
            selected_set.discard(bullet_idx)
        
        # Update line count display
        self._update_line_count()
    
    def _update_line_count(self):
        """Update the total line count display."""
        total_lines = 0
        
        for role, selected_indices in self.selected_bullets.items():
            bullets = self.recs.get(role, [])
            for idx in selected_indices:
                if idx < len(bullets):
                    lines = bullets[idx].get("lines", 0)
                    if isinstance(lines, (int, float)):
                        total_lines += int(lines)
        
        # Update label with color coding
        self.line_count_label.config(text=f"Total Lines: {total_lines}/21")
        
        if total_lines == 21:
            self.line_count_label.config(foreground="green")
        elif total_lines > 21:
            self.line_count_label.config(foreground="red")
        else:
            self.line_count_label.config(foreground="orange")
    
    def _create_skills_selection_panel(self) -> ttk.Frame:
        """Create the refactored skills selection panel."""
        panel = ttk.Frame(self.notebook, padding=20)
        panel.columnconfigure(0, weight=7)  # Skills area takes much more space
        panel.columnconfigure(1, weight=2)   # Minimal job description area
        panel.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(panel, text="Select Skills", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 20))
        
        # Left side: Skills selection
        skills_main_frame = ttk.LabelFrame(panel, text="Skills Selection", padding=15)
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
        self._bind_mouse_wheel(self.skills_content_frame, skills_canvas)
        
        # Right side: Job description
        jd_frame = ttk.LabelFrame(panel, text="Job Description Reference", padding=15)
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
        
        return panel
    
    def _populate_skills_panel(self):
        """Populate the new refactored skills panel."""
        # Populate job description text
        if hasattr(self, 'skills_jd_text'):
            self.skills_jd_text.config(state="normal")
            self.skills_jd_text.delete("1.0", tk.END)
            self.skills_jd_text.insert("1.0", self.jd_text)
            self.skills_jd_text.config(state="disabled")
        
        # Clear existing content
        for widget in self.categories_frame.winfo_children():
            widget.destroy()
        for widget in self.skills_content_frame.winfo_children():
            widget.destroy()
        
        # Populate category selection checkboxes
        if self.skills_data:
            all_categories = set()
            for skill_categories in self.skills_data.values():
                all_categories.update(skill_categories)
            all_categories = sorted(list(all_categories))
            
            ttk.Label(self.categories_frame, text="Select relevant categories:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 10))
            
            # Create category checkboxes in a 5-column grid
            categories_grid_frame = ttk.Frame(self.categories_frame)
            categories_grid_frame.pack(fill="x")
            
            self.category_vars = {}
            max_cols = 8  # Changed to 8 columns
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
        self.selected_categories = {cat for cat, var in self.category_vars.items() if var.get()}
        
        # Filter skills that belong to at least one selected category
        self.filtered_skills = {}
        for skill, categories in self.skills_data.items():
            if any(cat in self.selected_categories for cat in categories):
                self.filtered_skills[skill] = categories
        
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
            
            if self.filtered_skills:
                # Create checkboxes for filtered skills in a grid
                max_cols = 3
                sorted_skills = sorted(self.filtered_skills.keys())
                
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
            from .skill_recommender import format_skill_for_template
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
    
    def _create_review_panel(self) -> ttk.Frame:
        """Create the review panel."""
        panel = ttk.Frame(self.notebook, padding=20)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(panel, text="Review & Generate Resume", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 20), sticky="ew")
        
        # Scrollable review area - takes full width
        review_container = ttk.Frame(panel)
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
        self._bind_mouse_wheel(self.review_frame, review_canvas)
        
        # Generate button
        generate_frame = ttk.Frame(panel)
        generate_frame.grid(row=2, column=0, pady=(20, 0))
        
        self.generate_btn = ttk.Button(generate_frame, text="Generate Resume", command=self._generate_resume)
        self.generate_btn.pack()
        
        return panel
    
    def _load_skills(self):
        """Load skills data and generate recommendations."""
        try:
            # Ensure we have an excel path
            if not self.excel_path:
                raise ValueError("No Excel file selected")
            
            # Load skills data from Excel
            self.skills_data = load_skills_sheet(self.excel_path)
            
            if self.skills_data:
                # Generate skill recommendations
                skill_recommender = SkillRecommender(self.skills_data)
                self.skill_recommendations = skill_recommender.recommend_skills(self.jd_text, num_categories=4)
            else:
                self.skill_recommendations = []
                
            # Populate the skills panel
            self._populate_skills_panel()
            
        except Exception as e:
            error_msg = str(e)
            print(f"ERROR in _load_skills: {error_msg}")
            print(f"Exception type: {type(e)}")
            print(f"Excel path was: {self.excel_path}")
            
            if "Skills sheet not found" in error_msg:
                messagebox.showwarning("Skills Sheet Missing", 
                    f"Your Excel file doesn't contain a 'Skills' sheet.\n\n{error_msg}\n\n"
                    "You can still continue without skills recommendations.")
            else:
                messagebox.showwarning("Skills Warning", f"Could not load skills: {error_msg}")
            self.skill_recommendations = []
            self._populate_skills_panel()
    
    def _format_skill_with_limit(self, category, skills, limit=50):
        """Format skills and check character limit without truncation."""
        if not skills:
            return ""
        
        # Use the format_skill_for_template function from skill_recommender
        from .skill_recommender import format_skill_for_template
        formatted = format_skill_for_template(category, skills)
        
        return formatted
    
    def _collect_selected_skills(self):
        """Collect the currently selected skills from the new refactored UI."""
        self.selected_skills.clear()
        
        if hasattr(self, 'skill_sections'):
            for skill_key, section_data in self.skill_sections.items():
                category_name = section_data['category_name_var'].get().strip()
                selected_skills = [skill for skill, var in section_data['skill_vars'].items() if var.get()]
                
                if category_name and selected_skills:
                    from .skill_recommender import format_skill_for_template
                    formatted_skill = format_skill_for_template(category_name, selected_skills)
                    # Only add if within character limit
                    if len(formatted_skill) <= 50:
                        self.selected_skills[skill_key] = formatted_skill
    
    def _load_review(self):
        """Load and display selected bullets and skills for review in two columns."""
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
        total_bullets = sum(len(self.selected_bullets.get(role, set())) for role in self.selection_requirements.keys())
        total_lines = 0
        for role, selected_indices in self.selected_bullets.items():
            bullets = self.recs.get(role, [])
            for idx in selected_indices:
                if idx < len(bullets):
                    lines = bullets[idx].get("lines", 0)
                    if isinstance(lines, (int, float)):
                        total_lines += int(lines)
        
        total_skills = len([skill for skill in self.selected_skills.values() if skill.strip()])
        
        stats_text = f"Total Bullet Points: {total_bullets} | Total Lines: {total_lines} | Skills Categories: {total_skills}"
        ttk.Label(stats_frame, text=stats_text, font=("Arial", 12, "bold"), foreground="darkgreen").pack()
        
        # Left Column: Bullet Points Section
        bullets_section = ttk.LabelFrame(main_container, text="Selected Bullet Points", padding=15)
        bullets_section.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(0, 20))
        bullets_section.columnconfigure(0, weight=1)
        
        # Roles that need titles
        title_roles = ["Nodelink", "MAMM"]
        
        for role in self.selection_requirements.keys():
            selected_indices = self.selected_bullets.get(role, set())
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
                self.role_titles[role] = title_entry
            
            # Selected bullets
            ttk.Label(role_frame, text="Selected Bullets:", font=("Arial", 10, "bold")).grid(
                row=1 if role in title_roles else 0, column=0, columnspan=2, sticky="w", pady=(10, 5))
            
            bullets = self.recs.get(role, [])
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
        
        if self.selected_skills:
            skills_container = ttk.Frame(skills_section)
            skills_container.pack(fill="x")
            skills_container.columnconfigure(0, weight=1)
            
            row = 0
            for skill_key, skill_value in self.selected_skills.items():
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
    
    def _generate_resume(self):
        """Generate the final resume."""
        if not self.template_path:
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
            
            render_template(self.template_path, template_data, out_path)
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
        
        for role in self.selection_requirements.keys():
            template_prefix = role_mapping.get(role, role.upper().replace(' ', '').replace('-', ''))
            selected_indices = self.selected_bullets.get(role, set())
            
            # Add title if applicable
            if role in ["Nodelink", "MAMM"] and role in self.role_titles:
                title_entry = self.role_titles[role]
                title = title_entry.get().strip() if hasattr(title_entry, 'get') else ""
                template_data[f"{template_prefix}_TITLE"] = title
            else:
                template_data[f"{template_prefix}_TITLE"] = ""
            
            # Add selected bullets
            bullets = self.recs.get(role, [])
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
        for skill_key, skill_value in self.selected_skills.items():
            template_data[skill_key] = skill_value
        
        # Ensure all skill placeholders are filled
        for i in range(1, 5):
            skill_key = f"SKILL_{i}"
            if skill_key not in template_data:
                template_data[skill_key] = ""
        
        return template_data
    
    def _select_excel(self):
        """Select Excel file."""
        path = filedialog.askopenfilename(
            title="Select Candidate Excel File",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if path:
            self.excel_path = path
            self.excel_label.config(text=os.path.basename(path))
    
    def _select_template(self):
        """Select Word template file."""
        path = filedialog.askopenfilename(
            title="Select Word Template",
            filetypes=[("Word documents", "*.docx"), ("All files", "*.*")]
        )
        if path:
            self.template_path = path
            self.template_label.config(text=os.path.basename(path))
    
    def _go_back(self):
        """Go to previous panel."""
        if self.current_panel > 0:
            self.current_panel -= 1
            self.notebook.select(self.current_panel)
            self._update_navigation()
    
    def _go_next(self):
        """Go to next panel."""
        if self._validate_current_panel():
            if self.current_panel == 0:
                # Moving from file selection to recommendations
                self._load_recommendations()
            elif self.current_panel == 1:
                # Moving from recommendations to skills
                self._load_skills()
            elif self.current_panel == 2:
                # Moving from skills to review
                self._load_review()
            
            self.current_panel += 1
            self.notebook.select(self.current_panel)
            self._update_navigation()
    
    def _update_navigation(self):
        """Update navigation button states and status bar."""
        self.back_btn.config(state="normal" if self.current_panel > 0 else "disabled")
        
        # Update status bar
        step_names = ["File Selection", "Select Bullets", "Select Skills", "Review & Generate"]
        status_messages = [
            "Choose your files and enter job description",
            "Select the best bullet points for each role", 
            "Choose skills and categories for your resume",
            "Review your selections and generate resume"
        ]
        
        if self.current_panel < len(step_names):
            self.status_label.config(text=f"Step {self.current_panel + 1} of {len(step_names)}: {step_names[self.current_panel]}")
            self.progress_label.config(text=status_messages[self.current_panel])
        
        if self.current_panel < 3:
            self.next_btn.config(text="Next →", state="normal")
        else:
            self.next_btn.config(text="Generate Resume", state="normal")
    
    def _validate_current_panel(self) -> bool:
        """Validate current panel before proceeding."""
        if self.current_panel == 0:
            # Validate file selection
            if not self.excel_path:
                messagebox.showerror("Error", "Please select an Excel file.")
                return False
            if not self.template_path:
                messagebox.showerror("Error", "Please select a Word template.")
                return False
            
            self.jd_text = self.jd_text_widget.get("1.0", tk.END).strip()
            if not self.jd_text:
                messagebox.showerror("Error", "Please enter a job description.")
                return False
            
            return True
            
        elif self.current_panel == 1:
            # Validate bullet selection
            return self._validate_selections()
        
        elif self.current_panel == 2:
            # Validate skill selection - ensure no skill exceeds 50 characters
            self._collect_selected_skills()
            
            # Check if any skill exceeds 50 characters
            for skill_key, widget_data in getattr(self, 'skill_widgets', {}).items():
                custom_category = widget_data.get('new_category_var', tk.StringVar()).get().strip()
                dropdown_category = widget_data.get('category_var', tk.StringVar()).get().strip()
                category = custom_category if custom_category and custom_category != "Enter custom category..." else dropdown_category
                
                if category:
                    selected_skills = [skill for skill, var in widget_data.get('skill_vars', {}).items() if var.get()]
                    if selected_skills:
                        from .skill_recommender import format_skill_for_template
                        formatted = format_skill_for_template(category, selected_skills)
                        if len(formatted) > 50:
                            messagebox.showerror("Skill Character Limit", 
                                f"Skill category '{category}' exceeds 50 characters ({len(formatted)} chars). "
                                f"Please remove some skills or shorten the category name.")
                            return False
            
            return True
        
        return True
    
    def _validate_selections(self) -> bool:
        """Validate that required number of bullets are selected and total lines is exactly 21."""
        # Check bullet count requirements
        for role, required_count in self.selection_requirements.items():
            selected_count = len(self.selected_bullets.get(role, set()))
            if selected_count != required_count:
                messagebox.showerror(
                    "Selection Error", 
                    f"Please select exactly {required_count} bullet(s) for {role}. Currently selected: {selected_count}"
                )
                return False
        
        # Check total line count requirement
        total_lines = 0
        for role, selected_indices in self.selected_bullets.items():
            bullets = self.recs.get(role, [])
            for idx in selected_indices:
                if idx < len(bullets):
                    lines = bullets[idx].get("lines", 0)
                    if isinstance(lines, (int, float)):
                        total_lines += int(lines)
        
        if total_lines != 21:
            messagebox.showerror(
                "Line Count Error", 
                f"Total lines must be exactly 21. Currently selected: {total_lines} lines.\n"
                f"Please adjust your bullet point selections to reach exactly 21 lines."
            )
            return False
        
        return True


def run_app():
    root = tk.Tk()
    app = ResumeBuilderApp(root)
    root.mainloop()


if __name__ == "__main__":
    run_app()