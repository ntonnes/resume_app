"""Utility functions for UI components."""
import tkinter as tk


def bind_mouse_wheel(widget, canvas):
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