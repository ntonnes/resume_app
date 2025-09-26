"""Streamlined review panel using modular components."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, Any, List

from .base_panel import BasePanel
from ..components.bullets_section import BulletsSection
from ..components.skills_section import SkillsSection
from ..components.template_data_collector import TemplateDataCollector
from ...templates.template_renderer import render_template
from ...utils.ui_helpers import bind_mouse_wheel


class ReviewPanel(BasePanel):
    """Streamlined panel for reviewing selections and generating the resume."""
    
    def __init__(self, parent: ttk.Widget, app):
        """Initialize the review panel."""
        super().__init__(parent, app)
        
        # Initialize components
        self.bullets_section = None
        self.skills_section = None
        self.template_collector = TemplateDataCollector(app)
    
    def _build_ui(self):
        """Build the review panel UI."""
        # Configure frame
        self.frame.configure(padding=20)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(self.frame, text="Review & Generate Resume", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 10), sticky="ew")
        
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
        canvas_window = review_canvas.create_window((0, 0), window=self.review_frame, anchor="nw")
        
        review_canvas.grid(row=0, column=0, sticky="nsew")
        review_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Bind both scroll region and canvas width updates
        def configure_scroll_region(event):
            review_canvas.configure(scrollregion=review_canvas.bbox('all'))
            
        def configure_canvas_width(event):
            canvas_width = review_canvas.winfo_width()
            review_canvas.itemconfig(canvas_window, width=canvas_width)
            
        self.review_frame.bind('<Configure>', configure_scroll_region)
        review_canvas.bind('<Configure>', configure_canvas_width)
        
        # Enable mouse wheel scrolling for review
        bind_mouse_wheel(self.review_frame, review_canvas)
        
        # Generate button
        generate_frame = ttk.Frame(self.frame)
        generate_frame.grid(row=2, column=0, pady=(20, 0))
        
        self.generate_btn = ttk.Button(generate_frame, text="Generate Resume", command=self._generate_resume)
        self.generate_btn.pack()
    
    def load_data(self):
        """Load and display selected bullets and skills for review with reordering capability."""
        # Clear previous review content
        for child in self.review_frame.winfo_children():
            child.destroy()
        
        # Initialize ordered data structures if not already present
        self._initialize_ordered_data()
        
        # Create main container with full width layout
        main_container = ttk.Frame(self.review_frame)
        main_container.pack(fill="both", expand=True, padx=5, pady=5)
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=1)  # Two equal columns
        main_container.rowconfigure(1, weight=1)  # Allow content to expand vertically
        
        # Configure review_frame to expand properly
        self.review_frame.columnconfigure(0, weight=1)
        self.review_frame.rowconfigure(0, weight=1)
        
        # Summary statistics at the top - spanning both columns
        self._create_stats_section(main_container)
        
        # Left Column: Bullet Points Section with drag-and-drop
        self._create_bullets_section(main_container)
        
        # Right Column: Skills Section with drag-and-drop
        self._create_skills_section(main_container)
    
    def _initialize_ordered_data(self):
        """Initialize ordered data structures if not already present."""
        # Initialize ordered bullets
        if not hasattr(self.app, 'ordered_bullets'):
            self.app.ordered_bullets = {}
            for role, selected_indices in self.app.selected_bullets.items():
                bullets = self.app.recs.get(role, [])
                ordered_bullet_data = []
                for idx in sorted(selected_indices):
                    if idx < len(bullets):
                        ordered_bullet_data.append({
                            'original_index': idx,
                            'bullet': bullets[idx].get("bullet", ""),
                            'lines': bullets[idx].get("lines", "?")
                        })
                self.app.ordered_bullets[role] = ordered_bullet_data
        
        # Initialize ordered skills
        if not hasattr(self.app, 'ordered_skills'):
            self.app.ordered_skills = []
            for skill_key in sorted(self.app.selected_skills.keys()):
                if self.app.selected_skills[skill_key].strip():
                    skill_value = self.app.selected_skills[skill_key]
                    parsed_skills = SkillsSection.parse_skill_value(skill_value)
                    self.app.ordered_skills.append({
                        'key': skill_key,
                        'value': skill_value,
                        'parsed_skills': parsed_skills
                    })
    
    def _create_stats_section(self, parent: tk.Widget):
        """Create the statistics summary section."""
        stats_frame = ttk.LabelFrame(parent, text="Selection Summary", padding=10)
        stats_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        # Calculate totals using template collector
        stats = self.template_collector.calculate_selection_stats()
        
        stats_text = f"Total Bullet Points: {stats['total_bullets']} | Total Lines: {stats['total_lines']} | Skills Categories: {stats['total_skills']}"
        stats_label = ttk.Label(stats_frame, text=stats_text, font=("Arial", 12, "bold"), foreground="darkgreen")
        stats_label.pack()
        
        # Instructions
        instructions = ttk.Label(stats_frame, text="Drag and drop bullets and skills to reorder them", 
                               font=("Arial", 10, "italic"), foreground="blue")
        instructions.pack(pady=(5, 0))
    
    def _create_bullets_section(self, parent: tk.Widget):
        """Create the bullets section using the BulletsSection component."""
        self.bullets_section = BulletsSection(parent, self.app, on_reorder=self.load_data)
        bullets_section_frame = self.bullets_section.create_section()
        bullets_section_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 5), pady=(0, 10))
    
    def _create_skills_section(self, parent: tk.Widget):
        """Create the skills section using the SkillsSection component."""
        self.skills_section = SkillsSection(parent, self.app, on_reorder=self.load_data)
        skills_section_frame = self.skills_section.create_section()
        skills_section_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 0), pady=(0, 10))
    
    def _generate_resume(self):
        """Generate the final resume document."""
        # Collect template data using the collector component
        template_data = self.template_collector.collect_final_template_data()
        
        # Ask user where to save
        file_path = filedialog.asksaveasfilename(
            defaultextension=".docx",
            filetypes=[("Word documents", "*.docx"), ("All files", "*.*")],
            title="Save Resume As"
        )
        
        if file_path:
            try:
                # Use the template renderer to generate the document
                render_template("resume.docx", template_data, file_path)
                messagebox.showinfo("Success", f"Resume generated successfully!\nSaved to: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to generate resume: {str(e)}")
    
    def validate(self) -> bool:
        """Validate before final generation - always return True for review panel."""
        return True