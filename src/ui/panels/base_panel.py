"""Base panel class for all UI panels."""
import tkinter as tk
from tkinter import ttk
from abc import ABC, abstractmethod


class BasePanel(ABC):
    """Base class for all panels in the application."""
    
    def __init__(self, parent: ttk.Widget, app):
        self.parent = parent
        self.app = app
        self.frame = ttk.Frame(parent)
        self._build_ui()
    
    @abstractmethod
    def _build_ui(self):
        """Build the UI for this panel."""
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """Validate the panel before moving to next step."""
        pass
    
    def load_data(self):
        """Load data when panel becomes active. Override if needed."""
        pass