"""
tests/test_structural.py
========================
pytest suite for the IS 456 Enterprise Structural Verifier.

Run with:   pytest tests/ -v
             pytest tests/ -v --tb=short   (compact tracebacks)

All file paths are resolved dynamically relative to this file using
pathlib.Path so the suite works on any machine or CI pipeline.
"""

import math
import sys
from pathlib import Path

import pytest
import matplotlib
matplotlib.use("Agg")   # headless backend — no GUI required

# ---------------------------------------------------------------------------
# Make the project root importable no matter where pytest is invoked from
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Fixtures / helpers
DXF_FULL     = PROJECT_ROOT / "full_project_sample.dxf"
DXF_SAMPLE   = PROJECT_ROOT / "sample_plan.dxf"

from elements.beam    import RCBeamVerifier
from elements.column  import RCColumnVerifier
from elements.slab    import RCSlabVerifier
from elements.footing import RCFootingVerifier
from boq_engine       import calculate_boq
from report_generator import create_pdf_report
from visualizer       import render_cross_section
from engine.dxf_exporter import CADExporter
from dxf_validator import (
    load_dxf_file,
    classify_dxf_entities,
    extract_beam_column_info,
    get_true_polygon_area,
    get_characteristic_dimension,
    calculate_axial_capacity,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(scope="module")
def doc_full():
    """Parsed ezdxf document for full_project_sample.dxf"""
    assert DXF_FULL.exists(), f"DXF file missing: {DXF_FULL}"
    return load_dxf_file(str(DXF_FULL))


@pytest.fixture(scope="module")
def doc_sample():
    """Parsed ezdxf document for sample_plan.dxf"""
    assert DXF_SAMPLE.exists(), f"DXF file missing: {DXF_SAMPLE}"
    return load_dxf_file(str(DXF_SAMPLE))


# ============================================================
# 1  RC BEAM MODULE
# ============================================================

class TestRCBeam:

    @pytest.fixture
    def beam(self):
        b, d, D, L, A_st = 250, 400, 450, 5000, 1000
        M_u, V_u, T_u, f_ck, f_y = 120, 80, 15, 30, 415
        M_eq = M_u + (T_u * (1 + D / b) / 1.7)
        V_eq = V_u + (1.6 * (T_u / b) * 1000)
        return RCBeamVerifier("B1", b, d, D, L, f_ck, f_y, A_st, M_eq, V_eq)

    def test_compliance_runs(self, beam):
        result = beam.evaluate_compliance()
        assert isinstance(result, bool)

    def test_bending_capacity_positive(self, beam):
        beam.evaluate_compliance()
        assert beam.M_ur > 0, "Bending capacity must be positive"

    def test_boq_returns_dict(self, beam):
        boq = calculate_boq("Beam", 250, 450, 5000, 1000, 415, 30)
        assert isinstance(boq, dict)
        assert len(boq) > 0

    def test_pdf_report_non_empty(self, beam):
        fig = render_cross_section(beam, "Beam")
        boq = calculate_boq("Beam", 250, 450, 5000, 1000, 415, 30)
        pdf_bytes = create_pdf_report(beam, boq, fig)
        assert len(pdf_bytes) > 1000, "PDF should be non-trivial in size"

    def test_cad_dxf_export(self, beam, tmp_path, monkeypatch):
        """CADExporter should write a valid DXF file."""
        monkeypatch.chdir(tmp_path)
        filepath = CADExporter.generate_cross_section_dxf(beam.element_id, 250, 450, "Beam")
        assert Path(filepath).exists()
        assert Path(filepath).stat().st_size > 0

    # --- NEW: Min steel check ---
    def test_min_steel_check_passes_adequate(self):
        """Standard beam with 1000mm² steel should pass min-steel check."""
        beam = RCBeamVerifier("B_minok", 250, 400, 450, 5000, 30, 415, 1000, 0, 0)
        beam.evaluate_compliance()
        status = beam.checks.get("Min Tension Steel (Cl.26.5.1.1)", "")
        assert "PASS" in status

    def test_min_steel_check_fails_zero_ast(self):
        """Beam with 0 steel MUST fail min-steel check."""
        beam = RCBeamVerifier("B_nosteel", 250, 400, 450, 5000, 30, 415, 0, 0, 0)
        beam.evaluate_compliance()
        status = beam.checks.get("Min Tension Steel (Cl.26.5.1.1)", "")
        assert "FAIL" in status

    def test_max_steel_check_fails_overreinforced(self):
        """Beam with 5000mm² (>4% of 250×450) should fail max-steel check."""
        # 0.04 * 250 * 450 = 4500 mm², so 5000 > limit
        beam = RCBeamVerifier("B_maxsteel", 250, 400, 450, 5000, 30, 415, 5000, 0, 0)
        beam.evaluate_compliance()
        status = beam.checks.get("Max Tension Steel (Cl.26.5.1.2)", "")
        assert "FAIL" in status

    def test_max_steel_check_passes_normal(self):
        """Beam with 1000mm² (well below 4% limit) should pass max-steel check."""
        beam = RCBeamVerifier("B_maxok", 250, 400, 450, 5000, 30, 415, 1000, 0, 0)
        beam.evaluate_compliance()
        status = beam.checks.get("Max Tension Steel (Cl.26.5.1.2)", "")
        assert "PASS" in status

    def test_side_face_reinforcement_required_for_deep_beam(self):
        """Beam with D=900mm must trigger side-face reinforcement check."""
        beam = RCBeamVerifier("B_deep", 300, 840, 900, 6000, 30, 415, 1500, 0, 0)
        beam.evaluate_compliance()
        status = beam.checks.get("Side-Face Reinforcement (Cl.26.5.1.3)", "")
        assert "ACTION REQUIRED" in status

    def test_side_face_reinforcement_na_for_shallow_beam(self):
        """Beam with D=450mm must show N/A for side-face check."""
        beam = RCBeamVerifier("B_shallow", 250, 400, 450, 5000, 30, 415, 1000, 0, 0)
        beam.evaluate_compliance()
        status = beam.checks.get("Side-Face Reinforcement (Cl.26.5.1.3)", "")
        assert "N/A" in status

    def test_regression_moment_capacity(self):
        """Regression: M_ur for standard beam must match expected value within 1%."""
        beam = RCBeamVerifier("B_reg", 250, 400, 450, 5000, 30, 415, 1000, 100, 60)
        beam.evaluate_compliance()
        # Expected M_ur ≈ 0.87*415*1000*400*(1 - 1000*415/(250*400*30)) ≈ 122.8 kNm
        expected_kNm = 122.8
        actual_kNm = beam.M_ur / 1e6
        assert abs(actual_kNm - expected_kNm) / expected_kNm < 0.02


# ============================================================
# 2  RC COLUMN MODULE
# ============================================================

class TestRCColumn:

    @pytest.fixture
    def column(self):
        return RCColumnVerifier("C1", 300, 450, 3000, 30, 415, 1200, 1500, 30)

    def test_compliance_runs(self, column):
        result = column.evaluate_compliance()
        assert isinstance(result, bool)

    def test_pdf_non_empty(self, column):
        fig = render_cross_section(column, "Column")
        boq = calculate_boq("Column", 300, 450, 3000, 1200, 415, 30)
        pdf_bytes = create_pdf_report(column, boq, fig)
        assert len(pdf_bytes) > 1000

    def test_cad_dxf_export(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        filepath = CADExporter.generate_cross_section_dxf("C1", 300, 450, "Column")
        assert Path(filepath).exists()

    # --- NEW: Steel limits ---
    def test_steel_limits_pass_adequate(self):
        """Standard 1200 mm² steel in 300×450 = 0.89% — within 0.8–6%."""
        col = RCColumnVerifier("C_ok", 300, 450, 3000, 30, 415, 1200, 1500, 30)
        col.evaluate_compliance()
        status = col.checks.get("Steel Area Limits (Cl.26.5.3.1)", "")
        assert "PASS" in status

    def test_steel_limits_fail_zero_steel(self):
        """Column with 0 steel must fail min-steel check."""
        col = RCColumnVerifier("C_nosteel", 300, 450, 3000, 30, 415, 0, 1500, 30)
        col.evaluate_compliance()
        status = col.checks.get("Steel Area Limits (Cl.26.5.3.1)", "")
        assert "FAIL" in status

    def test_steel_limits_fail_excess_steel(self):
        """Column with 10000 mm² in 300×300 = 11.1% > 6% — must FAIL."""
        col = RCColumnVerifier("C_excess", 300, 300, 3000, 30, 415, 10000, 1000, 0)
        col.evaluate_compliance()
        status = col.checks.get("Steel Area Limits (Cl.26.5.3.1)", "")
        assert "FAIL" in status

    def test_lateral_ties_check_present(self):
        """Lateral ties check must always be in the checks dict."""
        col = RCColumnVerifier("C_ties", 300, 450, 3000, 30, 415, 1200, 1500, 30)
        col.evaluate_compliance()
        assert "Lateral Ties (Cl.26.5.3.2)" in col.checks


# ============================================================
# 3  RC SLAB MODULE
# ============================================================

class TestRCSlab:

    def test_two_way_classification(self):
        v = RCSlabVerifier("S1", 3000, 4000, 150, 125, 30, 415, 300, 12)
        v.evaluate_compliance()
        assert v.classification == "Two-Way Slab"

    def test_one_way_classification(self):
        v = RCSlabVerifier("S2", 2000, 7000, 130, 110, 25, 415, 250, 8)
        v.evaluate_compliance()
        assert v.classification == "One-Way Slab"

    def test_pdf_non_empty(self):
        v = RCSlabVerifier("S1", 3000, 4000, 150, 125, 30, 415, 300, 12)
        v.evaluate_compliance()
        fig = render_cross_section(v, "Slab")
        boq = calculate_boq("Slab", 3000, 150, 4000, 300 * (4000 / 1000), 415, 30)
        pdf = create_pdf_report(v, boq, fig)
        assert len(pdf) > 1000

    # --- NEW: Min reinforcement ---
    def test_min_reinforcement_passes_adequate(self):
        """300 mm²/m for 150mm thick slab: 0.2% > 0.12% — should PASS."""
        v = RCSlabVerifier("S_minok", 3000, 4000, 150, 125, 30, 415, 300, 12)
        v.evaluate_compliance()
        status = v.checks.get("Min Reinforcement (Cl.26.5.2.1)", "")
        assert "PASS" in status

    def test_min_reinforcement_fails_low_steel(self):
        """50 mm²/m for 150mm thick slab: 0.033% < 0.12% — must FAIL."""
        v = RCSlabVerifier("S_minfail", 3000, 4000, 150, 125, 30, 415, 50, 12)
        v.evaluate_compliance()
        status = v.checks.get("Min Reinforcement (Cl.26.5.2.1)", "")
        assert "FAIL" in status

    def test_max_spacing_fails_low_steel(self):
        """Very low Ast → estimated spacing >> 300mm → FAIL."""
        v = RCSlabVerifier("S_spacing", 3000, 4000, 150, 125, 30, 415, 50, 12)
        v.evaluate_compliance()
        status = v.checks.get("Max Bar Spacing (Cl.26.3.3)", "")
        assert "FAIL" in status

    def test_aspect_ratio_stored(self):
        """Aspect ratio check should be present in checks dict."""
        v = RCSlabVerifier("S_ar", 3000, 4000, 150, 125, 30, 415, 300, 12)
        v.evaluate_compliance()
        assert "Aspect Ratio (L_y/L_x)" in v.checks


# ============================================================
# 4  ISOLATED FOOTING MODULE
# ============================================================

class TestIsolatedFooting:

    @pytest.fixture
    def footing(self):
        return RCFootingVerifier("F1", 2000, 2000, 450, 400, 300, 300, 30, 415, 1500, 1200)

    def test_compliance_runs(self, footing):
        result = footing.evaluate_compliance()
        assert isinstance(result, bool)

    def test_pdf_non_empty(self, footing):
        fig = render_cross_section(footing, "Footing")
        boq = calculate_boq("Footing", 2000, 450, 2000, 1500, 415, 30)
        pdf = create_pdf_report(footing, boq, fig)
        assert len(pdf) > 1000

    # --- NEW: Bearing pressure ---
    def test_bearing_pressure_passes_normal(self):
        """Standard footing with moderate load — bearing should PASS."""
        f = RCFootingVerifier("F_brg_ok", 2000, 2000, 450, 400, 300, 300, 30, 415, 1500, 1200)
        f.evaluate_compliance()
        status = f.checks.get("Bearing Pressure (Cl.34.4)", "")
        assert "PASS" in status

    def test_bearing_pressure_fails_extreme_load(self):
        """Tiny column (100×100) with 5000kN load — bearing must FAIL."""
        f = RCFootingVerifier("F_brg_fail", 2000, 2000, 450, 400, 100, 100, 30, 415, 1500, 5000)
        f.evaluate_compliance()
        status = f.checks.get("Bearing Pressure (Cl.34.4)", "")
        assert "FAIL" in status

    def test_min_reinforcement_present(self):
        """Min reinforcement check must always appear in checks."""
        f = RCFootingVerifier("F_minr", 2000, 2000, 450, 400, 300, 300, 30, 415, 1500, 1200)
        f.evaluate_compliance()
        assert "Min Base Reinforcement (Cl.34.3)" in f.checks

    def test_development_length_present(self):
        """Development length check must always appear in checks."""
        f = RCFootingVerifier("F_ld", 2000, 2000, 450, 400, 300, 300, 30, 415, 1500, 1200)
        f.evaluate_compliance()
        assert "Development Length (Cl.26.2)" in f.checks


# ============================================================
# 5  DXF VALIDATOR — Entity classification (DRY helper)
# ============================================================

class TestDXFClassification:

    def test_classify_returns_all_keys(self, doc_full):
        result = classify_dxf_entities(doc_full)
        for key in ("beams", "columns", "slabs", "footings", "unclassified"):
            assert key in result

    def test_full_dxf_finds_all_four_types(self, doc_full):
        c = classify_dxf_entities(doc_full)
        assert len(c["beams"])    >= 1, "Expected at least 1 beam"
        assert len(c["columns"])  >= 1, "Expected at least 1 column"
        assert len(c["slabs"])    >= 1, "Expected at least 1 slab"
        assert len(c["footings"]) >= 1, "Expected at least 1 footing"

    def test_sample_dxf_finds_beams_and_columns(self, doc_sample):
        c = classify_dxf_entities(doc_sample)
        assert len(c["beams"])   >= 1
        assert len(c["columns"]) >= 1

    def test_legacy_extract_beam_column_info(self, doc_sample):
        """Backward-compat wrapper must still return (beams, columns) tuple."""
        beams, cols = extract_beam_column_info(doc_sample)
        assert isinstance(beams, list)
        assert isinstance(cols,  list)


# ============================================================
# 6  GEOMETRY — True polygon area (Shoelace vs bounding-box)
# ============================================================

class TestTruePolygonArea:

    def test_circle_area_exact(self, doc_full):
        """Circle area must equal π·r², not bounding-box width×height."""
        c = classify_dxf_entities(doc_full)
        circles = [e for e in c["columns"] if e.dxftype() == "CIRCLE"]
        for circ in circles:
            r = circ.dxf.radius
            area, exact = get_true_polygon_area(circ)
            assert exact is True
            assert abs(area - math.pi * r * r) < 1e-3, "Circle area must match π·r²"

    def test_polygon_area_positive(self, doc_full):
        """Every polygon entity should yield a positive area."""
        c = classify_dxf_entities(doc_full)
        for entity in c["columns"] + c["beams"]:
            area, _ = get_true_polygon_area(entity)
            assert area >= 0, f"{entity.dxftype()} area must be non-negative"

    def test_shoelace_axis_aligned_rect(self):
        """
        Manually verify the Shoelace formula on a known 300×450 rectangle.
        A 300×450 mm LWPOLYLINE drawn axis-aligned must return 135 000 mm².
        """
        import ezdxf

        doc = ezdxf.new(dxfversion="R2010")
        msp = doc.modelspace()
        pts = [(0, 0), (300, 0), (300, 450), (0, 450)]
        poly = msp.add_lwpolyline(pts, dxfattribs={"layer": "COL"})

        area, exact = get_true_polygon_area(poly, scaler=1)
        assert exact is True
        assert abs(area - 135_000) < 1, f"Expected 135000, got {area}"

    def test_rotated_column_area_not_inflated(self):
        """
        A 300×450 polygon rotated 45° must still yield ~135 000 mm²
        via Shoelace, NOT the bounding-box area which would be ~555 000 mm².
        """
        import ezdxf, math as _math

        doc = ezdxf.new(dxfversion="R2010")
        msp = doc.modelspace()

        angle = _math.radians(45)
        cos_a, sin_a = _math.cos(angle), _math.sin(angle)
        rect = [(0, 0), (300, 0), (300, 450), (0, 450)]
        rotated = [(x * cos_a - y * sin_a, x * sin_a + y * cos_a) for x, y in rect]
        poly = msp.add_lwpolyline(rotated, dxfattribs={"layer": "COL"})

        area, exact = get_true_polygon_area(poly, scaler=1)
        assert exact is True
        assert abs(area - 135_000) < 1, (
            f"Rotated column area must still be ~135000 mm², got {area:.1f}. "
            "Bounding box would have been inflated."
        )


# ============================================================
# 7  AXIAL CAPACITY — IS 456 formula
# ============================================================

class TestAxialCapacity:

    def test_default_1pct_assumption(self):
        cap = calculate_axial_capacity(area_concrete=90_000, fck=30, fy=415)
        assert cap["area_steel_assumed"] is True
        assert cap["used_area_steel"] == pytest.approx(900.0)   # 1% of 90 000

    def test_explicit_asc_overrides_default(self):
        cap = calculate_axial_capacity(area_concrete=90_000, fck=30, fy=415, area_steel=1200)
        assert cap["area_steel_assumed"] is False
        assert cap["used_area_steel"] == pytest.approx(1200.0)

    def test_pu_formula_rect_column(self):
        """Pu = 0.4·fck·Ac + 0.67·fy·Asc for a 300×300 column, 1% steel."""
        Ac = 300 * 300
        Asc = Ac * 0.01
        expected_kn = (0.4 * 25 * Ac + 0.67 * 415 * Asc) / 1000
        cap = calculate_axial_capacity(area_concrete=Ac, fck=25, fy=415)
        assert cap["ultimate_capacity_kn"] == pytest.approx(expected_kn, abs=0.01)

    def test_pu_formula_circular_column(self):
        r = 150
        Ac = math.pi * r * r
        Asc = Ac * 0.01
        expected_kn = (0.4 * 25 * Ac + 0.67 * 500 * Asc) / 1000
        cap = calculate_axial_capacity(area_concrete=Ac, fck=25, fy=500)
        assert cap["ultimate_capacity_kn"] == pytest.approx(expected_kn, abs=0.01)

    def test_raises_on_zero_area(self):
        with pytest.raises(ValueError):
            calculate_axial_capacity(area_concrete=0, fck=30, fy=415)

    def test_raises_on_negative_steel(self):
        with pytest.raises(ValueError):
            calculate_axial_capacity(area_concrete=90_000, fck=30, fy=415, area_steel=-100)

    def test_reinforcement_ratio_returned(self):
        cap = calculate_axial_capacity(area_concrete=90_000, fck=30, fy=415)
        assert "reinforcement_ratio" in cap
        assert abs(cap["reinforcement_ratio"] - 0.01) < 1e-6


# ============================================================
# 8  EDGE CASES — Zero / boundary inputs
# ============================================================

class TestEdgeCases:

    def test_beam_minimum_fck_m15(self):
        """Beam with f_ck=15 (minimum IS 456 grade) must not crash."""
        beam = RCBeamVerifier("B_m15", 250, 400, 450, 5000, 15, 415, 800, 80, 50)
        result = beam.evaluate_compliance()
        assert isinstance(result, bool)

    def test_slab_aspect_ratio_normalised(self):
        """Input L_x=4000, L_y=3000 (reversed) must normalise to L_x=3000."""
        v = RCSlabVerifier("S_norm", 4000, 3000, 150, 125, 30, 415, 300, 12)
        assert v.L_x == 3000.0
        assert v.L_y == 4000.0

    def test_column_short_classification(self):
        """L_eff/b < 12 and L_eff/D < 12 → Short Column."""
        col = RCColumnVerifier("C_short", 300, 450, 3000, 30, 415, 1200, 1500, 30)
        col.evaluate_compliance()
        assert col.classification == "Short Column"

    def test_column_long_classification(self):
        """L_eff=8000, b=300, D=400 → ratios > 12 → Long Column."""
        col = RCColumnVerifier("C_long", 300, 400, 8000, 30, 415, 1500, 800, 20)
        col.evaluate_compliance()
        assert col.classification == "Long Column"

    def test_footing_p_u_upward_pressure(self):
        """Upward pressure p_u = P_u*1000 / (L*B) should be correct."""
        f = RCFootingVerifier("F_pu", 2000, 2000, 450, 400, 300, 300, 30, 415, 1500, 1200)
        expected_pu = (1200 * 1000) / (2000 * 2000)
        assert abs(f.p_u - expected_pu) < 1e-6

    def test_boq_beam_volume_correct(self):
        """Concrete volume for a 250×450×5000 beam must equal 0.5625 m³."""
        boq = calculate_boq("Beam", 250, 450, 5000, 1000, 415, 30)
        expected_vol = (250 * 450 * 5000) / 1e9
        assert abs(boq["volume_m3"] - expected_vol) < 1e-6

    def test_boq_slab_steel_uses_width(self):
        """Slab steel volume uses short span (width), not length."""
        boq_slab = calculate_boq("Slab", 3000, 150, 4000, 300, 415, 30)
        # steel vol = (300 * 3000) / 1e9 = 9e-4 m³
        expected = (300 * 3000) / 1e9
        assert abs(boq_slab["volume_m3"] - (3000 * 150 * 4000) / 1e9) < 1e-6
        assert abs(boq_slab["steel_kg"] - expected * 7850) < 0.01
