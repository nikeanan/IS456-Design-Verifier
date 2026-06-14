# elements/slab.py
import math
from .base_element import StructuralElement

class RCSlabVerifier(StructuralElement):
    def __init__(self, element_id: str, L_x: float, L_y: float, D: float, d: float,
                 f_ck: float, f_y: float, A_st_main: float, w_u: float):
        super().__init__(element_id, f_ck, f_y)
        self.L_x = L_x
        self.L_y = L_y
        self.D = D
        self.d = d
        self.b = 1000.0
        self.A_st = A_st_main
        self.w_u = w_u
        
    def check_classification(self):
        """IS 456 Annex D - One-Way vs Two-Way Classification"""
        aspect_ratio = self.L_y / self.L_x
        
        if aspect_ratio > 2.0:
            self.classification = "One-Way Slab"
            self.suggestions.append("Slab classified as One-Way. Main reinforcement runs along the short span.")
        else:
            self.classification = "Two-Way Slab"
            self.suggestions.append("Slab classified as Two-Way. Torsional reinforcement may be required at corners.")
            
        self.checks["Aspect Ratio (L_y/L_x)"] = f"{aspect_ratio:.2f} ({self.classification})"
        self.log_calculation("Slab Aspect Ratio", "L_y / L_x", f"{aspect_ratio:.2f}")

    def check_minimum_depth(self):
        """IS 456 Clause 24.1 - Deflection Control for Slabs"""
        span_ratios = self.constants['deflection'].get('basic_span_ratios', {})
        
        if self.classification == "One-Way Slab":
            basic_ratio = span_ratios.get('simply_supported', 20)
        else:
            basic_ratio = span_ratios.get('two_way_simply_supported', 35)
            # Apply dynamic high yield modifier
            if self.f_y != 250:
                modifier = self.constants['deflection'].get('high_yield_steel_modifier', 0.8)
                basic_ratio = basic_ratio * modifier
            
        pt = (100 * self.A_st) / (self.b * self.d)
        f_s = 0.58 * self.f_y 
        
        try:
            denominator = 0.225 + (0.00322 * f_s) - (0.625 * math.log10(pt))
            F_t = min(2.0, max(0.5, 1.0 / denominator))
        except ValueError:
            F_t = 1.0
            
        allowable_L_d = basic_ratio * F_t
        actual_L_d = self.L_x / self.d
        
        if actual_L_d <= allowable_L_d:
            status = "PASS"
        else:
            status = "FAIL (Increase thickness)"
            self.suggestions.append("Slab Deflection: Span/depth ratio exceeds IS 456 limits. Increase overall depth (D).")
            
        self.checks["Deflection (L_x/d)"] = status
        self.log_calculation("Slab Modification Factor (F_t)", "Figure 4", f"{F_t:.2f} (pt={pt:.2f}%)")
        self.log_calculation("Allowable Span/Depth", "Basic Ratio * F_t", f"{allowable_L_d:.2f}")

    def check_flexure_strip(self):
        """IS 456 Annex G - Flexure check on 1m design strip"""
        # Load JSON config factors
        fac_y = self.constants['material_factors'].get('design_yield_stress_factor', 0.87)
        fac_c = self.constants['material_factors'].get('design_concrete_stress_factor', 0.36)
        xu_max_ratios = self.constants['flexure'].get('xu_max_ratio', {})
        xu_max_d = xu_max_ratios.get(str(int(self.f_y)), 0.46)

        if self.classification == "One-Way Slab":
            M_u = (self.w_u * (self.L_x / 1000)**2) / 8 
        else:
            r = self.L_y / self.L_x
            alpha_x = (r**4) / (1 + r**4)
            M_u = alpha_x * self.w_u * (self.L_x / 1000)**2 / 8
            
        M_u_bytes = M_u * 1e6
        x_max = xu_max_d * self.d
        x_u = (fac_y * self.f_y * self.A_st) / (fac_c * self.f_ck * self.b)
        
        if x_u <= x_max:
            M_ur = fac_y * self.f_y * self.A_st * self.d * (1 - (self.A_st * self.f_y) / (self.b * self.d * self.f_ck))
            is_safe = M_ur >= M_u_bytes
        else:
            M_ur = fac_c * xu_max_d * (1 - 0.42 * xu_max_d) * self.f_ck * self.b * (self.d ** 2)
            is_safe = False
            self.suggestions.append("Slab Flexure: Strip is over-reinforced. Increase slab depth (D).")
            
        self.checks["Strip Flexure Capacity"] = "PASS" if is_safe else "FAIL (Redesign Required)"
        
        self.log_calculation("Design Strip Moment (M_u)", "w*L^2/8", f"{M_u:.2f} kNm/m")
        self.log_calculation("Strip Capacity vs Demand", f"Cap = {M_ur/1e6:.2f} kNm/m", f"Dem = {M_u:.2f} kNm/m")

    def evaluate_compliance(self):
        self.check_classification()
        self.check_minimum_depth()
        self.check_flexure_strip()
        return not any("FAIL" in str(v) for v in self.checks.values())