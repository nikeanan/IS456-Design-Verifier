import ifcopenshell
import pandas as pd
import re

class BIMExtractor:
    def __init__(self, filepath):
        """Initializes the parser with an uploaded IFC file."""
        try:
            self.model = ifcopenshell.open(filepath)
        except Exception as e:
            raise ValueError(f"Failed to parse IFC model: {str(e)}")

    def extract_element_geometry(self, element):
        """Extracts width (b) and depth (D) from IfcRectangleProfileDef."""
        dimensions = {"b": 0.0, "D": 0.0}
        if hasattr(element, 'Representation') and element.Representation:
            for rep in element.Representation.Representations:
                for item in rep.Items:
                    if item.is_a('IfcExtrudedAreaSolid'):
                        profile = item.SweptArea
                        if profile.is_a('IfcRectangleProfileDef'):
                            dimensions['b'] = profile.XDim
                            dimensions['D'] = profile.YDim
        return dimensions

    def extract_properties(self, element):
        """Extracts all property values attached to the element via IfcPropertySet."""
        props = {}
        if hasattr(element, 'IsDefinedBy'):
            for definition in element.IsDefinedBy:
                if definition.is_a('IfcRelDefinesByProperties'):
                    pset = definition.RelatingPropertyDefinition
                    if pset.is_a('IfcPropertySet'):
                        for prop in pset.HasProperties:
                            if prop.is_a('IfcPropertySingleValue') and prop.NominalValue:
                                props[prop.Name.lower()] = prop.NominalValue.wrappedValue
        return props

    def extract_material_grade(self, element):
        """Attempts to extract f_ck from IfcMaterial."""
        if hasattr(element, 'HasAssociations'):
            for association in element.HasAssociations:
                if association.is_a('IfcRelAssociatesMaterial'):
                    material = association.RelatingMaterial
                    if material.is_a('IfcMaterial'):
                        name = material.Name.upper()
                        if "30" in name:
                            return 30.0
                        if "25" in name:
                            return 25.0
                        if "35" in name:
                            return 35.0
                        if "40" in name:
                            return 40.0
        return 30.0 

    def extract_thickness_from_name(self, name):
        """Regex fallback to extract thickness from names like 'Generic 150mm' or 'Generic 300'."""
        if not name:
            return 0.0
        
        # 1. First try explicit 'mm' matching (e.g., 150mm, 425 mm)
        match = re.search(r'(\d+)\s*mm', name, re.IGNORECASE)
        if match:
            return float(match.group(1))
            
        # 2. Fallback to standalone 2-to-4 digit numbers (e.g., "Generic 300")
        match_num = re.search(r'(?<!\d)(\d{2,4})(?!\d)', name)
        if match_num:
            return float(match_num.group(1))
            
        return 0.0

    def get_footings_dataframe(self):
        """Parses actual isolated footings/pads, strictly filtering out deep foundations (piles/caps)."""
        footings = self.model.by_type('IfcFooting')
        
        # Grab rogue slabs that act as pad footings
        rogue_slabs = [s for s in self.model.by_type('IfcSlab') if s.Name and "pad" in s.Name.lower()]
        raw_foundations = footings + rogue_slabs
        
        # --- THE DEEP FOUNDATION FILTER ---
        # Exclude IS 2911 elements (Piles, Pile Caps, Steel Pipes) from IS 456 Pad logic
        valid_pads = []
        for f in raw_foundations:
            name_lower = (f.Name or "").lower()
            if "pile" not in name_lower and "pipe" not in name_lower and "cap" not in name_lower:
                valid_pads.append(f)
                
        data = []
        for i, foot in enumerate(valid_pads):
            name = foot.Name if foot.Name else f"BIM_Footing_{i+1}"
            f_ck = self.extract_material_grade(foot)
            geom = self.extract_element_geometry(foot)
            props = self.extract_properties(foot)
            
            # Hierarchy of geometry extraction: Geometric Profile -> Property Sets -> 0.0
            L = geom['b'] or props.get('length') or 0.0
            B = geom['D'] or props.get('width') or 0.0
            
            # Extended depth checks for pads
            D = props.get('thickness') or props.get('depth') or self.extract_thickness_from_name(name) or 0.0
            
            # Regex Fallback for 3D bounding boxes (e.g., "600 x 600 x 900")
            if L == 0 and B == 0:
                match = re.search(r'(\d+)\s*[xX]\s*(\d+)\s*[xX]\s*(\d+)', name)
                if match:
                    L, B, D = float(match.group(1)), float(match.group(2)), float(match.group(3))
                    
            data.append({
                "Footing_ID": name,
                "L": float(L), "B": float(B), "D": float(D), "d": float(D) - 50 if D > 50 else 0.0,
                "col_L": 300.0, "col_B": 300.0,
                "f_ck": f_ck, "f_y": 415.0, "A_st": 0.0, "P_u": 0.0
            })
        return pd.DataFrame(data)
    
    def get_beams_dataframe(self):
        beams = self.model.by_type('IfcBeam')
        data = []
        for i, beam in enumerate(beams):
            geom = self.extract_element_geometry(beam)
            f_ck = self.extract_material_grade(beam)
            if geom['b'] > 0 and geom['D'] > 0:
                data.append({
                    "Beam_ID": beam.Name if beam.Name else f"BIM_Beam_{i+1}",
                    "b": geom['b'], "D": geom['D'], "d": geom['D'] - 50,
                    "L": 5000.0, "f_ck": f_ck, "f_y": 415.0, "A_st": 0.0,
                    "M_u": 0.0, "V_u": 0.0, "T_u": 0.0
                })
        return pd.DataFrame(data)

    def get_columns_dataframe(self):
        columns = self.model.by_type('IfcColumn')
        data = []
        for i, col in enumerate(columns):
            geom = self.extract_element_geometry(col)
            f_ck = self.extract_material_grade(col)
            if geom['b'] > 0 and geom['D'] > 0:
                data.append({
                    "Column_ID": col.Name if col.Name else f"BIM_Col_{i+1}",
                    "b": geom['b'], "D": geom['D'], "L_eff": 3000.0,
                    "f_ck": f_ck, "f_y": 415.0, "A_sc": 0.0,
                    "P_u": 0.0, "M_u_applied": 0.0
                })
        return pd.DataFrame(data)

    def get_slabs_dataframe(self):
        slabs = self.model.by_type('IfcSlab')
        data = []
        for i, slab in enumerate(slabs):
            name = slab.Name if slab.Name else ""
            name_lower = name.lower()
            
            # TAXONOMY FILTER: Skip piles, caps, and pads (route them to footings)
            if "pile" in name_lower or "pad" in name_lower or "footing" in name_lower:
                continue

            f_ck = self.extract_material_grade(slab)
            props = self.extract_properties(slab)
            
            # Find thickness via Property Sets, then Regex, then default to 0
            thickness = props.get('thickness') or props.get('width') or self.extract_thickness_from_name(name) or 0.0
            
            data.append({
                "Slab_ID": name if name else f"BIM_Slab_{i+1}",
                "L_x": 0.0,  # Zeroes force the engineer to input real spans
                "L_y": 0.0, 
                "D": float(thickness), 
                "d": float(thickness) - 25 if thickness > 25 else 0.0,
                "f_ck": f_ck, "f_y": 415.0, "A_st_main": 0.0, "w_u": 0.0
            })
        return pd.DataFrame(data)