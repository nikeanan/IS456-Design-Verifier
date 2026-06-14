# elements/beam.py
import math
from .base_element import StructuralElement

class RCBeamVerifier(StructuralElement):
    def __init__(self, element_id: str, b: float, d: float, D: float, L: float,
                 f_ck: float, f_y: float, A_st: float, M_eq: float, V_eq: float):
        super().__init__(element_id, f_ck, f_y)
        self.b = b
        self.d = d
        self.D = D
        self.L = L          # Span length in mm
        self.A_st = A_st
        self.M_u = M_eq     # Equivalent factored bending moment (kNm)
        self.V_eq = V_eq    # Equivalent factored shear force (kN)

    def check_flexure(self):
        """IS 456:2000 Annex G1.1 - Limit State of Collapse: Flexure"""
        M_u_bytes = self.M_u * 1e6
        
        fac_y = self.constants['material_factors'].get('design_yield_stress_factor', 0.87)
        fac_c = self.constants['material_factors'].get('design_concrete_stress_factor', 0.36)
        
        xu_max_ratios = self.constants['flexure'].get('xu_max_ratio', {})
        xu_max_d = xu_max_ratios.get(str(int(self.f_y)), 0.46)
            
        self.x_max = xu_max_d * self.d
        self.x_u = (fac_y * self.f_y * self.A_st) / (fac_c * self.f_ck * self.b)
        
        # 1. Check if section is Under-Reinforced (Ductile)
        if self.x_u <= self.x_max:
            self.M_ur = fac_y * self.f_y * self.A_st * self.d * (1 - (self.A_st * self.f_y) / (self.b * self.d * self.f_ck))
            section_type = "Under-Reinforced"
            is_safe = self.M_ur >= M_u_bytes
            
            # 2. If it's safe, check if it is a "Marginal Pass" (<= 5% headroom)
            if is_safe:
                margin = (self.M_ur - M_u_bytes) / M_u_bytes
                if margin <= 0.05:
                    status = f"PASS* (Marginal: {margin*100:.1f}% headroom)"
                    self.suggestions.append(f"Flexure: Capacity is within {margin*100:.1f}% of demand. Consider a slightly larger section or higher grade materials for safety.")
                else:
                    status = "PASS"
            else:
                status = "FAIL (Redesign Required)"
                self.suggestions.append("Flexure: Section is under-reinforced but lacks sufficient moment capacity. Increase steel area (A_st) or depth (d).")
                
        # 3. Handle Over-Reinforced Section (Brittle Failure Risk)
        else:
            self.M_ur = fac_c * xu_max_d * (1 - 0.42 * xu_max_d) * self.f_ck * self.b * (self.d ** 2)
            section_type = "Over-Reinforced"
            is_safe = False
            self.suggestions.append("Flexure: Section is over-reinforced. Increase depth (d) or width (b). Do not add more tension steel.")
            status = "FAIL (Redesign Required)"

        # Save Final Status
        self.checks["Flexure Capacity"] = status
        
        # Log Calculations
        self.log_calculation("Max Neutral Axis Depth", f"xu_max = {xu_max_d} * d", f"{self.x_max:.2f} mm")
        self.log_calculation("Actual Neutral Axis Depth", f"xu = ({fac_y}*fy*Ast)/({fac_c}*fck*b)", f"{self.x_u:.2f} mm ({section_type})")
        self.log_calculation("Moment Capacity vs Demand", f"Mu_capacity = {self.M_ur/1e6:.2f} kNm", f"Mu_demand = {self.M_u:.2f} kNm")
        
    def check_shear(self):
        """IS 456:2000 Clause 40 & 41 - Limit State of Collapse: Shear"""
        V_eq_scaled = self.V_eq * 1000 
        
        tau_v = V_eq_scaled / (self.b * self.d)
        pt = (100 * self.A_st) / (self.b * self.d)
        
        tau_c_base = 0.16 * math.sqrt(self.f_ck) * (pt ** 0.4)
        tau_c = max(0.28, min(tau_c_base, 0.85)) 
        
        # --- NEW: Dynamic Constants Integration ---
        tau_c_max_dict = self.constants['shear'].get('tau_c_max', {})
        # Lookup table value, fallback to empirical 0.62*sqrt(fck) if not found
        tau_c_max = tau_c_max_dict.get(str(int(self.f_ck)), 0.62 * math.sqrt(self.f_ck))
        fac_y = self.constants['material_factors'].get('design_yield_stress_factor', 0.87)

        if tau_v > tau_c_max:
            status = "FAIL (Section too small)"
            self.suggestions.append("Shear: tau_v > tau_c_max. You must increase web width (b) or depth (d) to prevent diagonal compression failure.")
        elif tau_v > tau_c:
            status = "ACTION REQUIRED (Design Shear Stirrups)"
            
            V_us = V_eq_scaled - (tau_c * self.b * self.d)
            A_sv = 100.53  # Area of 2-legged 8mm dia stirrup
            
            # Using dynamic fac_y instead of hardcoded 0.87
            s_v_req = (fac_y * self.f_y * A_sv * self.d) / V_us if V_us > 0 else 300
            s_v_min = (fac_y * self.f_y * A_sv) / (0.4 * self.b)
            s_v_final = min(s_v_req, s_v_min, 0.75 * self.d, 300)
            
            self.suggestions.append(f"Shear: Provide 2-Legged 8mm dia stirrups @ {int(s_v_final)} mm c/c.")
            self.log_calculation("Shear carried by steel (V_us)", "V_eq - tau_c*b*d", f"{V_us/1000:.2f} kN")
            self.log_calculation("Stirrup Spacing (s_v)", f"min({fac_y}*fy*Asv*d/V_us, 0.75d, 300)", f"{int(s_v_final)} mm")
        else:
            status = "PASS (Provide Nominal Stirrups)"
            s_v_min = (fac_y * self.f_y * 100.53) / (0.4 * self.b)
            s_v_final = min(s_v_min, 0.75 * self.d, 300)
            self.suggestions.append(f"Shear: Provide nominal 2-Legged 8mm dia stirrups @ {int(s_v_final)} mm c/c.")

        self.checks["Shear & Torsion (tau_v)"] = status
        self.log_calculation("Equivalent Shear Stress", "tau_v = V_eq / (b * d)", f"{tau_v:.3f} N/mm^2")
        self.log_calculation("Concrete Shear Capacity", "tau_c", f"{tau_c:.3f} N/mm^2")
        self.log_calculation("Maximum Concrete Capacity", "tau_c_max", f"{tau_c_max:.3f} N/mm^2")

    def check_deflection(self):
        """IS 456:2000 Clause 23.2 - Limit State of Serviceability: Deflection"""
        
        # --- NEW: Fetch base ratio dynamically from config ---
        basic_span_ratio = self.constants['deflection']['basic_span_ratios'].get('simply_supported', 20)
        
        pt = (100 * self.A_st) / (self.b * self.d)
        f_s = 0.58 * self.f_y 
        
        try:
            denominator = 0.225 + (0.00322 * f_s) - (0.625 * math.log10(pt))
            F_t = min(2.0, max(0.5, 1.0 / denominator))
        except ValueError:
            F_t = 1.0 
            
        allowable_L_d = basic_span_ratio * F_t
        actual_L_d = self.L / self.d
        
       # Determine the raw numerical status first
        num_pass = actual_L_d <= allowable_L_d
        
        # Check if flexure is already compromised
        flexure_failed = "FAIL" in self.checks.get("Flexure Capacity", "")
        
        if num_pass and not flexure_failed:
            status = "PASS"
        elif num_pass and flexure_failed:
            status = "PASS* (Warning: Void due to Flexure Failure)"
            self.suggestions.append("Deflection: The L/d check passes numerically, but is invalid because the section is under-capacity in flexure. Redesign flexure first.")
        elif not num_pass and not flexure_failed:
            status = "FAIL (Increase depth)"
            self.suggestions.append("Deflection: Span/depth ratio exceeds allowable limit. Increase effective depth (d) or tension steel.")
        else:
            status = "FAIL* (Also under-capacity in flexure)"
            self.suggestions.append("Deflection & Flexure: Section fails both strength and serviceability limits. Major redesign required.")
        self.checks["Deflection (L/d)"] = status
        self.log_calculation("Actual Span/Depth", "L / d", f"{actual_L_d:.2f}")
        
        # Updated to log the dynamically fetched ratio instead of static '20'
        self.log_calculation("Allowable Span/Depth", f"{basic_span_ratio} * F_t", f"{allowable_L_d:.2f} (F_t={F_t:.2f})")

    def evaluate_compliance(self):
        self.check_flexure()
        self.check_shear()
        self.check_deflection()
        return not any("FAIL" in str(v) for v in self.checks.values())