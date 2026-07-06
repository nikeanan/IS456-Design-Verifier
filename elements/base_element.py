# elements/base_element.py
from engine.rule_engine import RuleEngine

class StructuralElement:
    """
    Base class for all structural design verification elements.
    """
    def __init__(self, element_id: str, f_ck: float, f_y: float, codes=None):
        self.element_id = element_id
        self.f_ck = f_ck
        self.f_y = f_y
        self.codes = codes or ["IS456_2000"]
        
        self.rule_engine = RuleEngine(self.codes)
        self.constants = self.rule_engine.constants
            
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