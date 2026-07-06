# report_generator.py
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import tempfile
import os
import matplotlib.pyplot as plt

class StructuralReport(FPDF):
    def normalize_text(self, text: str) -> str:
        """Sanitize all text before fpdf processes it to avoid UnicodeEncodeError"""
        text = str(text)
        # Mathematical and greek symbol substitutions
        text = text.replace("≥", ">=").replace("≤", "<=").replace("≈", "~")
        text = text.replace("α", "alpha").replace("×", "x").replace("²", "^2")
        text = text.replace("σ", "sigma").replace("τ", "tau").replace("μ", "mu")
        # Strip any remaining unencodable characters
        text = text.encode('latin-1', 'ignore').decode('latin-1')
        return super().normalize_text(text)

    def header(self):
        self.set_font('Helvetica', 'B', 15)
        self.set_text_color(50, 50, 50)
        self.cell(0, 10, 'Enterprise IS 456 Structural Verification',
                  border=False, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        self.set_line_width(0.5)
        self.line(10, 20, 200, 20)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

def create_pdf_report(verifier, boq_data, fig):
    """
    Generates a dynamic PDF report from any structural element object.
    """
    # 1. Initialize the PDF document
    pdf = StructuralReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

   # --- 1. Element Summary ---
    pdf.set_font("Helvetica", 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10,
             f"Element ID: {verifier.element_id} ({verifier.__class__.__name__.replace('Verifier', '')})",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
    pdf.ln(2)

    pdf.set_font("Helvetica", '', 10)
    pdf.cell(0, 6, f"Concrete Grade: M{verifier.f_ck} | Steel Grade: Fe{verifier.f_y}",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Safely adapt dimensions based on the element type
    depth_val = getattr(verifier, 'D', getattr(verifier, 'd', 'N/A'))

    if hasattr(verifier, 'L') and hasattr(verifier, 'B'):
        # Footing Geometry
        pdf.cell(0, 6, f"Dimensions: {verifier.L} mm (L) x {verifier.B} mm (B) x {depth_val} mm (D)",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    elif hasattr(verifier, 'L_x') and hasattr(verifier, 'L_y'):
        # Slab Geometry
        pdf.cell(0, 6, f"Dimensions: {verifier.L_x} mm (Lx) x {verifier.L_y} mm (Ly) x {depth_val} mm (D)",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    else:
        # Beam/Column Geometry
        width_val = getattr(verifier, 'b', 'N/A')
        pdf.cell(0, 6, f"Dimensions: {width_val} mm (Width) x {depth_val} mm (Depth)",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(5)

   # --- 2. Compliance Status Breakdown ---
    pdf.set_font("Helvetica", 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, "Limit State Verification Summary",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, border='B')
    pdf.ln(3)

    pdf.set_font("Helvetica", 'B', 10)

    # Iterate through each specific code check
    for check_name, status in verifier.checks.items():
        # Safely convert any booleans to strings to prevent TypeErrors
        status_str = str(status).replace("≥", ">=").replace("≤", "<=").replace("≈", "~")
        check_name = str(check_name).replace("≥", ">=").replace("≤", "<=").replace("≈", "~")

        if "FAIL" in status_str or status_str == "False":
            pdf.set_text_color(220, 20, 60)   # Crimson Red
        elif "ACTION" in status_str or "WARNING" in status_str or "PENDING" in status_str:
            pdf.set_text_color(255, 140, 0)   # Dark Orange
        else:
            pdf.set_text_color(34, 139, 34)   # Forest Green

        pdf.cell(0, 6, f"{check_name}: {status_str}",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_text_color(0, 0, 0)  # Reset to black
    pdf.ln(5)

    # --- 3. Step-by-Step Mathematical Logs ---
    if hasattr(verifier, 'calculations') and verifier.calculations:
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 10, "Traceable Mathematical Formulations",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT, border='B')
        pdf.ln(3)

        pdf.set_font("Courier", '', 9)
        for calc in verifier.calculations:
            step_str = str(calc['step']).replace("≥", ">=").replace("≤", "<=").replace("≈", "~").replace("α", "alpha").replace("×", "x").replace("²", "^2")
            formula_str = str(calc['formula']).replace("≥", ">=").replace("≤", "<=").replace("≈", "~").replace("α", "alpha").replace("×", "x").replace("²", "^2")
            result_str = str(calc['result']).replace("≥", ">=").replace("≤", "<=").replace("≈", "~").replace("α", "alpha").replace("×", "x").replace("²", "^2")
            
            pdf.set_font("Courier", 'B', 9)
            pdf.cell(0, 5, f"Step: {step_str}",
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Courier", '', 9)
            pdf.cell(0, 5, f"Formula: {formula_str}",
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.cell(0, 5, f"Result:  {result_str}",
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(3)

    # --- 4. Suggestions Engine ---
    if hasattr(verifier, 'suggestions') and verifier.suggestions:
        pdf.set_font("Helvetica", 'B', 12)

        # Hard-reset cursor to left margin (10mm) before starting this section
        pdf.set_x(10)
        pdf.cell(0, 10, "Engineering Recommendations",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT, border='B')
        pdf.ln(3)

        pdf.set_font("Helvetica", '', 10)
        for suggestion in verifier.suggestions:
            pdf.set_x(10)  # Guarantee the cursor is at the left edge for every new bullet
            # Use explicit width (190mm = 210mm A4 width - 20mm margins) instead of '0'
            pdf.multi_cell(190, 6, f"- {suggestion}")

        pdf.ln(5)

    # --- 5. Embed Matplotlib Visualization ---
    if fig:
        # Save matplotlib figure to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
            # Change colors to black/white for printing purposes before saving
            for text in fig.findobj(match=plt.Text): text.set_color('black')
            for line in fig.findobj(match=plt.Line2D): line.set_color('black')
            fig.patch.set_facecolor('white')
            fig.savefig(tmpfile.name, format="png", bbox_inches='tight', dpi=300)

        pdf.add_page()
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 10, "Cross-Section Detailing",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.image(tmpfile.name, x=50, w=100)

        # Cleanup temporary image file
        os.remove(tmpfile.name)

    # --- 6. Bill of Quantities ---
    if boq_data:
        pdf.ln(10)
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 10, "Estimated Bill of Quantities (BOQ)",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT, border='B')
        pdf.ln(3)
        pdf.set_font("Helvetica", '', 10)
        pdf.cell(0, 6, f"Concrete Volume: {boq_data['volume_m3']} m3",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(0, 6, f"Main Steel Weight: {boq_data['steel_kg']} kg",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(0, 6, f"Estimated Material Cost: INR {boq_data['total_cost']:,.2f}",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Output to byte string for Streamlit download
    return bytes(pdf.output())

# ---------------------------------------------------------------------------
# Batch Report Generation
# ---------------------------------------------------------------------------

def create_batch_summary_report(batch_results: list, benchmark_metrics: dict = None):
    """
    Generates a single summary PDF for a batch of DXF drawings.
    batch_results: list of dicts with 'drawing_id', 'total_elements', 'passed', 'failed', 'warnings'
    """
    pdf = StructuralReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, "Batch Compliance Summary Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.ln(10)
    
    if benchmark_metrics:
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 10, "Benchmark Metrics (Ground Truth Comparison)", new_x=XPos.LMARGIN, new_y=YPos.NEXT, border='B')
        pdf.set_font("Helvetica", '', 10)
        pdf.cell(0, 6, f"Total Checks Evaluated: {benchmark_metrics.get('total_evaluated', 0)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(0, 6, f"Precision: {benchmark_metrics.get('precision', 0):.3f}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(0, 6, f"Recall: {benchmark_metrics.get('recall', 0):.3f}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(0, 6, f"F1-Score: {benchmark_metrics.get('f1_score', 0):.3f}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(5)

    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, "Drawing Summary Breakdown", new_x=XPos.LMARGIN, new_y=YPos.NEXT, border='B')
    pdf.ln(3)

    pdf.set_font("Helvetica", '', 10)
    for result in batch_results:
        status = "PASS" if result.get('failed', 0) == 0 else "FAIL"
        pdf.set_text_color(34, 139, 34) if status == "PASS" else pdf.set_text_color(220, 20, 60)
        pdf.cell(0, 6, f"Drawing: {result['drawing_id']} - Overall Status: {status}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.set_text_color(50, 50, 50)
        pdf.cell(0, 6, f"  Elements: {result.get('total_elements', 0)} | Passed: {result.get('passed', 0)} | Failed: {result.get('failed', 0)} | Warnings: {result.get('warnings', 0)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

    return bytes(pdf.output())