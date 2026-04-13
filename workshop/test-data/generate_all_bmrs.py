#!/usr/bin/env python3
"""Generate realistic BMR PDFs that match the reference expected JSON files.

Each PDF simulates a filled-in pharmaceutical Batch Manufacturing Record form
with handwriting-style fonts (italic Courier in dark blue) over a printed form template.

- Sample 01 (clean): Neat, all fields filled, 3 ingredients
- Sample 02 (messy): Simulated corrections, smudge notes, all fields filled
- Sample 03 (partial): Some fields left blank (null in reference JSON)
"""

import os
import random
from fpdf import FPDF


class BMRForm(FPDF):
    """Custom PDF class for BMR form generation."""

    def __init__(self, variant_label: str = ""):
        super().__init__()
        self._variant_label = variant_label

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(180, 0, 0)
        self.cell(
            0, 6, "CONTROLLED DOCUMENT - DO NOT COPY",
            align="C", new_x="LMARGIN", new_y="NEXT",
        )
        self.set_text_color(0, 0, 0)

    def form_label(self, text: str, w: int = 55):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(60, 60, 60)
        self.cell(w, 8, text)

    def form_value(self, text: str | None, w: int = 0, strikethrough: bool = False):
        """Simulate handwritten entry using italic Courier in dark blue."""
        if text is None:
            # Draw an empty underline to show the field was left blank
            self.set_draw_color(180, 180, 180)
            x = self.get_x()
            y = self.get_y() + 7
            self.line(x, y, x + 80, y)
            self.cell(w, 8, "", new_x="LMARGIN", new_y="NEXT")
            return
        self.set_font("Courier", "I", 11)
        self.set_text_color(10, 10, 140)
        if strikethrough:
            x_start = self.get_x()
            y_mid = self.get_y() + 4
            self.cell(w, 8, text, new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(180, 0, 0)
            self.set_line_width(0.4)
            self.line(x_start, y_mid, x_start + self.get_string_width(text) + 2, y_mid)
            self.set_line_width(0.2)
        else:
            self.cell(w, 8, text, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)

    def section_header(self, text: str):
        self.ln(3)
        self.set_fill_color(230, 230, 240)
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 8, f"  {text}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def draw_line(self):
        y = self.get_y()
        self.set_draw_color(180, 180, 180)
        self.line(15, y, 195, y)
        self.ln(2)

    def add_smudge_note(self, text: str):
        """Add a small annotation simulating a smudge / correction note."""
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(160, 100, 100)
        self.cell(0, 5, f"  [{text}]", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)


def _title_block(pdf: BMRForm, company: str = "PharmaCorp Manufacturing Division"):
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(
        0, 10, "BATCH MANUFACTURING RECORD",
        align="C", new_x="LMARGIN", new_y="NEXT",
    )
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(
        0, 5, f"{company}  |  Form BMR-001 Rev 3.2",
        align="C", new_x="LMARGIN", new_y="NEXT",
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)
    pdf.set_draw_color(0, 0, 0)
    pdf.rect(12, 28, 186, 252)


def _ingredient_table(
    pdf: BMRForm,
    ingredients: list[dict],
    extra_col: str | None = "Verified By",
    extra_vals: list[str] | None = None,
    show_strikethrough_row: dict | None = None,
):
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(220, 220, 220)
    col_w = [55, 25, 45]
    headers = ["Ingredient Name", "Wt (kg)", "Lot Number"]
    if extra_col:
        col_w.append(30)
        headers.append(extra_col)
    for h, w in zip(headers, col_w):
        pdf.cell(w, 7, h, border=1, fill=True)
    pdf.ln()

    # Optional struck-through row (for messy variant)
    if show_strikethrough_row:
        pdf.set_font("Courier", "I", 10)
        pdf.set_text_color(180, 0, 0)
        x0 = pdf.get_x()
        y0 = pdf.get_y()
        row = show_strikethrough_row
        vals = [
            row.get("ingredient_name", ""),
            str(row.get("weight_kg", "")),
            row.get("lot_number", ""),
        ]
        for v, w in zip(vals, col_w[:3]):
            pdf.cell(w, 7, v, border=1)
        if extra_col:
            pdf.cell(col_w[3], 7, "", border=1)
        # Strikethrough line
        y_mid = y0 + 3.5
        pdf.set_draw_color(180, 0, 0)
        pdf.set_line_width(0.5)
        pdf.line(x0, y_mid, x0 + sum(col_w), y_mid)
        pdf.set_line_width(0.2)
        pdf.ln()
        pdf.set_text_color(0, 0, 0)

    pdf.set_font("Courier", "I", 10)
    pdf.set_text_color(10, 10, 140)
    for i, ing in enumerate(ingredients):
        name = ing.get("ingredient_name", "")
        wt = ing.get("weight_kg")
        lot = ing.get("lot_number") or ""
        wt_str = f"{wt:.2f}" if wt is not None else ""
        pdf.cell(col_w[0], 7, name, border=1)
        pdf.cell(col_w[1], 7, wt_str, border=1)
        pdf.cell(col_w[2], 7, lot, border=1)
        if extra_col and extra_vals:
            pdf.cell(col_w[3], 7, extra_vals[i] if i < len(extra_vals) else "", border=1)
        elif extra_col:
            pdf.cell(col_w[3], 7, "", border=1)
        pdf.ln()
    pdf.set_text_color(0, 0, 0)


def _footer_line(pdf: BMRForm):
    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(
        0, 5,
        "Form BMR-001 Rev 3.2  |  PharmaCorp Manufacturing  |  CONTROLLED DOCUMENT",
        align="C",
    )


# -------------------------------------------------------------------------
# BMR SAMPLE 01 — CLEAN
# -------------------------------------------------------------------------
def create_bmr_01_clean(out_dir: str):
    pdf = BMRForm("CLEAN")
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    _title_block(pdf)

    # Section A: Product Info
    pdf.section_header("SECTION A: PRODUCT INFORMATION")
    pdf.form_label("Product Name:")
    pdf.form_value("Amoxicillin 500mg Capsules")
    pdf.form_label("Batch Number:")
    pdf.form_value("BMR-2024-0847")
    pdf.form_label("Batch Size:")
    pdf.form_value("50,000 capsules (25.0 kg active)")
    pdf.form_label("Manufacturing Date:")
    pdf.form_value("15-Mar-2024")
    pdf.draw_line()

    # Section B: Personnel
    pdf.section_header("SECTION B: PERSONNEL")
    pdf.form_label("Operator Initials:")
    pdf.form_value("JKL")
    pdf.form_label("Supervisor:")
    pdf.form_value("Dr. S. Patel")
    pdf.form_label("QA Reviewer:")
    pdf.form_value("M. Thompson")
    pdf.draw_line()

    # Section C: Equipment
    pdf.section_header("SECTION C: EQUIPMENT USED")
    equip = [
        ("MIX-401", "High-Shear Granulator", "2024-09-30"),
        ("GRAN-205", "Fluid Bed Dryer", "2024-08-15"),
        ("PRESS-112", "Rotary Tablet Press", "2024-11-01"),
    ]
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(40, 7, "Equipment ID", border=1, fill=True)
    pdf.cell(65, 7, "Description", border=1, fill=True)
    pdf.cell(40, 7, "Calibration Due", border=1, fill=True)
    pdf.ln()
    pdf.set_font("Courier", "I", 10)
    pdf.set_text_color(10, 10, 140)
    for eid, desc, cal in equip:
        pdf.cell(40, 7, eid, border=1)
        pdf.cell(65, 7, desc, border=1)
        pdf.cell(40, 7, cal, border=1)
        pdf.ln()
    pdf.set_text_color(0, 0, 0)
    pdf.draw_line()

    # Section D: Ingredients
    pdf.section_header("SECTION D: RAW MATERIALS / INGREDIENTS")
    ingredients = [
        {"ingredient_name": "Amoxicillin Trihydrate", "weight_kg": 25.00, "lot_number": "LOT-AM-20240115"},
        {"ingredient_name": "Magnesium Stearate", "weight_kg": 0.75, "lot_number": "LOT-MG-20240203"},
        {"ingredient_name": "Microcrystalline Cellulose", "weight_kg": 12.50, "lot_number": "LOT-MC-20240118"},
    ]
    _ingredient_table(pdf, ingredients, extra_col="Verified By", extra_vals=["JKL", "JKL", "JKL"])
    pdf.draw_line()

    # Section E: Timing
    pdf.section_header("SECTION E: PROCESS TIMING")
    pdf.form_label("Start Time:")
    pdf.form_value("2024-03-15  06:30")
    pdf.form_label("End Time:")
    pdf.form_value("2024-03-15  14:45")
    pdf.form_label("Total Duration:")
    pdf.form_value("8 hours 15 minutes")

    _footer_line(pdf)
    path = os.path.join(out_dir, "bmr-sample-01-clean.pdf")
    pdf.output(path)
    print(f"  Created: {path}")


# -------------------------------------------------------------------------
# BMR SAMPLE 02 — MESSY
# -------------------------------------------------------------------------
def create_bmr_02_messy(out_dir: str):
    pdf = BMRForm("MESSY")
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    _title_block(pdf, "GeneriPharma Manufacturing Site B")

    # Section A
    pdf.section_header("SECTION A: PRODUCT INFORMATION")
    pdf.form_label("Product Name:")
    pdf.form_value("Metformin HCl 850mg Tablets")
    pdf.add_smudge_note("ink smudge near product name - verified legible")

    pdf.form_label("Batch Number:")
    # Show a struck-through wrong number, then the correct one
    pdf.form_value("BMR-2024-1103", strikethrough=True)
    pdf.form_label("Batch Number (corrected):")
    pdf.form_value("BMR-2024-1203")
    pdf.add_smudge_note("operator corrected batch number, initialed RMP 02-Apr-2024")

    pdf.form_label("Batch Size:")
    pdf.form_value("100,000 tablets (42.5 kg active)")
    pdf.form_label("Manufacturing Date:")
    pdf.form_value("02-Apr-2024")
    pdf.draw_line()

    # Section B
    pdf.section_header("SECTION B: PERSONNEL")
    pdf.form_label("Operator Initials:")
    pdf.form_value("RMP")
    pdf.form_label("Supervisor:")
    pdf.form_value("Dr. A. Krishnan")
    pdf.form_label("QA Reviewer:")
    pdf.form_value("J. O'Brien")
    pdf.draw_line()

    # Section C
    pdf.section_header("SECTION C: EQUIPMENT USED")
    equip = [
        ("MIX-402", "V-Blender", "2024-10-15"),
        ("DRY-108", "Tray Dryer", "2024-07-22"),
        ("PRESS-115", "Single-Punch Press", "2024-12-01"),
    ]
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(40, 7, "Equipment ID", border=1, fill=True)
    pdf.cell(65, 7, "Description", border=1, fill=True)
    pdf.cell(40, 7, "Calibration Due", border=1, fill=True)
    pdf.ln()
    pdf.set_font("Courier", "I", 10)
    pdf.set_text_color(10, 10, 140)
    for eid, desc, cal in equip:
        pdf.cell(40, 7, eid, border=1)
        pdf.cell(65, 7, desc, border=1)
        pdf.cell(40, 7, cal, border=1)
        pdf.ln()
    pdf.set_text_color(0, 0, 0)
    pdf.add_smudge_note("DRY-108 ID partially smudged - confirmed from equipment log")
    pdf.draw_line()

    # Section D: Ingredients (with a struck-through wrong row)
    pdf.section_header("SECTION D: RAW MATERIALS / INGREDIENTS")
    wrong_row = {"ingredient_name": "Povidone K90", "weight_kg": 3.50, "lot_number": "LOT-PV-20240210"}
    ingredients = [
        {"ingredient_name": "Metformin Hydrochloride", "weight_kg": 42.50, "lot_number": "LOT-MF-20240301"},
        {"ingredient_name": "Povidone K30", "weight_kg": 3.20, "lot_number": "LOT-PV-20240215"},
        {"ingredient_name": "Stearic Acid", "weight_kg": 1.10, "lot_number": "LOT-SA-20240228"},
    ]
    _ingredient_table(
        pdf, ingredients,
        extra_col="Verified By",
        extra_vals=["RMP", "RMP", "RMP"],
        show_strikethrough_row=wrong_row,
    )
    pdf.add_smudge_note("Povidone K90 row struck out - wrong grade, replaced with K30 per deviation DEV-2024-041")
    pdf.draw_line()

    # Section E
    pdf.section_header("SECTION E: PROCESS TIMING")
    pdf.form_label("Start Time:")
    pdf.form_value("2024-04-02  07:15")
    pdf.form_label("End Time:")
    pdf.form_value("2024-04-02  16:30")
    pdf.form_label("Total Duration:")
    pdf.form_value("9 hours 15 minutes")

    _footer_line(pdf)
    path = os.path.join(out_dir, "bmr-sample-02-messy.pdf")
    pdf.output(path)
    print(f"  Created: {path}")


# -------------------------------------------------------------------------
# BMR SAMPLE 03 — PARTIAL
# -------------------------------------------------------------------------
def create_bmr_03_partial(out_dir: str):
    pdf = BMRForm("PARTIAL")
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    _title_block(pdf, "MedCore Pharmaceuticals - Plant 3")

    # Section A
    pdf.section_header("SECTION A: PRODUCT INFORMATION")
    pdf.form_label("Product Name:")
    pdf.form_value("Ibuprofen 200mg Tablets")
    pdf.form_label("Batch Number:")
    pdf.form_value("BMR-2024-0592")
    pdf.form_label("Batch Size:")
    pdf.form_value("200,000 tablets (20.0 kg active)")
    pdf.form_label("Manufacturing Date:")
    pdf.form_value("10-Apr-2024")
    pdf.draw_line()

    # Section B
    pdf.section_header("SECTION B: PERSONNEL")
    pdf.form_label("Operator Initials:")
    pdf.form_value("TNB")
    pdf.form_label("Supervisor:")
    pdf.form_value(None)  # blank
    pdf.form_label("QA Reviewer:")
    pdf.form_value(None)  # blank
    pdf.draw_line()

    # Section C — entirely blank
    pdf.section_header("SECTION C: EQUIPMENT USED")
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(40, 7, "Equipment ID", border=1, fill=True)
    pdf.cell(65, 7, "Description", border=1, fill=True)
    pdf.cell(40, 7, "Calibration Due", border=1, fill=True)
    pdf.ln()
    # 3 empty rows
    for _ in range(3):
        pdf.cell(40, 7, "", border=1)
        pdf.cell(65, 7, "", border=1)
        pdf.cell(40, 7, "", border=1)
        pdf.ln()
    pdf.draw_line()

    # Section D: Ingredients — partially filled
    pdf.section_header("SECTION D: RAW MATERIALS / INGREDIENTS")
    ingredients = [
        {"ingredient_name": "Ibuprofen", "weight_kg": 20.00, "lot_number": "LOT-IB-20240410"},
        {"ingredient_name": "Croscarmellose Sodium", "weight_kg": None, "lot_number": "LOT-CS-20240405"},
    ]
    _ingredient_table(pdf, ingredients, extra_col="Verified By", extra_vals=["TNB", ""])
    pdf.draw_line()

    # Section E — blank timestamps
    pdf.section_header("SECTION E: PROCESS TIMING")
    pdf.form_label("Start Time:")
    pdf.form_value(None)
    pdf.form_label("End Time:")
    pdf.form_value(None)
    pdf.form_label("Total Duration:")
    pdf.form_value(None)

    _footer_line(pdf)
    path = os.path.join(out_dir, "bmr-sample-03-partial.pdf")
    pdf.output(path)
    print(f"  Created: {path}")


# -------------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------------
def main():
    out_dir = os.path.join(os.path.dirname(__file__), "bmr")
    os.makedirs(out_dir, exist_ok=True)
    print("Generating BMR test PDFs...")
    create_bmr_01_clean(out_dir)
    create_bmr_02_messy(out_dir)
    create_bmr_03_partial(out_dir)
    print("Done.")


if __name__ == "__main__":
    main()
