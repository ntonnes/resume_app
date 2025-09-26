"""Bullets section component for the review panel with drag-and-drop reordering."""
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, List, Callable, Optional


class BulletsSection:
    """Component for displaying and reordering bullet points in the review panel."""
    
    def __init__(self, parent: tk.Widget, app: Any, on_reorder: Optional[Callable] = None):
        """Initialize the bullets section.
        
        Args:
            parent: Parent widget to contain this section
            app: Application instance with data
            on_reorder: Optional callback when bullets are reordered
        """
        self.parent = parent
        self.app = app
        self.on_reorder = on_reorder
        self.drag_data: Optional[Dict[str, Any]] = None
        
    def create_section(self) -> ttk.LabelFrame:
        """Create the bullet points section with drag-and-drop reordering."""
        bullets_section = ttk.LabelFrame(self.parent, text="Selected Bullet Points (Drag to Reorder)", padding=10)
        bullets_section.columnconfigure(0, weight=1)
        bullets_section.rowconfigure(0, weight=1)
        
        # Create scrollable canvas
        canvas = tk.Canvas(bullets_section, highlightthickness=0)
        scrollbar = ttk.Scrollbar(bullets_section, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.columnconfigure(0, weight=1)  # Allow content to expand
        
        # Configure canvas window and scrolling
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def configure_bullets_scroll(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            
        def configure_bullets_width(event):
            canvas_width = canvas.winfo_width()
            canvas.itemconfig(canvas_window, width=canvas_width)
            
        scrollable_frame.bind("<Configure>", configure_bullets_scroll)
        canvas.bind("<Configure>", configure_bullets_width)
        
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Roles that need titles
        title_roles = ["Nodelink", "MAMM"]
        
        for role in self.app.selection_requirements.keys():
            if role not in self.app.ordered_bullets or not self.app.ordered_bullets[role]:
                continue
                
            # Role section
            role_frame = ttk.LabelFrame(scrollable_frame, text=role, padding=15)
            role_frame.pack(fill="x", padx=5, pady=10)
            role_frame.columnconfigure(0, weight=1)
            
            # Title input for applicable roles
            if role in title_roles:
                title_frame = ttk.Frame(role_frame)
                title_frame.pack(fill="x", pady=(0, 10))
                title_frame.columnconfigure(1, weight=1)
                
                ttk.Label(title_frame, text="Job Title:").grid(row=0, column=0, sticky="w")
                title_entry = ttk.Entry(title_frame, width=60)
                title_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0))
                
                # Set default title
                default_titles = {
                    "Nodelink": "Software Engineer",
                    "MAMM": "Research Assistant"
                }
                title_entry.insert(0, default_titles.get(role, ""))
                
                # Store title entry in app
                if not hasattr(self.app, 'role_titles'):
                    self.app.role_titles = {}
                self.app.role_titles[role] = title_entry
            
            # Create draggable bullet list
            bullets_frame = ttk.Frame(role_frame)
            bullets_frame.pack(fill="x", pady=(10, 0))
            bullets_frame.columnconfigure(0, weight=1)  # Allow bullets to expand
            
            self._create_draggable_bullets(bullets_frame, role)
            
        return bullets_section
    
    def _create_draggable_bullets(self, parent: tk.Widget, role: str):
        """Create draggable bullet points for a role."""
        bullets_data = self.app.ordered_bullets[role]
        
        for i, bullet_data in enumerate(bullets_data):
            # Create bullet frame
            bullet_frame = ttk.Frame(parent, relief="raised", borderwidth=1, padding=5)
            bullet_frame.pack(fill="x", pady=2)
            bullet_frame.columnconfigure(1, weight=1)
            
            # Drag handle
            drag_label = ttk.Label(bullet_frame, text="⋮⋮", font=("Arial", 12), foreground="gray")
            drag_label.grid(row=0, column=0, sticky="w", padx=(0, 10))
            
            # Bullet text
            bullet_text = f"• {bullet_data['bullet']} (Lines: {bullet_data['lines']})"
            bullet_label = ttk.Label(bullet_frame, text=bullet_text, wraplength=600, 
                                   justify="left", font=("Arial", 9))
            bullet_label.grid(row=0, column=1, sticky="ew")
            
            # Bind drag events
            self._bind_bullet_drag_events(bullet_frame, role, i)
            self._bind_bullet_drag_events(drag_label, role, i)
            self._bind_bullet_drag_events(bullet_label, role, i)
    
    def _bind_bullet_drag_events(self, widget: tk.Widget, role: str, index: int):
        """Bind drag events to a bullet widget."""
        widget.bind('<Button-1>', lambda e: self._start_bullet_drag(e, role, index))
        widget.bind('<B1-Motion>', lambda e: self._on_bullet_drag(e, role, index))
        widget.bind('<ButtonRelease-1>', lambda e: self._end_bullet_drag(e, role, index))
    
    def _start_bullet_drag(self, event, role: str, index: int):
        """Start dragging a bullet point."""
        self.drag_data = {
            'role': role,
            'index': index,
            'start_y': event.y_root
        }
    
    def _on_bullet_drag(self, event, role: str, index: int):
        """Handle bullet dragging motion."""
        if hasattr(self, 'drag_data'):
            # Visual feedback could be added here
            pass
    
    def _end_bullet_drag(self, event, role: str, index: int):
        """End bullet dragging and perform reorder."""
        if not hasattr(self, 'drag_data') or self.drag_data is None:
            return
        
        # Calculate drop position based on y movement
        y_diff = event.y_root - self.drag_data['start_y']
        if abs(y_diff) > 30:  # Minimum drag distance
            bullets = self.app.ordered_bullets[role]
            direction = 1 if y_diff > 0 else -1
            new_index = max(0, min(len(bullets) - 1, index + direction))
            
            if new_index != index:
                # Perform the reorder
                bullet_data = bullets.pop(index)
                bullets.insert(new_index, bullet_data)
                
                # Notify parent of reorder
                if self.on_reorder:
                    self.on_reorder()
        
        # Clean up
        if hasattr(self, 'drag_data'):
            delattr(self, 'drag_data')