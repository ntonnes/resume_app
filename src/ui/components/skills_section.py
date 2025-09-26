"""Skills section component for the review panel with drag-and-drop reordering."""
import tkinter as tk
from tkinter import ttk
import re
from typing import Dict, Any, List, Callable, Optional


class SkillsSection:
    """Component for displaying and reordering skills in the review panel."""
    
    def __init__(self, parent: tk.Widget, app: Any, on_reorder: Optional[Callable] = None):
        """Initialize the skills section.
        
        Args:
            parent: Parent widget to contain this section
            app: Application instance with data
            on_reorder: Optional callback when skills are reordered
        """
        self.parent = parent
        self.app = app
        self.on_reorder = on_reorder
        self.skill_drag_data: Optional[Dict[str, Any]] = None
        
    def create_section(self) -> ttk.LabelFrame:
        """Create the skills section with drag-and-drop reordering."""
        skills_section = ttk.LabelFrame(self.parent, text="Selected Skills (Drag to Reorder)", padding=10)
        skills_section.columnconfigure(0, weight=1)
        skills_section.rowconfigure(0, weight=1)
        
        if not self.app.ordered_skills:
            ttk.Label(skills_section, text="No skills selected", font=("Arial", 10, "italic"), 
                     foreground="gray").pack(pady=10)
            return skills_section
        
        # Create scrollable canvas for skills
        canvas = tk.Canvas(skills_section, highlightthickness=0)
        scrollbar = ttk.Scrollbar(skills_section, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.columnconfigure(0, weight=1)  # Allow content to expand
        
        # Configure canvas window and scrolling
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def configure_skills_scroll(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            
        def configure_skills_width(event):
            canvas_width = canvas.winfo_width()
            canvas.itemconfig(canvas_window, width=canvas_width)
            
        scrollable_frame.bind("<Configure>", configure_skills_scroll)
        canvas.bind("<Configure>", configure_skills_width)
        
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Create draggable skill groups
        for i, skill_data in enumerate(self.app.ordered_skills):
            self._create_draggable_skill_group(scrollable_frame, i, skill_data)
            
        return skills_section
    
    def _create_draggable_skill_group(self, parent: tk.Widget, index: int, skill_data: Dict[str, Any]):
        """Create a draggable skill group."""
        # Main skill frame
        skill_frame = ttk.Frame(parent, relief="raised", borderwidth=1, padding=10)
        skill_frame.pack(fill="x", pady=5)
        skill_frame.columnconfigure(1, weight=1)
        
        # Drag handle
        drag_label = ttk.Label(skill_frame, text="⋮⋮", font=("Arial", 12), foreground="gray")
        drag_label.grid(row=0, column=0, sticky="nw", padx=(0, 10))
        
        # Skill content frame
        content_frame = ttk.Frame(skill_frame)
        content_frame.grid(row=0, column=1, sticky="ew")
        content_frame.columnconfigure(1, weight=1)
        
        # Skill key label
        key_label = ttk.Label(content_frame, text=f"{skill_data['key']}:", 
                             font=("Arial", 10, "bold"))
        key_label.grid(row=0, column=0, sticky="w", padx=(0, 10))
        
        # Skill value with character count
        char_count = len(skill_data['value'])
        color = "green" if char_count <= 50 else "red"
        value_text = f"{skill_data['value']} ({char_count}/50 chars)"
        value_label = ttk.Label(content_frame, text=value_text, font=("Arial", 10), 
                               foreground=color, wraplength=500)
        value_label.grid(row=0, column=1, sticky="ew")
        
        # Individual skills reordering (if skills are parsed)
        if 'parsed_skills' in skill_data and skill_data['parsed_skills']['skills']:
            self._create_individual_skills_reorder(content_frame, index, skill_data)
        
        # Bind drag events for the skill group
        self._bind_skill_group_drag_events(skill_frame, index)
        self._bind_skill_group_drag_events(drag_label, index)
    
    def _create_individual_skills_reorder(self, parent: tk.Widget, group_index: int, skill_data: Dict[str, Any]):
        """Create reorderable individual skills within a group."""
        skills_frame = ttk.LabelFrame(parent, text="Individual Skills (drag to reorder)", padding=5)
        skills_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        parsed_skills = skill_data['parsed_skills']
        skills = parsed_skills['skills']
        
        for i, skill in enumerate(skills):
            individual_skill_frame = ttk.Frame(skills_frame, relief="groove", borderwidth=1, padding=2)
            individual_skill_frame.pack(fill="x", pady=1)
            individual_skill_frame.columnconfigure(1, weight=1)
            
            # Mini drag handle
            mini_drag = ttk.Label(individual_skill_frame, text="⋮", font=("Arial", 8), foreground="gray")
            mini_drag.grid(row=0, column=0, sticky="w", padx=(0, 5))
            
            # Skill name
            skill_label = ttk.Label(individual_skill_frame, text=skill, font=("Arial", 9))
            skill_label.grid(row=0, column=1, sticky="ew")
            
            # Bind individual skill drag events
            self._bind_individual_skill_drag_events(individual_skill_frame, group_index, i)
            self._bind_individual_skill_drag_events(mini_drag, group_index, i)
            self._bind_individual_skill_drag_events(skill_label, group_index, i)
    
    def _bind_skill_group_drag_events(self, widget: tk.Widget, index: int):
        """Bind drag events for skill group reordering."""
        widget.bind('<Button-1>', lambda e: self._start_skill_group_drag(e, index))
        widget.bind('<B1-Motion>', lambda e: self._on_skill_group_drag(e, index))
        widget.bind('<ButtonRelease-1>', lambda e: self._end_skill_group_drag(e, index))
    
    def _bind_individual_skill_drag_events(self, widget: tk.Widget, group_index: int, skill_index: int):
        """Bind drag events for individual skill reordering."""
        widget.bind('<Button-1>', lambda e: self._start_individual_skill_drag(e, group_index, skill_index))
        widget.bind('<B1-Motion>', lambda e: self._on_individual_skill_drag(e, group_index, skill_index))
        widget.bind('<ButtonRelease-1>', lambda e: self._end_individual_skill_drag(e, group_index, skill_index))
    
    def _start_skill_group_drag(self, event, index: int):
        """Start dragging a skill group."""
        self.skill_drag_data = {
            'type': 'group',
            'index': index,
            'start_y': event.y_root
        }
    
    def _on_skill_group_drag(self, event, index: int):
        """Handle skill group dragging motion."""
        pass  # Visual feedback could be added
    
    def _end_skill_group_drag(self, event, index: int):
        """End skill group dragging and reorder."""
        if not hasattr(self, 'skill_drag_data') or self.skill_drag_data is None or self.skill_drag_data['type'] != 'group':
            return
        
        y_diff = event.y_root - self.skill_drag_data['start_y']
        if abs(y_diff) > 40:  # Minimum drag distance for groups
            direction = 1 if y_diff > 0 else -1
            new_index = max(0, min(len(self.app.ordered_skills) - 1, index + direction))
            
            if new_index != index:
                # Perform the reorder
                skill_data = self.app.ordered_skills.pop(index)
                self.app.ordered_skills.insert(new_index, skill_data)
                
                # Debug: print the new order
                print(f"Skill group reordered from {index} to {new_index}")
                print("New skill order:", [s['key'] for s in self.app.ordered_skills])
                
                # Update the selected_skills dict to match new order
                self._update_selected_skills_from_ordered()
                
                # Notify parent of reorder
                if self.on_reorder:
                    self.on_reorder()
        
        if hasattr(self, 'skill_drag_data'):
            delattr(self, 'skill_drag_data')
    
    def _start_individual_skill_drag(self, event, group_index: int, skill_index: int):
        """Start dragging an individual skill."""
        self.skill_drag_data = {
            'type': 'individual',
            'group_index': group_index,
            'skill_index': skill_index,
            'start_y': event.y_root
        }
    
    def _on_individual_skill_drag(self, event, group_index: int, skill_index: int):
        """Handle individual skill dragging motion."""
        pass  # Visual feedback could be added
    
    def _end_individual_skill_drag(self, event, group_index: int, skill_index: int):
        """End individual skill dragging and reorder."""
        if not hasattr(self, 'skill_drag_data') or self.skill_drag_data is None or self.skill_drag_data['type'] != 'individual':
            return
        
        y_diff = event.y_root - self.skill_drag_data['start_y']
        if abs(y_diff) > 20:  # Minimum drag distance for individual skills
            skill_data = self.app.ordered_skills[group_index]
            skills = skill_data['parsed_skills']['skills']
            
            direction = 1 if y_diff > 0 else -1
            new_index = max(0, min(len(skills) - 1, skill_index + direction))
            
            if new_index != skill_index:
                # Perform the reorder
                skill = skills.pop(skill_index)
                skills.insert(new_index, skill)
                
                # Update the skill value
                category = skill_data['parsed_skills']['category']
                new_value = f"{category} [" + ", ".join(skills) + "]"
                skill_data['value'] = new_value
                
                # Update the selected_skills dict
                self._update_selected_skills_from_ordered()
                
                # Notify parent of reorder
                if self.on_reorder:
                    self.on_reorder()
        
        if hasattr(self, 'skill_drag_data'):
            delattr(self, 'skill_drag_data')
    
    def _update_selected_skills_from_ordered(self):
        """Update the selected_skills dict from ordered_skills list."""
        self.app.selected_skills.clear()
        for skill_data in self.app.ordered_skills:
            self.app.selected_skills[skill_data['key']] = skill_data['value']
    
    @staticmethod
    def parse_skill_value(skill_value: str) -> Dict[str, Any]:
        """Parse a skill value to extract category and individual skills."""
        # Example format: "Programming [Python, Java, JavaScript]"
        match = re.match(r'^(.+?)\s*\[(.+?)\]$', skill_value.strip())
        if match:
            category = match.group(1).strip()
            skills_str = match.group(2).strip()
            skills = [skill.strip() for skill in skills_str.split(',')]
            return {'category': category, 'skills': skills}
        else:
            return {'category': skill_value, 'skills': []}