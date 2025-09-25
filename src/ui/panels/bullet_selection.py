"""Bullet selection panel for the Resume Builder."""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Set

from .base_panel import BasePanel
from ...ai.recommender import recommend_with_matches
from ...utils.ui_helpers import bind_mouse_wheel


class BulletSelectionPanel(BasePanel):
    """Panel for selecting bullet points from recommendations."""
    
    def _build_ui(self):
        """Build the bullet selection UI."""
        # Configure frame
        self.frame.configure(padding=10)
        self.frame.columnconfigure(0, weight=7)  # Much more space for bullets
        self.frame.columnconfigure(1, weight=3)   # Minimal space for job description
        self.frame.rowconfigure(0, weight=1)
        
        # Left side - bullet recommendations
        left_frame = ttk.Frame(self.frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)
        
        # Title and instructions
        title_label = ttk.Label(left_frame, text="Select Your Best Bullet Points", font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 10), sticky="w")
        
        instruction_text = f"Required selections: {self.app.selection_requirements['Nodelink']} Nodelink, {self.app.selection_requirements['MAMM']} MAMM, {self.app.selection_requirements['FactCheckAI']} FactCheckAI, {self.app.selection_requirements['Medical Classifier']} Medical"
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
        bind_mouse_wheel(self.recs_frame, self.recs_canvas)
        
        # Right side - job description
        right_frame = ttk.LabelFrame(self.frame, text="Job Description", padding=10)
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
    
    def load_data(self):
        """Load and display bullet recommendations."""
        try:
            # Clear previous recommendations
            for child in self.recs_frame.winfo_children():
                child.destroy()
            
            # Initialize selected bullets dict
            for role in self.app.selection_requirements.keys():
                self.app.selected_bullets[role] = set()
            
            # Load candidate data and compute recommendations
            if not self.app.excel_path:
                return
                
            from ...data.excel_loader import load_candidate_sheet
            candidate = load_candidate_sheet(self.app.excel_path)
            bullets_by_role = candidate.get("bullets", {}) if isinstance(candidate, dict) else {}
            
            self.app.recs = {}
            for role in self.app.selection_requirements.keys():
                bullets = bullets_by_role.get(role, [])
                if not bullets:
                    continue
                scored = recommend_with_matches(bullets, self.app.jd_text, top_n=len(bullets))
                self.app.recs[role] = [{**b, "score": s, "matches": m} for (b, s, m) in scored]
            
            # Display recommendations for each role
            self._display_role_recommendations()
            
            # Display job description in right panel
            self.jd_display.config(state="normal")
            self.jd_display.delete("1.0", tk.END)
            self.jd_display.insert("1.0", self.app.jd_text)
            self.jd_display.config(state="disabled")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load recommendations: {e}")
    
    def _display_role_recommendations(self):
        """Display recommendations for all roles."""
        for role, items in self.app.recs.items():
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
            requirement_label = ttk.Label(role_frame, text=f"Select {self.app.selection_requirements[role]} bullet points", 
                                        font=("Arial", 10, "italic"), foreground="gray")
            requirement_label.grid(row=1, column=0, sticky="w", pady=(0, 15))
            
            # Pre-select first x bullets for each role
            required_count = self.app.selection_requirements[role]
            
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
                    self.app.selected_bullets.setdefault(role, set()).add(idx)
                
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
        required_count = self.app.selection_requirements[role]
        selected_set = self.app.selected_bullets[role]
        
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
        
        for role, selected_indices in self.app.selected_bullets.items():
            bullets = self.app.recs.get(role, [])
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
    
    def validate(self) -> bool:
        """Validate bullet selections."""
        # Check that all required selections are made
        for role, required_count in self.app.selection_requirements.items():
            selected_count = len(self.app.selected_bullets.get(role, set()))
            if selected_count != required_count:
                messagebox.showerror("Error", f"Please select exactly {required_count} bullets for {role}. Currently selected: {selected_count}")
                return False
        return True