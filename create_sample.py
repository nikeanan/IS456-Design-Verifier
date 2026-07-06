import ezdxf
import json
import os

# --- Configuration ---
DXF_FILE_PATH = 'sample_plan.dxf'
JSON_FILE_PATH = 'sample_is456_codes.json'

# --- Block 1: Generate IS 456 Data ---
def generate_is456_json():
    """Creates the IS 456 threshold database if it doesn't exist."""
    is456_data = {
        "MIN_COLUMN_DIMENSION_MM": 200, # IS 456 Cl 25.1.2 
        "MIN_COLUMN_RADIUS_MM": 100,    # Equivalent for circular
        "MIN_BEAM_WIDTH_MM": 200,
        "MAX_SPAN_TO_DEPTH_RATIO": 20   # Simply supported
    }
    
    with open(JSON_FILE_PATH, 'w') as f:
        json.dump(is456_data, f, indent=4)
    print(f"✅ Generated {JSON_FILE_PATH} with structural thresholds.")
    return is456_data

# --- Block 2: Check DXF File Integrity ---
def check_dxf_file(file_path):
    if not os.path.exists(file_path):
        print(f"❌ Error: Could not find '{file_path}'.")
        return None
    try:
        doc = ezdxf.readfile(file_path)
        print("✅ DXF file loaded successfully.")
        return doc
    except Exception as e:
        print(f"❌ Invalid DXF file: {e}")
        return None

# --- Block 3: Extract by CAD Layers ---
def extract_beam_column_info(doc):
    beams = []
    columns = []
    
    msp = doc.modelspace()
    for entity in msp:
        layer_name = entity.dxf.layer.upper()
        
        # Look for entities specifically placed on Beam or Column layers
        if 'BEAM' in layer_name:
            beams.append(entity)
        elif 'S-COL' in layer_name and entity.dxftype() == 'LWPOLYLINE':
            columns.append(entity)
            
    prin@t(f"🔍 Found {len(beams)} beam entities and {len(columns)} column entities.")
    return beams, columns

# --- Helper function to calculate bounding box of a polyline ---
def get_polyline_bounding_box(polyline):
    min_x = float('inf')
    max_x = float('-inf')
    min_y = float('inf')
    max_y = float('-inf')
    
    for point in polyline.get_points():
        if point[0] < min_x:
            min_x = point[0]
        if point[0] > max_x:
            max_x = point[0]
        if point[1] < min_y:
            min_y = point[1]
        if point[1] > max_y:
            max_y = point[1]
    
    width = max_x - min_x
    depth = max_y

