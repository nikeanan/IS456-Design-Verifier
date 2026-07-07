# elements/column.py
from .base_element import StructuralElement

class RCColumnVerifier(StructuralElement):
    def __init__(self, element_id: str, b: float, D: float, L_eff: float, 
                 f_ck: float, f_y: float, A_sc: float, P_u: float, M_u_applied: float = 0.0):
        super().__init__(element_id, f_ck, f_y)
        self.b = b
        self.D = D
        self.L_eff = L_eff
        self.A_sc = A_sc
        self.P_u = P_u
        self.M_u_applied = M_u_applied 
        
        self.A_g = self.b * self.D
        self.A_c = self.A_g - self.A_sc

    def check_slenderness(self):
        """IS 456 Clause 25.1.2 - Short vs Long Column Classification"""
        ratio_b = self.L_eff / self.b
        ratio_D = self.L_eff / self.D
        
        if ratio_b < 12 and ratio_D < 12:
            self.classification = "Short Column"
        else:
            self.classification = "Long Column"
            self.suggestions.append("Slenderness > 12. Additional moments must be considered.")
            
        is_within_limits = (ratio_b <= 60 and ratio_D <= 60)
        self.checks["Slenderness Limit"] = "PASS" if is_within_limits else "FAIL (Exceeds maximum limits)"
        
        self.log_calculation("Slenderness Ratio (Width)", "L_eff / b", f"{ratio_b:.2f}")
        self.log_calculation("Slenderness Ratio (Depth)", "L_eff / D", f"{ratio_D:.2f}")

    def check_pm_interaction(self):
        """IS 456 Clause 25.4 & 39.5 - Eccentricity and P-M Interaction"""
        # Load dynamic material factors from configuration
        fac_c_axial = self.constants['material_factors'].get('column_pure_axial_concrete_factor', 0.45)
        fac_y_axial = self.constants['material_factors'].get('column_pure_axial_steel_factor', 0.75)
        fac_y_flex = self.constants['material_factors'].get('design_yield_stress_factor', 0.87)

        # 1. Calculate Minimum Eccentricity
        e_min = max((self.L_eff / 500) + (self.D / 30), 20.0)
        
        # 2. Determine Design Moment
        M_u_min = self.P_u * (e_min / 1000)
        M_design = max(self.M_u_applied, M_u_min)
        
        # 3. Pure Axial Capacity (P_uz)
        p_uz_capacity = (fac_c_axial * self.f_ck * self.A_c) + (fac_y_axial * self.f_y * self.A_sc)
        self.P_uz_kNm = p_uz_capacity / 1000
        
        # 4. Pure Bending Capacity (M_uo) - Simplified Approx
        A_st_half = self.A_sc / 2
        d_eff = self.D - 40 
        M_uo_bytes = fac_y_flex * self.f_y * A_st_half * d_eff * (1 - (A_st_half * self.f_y) / (self.b * d_eff * self.f_ck))
        self.M_uo_kNm = M_uo_bytes / 1e6
        
        # 5. Linear P-M Interaction Check
        interaction_ratio = (self.P_u / self.P_uz_kNm) + (M_design / self.M_uo_kNm)
        
        if self.P_u > self.P_uz_kNm:
            status = "FAIL (Exceeds Pure Axial Capacity)"
        elif interaction_ratio <= 1.0:
            status = "PASS (Safe via Conservative Linear P-M)"
        else:
            status = "ACTION REQUIRED (Check SP-16 Charts)"
            self.suggestions.append("Column: Fails conservative linear P-M check. Precise verification via SP-16 interaction charts is required.")

        self.checks["Minimum Eccentricity (e_min)"] = f"Governing M_u = {M_design:.2f} kNm"
        self.checks["P-M Interaction (Uniaxial)"] = status

        self.log_calculation("Minimum Eccentricity", "max(L/500 + D/30, 20)", f"{e_min:.2f} mm")
        self.log_calculation("Design Moment (M_u)", "max(M_applied, P_u * e_min)", f"{M_design:.2f} kNm")
        self.log_calculation("Pure Axial Capacity (P_uz)", f"{fac_c_axial}*fck*Ac + {fac_y_axial}*fy*Asc", f"{self.P_uz_kNm:.2f} kN")
        self.log_calculation("Linear Interaction Ratio", "P_u/P_uz + M_u/M_uo", f"{interaction_ratio:.2f}")

    def evaluate_compliance(self):
        self.check_slenderness()
        self.check_pm_interaction()
        return not any("FAIL" in str(v) for v in self.checks.values())