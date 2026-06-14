# elements/footing.py
import math
from .base_element import StructuralElement

class RCFootingVerifier(StructuralElement):
    def __init__(self, element_id: str, L: float, B: float, D: float, d: float,
                 col_L: float, col_B: float, f_ck: float, f_y: float, A_st: float, P_u: float):
        super().__init__(element_id, f_ck, f_y)
        self.L = L              
        self.B = B              
        self.D = D              
        self.d = d              
        self.col_L = col_L      
        self.col_B = col_B      
        self.A_st = A_st        
        self.P_u = P_u          
        
        self.p_u = (self.P_u * 1000) / (self.L * self.B)

    def check_flexure(self):
        """IS 456 Clause 34.2.3.2 - Bending Moment at Column Face"""
        fac_y = self.constants['material_factors'].get('design_yield_stress_factor', 0.87)
        fac_c = self.constants['material_factors'].get('design_concrete_stress_factor', 0.36)
        xu_max_ratios = self.constants['flexure'].get('xu_max_ratio', {})
        xu_max_d = xu_max_ratios.get(str(int(self.f_y)), 0.46)

        l_x = (self.L - self.col_L) / 2
        l_y = (self.B - self.col_B) / 2

        M_ux_bytes = self.p_u * self.B * (l_x ** 2) / 2
        M_uy_bytes = self.p_u * self.L * (l_y ** 2) / 2
        
        M_u_max_bytes = max(M_ux_bytes, M_uy_bytes)
        M_u_kNm = M_u_max_bytes / 1e6
        
        x_max = xu_max_d * self.d
        x_u = (fac_y * self.f_y * self.A_st) / (fac_c * self.f_ck * self.B)
        
        if x_u <= x_max:
            M_ur = fac_y * self.f_y * self.A_st * self.d * (1 - (self.A_st * self.f_y) / (self.B * self.d * self.f_ck))
            is_safe = M_ur >= M_u_max_bytes
        else:
            M_ur = fac_c * xu_max_d * (1 - 0.42 * xu_max_d) * self.f_ck * self.B * (self.d ** 2)
            is_safe = False
            self.suggestions.append("Footing Flexure: Base is over-reinforced or under-capacity. Increase depth (D) or base steel area.")
            
        self.checks["Base Flexure Capacity"] = "PASS" if is_safe else "FAIL (Redesign Required)"
        
        self.log_calculation("Max Neutral Axis Depth", f"xu_max = {xu_max_d} * d", f"{x_max:.2f} mm")
        self.log_calculation("Design Moment (M_u)", "max(p_u * B * l_x^2 / 2)", f"{M_u_kNm:.2f} kNm")
        self.log_calculation("Base Capacity vs Demand", f"Cap = {M_ur/1e6:.2f} kNm", f"Dem = {M_u_kNm:.2f} kNm")

    def check_punching_shear(self):
        """IS 456 Clause 31.6 - Two-Way (Punching) Shear"""
        perim_L = self.col_L + self.d
        perim_B = self.col_B + self.d
        b_0 = 2 * (perim_L + perim_B)
        
        V_p_newtons = (self.P_u * 1000) - (self.p_u * perim_L * perim_B)
        tau_v = V_p_newtons / (b_0 * self.d)
        
        beta_c = min(self.col_L / self.col_B, self.col_B / self.col_L)
        k_s = min(0.5 + beta_c, 1.0)
        tau_c = k_s * 0.25 * math.sqrt(self.f_ck)
        
        if tau_v <= tau_c:
            status = "PASS"
        else:
            status = "FAIL (Increase depth)"
            self.suggestions.append("Punching Shear: tau_v > tau_c. Increase footing depth (D).")
            
        self.checks["Two-Way (Punching) Shear"] = status
        self.log_calculation("Upward Soil Pressure (p_u)", "P_u / (L*B)", f"{self.p_u:.3f} N/mm^2")
        self.log_calculation("Punching Shear Stress", "V_p / (b_0 * d)", f"{tau_v:.3f} N/mm^2")
        self.log_calculation("Allowable Punching Stress", "k_s * 0.25 * sqrt(f_ck)", f"{tau_c:.3f} N/mm^2")

    def check_one_way_shear(self):
        """IS 456 Clause 34.2.4 - One-Way Shear"""
        l_x = (self.L - self.col_L) / 2
        l_shear = l_x - self.d
        
        if l_shear > 0:
            V_u_newtons = self.p_u * self.B * l_shear
            tau_v = V_u_newtons / (self.B * self.d)
        else:
            tau_v = 0.0
            
        pt = (100 * self.A_st) / (self.B * self.d)
        tau_c_base = 0.16 * math.sqrt(self.f_ck) * (pt ** 0.4)
        tau_c = max(0.28, min(tau_c_base, 0.85))
        
        if tau_v <= tau_c:
            status = "PASS"
        else:
            status = "FAIL (Increase depth)"
            self.suggestions.append("One-Way Shear: tau_v > tau_c. Increase footing depth (D) or concrete grade.")
            
        self.checks["One-Way Shear"] = status
        self.log_calculation("One-Way Shear Stress", "V_u / (B*d)", f"{tau_v:.3f} N/mm^2")

    def evaluate_compliance(self):
        self.check_flexure()
        self.check_punching_shear()
        self.check_one_way_shear()
        return not any("FAIL" in str(v) for v in self.checks.values())