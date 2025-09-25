"""File selection panel for the Resume Builder."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os

from .base_panel import BasePanel


class FileSelectionPanel(BasePanel):
    """Panel for selecting files and entering job description."""
    
    def _build_ui(self):
        """Build the file selection UI."""
        # Configure frame
        self.frame.configure(padding=20)
        
        # Title
        title_label = ttk.Label(self.frame, text="Resume Builder Setup", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 30))
        
        # Instructions
        instruction_text = "Select your files to begin generating your tailored resume:"
        instruction_label = ttk.Label(self.frame, text=instruction_text, font=("Arial", 10))
        instruction_label.grid(row=1, column=0, columnspan=3, pady=(0, 20))
        
        # File selection section
        file_frame = ttk.LabelFrame(self.frame, text="Required Files", padding=15)
        file_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=10)
        file_frame.columnconfigure(1, weight=1)
        
        # Excel file
        ttk.Label(file_frame, text="Candidate Data (Excel):").grid(row=0, column=0, sticky="w", pady=5)
        self.excel_label = ttk.Label(file_frame, text=os.path.basename(self.app.excel_path) if self.app.excel_path else "(none selected)")
        self.excel_label.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=5)
        ttk.Button(file_frame, text="Browse...", command=self._select_excel).grid(row=0, column=2, padx=(10, 0), pady=5)
        
        # Template file
        ttk.Label(file_frame, text="Word Template:").grid(row=1, column=0, sticky="w", pady=5)
        self.template_label = ttk.Label(file_frame, text=os.path.basename(self.app.template_path) if self.app.template_path else "(none selected)")
        self.template_label.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=5)
        ttk.Button(file_frame, text="Browse...", command=self._select_template).grid(row=1, column=2, padx=(10, 0), pady=5)
        
        # Job description section
        jd_frame = ttk.LabelFrame(self.frame, text="Job Description", padding=15)
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
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(3, weight=1)
    
    def _select_excel(self):
        """Select Excel file."""
        path = filedialog.askopenfilename(
            title="Select Candidate Excel File",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if path:
            self.app.excel_path = path
            self.excel_label.config(text=os.path.basename(path))
    
    def _select_template(self):
        """Select Word template file."""
        path = filedialog.askopenfilename(
            title="Select Word Template",
            filetypes=[("Word documents", "*.docx"), ("All files", "*.*")]
        )
        if path:
            self.app.template_path = path
            self.template_label.config(text=os.path.basename(path))
    
    def validate(self) -> bool:
        """Validate file selection and job description."""
        # Check Excel file
        if not self.app.excel_path or not os.path.exists(self.app.excel_path):
            messagebox.showerror("Error", "Please select a valid Excel file.")
            return False
        
        # Check template file
        if not self.app.template_path or not os.path.exists(self.app.template_path):
            messagebox.showerror("Error", "Please select a valid Word template.")
            return False
        
        # Check job description
        jd_text = self.jd_text_widget.get("1.0", tk.END).strip()
        if not jd_text:
            messagebox.showerror("Error", "Please enter a job description.")
            return False
        
        # Store job description in app state
        self.app.jd_text = jd_text
        return True