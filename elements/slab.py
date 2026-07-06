# elements/slab.py
import math
from .base_element import StructuralElement

class RCSlabVerifier(StructuralElement):
    def __init__(self, element_id: str, L_x: float, L_y: float, D: float, d: float,
                 f_ck: float, f_y: float, A_st_main: float, w_u: float):
        super().__init__(element_id, f_ck, f_y)
        # Ensure L_x is always the shorter span
        self.L_x = min(L_x, L_y)
        self.L_y = max(L_x, L_y)
        self.D = D
        self.d = d
        self.b = 1000.0       # 1 m design strip
        self.A_st = A_st_main
        self.w_u = w_u

    # ------------------------------------------------------------------
    # IS 456 Annex D — Classification
    # ------------------------------------------------------------------
    def check_classification(self):
        """IS 456 Annex D - One-Way vs Two-Way Classification"""
        aspect_ratio = self.L_y / self.L_x

        if aspect_ratio > 2.0:
            self.classification = "One-Way Slab"
            self.suggestions.append(
                "Slab classified as One-Way. Main reinforcement runs along the short span."
            )
        else:
            self.classification = "Two-Way Slab"
            self.suggestions.append(
                "Slab classified as Two-Way. Torsional reinforcement required at corners "
                "(IS 456 Annex D, Cl. D-1.8)."
            )

        self.checks["Aspect Ratio (L_y/L_x)"] = f"{aspect_ratio:.2f} ({self.classification})"
        self.log_calculation("Slab Aspect Ratio", "L_y / L_x", f"{aspect_ratio:.2f}")

    # ------------------------------------------------------------------
    # IS 456 Cl. 26.5.2.1 — Minimum Reinforcement
    # ------------------------------------------------------------------
    def check_min_reinforcement(self):
        """IS 456:2000 Cl. 26.5.2.1 — Ast_min = 0.12% bD (HYSD) or 0.15% bD (MS)"""
        if self.f_y >= 415:
            pct_min = 0.0012   # 0.12% for HYSD bars (Fe415/Fe500)
            bar_type = "HYSD (Fe415+)"
        else:
            pct_min = 0.0015   # 0.15% for mild steel (Fe250)
            bar_type = "Mild Steel (Fe250)"

        A_st_min = pct_min * self.b * self.D   # per 1m strip

        if self.A_st >= A_st_min:
            status = f"PASS (Ast={self.A_st:.0f} ≥ Ast_min={A_st_min:.0f} mm²/m)"
        else:
            status = f"FAIL (Ast={self.A_st:.0f} < Ast_min={A_st_min:.0f} mm²/m)"
            self.suggestions.append(
                f"Min Reinforcement: Provide at least {A_st_min:.0f} mm²/m "
                f"({pct_min*100:.2f}% of bD for {bar_type}) — IS 456 Cl. 26.5.2.1."
            )

        self.checks["Min Reinforcement (Cl.26.5.2.1)"] = status
        self.log_calculation("Min Steel Area", f"{pct_min*100:.2f}% * b * D", f"{A_st_min:.1f} mm²/m")

    # ------------------------------------------------------------------
    # IS 456 Cl. 26.3.3 — Maximum Bar Spacing
    # ------------------------------------------------------------------
    def check_max_spacing(self):
        """IS 456:2000 Cl. 26.3.3 — Max bar spacing = min(3d, 300mm)"""
        # Estimate spacing from steel area assuming 10mm dia bars
        dia = 10
        a_bar = math.pi * (dia ** 2) / 4   # = 78.54 mm²
        if self.A_st > 0:
            s_provided = (a_bar / self.A_st) * 1000   # mm (per 1m strip)
        else:
            s_provided = 9999   # Effectively infinite → FAIL

        s_max = min(3 * self.d, 300)

        if s_provided <= s_max:
            status = f"PASS (Spacing ≈ {s_provided:.0f} mm ≤ {s_max:.0f} mm)"
        else:
            status = f"FAIL (Spacing ≈ {s_provided:.0f} mm > {s_max:.0f} mm)"
            self.suggestions.append(
                f"Max Bar Spacing: Estimated bar spacing ({s_provided:.0f} mm) exceeds "
                f"min(3d={3*self.d:.0f}, 300) = {s_max:.0f} mm. "
                "Use a smaller bar diameter or increase steel area (IS 456 Cl. 26.3.3)."
            )

        self.checks["Max Bar Spacing (Cl.26.3.3)"] = status
        self.log_calculation("Max Allowable Spacing", "min(3d, 300)", f"{s_max:.0f} mm")
        self.log_calculation("Estimated Bar Spacing (10Ø)", "a_bar/Ast × 1000", f"{s_provided:.0f} mm")

    # ------------------------------------------------------------------
    # IS 456 Cl. 24.1 — Deflection Control
    # ------------------------------------------------------------------
    def check_minimum_depth(self):
        """IS 456 Clause 24.1 - Deflection Control for Slabs"""
        span_ratios = self.constants['deflection'].get('basic_span_ratios', {})

        if self.classification == "One-Way Slab":
            basic_ratio = span_ratios.get('simply_supported', 20)
        else:
            basic_ratio = span_ratios.get('two_way_simply_supported', 35)
            if self.f_y != 250:
                modifier = self.constants['deflection'].get('high_yield_steel_modifier', 0.8)
                basic_ratio = basic_ratio * modifier

        pt = (100 * self.A_st) / (self.b * self.d)
        f_s = 0.58 * self.f_y

        try:
            denominator = 0.225 + (0.00322 * f_s) - (0.625 * math.log10(pt))
            F_t = min(2.0, max(0.5, 1.0 / denominator))
        except (ValueError, ZeroDivisionError):
            F_t = 1.0

        allowable_L_d = basic_ratio * F_t
        actual_L_d = self.L_x / self.d

        if actual_L_d <= allowable_L_d:
            status = "PASS"
        else:
            status = "FAIL (Increase thickness)"
            self.suggestions.append(
                "Slab Deflection: Span/depth ratio exceeds IS 456 limits. "
                "Increase overall depth (D)."
            )

        self.checks["Deflection (L_x/d)"] = status
        self.log_calculation("Slab Modification Factor (F_t)", "Figure 4", f"{F_t:.2f} (pt={pt:.2f}%)")
        self.log_calculation("Allowable Span/Depth", "Basic Ratio × F_t", f"{allowable_L_d:.2f}")
        self.log_calculation("Actual Span/Depth", "L_x / d", f"{actual_L_d:.2f}")

    # ------------------------------------------------------------------
    # IS 456 Annex G — Strip Flexure (both one-way and two-way)
    # ------------------------------------------------------------------
    def check_flexure_strip(self):
        """IS 456 Annex G - Flexure check on 1m design strip"""
        fac_y = self.constants['material_factors'].get('design_yield_stress_factor', 0.87)
        fac_c = self.constants['material_factors'].get('design_concrete_stress_factor', 0.36)
        xu_max_ratios = self.constants['flexure'].get('xu_max_ratio', {})
        xu_max_d = xu_max_ratios.get(str(int(self.f_y)), 0.46)

        if self.classification == "One-Way Slab":
            M_u = (self.w_u * (self.L_x / 1000) ** 2) / 8
        else:
            # IS 456 Table 26 — both αx and αy coefficients
            r = self.L_y / self.L_x
            alpha_x = (r ** 4) / (1 + r ** 4)
            alpha_y = 1.0 / (1 + r ** 4)   # complementary coefficient
            M_u = alpha_x * self.w_u * (self.L_x / 1000) ** 2 / 8
            M_u_y = alpha_y * self.w_u * (self.L_x / 1000) ** 2 / 8
            self.log_calculation(
                "Two-Way Moment (My)",
                f"αy={alpha_y:.3f} × wu × Lx²/8",
                f"{M_u_y:.3f} kNm/m"
            )

        M_u_bytes = M_u * 1e6
        x_max = xu_max_d * self.d
        x_u = (fac_y * self.f_y * self.A_st) / (fac_c * self.f_ck * self.b)

        if x_u <= x_max:
            M_ur = fac_y * self.f_y * self.A_st * self.d * (
                1 - (self.A_st * self.f_y) / (self.b * self.d * self.f_ck)
            )
            is_safe = M_ur >= M_u_bytes
        else:
            M_ur = fac_c * xu_max_d * (1 - 0.42 * xu_max_d) * self.f_ck * self.b * (self.d ** 2)
            is_safe = False
            self.suggestions.append(
                "Slab Flexure: Strip is over-reinforced. Increase slab depth (D)."
            )

        self.checks["Strip Flexure Capacity"] = "PASS" if is_safe else "FAIL (Redesign Required)"

        self.log_calculation("Design Strip Moment (Mx)", "αx × wu × Lx²/8", f"{M_u:.3f} kNm/m")
        self.log_calculation("Strip Capacity vs Demand", f"Cap={M_ur/1e6:.3f} kNm/m", f"Dem={M_u:.3f} kNm/m")

    # ------------------------------------------------------------------
    # Orchestrator
    # ------------------------------------------------------------------
    def evaluate_compliance(self):
        self.check_classification()
        self.check_min_reinforcement()
        self.check_max_spacing()
        self.check_minimum_depth()
        self.check_flexure_strip()
        return not any("FAIL" in str(v) for v in self.checks.values())