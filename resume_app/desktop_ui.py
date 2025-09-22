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
        root.geometry("1400x800")
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
        panel.columnconfigure(0, weight=3)  # More space for bullets
        panel.columnconfigure(1, weight=1)  # Less space for job description
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
        instruction_label.grid(row=0, column=0, pady=(20, 10), sticky="w")
        
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
        
        self.jd_display = tk.Text(right_frame, wrap=tk.WORD, state="disabled")
        jd_scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=self.jd_display.yview)
        self.jd_display.configure(yscrollcommand=jd_scrollbar.set)
        
        self.jd_display.grid(row=0, column=0, sticky="nsew")
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
                
            # Role frame
            role_frame = ttk.LabelFrame(self.recs_frame, text=f"{role} (Select {self.selection_requirements[role]})", padding=10)
            role_frame.pack(fill="x", padx=5, pady=5)
            role_frame.columnconfigure(0, weight=1)
            
            # Create bullet checkboxes
            for idx, item in enumerate(items):
                bullet_frame = ttk.Frame(role_frame)
                bullet_frame.grid(row=idx, column=0, sticky="ew", pady=2)
                bullet_frame.columnconfigure(1, weight=1)  # Allow text to expand
                
                # Checkbox
                var = tk.BooleanVar()
                checkbox = ttk.Checkbutton(bullet_frame, variable=var, 
                    command=lambda r=role, i=idx, v=var: self._on_bullet_selection(r, i, v))
                checkbox.grid(row=0, column=0, sticky="w")
                
                # Score and lines info
                score = item.get("score", 0)
                lines = item.get("lines", "?")
                info_text = f"[Score: {score:.0f}, Lines: {lines}]"
                info_label = ttk.Label(bullet_frame, text=info_text, font=("Arial", 8), foreground="gray")
                info_label.grid(row=0, column=1, sticky="w", padx=(5, 0))
                
                # Bullet text - make it fully visible with proper wrapping
                bullet_text = item.get("bullet", "")
                bullet_label = ttk.Label(bullet_frame, text=bullet_text, wraplength=800, justify="left")
                bullet_label.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(20, 0), pady=(2, 5))
                
                # Color coding based on score
                self._apply_bullet_color_coding(bullet_label, score, items)
    
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
    
    def _create_skills_selection_panel(self) -> ttk.Frame:
        """Create the skills selection panel."""
        panel = ttk.Frame(self.notebook, padding=20)
        panel.columnconfigure(0, weight=3)  # Skills area takes more space
        panel.columnconfigure(1, weight=2)  # Job description area
        panel.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(panel, text="Select Skills", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 20))
        
        # Left side: Skills selection with better layout
        skills_main_frame = ttk.LabelFrame(panel, text="Skills Selection", padding=15)
        skills_main_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 15))
        skills_main_frame.columnconfigure(0, weight=1)
        skills_main_frame.rowconfigure(2, weight=1)  # Make skills area expandable
        
        # Instructions (fixed at top)
        instruction_text = ("Select categories and skills for your resume. Each skill line must be under 50 characters total.\n"
                          "Choose from existing categories or create new ones.")
        instruction_label = ttk.Label(skills_main_frame, text=instruction_text, font=("Arial", 10), wraplength=500)
        instruction_label.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        
        # Load skills button (fixed)
        load_skills_btn = ttk.Button(skills_main_frame, text="Load Recommended Skills", command=self._load_skills)
        load_skills_btn.grid(row=1, column=0, sticky="w", pady=(0, 15))
        
        # Skills content area - with scrolling capability when needed
        skills_outer_frame = ttk.Frame(skills_main_frame)
        skills_outer_frame.grid(row=2, column=0, sticky="nsew")
        skills_outer_frame.columnconfigure(0, weight=1)
        skills_outer_frame.rowconfigure(0, weight=1)
        
        # Canvas and scrollbar for when content is too tall
        skills_canvas = tk.Canvas(skills_outer_frame)
        skills_scrollbar = ttk.Scrollbar(skills_outer_frame, orient="vertical", command=skills_canvas.yview)
        skills_canvas.configure(yscrollcommand=skills_scrollbar.set)
        
        self.skills_content_frame = ttk.Frame(skills_canvas)
        self.skills_content_frame.columnconfigure(0, weight=1)
        
        # Bind scrolling configuration
        self.skills_content_frame.bind('<Configure>', 
                                     lambda e: skills_canvas.configure(scrollregion=skills_canvas.bbox('all')))
        
        skills_canvas.create_window((0, 0), window=self.skills_content_frame, anchor="nw")
        skills_canvas.grid(row=0, column=0, sticky="nsew")
        skills_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Enable mouse wheel scrolling for skills
        self._bind_mouse_wheel(self.skills_content_frame, skills_canvas)
        
        # Right side: Job description with improved layout
        jd_frame = ttk.LabelFrame(panel, text="Job Description Reference", padding=15)
        jd_frame.grid(row=1, column=1, sticky="nsew")
        jd_frame.columnconfigure(0, weight=1)
        jd_frame.rowconfigure(1, weight=1)
        
        jd_label = ttk.Label(jd_frame, text="Use this as reference for skill selection:", font=("Arial", 10, "bold"))
        jd_label.grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        # Job description text area (read-only) with better sizing
        jd_text_frame = ttk.Frame(jd_frame)
        jd_text_frame.grid(row=1, column=0, sticky="nsew")
        jd_text_frame.columnconfigure(0, weight=1)
        jd_text_frame.rowconfigure(0, weight=1)
        
        self.skills_jd_text = tk.Text(jd_text_frame, wrap=tk.WORD, state="disabled", font=("Arial", 9))
        jd_scrollbar = ttk.Scrollbar(jd_text_frame, orient="vertical", command=self.skills_jd_text.yview)
        self.skills_jd_text.configure(yscrollcommand=jd_scrollbar.set)
        
        self.skills_jd_text.grid(row=0, column=0, sticky="nsew")
        jd_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Enable mouse wheel scrolling for skills job description
        def skills_jd_mousewheel(event):
            self.skills_jd_text.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.skills_jd_text.bind("<MouseWheel>", skills_jd_mousewheel)
        
        return panel
    
    def _populate_skills_panel(self):
        """Populate the skills panel with recommendations."""
        # Clear existing content
        for widget in self.skills_content_frame.winfo_children():
            widget.destroy()
        
        # Populate job description text
        if hasattr(self, 'skills_jd_text'):
            self.skills_jd_text.config(state="normal")
            self.skills_jd_text.delete("1.0", tk.END)
            self.skills_jd_text.insert("1.0", self.jd_text)
            self.skills_jd_text.config(state="disabled")
        
        if not self.skill_recommendations:
            # Show message if no recommendations
            no_skills_label = ttk.Label(
                self.skills_content_frame,
                text="No skill recommendations available. Make sure your Excel file has a 'Skills' sheet.",
                font=("Arial", 12)
            )
            no_skills_label.grid(row=0, column=0, pady=20)
            return
        
        # Get all unique categories from skills data
        all_categories = set()
        for skill_categories in self.skills_data.values():
            all_categories.update(skill_categories)
        all_categories = sorted(list(all_categories))
        
        # Create skill selection widgets
        self.skill_widgets = {}
        
        for i in range(4):  # Always create 4 skill slots
            # Create frame for this skill category
            skill_frame = ttk.LabelFrame(
                self.skills_content_frame,
                text=f"SKILL_{i+1}",
                padding=15
            )
            skill_frame.grid(row=i, column=0, sticky="ew", pady=10, padx=5)
            skill_frame.columnconfigure(1, weight=1)
            
            # Get recommended category and skills (if available)
            if i < len(self.skill_recommendations):
                rec_category, rec_skills = self.skill_recommendations[i]
            else:
                rec_category, rec_skills = ("", [])
            
            # Category selection with dropdown and custom entry
            ttk.Label(skill_frame, text="Category:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 10))
            
            category_frame = ttk.Frame(skill_frame)
            category_frame.grid(row=0, column=1, sticky="ew", pady=2)
            category_frame.columnconfigure(1, weight=1)
            
            # Dropdown for existing categories with improved styling
            category_var = tk.StringVar(value=rec_category)
            category_combo = ttk.Combobox(category_frame, textvariable=category_var, values=all_categories, width=25, state="readonly")
            category_combo.grid(row=0, column=0, sticky="w", padx=(0, 10))
            
            # "Or create new" entry with better prompt
            ttk.Label(category_frame, text="or create new:").grid(row=0, column=1, sticky="w", padx=(0, 5))
            new_category_var = tk.StringVar()
            new_category_entry = ttk.Entry(category_frame, textvariable=new_category_var, width=20, 
                                         font=("Arial", 9))
            new_category_entry.grid(row=0, column=2, sticky="w")
            
            # Add placeholder text behavior
            def on_focus_in(event, entry=new_category_entry):
                if entry.get() == "Enter custom category...":
                    entry.delete(0, tk.END)
                    entry.config(foreground="black")
            
            def on_focus_out(event, entry=new_category_entry):
                if not entry.get():
                    entry.insert(0, "Enter custom category...")
                    entry.config(foreground="gray")
            
            new_category_entry.bind("<FocusIn>", on_focus_in)
            new_category_entry.bind("<FocusOut>", on_focus_out)
            new_category_entry.insert(0, "Enter custom category...")
            new_category_entry.config(foreground="gray")
            
            # Skills selection
            ttk.Label(skill_frame, text="Skills:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(15, 5))
            
            # Get all available skills
            all_skills = sorted(list(self.skills_data.keys()))
            
            # Skills selection frame - simplified layout without nested scrolling
            skills_display_frame = ttk.Frame(skill_frame)
            skills_display_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
            skills_display_frame.columnconfigure(0, weight=1)
            
            # Create checkboxes for skills in a compact grid (max 4 columns)
            skill_vars = {}
            max_cols = 4
            for j, skill in enumerate(all_skills):
                var = tk.BooleanVar(value=skill in rec_skills)
                checkbox = ttk.Checkbutton(skills_display_frame, text=skill, variable=var)
                row = j // max_cols
                col = j % max_cols
                checkbox.grid(row=row, column=col, sticky="w", padx=8, pady=1)
                skill_vars[skill] = var
            
            # Character count display
            char_count_label = ttk.Label(skill_frame, text="Characters: 0/50", font=("Arial", 9))
            char_count_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))
            
            # Update character count when category or skills change
            def create_update_function(skill_key, cat_var, new_cat_var, skill_vars_dict, char_label):
                def update_char_count(*args):
                    category = new_cat_var.get().strip() or cat_var.get().strip()
                    selected_skills = [skill for skill, var in skill_vars_dict.items() if var.get()]
                    
                    if category and selected_skills:
                        # Truncate skills if necessary to fit under 50 chars
                        formatted = self._format_skill_with_limit(category, selected_skills, 50)
                        char_count = len(formatted)
                        char_label.config(text=f"Characters: {char_count}/50")
                        
                        # Color code based on length
                        if char_count > 50:
                            char_label.config(foreground="red")
                        elif char_count > 45:
                            char_label.config(foreground="orange")
                        else:
                            char_label.config(foreground="green")
                    else:
                        char_label.config(text="Characters: 0/50", foreground="black")
                
                return update_char_count
            
            update_func = create_update_function(f"SKILL_{i+1}", category_var, new_category_var, skill_vars, char_count_label)
            
            # Bind update function to changes
            category_var.trace_add("write", update_func)
            new_category_var.trace_add("write", update_func)
            for var in skill_vars.values():
                var.trace_add("write", update_func)
            
            # Initial update
            update_func()
            
            # Store references
            self.skill_widgets[f"SKILL_{i+1}"] = {
                'category_var': category_var,
                'new_category_var': new_category_var,
                'skill_vars': skill_vars,
                'char_count_label': char_count_label,
                'frame': skill_frame
            }
    
    def _create_review_panel(self) -> ttk.Frame:
        """Create the review panel."""
        panel = ttk.Frame(self.notebook, padding=20)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(panel, text="Review & Generate Resume", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # Scrollable review area
        review_canvas = tk.Canvas(panel)
        review_scrollbar = ttk.Scrollbar(panel, orient="vertical", command=review_canvas.yview)
        review_canvas.configure(yscrollcommand=review_scrollbar.set)
        
        self.review_frame = ttk.Frame(review_canvas)
        review_canvas.create_window((0, 0), window=self.review_frame, anchor="nw")
        
        review_canvas.grid(row=1, column=0, sticky="nsew")
        review_scrollbar.grid(row=1, column=1, sticky="ns")
        
        self.review_frame.bind('<Configure>', lambda e: review_canvas.configure(scrollregion=review_canvas.bbox('all')))
        
        # Enable mouse wheel scrolling for review
        self._bind_mouse_wheel(self.review_frame, review_canvas)
        
        # Generate button
        generate_frame = ttk.Frame(panel)
        generate_frame.grid(row=2, column=0, columnspan=2, pady=(20, 0))
        
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
            messagebox.showwarning("Skills Warning", f"Could not load skills: {e}")
            self.skill_recommendations = []
            self._populate_skills_panel()
    
    def _format_skill_with_limit(self, category, skills, limit=50):
        """Format skills with character limit and indicate truncation."""
        if not skills:
            return ""
        
        # Use the format_skill_for_template function from skill_recommender
        from .skill_recommender import format_skill_for_template
        formatted = format_skill_for_template(category, skills)
        
        if len(formatted) <= limit:
            return formatted
        
        # If too long, try to truncate skillfully
        if len(skills) == 1:
            # Single skill, just truncate
            available = limit - len(category) - 4  # Account for " ", "[", "]" 
            if available > 10:  # Minimum skill length
                truncated_skill = skills[0][:available-3] + "..."
                return f"{category} [{truncated_skill}]"
        else:
            # Multiple skills, remove from end until it fits
            working_skills = skills.copy()
            while working_skills and len(format_skill_for_template(category, working_skills)) > limit:
                working_skills.pop()
            
            if working_skills:
                formatted = format_skill_for_template(category, working_skills)
                remaining = len(skills) - len(working_skills)
                if remaining > 0:
                    # Add indicator of truncation
                    if len(formatted) + 5 <= limit:  # Space for " +X"
                        return formatted[:-1] + f" +{remaining}]"
                return formatted
        
        # Fallback - just category
        return f"{category} [...]"
    
    def _collect_selected_skills(self):
        """Collect the currently selected skills from the UI."""
        self.selected_skills.clear()
        
        if hasattr(self, 'skill_widgets'):
            for skill_key, widget_data in self.skill_widgets.items():
                # Get category (from dropdown or custom entry)
                category = widget_data['category_var'].get()
                new_category_var = widget_data.get('new_category_var')
                custom_category = new_category_var.get() if new_category_var else ""
                
                # Use custom category if provided and "Custom" is selected
                if category == "Custom" and custom_category:
                    category = custom_category
                
                # Get selected skills
                selected_skill_names = []
                for skill, var in widget_data['skill_vars'].items():
                    if var.get():
                        selected_skill_names.append(skill)
                
                # Also check for custom skill entry
                custom_skill_var = widget_data.get('custom_skill_var')
                custom_skill = custom_skill_var.get() if custom_skill_var else ""
                if custom_skill:
                    selected_skill_names.append(custom_skill)
                
                if category and selected_skill_names:
                    # Use our character-limited formatting
                    formatted_skill = self._format_skill_with_limit(category, selected_skill_names)
                    self.selected_skills[skill_key] = formatted_skill
    
    def _load_review(self):
        """Load and display selected bullets for review."""
        # Clear previous review content
        for child in self.review_frame.winfo_children():
            child.destroy()
        
        # Roles that need titles
        title_roles = ["Nodelink", "MAMM"]
        
        for role in self.selection_requirements.keys():
            selected_indices = self.selected_bullets.get(role, set())
            if not selected_indices:
                continue
                
            # Role section
            role_frame = ttk.LabelFrame(self.review_frame, text=role, padding=15)
            role_frame.pack(fill="x", padx=10, pady=10)
            role_frame.columnconfigure(1, weight=1)
            
            # Title input for applicable roles
            if role in title_roles:
                ttk.Label(role_frame, text="Job Title:").grid(row=0, column=0, sticky="w", pady=(0, 10))
                title_entry = ttk.Entry(role_frame, width=50)
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
                    
                    bullet_label = ttk.Label(role_frame, text=f"• {bullet_text}", 
                                           wraplength=700, justify="left")
                    bullet_label.grid(row=2+i if role in title_roles else 1+i, column=0, 
                                    columnspan=2, sticky="ew", pady=2, padx=(20, 0))
    
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
            # Validate skill selection (optional - can proceed without skills)
            self._collect_selected_skills()
            return True
        
        return True
    
    def _validate_selections(self) -> bool:
        """Validate that required number of bullets are selected."""
        for role, required_count in self.selection_requirements.items():
            selected_count = len(self.selected_bullets.get(role, set()))
            if selected_count != required_count:
                messagebox.showerror(
                    "Selection Error", 
                    f"Please select exactly {required_count} bullet(s) for {role}. Currently selected: {selected_count}"
                )
                return False
        return True


def run_app():
    root = tk.Tk()
    app = ResumeBuilderApp(root)
    root.mainloop()


if __name__ == "__main__":
    run_app()