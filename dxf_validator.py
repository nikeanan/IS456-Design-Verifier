"""
dxf_validator.py  –  IS 456 DXF Layout Parser & Geometry Validator
====================================================================
Refactored to:
  1. Use true polygon area (Shoelace formula) for LWPOLYLINE/POLYLINE columns
     instead of bounding-box area, which over-estimates rotated shapes.
  2. Expose classify_dxf_entities() as a single reusable helper so that
     Streamlit, tests, and CLI all share the same classification logic (DRY).
  3. Accept explicit Asc (steel area) in calculate_axial_capacity(); defaults
     to 1% of concrete gross-area if not provided by the caller.
"""

import ezdxf
from ezdxf import bbox
import json
import os
import csv
import math


# ---------------------------------------------------------------------------
# JSON code helpers
# ---------------------------------------------------------------------------

def generate_is456_json():
    codes = {
        "concrete": {"name": "M25", "strength": 30},
        "steel": {"name": "Fe500", "yield_strength": 500},
        "geometric_limits": {
            "min_column_height": 200,
            "min_beam_width": 200
        },
        "unit_scaler": 1000  # 1 unit = 1 mm.  Set to 1000 if drawing is in metres.
    }
    with open('dxf_codes.json', 'w') as f:
        json.dump(codes, f, indent=4)


# ---------------------------------------------------------------------------
# DXF file loader
# ---------------------------------------------------------------------------

def load_dxf_file(file_path):
    return ezdxf.readfile(file_path)


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def get_true_polygon_area(entity, scaler: float = 1.0) -> float:
    """
    Return the true cross-sectional area of a DXF polygon entity.

    Strategy per entity type
    -------------------------
    LWPOLYLINE / POLYLINE  →  Shoelace (Gauss) formula on the actual vertices.
                               This is correct even when the polygon is rotated,
                               skewed, or non-rectangular.
    CIRCLE                 →  π · r²  (exact, not affected by bounding box)
    LINE / INSERT / other  →  Falls back to bounding-box rectangle as a last
                               resort; the caller may flag the result.

    Parameters
    ----------
    entity  : ezdxf entity object
    scaler  : multiply every coordinate by this factor before area computation
              (use 1000 when drawing units are metres and output is in mm)

    Returns
    -------
    area in (drawing_units * scaler)²  — typically mm²
    flag    : bool – True when the Shoelace formula was used (exact),
                     False when bounding-box fallback was used (approximate)
    """
    dtype = entity.dxftype()

    if dtype == 'CIRCLE':
        r = entity.dxf.radius * scaler
        return math.pi * r * r, True

    if dtype in ('LWPOLYLINE', 'POLYLINE'):
        try:
            if dtype == 'LWPOLYLINE':
                pts = [(x * scaler, y * scaler) for x, y, *_ in entity.get_points()]
            else:  # POLYLINE (3-D)
                pts = [(v.dxf.location.x * scaler, v.dxf.location.y * scaler)
                       for v in entity.vertices]

            if len(pts) >= 3:
                # Shoelace formula  (works for any simple polygon, including rotated ones)
                n = len(pts)
                area = 0.0
                for i in range(n):
                    x0, y0 = pts[i]
                    x1, y1 = pts[(i + 1) % n]
                    area += x0 * y1 - x1 * y0
                return abs(area) / 2.0, True
        except Exception:
            pass  # fall through to bounding-box

    # Bounding-box fallback (approximate; warns caller via False flag)
    try:
        box = bbox.extents([entity])
        min_x, min_y, _ = box.extmin
        max_x, max_y, _ = box.extmax
        w = (max_x - min_x) * scaler
        h = (max_y - min_y) * scaler
        return w * h, False
    except Exception:
        return 0.0, False


def get_characteristic_dimension(entity, scaler: float = 1.0) -> float:
    """
    Return the governing dimension of a section entity (diameter for circles,
    max(width, height) for rectangular/polygonal shapes).
    Uses bounding-box for speed; dimension check is less rotation-sensitive.
    """
    dtype = entity.dxftype()
    if dtype == 'CIRCLE':
        return entity.dxf.radius * 2 * scaler

    try:
        box = bbox.extents([entity])
        min_x, min_y, _ = box.extmin
        max_x, max_y, _ = box.extmax
        return max((max_x - min_x) * scaler, (max_y - min_y) * scaler)
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Entity classification  (single reusable helper — DRY)
# ---------------------------------------------------------------------------

# Supported entity types for structural classification
_STRUCTURAL_ENTITY_TYPES = {'LINE', 'CIRCLE', 'LWPOLYLINE', 'POLYLINE', 'INSERT', 'ARC', 'SPLINE'}


def classify_dxf_entities(doc, dxf_path=None, use_ocr=False):
    """
    Classify DXF entities into structural components based on layer naming conventions.
    """
    result = {
        'beams': [],
        'columns': [],
        'slabs': [],
        'footings': [],
        'unclassified': []
    }

    if doc is None:
        return result

    msp = doc.modelspace()
    for entity in msp:
        if not hasattr(entity.dxf, 'layer'):
            continue
        
        layer = entity.dxf.layer.upper()

        if ('BEAM' in layer) or ('BM' in layer and 'COL' not in layer):
            result['beams'].append(entity)
        elif 'COL' in layer:
            result['columns'].append(entity)
        elif 'SLAB' in layer:
            result['slabs'].append(entity)
        elif 'FOOT' in layer:
            result['footings'].append(entity)
        else:
            result['unclassified'].append(entity)

    # Trigger OCR fallback if no structural entities were found and OCR is enabled
    if use_ocr and not any(result[k] for k in ['beams', 'columns', 'slabs', 'footings']):
        print("[WARNING] No native structural entities found. Triggering OCR Fallback...")
        try:
            from engine.ocr_extractor import OCRExtractor
            ocr = OCRExtractor()
            
            ocr_results = ocr.extract_text_from_dxf(dxf_path if dxf_path else "current_drawing.dxf")
            print(f"OCR Extracted: {ocr_results['extracted_text']}")
            if 'structured_data' in ocr_results:
                result['ocr_data'] = ocr_results['structured_data']
        except ImportError:
            print("[ERROR] OCR Extractor module not found.")

    return result


