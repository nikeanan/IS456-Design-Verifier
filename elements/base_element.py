# elements/base_element.py
import json
import os

class StructuralElement:
    """
    Base class for all IS 456 structural design verification elements.
    """
    def __init__(self, element_id: str, f_ck: float, f_y: float, code_edition="IS456_2000"):
        self.element_id = element_id
        self.f_ck = f_ck
        self.f_y = f_y
        self.code_edition = code_edition
        
        # --- NEW: Dynamic Constants Loader ---
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir, 'is456_codes.json')
        override_path = os.path.join(base_dir, 'config_override.json')
        
        with open(config_path, 'r') as f:
            all_codes = json.load(f)
            self.constants = all_codes.get(self.code_edition, {})
            
        # --- NEW: Override logic ---
        if os.path.exists(override_path):
            with open(override_path, 'r') as f:
                overrides = json.load(f)
                # Deep merge logic
                for key in overrides:
                    if key in self.constants:
                        self.constants[key].update(overrides[key])
                        
        try:
            with open(config_path, 'r') as f:
                all_codes = json.load(f)
                # Attach the specific edition's constants to the object
                self.constants = all_codes.get(self.code_edition, {})
        except FileNotFoundError:
            raise FileNotFoundError("Critical Error: is456_codes.json configuration file is missing.")
            
        self.checks = {}
        self.calculations = []
        self.suggestions = []

    def log_calculation(self, step_title: str, formula: str, result: str):
        self.calculations.append({
            "step": step_title,
            "formula": formula,
            "result": result
        })

    def evaluate_compliance(self):
        raise NotImplementedError("Subclasses must implement evaluate_compliance()")