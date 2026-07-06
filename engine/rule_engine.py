# engine/rule_engine.py
import json
import os
from typing import List, Dict, Any

class RuleEngine:
    """
    RuleEngine loads and merges configuration constants from multiple IS codes,
    enabling multi-code rule validation (e.g., IS 456 + IS 13920).
    """
    def __init__(self, applicable_codes: List[str] = None):
        self.applicable_codes = applicable_codes or ["IS456_2000"]
        self.constants: Dict[str, Any] = {}
        self._load_configurations()

    def _load_configurations(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Mapping code to json file
        code_files = {
            "IS456_2000": "is456_codes.json",
            "IS13920_2016": "is13920_codes.json",
            "IS1893_2016": "is1893_codes.json"
        }
        
        for code in self.applicable_codes:
            filename = code_files.get(code)
            if filename:
                config_path = os.path.join(base_dir, filename)
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        all_codes = json.load(f)
                        # Depending on the JSON structure, it might be nested under the code name or flat.
                        # Assuming it's nested like is456_codes.json currently is (or will be)
                        code_constants = all_codes.get(code, all_codes)
                        self._deep_merge(self.constants, code_constants)

        # Apply overrides
        override_path = os.path.join(base_dir, 'config_override.json')
        if os.path.exists(override_path):
            try:
                with open(override_path, 'r') as f:
                    overrides = json.load(f)
                    self._deep_merge(self.constants, overrides)
            except (json.JSONDecodeError, FileNotFoundError):
                pass

    def _deep_merge(self, base: dict, update: dict):
        for k, v in update.items():
            if isinstance(v, dict) and k in base and isinstance(base[k], dict):
                self._deep_merge(base[k], v)
            else:
                base[k] = v
                
    def get_constant(self, path: str, default: Any = None) -> Any:
        keys = path.split('.')
        curr = self.constants
        for k in keys:
            if isinstance(curr, dict) and k in curr:
                curr = curr[k]
            else:
                return default
        return curr
