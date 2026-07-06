# elements/footing.py
import math
from .base_element import StructuralElement

class RCFootingVerifier(StructuralElement):
    def __init__(self, element_id: str, L: float, B: float, D: float, d: float,
                 col_L: float, col_B: float, f_ck: float, f_y: float,
                 A_st: float, P_u: float):
        super().__init__(element_id, f_ck, f_y)
        self.L = L
        self.B = B
        self.D = D
        self.d = d
        self.col_L = col_L
        self.col_B = col_B
        self.A_st = A_st
        self.P_u = P_u

        self.p_u = (self.P_u * 1000) / (self.L * self.B)   # N/mm²

    # ------------------------------------------------------------------
    # IS 456 Cl. 34.3 — Minimum Reinforcement in Footing
    # ------------------------------------------------------------------
    def check_min_reinforcement(self):
        """IS 456:2000 Cl. 34.3 — Min steel in footing base (same as slab: 0.12% bD)"""
        pct_min = 0.0012 if self.f_y >= 415 else 0.0015
        A_st_min = pct_min * self.B * self.D

        if self.A_st >= A_st_min:
            status = f"PASS (Ast={self.A_st:.0f} ≥ Ast_min={A_st_min:.0f} mm²)"
        else:
            status = f"FAIL (Ast={self.A_st:.0f} < Ast_min={A_st_min:.0f} mm²)"
            self.suggestions.append(
                f"Footing Min Steel: Provide at least {A_st_min:.0f} mm² base reinforcement "
                f"(IS 456 Cl. 34.3 — {pct_min*100:.2f}% of B×D)."
            )

        self.checks["Min Base Reinforcement (Cl.34.3)"] = status
        self.log_calculation("Min Steel Area", f"{pct_min*100:.2f}% × B × D", f"{A_st_min:.1f} mm²")

    # ------------------------------------------------------------------
    # IS 456 Cl. 34.4 — Bearing Pressure at Column-Footing Interface
    # ------------------------------------------------------------------
    def check_bearing_pressure(self):
        """IS 456:2000 Cl. 34.4 — Bearing stress at column base"""
        # Design bearing strength of column concrete
        bearing_capacity = 0.45 * self.f_ck    # N/mm²

        # Bearing stress from column load
        col_area = self.col_L * self.col_B
        if col_area > 0:
            sigma_br = (self.P_u * 1000) / col_area   # N/mm²
        else:
            sigma_br = float('inf')

        # Enhancement factor for footing (IS 456 Cl. 34.4): sqrt(A1/A2) ≤ 2
        A1 = self.L * self.B
        A2 = col_area
        if A2 > 0:
            enhancement = min(math.sqrt(A1 / A2), 2.0)
        else:
            enhancement = 1.0

        bearing_allow = bearing_capacity * enhancement

        if sigma_br <= bearing_allow:
            status = f"PASS (σ_br={sigma_br:.2f} ≤ {bearing_allow:.2f} N/mm²)"
        else:
            status = f"FAIL (σ_br={sigma_br:.2f} > {bearing_allow:.2f} N/mm²)"
            self.suggestions.append(
                f"Bearing: Column base stress ({sigma_br:.2f} N/mm²) exceeds allowable "
                f"({bearing_allow:.2f} N/mm²). Increase column size or footing area "
                "(IS 456 Cl. 34.4)."
            )

        self.checks["Bearing Pressure (Cl.34.4)"] = status
        self.log_calculation("Column Base Stress", "P_u / (col_L × col_B)", f"{sigma_br:.2f} N/mm²")
        self.log_calculation("Bearing Capacity", f"0.45 × fck × enhancement", f"{bearing_allow:.2f} N/mm²")
        self.log_calculation("Enhancement Factor", "min(√(A1/A2), 2.0)", f"{enhancement:.2f}")

    # ------------------------------------------------------------------
    # IS 456 Cl. 26.2 — Development Length Check
    # ------------------------------------------------------------------
    def check_development_length(self):
        """IS 456:2000 Cl. 26.2 — Column bars must develop within footing depth"""
        # For Fe415: τ_bd = 1.6 N/mm² (IS 456 Table 5 enhanced for deformed bars)
        tau_bd = 1.6 if self.f_y >= 415 else 1.0
        dia_col_bar = 20   # Assumed 20mm column bars (conservative)
        sigma_s = 0.87 * self.f_y

        L_d = (sigma_s * dia_col_bar) / (4 * tau_bd)    # mm

        # Available anchorage = footing depth - 75mm cover
        L_avail = self.D - 75

        if L_avail >= L_d:
            status = f"PASS (L_avail={L_avail:.0f} ≥ L_d={L_d:.0f} mm)"
        else:
            status = f"FAIL (L_avail={L_avail:.0f} < L_d={L_d:.0f} mm)"
            self.suggestions.append(
                f"Development Length: Available depth ({L_avail:.0f} mm) < L_d ({L_d:.0f} mm) "
                "for assumed 20mm column bars. Increase footing depth (D) or use 90° hooks "
                "(IS 456 Cl. 26.2)."
            )

        self.checks["Development Length (Cl.26.2)"] = status
        self.log_calculation("Required Development Length", "(0.87fy × dia) / (4τbd)", f"{L_d:.0f} mm")
        self.log_calculation("Available Anchorage Depth", "D - 75mm cover", f"{L_avail:.0f} mm")

    # ------------------------------------------------------------------
    # IS 456 Cl. 34.2.3.2 — Flexure
    # ------------------------------------------------------------------
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
            M_ur = fac_y * self.f_y * self.A_st * self.d * (
                1 - (self.A_st * self.f_y) / (self.B * self.d * self.f_ck)
            )
            is_safe = M_ur >= M_u_max_bytes
        else:
            M_ur = fac_c * xu_max_d * (1 - 0.42 * xu_max_d) * self.f_ck * self.B * (self.d ** 2)
            is_safe = False
            self.suggestions.append(
                "Footing Flexure: Base is over-reinforced or under-capacity. "
                "Increase depth (D) or base steel area."
            )

        self.checks["Base Flexure Capacity"] = "PASS" if is_safe else "FAIL (Redesign Required)"

        self.log_calculation("Max Neutral Axis Depth", f"xu_max = {xu_max_d} × d", f"{x_max:.2f} mm")
        self.log_calculation("Design Moment (M_u)", "max(p_u × B × l_x²/2)", f"{M_u_kNm:.2f} kNm")
        self.log_calculation("Base Capacity vs Demand", f"Cap={M_ur/1e6:.2f} kNm", f"Dem={M_u_kNm:.2f} kNm")

    # ------------------------------------------------------------------
    # IS 456 Cl. 31.6 — Punching Shear
    # ------------------------------------------------------------------
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
            self.suggestions.append(
                "Punching Shear: tau_v > tau_c. Increase footing depth (D)."
            )

        self.checks["Two-Way (Punching) Shear"] = status
        self.log_calculation("Upward Soil Pressure (p_u)", "P_u / (L×B)", f"{self.p_u:.3f} N/mm²")
        self.log_calculation("Punching Shear Stress", "V_p / (b_0 × d)", f"{tau_v:.3f} N/mm²")
        self.log_calculation("Allowable Punching Stress", "k_s × 0.25 × √fck", f"{tau_c:.3f} N/mm²")

    # ------------------------------------------------------------------
    # IS 456 Cl. 34.2.4 — One-Way Shear
    # ------------------------------------------------------------------
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
            self.suggestions.append(
                "One-Way Shear: tau_v > tau_c. Increase footing depth (D) or concrete grade."
            )

        self.checks["One-Way Shear"] = status
        self.log_calculation("One-Way Shear Stress", "V_u / (B×d)", f"{tau_v:.3f} N/mm²")
        self.log_calculation("Concrete Shear Capacity", "tau_c", f"{tau_c:.3f} N/mm²")

    # ------------------------------------------------------------------
    # Orchestrator
    # ------------------------------------------------------------------
    def evaluate_compliance(self):
        self.check_min_reinforcement()
        self.check_bearing_pressure()
        self.check_development_length()
        self.check_flexure()
        self.check_punching_shear()
        self.check_one_way_shear()
        return not any("FAIL" in str(v) for v in self.checks.values())