"""Main entry point for the Resume Builder application."""
import tkinter as tk
from src.core.application import ResumeBuilderApp


def main():
    """Main entry point for the application."""
    root = tk.Tk()
    app = ResumeBuilderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()