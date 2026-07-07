import ezdxf
import json
import os
import csv

def generate_is456_json():
    codes = {
        "concrete": {"name": "M25", "strength": 30},
        "steel": {"name": "Fe500", "yield_strength": 500},
        "geometric_limits": {
            "min_column_height": 200,
            "min_beam_width": 200
        },
        "unit_scaler": 1000  # Default: 1 unit = 1mm. If meters, set to 1000.
    }
    with open('is456_codes.json', 'w') as f:
        json.dump(codes, f, indent=4)

def load_dxf_file(file_path):
    return ezdxf.readfile(file_path)

def extract_beam_column_info(doc):
    beams = []
    columns = []
    for entity in doc.modelspace():
        if entity.dxftype() == 'LWPOLYLINE':
            layer = entity.dxf.layer
            # Robust check for variations in CAD drafting styles
            if 'BEAM' in layer.upper():
                beams.append(entity)
            elif 'COL' in layer.upper():
                columns.append(entity)
    return beams, columns

def calculate_axial_capacity(area_concrete: float, area_steel: float = None, fck: float = 30, fy: float = 500) -> dict:
    if area_concrete <= 0 or fck <= 0 or fy <= 0:
        raise ValueError("Area of concrete, fck, and fy must be positive values.")

    if area_steel is None:
        area_steel = area_concrete * 0.01 # Assume 1% reinforcement
        note = "Steel area estimated at 1% reinforcement ratio."
    else:
        if area_steel <= 0:
            raise ValueError("Provided area of steel must be positive.")
        note = "User-provided steel area used for calculation."

    # Pu = 0.4 * fck * Ac + 0.67 * fy * Asc
    capacity_n = (0.4 * fck * area_concrete) + (0.67 * fy * area_steel)
    capacity_kn = capacity_n / 1000

    return {
        "ultimate_capacity_kn": round(capacity_kn, 2),
        "used_area_steel": area_steel,
        "calculation_note": note
    }

def export_to_csv(report_data):
    file_path = 'compliance_report.csv'
    if not report_data:
        return
    
    keys = report_data[0].keys()
    with open(file_path, 'w', newline='') as f:
        dict_writer = csv.DictWriter(f, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(report_data)
    print(f"✅ Report exported to {file_path}")

def check_geometry(beams, columns, codes):
    min_column_height = codes['geometric_limits']['min_column_height']
    min_beam_width = codes['geometric_limits']['min_beam_width']
    scaler = codes.get('unit_scaler', 1)

    report_data = []

    print("--- Geometric Compliance Report ---")
    for i, beam in enumerate(beams):
        bbox = beam.bounding_box()
        min_x, min_y = bbox.min
        max_x, max_y = bbox.max
        width = (max_x - min_x) * scaler
        status = "Pass" if width >= min_beam_width else f"FAIL: {width:.2f}mm < {min_beam_width}mm"
        print(f"Beam {i+1}: Width {width:.2f}mm - {status}")
        report_data.append({
            "Type": "BEAM",
            "ID": i+1,
            "Dimension": f"{width:.2f}mm",
            "Status": status,
            "Capacity_kN": "N/A"
        })

    for i, column in enumerate(columns):
        bbox = column.bounding_box()
        min_x, min_y = bbox.min
        max_x, max_y = bbox.max
        height = (max_y - min_y) * scaler
        status = "Pass" if height >= min_column_height else f"FAIL: {height:.2f}mm < {min_column_height}mm"
        print(f"Column {i+1}: Height {height:.2f}mm - {status}")
        
        # Calculate Structural Capacity
        area_c = (max_x - min_x) * (max_y - min_y) * (scaler**2)
        try:
            analysis = calculate_axial_capacity(
                area_concrete=area_c, 
                fck=codes['concrete']['strength'], 
                fy=codes['steel']['yield_strength']
            )
            report_data.append({
                "Type": "COLUMN",
                "ID": i+1,
                "Dimension": f"{height:.2f}mm",
                "Status": status,
                "Capacity_kN": analysis['ultimate_capacity_kn']
            })
        except Exception:
            report_data.append({
                "Type": "COLUMN",
                "ID": i+1,
                "Dimension": f"{height:.2f}mm",
                "Status": status,
                "Capacity_kN": "Error"
            })

    print("\n--- Structural Capacity Analysis ---")
    for entry in report_data:
        if entry["Type"] == "COLUMN":
            print(f"Column {entry['ID']} Capacity: {entry['Capacity_kN']} kN")

    export_to_csv(report_data)

def main():
    generate_is456_json()
    with open('is456_codes.json', 'r') as f:
        codes = json.load(f)
    
    file_path = 'sample_plan.dxf'
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    doc = load_dxf_file(file_path)
    beams, columns = extract_beam_column_info(doc)
    
    check_geometry(beams, columns, codes)

if __name__ == "__main__":
    main()