# ---------------------------------------------------------------------------
# Legacy helpers (kept for backward compatibility with existing callers)
# ---------------------------------------------------------------------------

def extract_beam_column_info(doc):
    """Backward-compatible wrapper around classify_dxf_entities."""
    classified = classify_dxf_entities(doc)
    return classified['beams'], classified['columns']


# ---------------------------------------------------------------------------
# Structural capacity
# ---------------------------------------------------------------------------

def calculate_axial_capacity(
    area_concrete: float,
    fck: float = 30,
    fy: float = 500,
    area_steel: float = None,
) -> dict:
    """
    IS 456 short-column axial capacity:  Pu = 0.4·fck·Ac + 0.67·fy·Asc

    Parameters
    ----------
    area_concrete : float  – gross concrete cross-sectional area [mm²]
    fck           : float  – characteristic compressive strength [MPa]
    fy            : float  – steel yield strength [MPa]
    area_steel    : float  – longitudinal steel area [mm²].
                             If None → assumed as 1 % of gross concrete area.

    Returns
    -------
    dict with keys:
        ultimate_capacity_kn  – Pu in kN
        used_area_steel       – Asc used [mm²]
        reinforcement_ratio   – p = Asc / Ag (as fraction)
        calculation_note      – descriptive string
        area_steel_assumed    – bool, True when Asc was not user-provided
    """
    if area_concrete <= 0 or fck <= 0 or fy <= 0:
        raise ValueError("area_concrete, fck, and fy must all be positive.")

    steel_assumed = area_steel is None
    if steel_assumed:
        area_steel = area_concrete * 0.01   # IS 456 minimum = 0.8 %; use 1 %
        note = "Asc assumed at 1 % of gross concrete area (IS 456 Cl. 26.5.3.1). Provide Asc for exact result."
    else:
        if area_steel <= 0:
            raise ValueError("area_steel must be positive when provided.")
        note = "User-provided Asc used for calculation."

    capacity_n = (0.4 * fck * area_concrete) + (0.67 * fy * area_steel)
    capacity_kn = capacity_n / 1000

    return {
        "ultimate_capacity_kn":  round(capacity_kn, 2),
        "used_area_steel":       round(area_steel, 2),
        "reinforcement_ratio":   round(area_steel / area_concrete, 4),
        "calculation_note":      note,
        "area_steel_assumed":    steel_assumed,
    }


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def export_to_csv(report_data, file_path='compliance_report.csv'):
    if not report_data:
        return
    keys = report_data[0].keys()
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(report_data)
    print(f"Report exported to {file_path}")


# ---------------------------------------------------------------------------
# check_geometry  (CLI / legacy path; Streamlit uses classify_dxf_entities)
# ---------------------------------------------------------------------------

def check_geometry(beams, columns, codes):
    min_column_height = codes['geometric_limits']['min_column_height']
    min_beam_width    = codes['geometric_limits']['min_beam_width']
    scaler            = codes.get('unit_scaler', 1)
    fck               = codes['concrete']['strength']
    fy                = codes['steel']['yield_strength']

    report_data = []

    print("--- Geometric Compliance Report ---")
    for i, beam in enumerate(beams):
        try:
            dim = get_characteristic_dimension(beam, scaler)
            status = "Pass" if dim >= min_beam_width else f"FAIL: {dim:.1f}mm < {min_beam_width}mm"
            print(f"Beam {i+1}: Width {dim:.1f}mm – {status}")
            report_data.append({"Type": "BEAM", "ID": i+1,
                                 "Dimension_mm": f"{dim:.1f}", "Status": status, "Capacity_kN": "N/A"})
        except Exception as e:
            print(f"Beam {i+1}: Error – {e}")

    print("\n--- Structural Capacity Analysis ---")
    for i, column in enumerate(columns):
        try:
            area_c, exact = get_true_polygon_area(column, scaler)
            dim = get_characteristic_dimension(column, scaler)
            area_method = "Shoelace" if exact else "BBox (approx)"
            status = "Pass" if dim >= min_column_height else f"FAIL: {dim:.1f}mm < {min_column_height}mm"

            cap = calculate_axial_capacity(area_concrete=area_c, fck=fck, fy=fy)
            print(f"Column {i+1}: {dim:.1f}mm | Area={area_c:.0f}mm² [{area_method}] | "
                  f"Pu={cap['ultimate_capacity_kn']}kN – {status}")

            report_data.append({
                "Type":            "COLUMN",
                "ID":              i + 1,
                "Dimension_mm":    f"{dim:.1f}",
                "Area_mm2":        f"{area_c:.0f}",
                "Area_Method":     area_method,
                "Status":          status,
                "Capacity_kN":     cap['ultimate_capacity_kn'],
                "Note":            cap['calculation_note'],
            })
        except Exception as e:
            print(f"Column {i+1}: Error – {e}")

    export_to_csv(report_data)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    generate_is456_json()
    with open('dxf_codes.json', 'r') as f:
        codes = json.load(f)

    file_path = 'sample_plan.dxf'
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    doc = load_dxf_file(file_path)
    classified = classify_dxf_entities(doc)
    beams, columns = classified['beams'], classified['columns']
    check_geometry(beams, columns, codes)


if __name__ == "__main__":
    main()