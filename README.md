# Resume Builder Scaffold

This scaffold provides a starting point for a resume generation pipeline that:
- Reads a job description text file
- Loads candidate data from an Excel file
- Renders a template with the merged data

Components:
- `resume_app/job_parser.py` — extract keywords and sections from job descriptions
- `resume_app/excel_loader.py` — load candidate data from Excel
- `resume_app/template_renderer.py` — render templates (simple placeholder)
- `resume_app/generator.py` — pipeline orchestrator
- `resume_builder.py` — simple CLI entrypoint

Setup (PowerShell):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Basic usage:

```powershell
python resume_builder.py --job job.txt --excel candidate.xlsx --template template.txt --out out.txt
```

Desktop UI:

```powershell
# Create and activate a venv (if not already active)
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Launch the desktop app
python app.py
```

Next steps:
- Implement `load_candidate_sheet` using `pandas.read_excel` or `openpyxl`.
- Improve `parse_job_description` with NLP (spaCy) or regex rules.
- Replace `template_renderer` naive replacement with `jinja2` templates or python-docx.
