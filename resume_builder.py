"""CLI entrypoint for the resume builder scaffold.

Usage: run `python resume_builder.py --job job.txt --excel data.xlsx --template template.txt --out out.txt`
"""
import argparse
from resume_app.generator import generate_resume


def main():
	parser = argparse.ArgumentParser(description="Generate tailored resumes from a job description, Excel data, and a template. Selection of bullet points is interactive.")
	parser.add_argument("--job", required=True, help="Path to job description text file")
	parser.add_argument("--excel", required=True, help="Path to candidate Excel file")
	parser.add_argument("--template", required=True, help="Path to resume template file (.docx supported)")
	parser.add_argument("--out", required=True, help="Output path for generated resume")
	parser.add_argument("--sheet", required=False, help="Excel sheet name to load")

	args = parser.parse_args()

	result = generate_resume(args.job, args.excel, args.template, args.out, sheet_name=args.sheet)
	print(f"Generated: {result.get('output_path')} (status={result.get('status')})")


if __name__ == "__main__":
	main()

