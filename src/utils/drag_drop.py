"""Drag and drop utilities for reordering UI elements."""
import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Any, Dict, Optional


class DragDropListbox:
    """A listbox with drag-and-drop reordering capability."""
    
    def __init__(self, parent, items: List[Any], item_formatter: Callable[[Any], str], 
                 on_reorder: Optional[Callable[[List[Any]], None]] = None):
        self.parent = parent
        self.items = items.copy()
        self.item_formatter = item_formatter
        self.on_reorder = on_reorder
        self.drag_start_index = None
        
        # Create the main frame
        self.frame = ttk.Frame(parent)
        
        # Create listbox with scrollbar
        listbox_frame = ttk.Frame(self.frame)
        listbox_frame.pack(fill="both", expand=True)
        
        self.listbox = tk.Listbox(listbox_frame, selectmode=tk.SINGLE)
        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind drag and drop events
        self.listbox.bind('<Button-1>', self._on_drag_start)
        self.listbox.bind('<B1-Motion>', self._on_drag_motion)
        self.listbox.bind('<ButtonRelease-1>', self._on_drag_end)
        
        # Populate the listbox
        self._populate_listbox()
    
    def _populate_listbox(self):
        """Populate the listbox with formatted items."""
        self.listbox.delete(0, tk.END)
        for item in self.items:
            self.listbox.insert(tk.END, self.item_formatter(item))
    
    def _on_drag_start(self, event):
        """Handle drag start."""
        self.drag_start_index = self.listbox.nearest(event.y)
        if self.drag_start_index < len(self.items):
            self.listbox.selection_set(self.drag_start_index)
    
    def _on_drag_motion(self, event):
        """Handle drag motion."""
        if self.drag_start_index is not None:
            current_index = self.listbox.nearest(event.y)
            if 0 <= current_index < len(self.items) and current_index != self.drag_start_index:
                # Visual feedback - highlight the drop target
                self.listbox.selection_clear(0, tk.END)
                self.listbox.selection_set(current_index)
    
    def _on_drag_end(self, event):
        """Handle drag end and perform the reorder."""
        if self.drag_start_index is not None:
            drop_index = self.listbox.nearest(event.y)
            if 0 <= drop_index < len(self.items) and drop_index != self.drag_start_index:
                # Perform the reorder
                item = self.items.pop(self.drag_start_index)
                self.items.insert(drop_index, item)
                
                # Update the listbox
                self._populate_listbox()
                self.listbox.selection_set(drop_index)
                
                # Notify parent of the change
                if self.on_reorder:
                    self.on_reorder(self.items)
        
        self.drag_start_index = None
    
    def get_items(self) -> List[Any]:
        """Get the current ordered items."""
        return self.items.copy()
    
    def update_items(self, new_items: List[Any]):
        """Update the items and refresh the display."""
        self.items = new_items.copy()
        self._populate_listbox()


class DragDropFrame:
    """A frame containing draggable items for reordering."""
    
    def __init__(self, parent, items: List[Dict], item_creator: Callable[[Any, tk.Widget], tk.Widget],
                 on_reorder: Optional[Callable[[List[Any]], None]] = None):
        self.parent = parent
        self.items = items.copy()
        self.item_creator = item_creator
        self.on_reorder = on_reorder
        self.item_widgets = []
        self.drag_start_y = None
        self.drag_item_index = None
        
        # Create scrollable frame
        self.canvas = tk.Canvas(parent)
        self.scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Populate the frame
        self._populate_frame()
    
    def _populate_frame(self):
        """Populate the frame with draggable items."""
        # Clear existing widgets
        for widget in self.item_widgets:
            widget.destroy()
        self.item_widgets.clear()
        
        # Create new widgets
        for i, item in enumerate(self.items):
            # Create a container frame for each item
            item_frame = ttk.Frame(self.scrollable_frame, relief="raised", borderwidth=1)
            item_frame.pack(fill="x", padx=2, pady=2)
            
            # Create the actual item widget
            item_widget = self.item_creator(item, item_frame)
            
            # Bind drag events to the frame
            item_frame.bind('<Button-1>', lambda e, idx=i: self._on_drag_start(e, idx))
            item_frame.bind('<B1-Motion>', lambda e, idx=i: self._on_drag_motion(e, idx))
            item_frame.bind('<ButtonRelease-1>', lambda e, idx=i: self._on_drag_end(e, idx))
            
            # Also bind to child widgets for better UX
            for child in item_frame.winfo_children():
                child.bind('<Button-1>', lambda e, idx=i: self._on_drag_start(e, idx))
                child.bind('<B1-Motion>', lambda e, idx=i: self._on_drag_motion(e, idx))
                child.bind('<ButtonRelease-1>', lambda e, idx=i: self._on_drag_end(e, idx))
            
            self.item_widgets.append(item_frame)
    
    def _on_drag_start(self, event, index):
        """Handle drag start."""
        self.drag_start_y = event.y_root
        self.drag_item_index = index
        # Highlight the dragged item
        self.item_widgets[index].configure(relief="sunken")
    
    def _on_drag_motion(self, event, index):
        """Handle drag motion."""
        if self.drag_item_index is not None and self.drag_start_y is not None:
            # Calculate which item we're hovering over
            for i, widget in enumerate(self.item_widgets):
                if i == self.drag_item_index:
                    continue
                
                widget_y = widget.winfo_rooty()
                widget_height = widget.winfo_height()
                
                if widget_y <= event.y_root <= widget_y + widget_height:
                    # Provide visual feedback
                    widget.configure(relief="groove")
                else:
                    widget.configure(relief="raised")
    
    def _on_drag_end(self, event, index):
        """Handle drag end and perform reorder."""
        if self.drag_item_index is not None:
            # Find the drop target
            target_index = None
            for i, widget in enumerate(self.item_widgets):
                if i == self.drag_item_index:
                    continue
                
                widget_y = widget.winfo_rooty()
                widget_height = widget.winfo_height()
                
                if widget_y <= event.y_root <= widget_y + widget_height:
                    target_index = i
                    break
            
            if target_index is not None and target_index != self.drag_item_index:
                # Perform the reorder
                item = self.items.pop(self.drag_item_index)
                self.items.insert(target_index, item)
                
                # Refresh the display
                self._populate_frame()
                
                # Notify parent
                if self.on_reorder:
                    self.on_reorder(self.items)
        
        # Reset drag state and visual feedback
        self.drag_start_y = None
        self.drag_item_index = None
        for widget in self.item_widgets:
            widget.configure(relief="raised")
    
    def get_items(self) -> List[Any]:
        """Get the current ordered items."""
        return self.items.copy()
    
    def update_items(self, new_items: List[Any]):
        """Update items and refresh display."""
        self.items = new_items.copy()
        self._populate_frame()