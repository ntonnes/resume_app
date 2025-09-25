"""Main application class for the Resume Builder."""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, Set
import os

from .generator import DEFAULT_COUNTS
from ..templates.template_renderer import render_template
from ..ai.recommender import recommend_with_matches, extract_skills_from_jd
from ..data.excel_loader import load_skills_sheet
from ..ai.skill_recommender import SkillRecommender, format_skill_for_template

from ..ui.panels.file_selection import FileSelectionPanel
from ..ui.panels.bullet_selection import BulletSelectionPanel
from ..ui.panels.skills_selection import SkillsSelectionPanel
from ..ui.panels.review_panel import ReviewPanel


class ResumeBuilderApp:
    """Main application class that coordinates all panels and navigation."""
    
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
        self.panel1 = FileSelectionPanel(self.notebook, self)
        self.panel2 = BulletSelectionPanel(self.notebook, self)
        self.panel3 = SkillsSelectionPanel(self.notebook, self)
        self.panel4 = ReviewPanel(self.notebook, self)
        
        # Add panels to notebook
        self.notebook.add(self.panel1.frame, text="1. File Selection")
        self.notebook.add(self.panel2.frame, text="2. Select Bullets")
        self.notebook.add(self.panel3.frame, text="3. Select Skills")
        self.notebook.add(self.panel4.frame, text="4. Review & Generate")
        
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
    
    def _go_next(self):
        """Navigate to next panel."""
        if self.current_panel < 3:
            if self._validate_current_panel():
                self.current_panel += 1
                self.notebook.select(self.current_panel)
                self._on_panel_change()
                self._update_navigation()
    
    def _go_back(self):
        """Navigate to previous panel."""
        if self.current_panel > 0:
            self.current_panel -= 1
            self.notebook.select(self.current_panel)
            self._on_panel_change()
            self._update_navigation()
    
    def _validate_current_panel(self) -> bool:
        """Validate current panel before moving to next."""
        if self.current_panel == 0:
            return self.panel1.validate()
        elif self.current_panel == 1:
            return self.panel2.validate()
        elif self.current_panel == 2:
            return self.panel3.validate()
        elif self.current_panel == 3:
            return self.panel4.validate()
        return True
    
    def _on_panel_change(self):
        """Handle panel change events."""
        if self.current_panel == 1:
            self.panel2.load_data()
        elif self.current_panel == 2:
            self.panel3.load_data()
        elif self.current_panel == 3:
            self.panel4.load_data()
    
    def _update_navigation(self):
        """Update navigation button states and status."""
        # Update button states
        self.back_btn.config(state="normal" if self.current_panel > 0 else "disabled")
        self.next_btn.config(state="normal" if self.current_panel < 3 else "disabled")
        
        # Update status
        steps = ["File Selection", "Select Bullets", "Select Skills", "Review & Generate"]
        self.status_label.config(text=f"Step {self.current_panel + 1} of 4: {steps[self.current_panel]}")
        
        # Update progress
        if self.current_panel == 0:
            self.progress_label.config(text="Select files and enter job description")
        elif self.current_panel == 1:
            self.progress_label.config(text="Choose your best bullet points")
        elif self.current_panel == 2:
            self.progress_label.config(text="Select skills and categories")
        elif self.current_panel == 3:
            self.progress_label.config(text="Review and generate resume")


def main():
    """Main entry point."""
    root = tk.Tk()
    app = ResumeBuilderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()