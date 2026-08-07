"""
create_fixture_pdf.py — generates a small test PDF for CI reproducibility.

Run once: python create_fixture_pdf.py
Requires: pip install pymupdf
"""
import fitz  # PyMuPDF
from pathlib import Path

OUTPUT = Path(__file__).parent / "sample_doc.pdf"

PAGES = [
    {
        "heading": "Executive Summary",
        "body": (
            "This document outlines the company's Employee Handbook for fiscal year 2024. "
            "It covers all policies relating to employment, benefits, and code of conduct. "
            "All employees are required to read and acknowledge this handbook annually. "
            "The policies contained herein supersede all previous versions. "
            "Failure to comply with these policies may result in disciplinary action."
        ),
    },
    {
        "heading": "Section 1 — Leave Policy",
        "body": (
            "Employees are entitled to 20 days of annual leave per calendar year. "
            "Leave must be approved by the employee's line manager at least 14 days in advance. "
            "Unused leave may be carried forward up to a maximum of 5 days. "
            "Sick leave is granted separately and requires a medical certificate after 3 consecutive days. "
            "Maternity leave is 26 weeks, and paternity leave is 2 weeks, both fully paid."
        ),
    },
    {
        "heading": "Section 2 — Remote Work Policy",
        "body": (
            "Employees may work remotely up to 3 days per week, subject to manager approval. "
            "Remote workers are expected to be available during core hours of 10:00 to 16:00. "
            "All remote work must be conducted on company-approved equipment with a VPN enabled. "
            "Home offices must comply with health and safety requirements outlined in Appendix B. "
            "Remote work privileges may be revoked if performance targets are not met."
        ),
    },
    {
        "heading": "Section 3 — Code of Conduct",
        "body": (
            "All employees must treat colleagues, clients, and partners with respect and professionalism. "
            "Harassment of any form, including verbal, physical, or digital, is strictly prohibited. "
            "Employees must not disclose confidential company information to external parties. "
            "Gifts and hospitality exceeding $50 in value must be declared to the compliance team. "
            "Violations of the code of conduct will be investigated and may result in termination."
        ),
    },
    {
        "heading": "Section 4.2 — Termination and Resignation",
        "body": (
            "Employees wishing to resign must submit a written notice to their line manager. "
            "The required notice period is 30 days for all permanent employees. "
            "Employees must provide a minimum of 30 days written notice before their last working day. "
            "The company reserves the right to place employees on garden leave during the notice period. "
            "All company property must be returned on or before the last working day."
        ),
    },
]


def create_pdf():
    doc = fitz.open()
    for page_content in PAGES:
        page = doc.new_page(width=595, height=842)  # A4
        heading = page_content["heading"]
        body = page_content["body"]

        # Heading (bold, 16pt)
        page.insert_text(
            (50, 80),
            heading,
            fontsize=16,
            fontname="helv",
            color=(0, 0, 0),
        )
        # Body (12pt)
        tw = fitz.TextWriter(page.rect)
        font = fitz.Font("helv")
        tw.append(
            (50, 130),
            body,
            font=font,
            fontsize=12,
        )
        tw.write_text(page)

    doc.save(str(OUTPUT))
    print(f"Created: {OUTPUT} ({len(PAGES)} pages)")


if __name__ == "__main__":
    create_pdf()
