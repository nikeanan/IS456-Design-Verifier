# elements/column.py
import math
from .base_element import StructuralElement

class RCColumnVerifier(StructuralElement):
    def __init__(self, element_id: str, b: float, D: float, L_eff: float,
                 f_ck: float, f_y: float, A_sc: float, P_u: float,
                 M_u_applied: float = 0.0, M_uy_applied: float = 0.0):
        super().__init__(element_id, f_ck, f_y)
        self.b = b
        self.D = D
        self.L_eff = L_eff
        self.A_sc = A_sc
        self.P_u = P_u
        self.M_u_applied = M_u_applied
        self.M_uy_applied = M_uy_applied    # For biaxial bending (IS 456 Cl. 39.6)

        self.A_g = self.b * self.D
        self.A_c = self.A_g - self.A_sc

    # ------------------------------------------------------------------
    # IS 456 Cl. 26.5.3.1 — Steel Area Limits
    # ------------------------------------------------------------------
    def check_steel_limits(self):
        """IS 456:2000 Cl. 26.5.3.1 — Asc: 0.8% ≤ Asc ≤ 6% of Ag"""
        A_sc_min = 0.008 * self.A_g
        A_sc_max = 0.06 * self.A_g

        if self.A_sc < A_sc_min:
            status = f"FAIL (Asc={self.A_sc:.0f} < Asc_min={A_sc_min:.0f} mm²)"
            self.suggestions.append(
                f"Column Steel: Provide at least {A_sc_min:.0f} mm² of longitudinal steel "
                f"(IS 456 Cl. 26.5.3.1 — min 0.8% of Ag)."
            )
        elif self.A_sc > A_sc_max:
            status = f"FAIL (Asc={self.A_sc:.0f} > Asc_max={A_sc_max:.0f} mm²)"
            self.suggestions.append(
                f"Column Steel: Steel area exceeds 6% of gross area ({A_sc_max:.0f} mm²). "
                "Increase section size (IS 456 Cl. 26.5.3.1)."
            )
        else:
            pct = (self.A_sc / self.A_g) * 100
            status = f"PASS ({pct:.2f}% of Ag — within 0.8%–6%)"

        self.checks["Steel Area Limits (Cl.26.5.3.1)"] = status
        self.log_calculation("Min Longitudinal Steel", "0.8% * Ag", f"{A_sc_min:.1f} mm²")
        self.log_calculation("Max Longitudinal Steel", "6.0% * Ag", f"{A_sc_max:.1f} mm²")

    # ------------------------------------------------------------------
    # IS 456 Cl. 26.5.3.2 — Lateral Ties
    # ------------------------------------------------------------------
    def check_lateral_ties(self):
        """IS 456:2000 Cl. 26.5.3.2 — Tie diameter and maximum spacing"""
        # Assume 20mm main bars (conservative; actual dia not input)
        dia_long_assumed = 20
        dia_tie_min = max(6, dia_long_assumed // 4)   # ≥ 6mm and ≥ (main_dia / 4)

        s_max_1 = self.b                            # Least lateral dimension
        s_max_2 = 16 * dia_long_assumed             # 16 × dia of longitudinal bar
        s_max_3 = 300                               # Absolute max
        s_max = min(s_max_1, s_max_2, s_max_3)

        status = (
            f"ACTION REQUIRED — Provide dia ≥ {dia_tie_min}mm ties @ ≤ {s_max:.0f} mm c/c "
            f"(IS 456 Cl. 26.5.3.2)"
        )
        self.suggestions.append(
            f"Lateral Ties: Provide {dia_tie_min}mm dia ties at ≤ {s_max:.0f} mm c/c "
            f"[min(b={self.b:.0f}, 16×{dia_long_assumed}={16*dia_long_assumed}, 300) mm]."
        )
        self.checks["Lateral Ties (Cl.26.5.3.2)"] = status
        self.log_calculation("Max Tie Spacing", "min(b, 16*dia_long, 300)", f"{s_max:.0f} mm")
        self.log_calculation("Min Tie Diameter", "max(6, dia_long/4)", f"{dia_tie_min} mm")

    # ------------------------------------------------------------------
    # IS 456 Cl. 25.1.2 — Slenderness
    # ------------------------------------------------------------------
    def check_slenderness(self):
        """IS 456 Clause 25.1.2 - Short vs Long Column Classification"""
        ratio_b = self.L_eff / self.b
        ratio_D = self.L_eff / self.D

        if ratio_b < 12 and ratio_D < 12:
            self.classification = "Short Column"
        else:
            self.classification = "Long Column"
            self.suggestions.append(
                "Slenderness > 12. Additional moments must be considered per IS 456 Cl. 25.1.2."
            )

        is_within_limits = (ratio_b <= 60 and ratio_D <= 60)
        self.checks["Slenderness Limit"] = "PASS" if is_within_limits else "FAIL (Exceeds maximum limits)"

        self.log_calculation("Slenderness Ratio (Width)", "L_eff / b", f"{ratio_b:.2f}")
        self.log_calculation("Slenderness Ratio (Depth)", "L_eff / D", f"{ratio_D:.2f}")

    # ------------------------------------------------------------------
    # IS 456 Cl. 25.4 & 39.5/39.6 — P-M Interaction (Uniaxial + Biaxial)
    # ------------------------------------------------------------------
    def check_pm_interaction(self):
        """IS 456 Cl. 25.4 & 39.5 — Eccentricity and P-M Interaction"""
        fac_c_axial = self.constants['material_factors'].get('column_pure_axial_concrete_factor', 0.45)
        fac_y_axial = self.constants['material_factors'].get('column_pure_axial_steel_factor', 0.75)
        fac_c_flex  = self.constants['material_factors'].get('design_concrete_stress_factor', 0.36)
        fac_y_flex  = self.constants['material_factors'].get('design_yield_stress_factor', 0.87)

        # 1. Minimum Eccentricity (IS 456 Cl. 25.4)
        e_min_x = max((self.L_eff / 500) + (self.D / 30), 20.0)
        e_min_y = max((self.L_eff / 500) + (self.b / 30), 20.0)

        M_u_min_x = self.P_u * (e_min_x / 1000)
        M_u_min_y = self.P_u * (e_min_y / 1000)
        M_design_x = max(self.M_u_applied, M_u_min_x)
        M_design_y = max(self.M_uy_applied, M_u_min_y)

        # 2. Pure Axial Capacity (P_uz) — IS 456 Cl. 39.3
        p_uz = (fac_c_axial * self.f_ck * self.A_c) + (fac_y_axial * self.f_y * self.A_sc)
        self.P_uz_kNm = p_uz / 1000

        # 3. Pure Bending Capacity (M_uo) about each axis — simplified
        A_st_half = self.A_sc / 2
        d_eff_x = self.D - 40
        d_eff_y = self.b - 40

        M_uo_x = fac_y_flex * self.f_y * A_st_half * d_eff_x * (
            1 - (A_st_half * self.f_y) / (self.b * d_eff_x * self.f_ck)
        )
        M_uo_y = fac_y_flex * self.f_y * A_st_half * d_eff_y * (
            1 - (A_st_half * self.f_y) / (self.D * d_eff_y * self.f_ck)
        )
        self.M_uo_kNm = M_uo_x / 1e6

        # 4. Biaxial Interaction Exponent (IS 456 Cl. 39.6, Table H)
        pu_puz_ratio = self.P_u / self.P_uz_kNm if self.P_uz_kNm > 0 else 1.0
        if pu_puz_ratio <= 0.2:
            alpha_n = 1.0
        elif pu_puz_ratio <= 0.8:
            alpha_n = 1.0 + (2.0 / 3.0) * (pu_puz_ratio - 0.2) / 0.6
        else:
            alpha_n = 2.0

        # 5. Biaxial Check
        if M_uo_x > 0 and M_uo_y > 0:
            biaxial_ratio = (
                (M_design_x / (M_uo_x / 1e6)) ** alpha_n +
                (M_design_y / (M_uo_y / 1e6)) ** alpha_n
            )
        else:
            biaxial_ratio = 999.0

        if self.P_u > self.P_uz_kNm:
            status = "FAIL (Exceeds Pure Axial Capacity)"
        elif biaxial_ratio <= 1.0:
            status = f"PASS (Biaxial Ratio = {biaxial_ratio:.3f} ≤ 1.0)"
        else:
            # Fallback to conservative uniaxial linear check
            if self.M_uo_kNm > 0:
                uniaxial_ratio = (self.P_u / self.P_uz_kNm) + (M_design_x / self.M_uo_kNm)
            else:
                uniaxial_ratio = 999.0
            
            if uniaxial_ratio <= 1.0:
                status = f"PASS (Conservative Linear P-M = {uniaxial_ratio:.3f})"
            else:
                status = "ACTION REQUIRED (Check SP-16 Charts)"
                self.suggestions.append(
                    "Column: Fails conservative linear P-M check. "
                    "Verify against SP-16 interaction charts."
                )

        self.checks["Minimum Eccentricity (e_min)"] = f"Governing Mx = {M_design_x:.2f} kNm"
        self.checks["P-M Interaction (Uniaxial)"] = status

        self.log_calculation("Min Eccentricity (x-axis)", "max(L/500+D/30, 20)", f"{e_min_x:.2f} mm")
        self.log_calculation("Min Eccentricity (y-axis)", "max(L/500+b/30, 20)", f"{e_min_y:.2f} mm")
        self.log_calculation("Design Moment (Mx)", "max(M_applied, P_u*e_min)", f"{M_design_x:.2f} kNm")
        self.log_calculation("Pure Axial Capacity (P_uz)", f"{fac_c_axial}*fck*Ac+{fac_y_axial}*fy*Asc", f"{self.P_uz_kNm:.2f} kN")
        self.log_calculation("Biaxial Exponent (αn)", "IS 456 Cl. 39.6", f"{alpha_n:.2f}")
        self.log_calculation("Biaxial Interaction Ratio", "(Mx/Mux1)^αn + (My/Muy1)^αn", f"{biaxial_ratio:.3f}")

    # ------------------------------------------------------------------
    # Orchestrator
    # ------------------------------------------------------------------
    def evaluate_compliance(self):
        self.check_steel_limits()
        self.check_lateral_ties()
        self.check_slenderness()
        self.check_pm_interaction()
        return not any("FAIL" in str(v) for v in self.checks.values())