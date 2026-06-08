class RCBeamVerifier:
    def __init__(self, b: float, d: float, f_ck: float, f_y: float, A_st: float, d_prime: float = 50.0):
        # Standardizing units to mm and N/mm² (MPa) for IS 456 compliance
        self.b = b
        self.d = d
        self.f_ck = f_ck
        self.f_y = f_y
        self.A_st = A_st
        self.d_prime = d_prime

    def limiting_neutral_axis(self) -> float:
        if self.f_y == 250:
            return 0.53 * self.d
        elif self.f_y == 415:
            return 0.48 * self.d
        elif self.f_y == 500:
            return 0.46 * self.d
        else:
            raise ValueError("Steel grade must be 250, 415, or 500.")

    def is_under_or_over_reinforced(self) -> str:
        x_u = (0.87 * self.f_y * self.A_st) / (0.36 * self.f_ck * self.b)
        if x_u <= self.limiting_neutral_axis():
            return "Under-reinforced"
        return "Over-reinforced"

    def ultimate_moment_capacity(self) -> float:
        x_u = (0.87 * self.f_y * self.A_st) / (0.36 * self.f_ck * self.b)
        x_ul = self.limiting_neutral_axis()
        
        if x_u <= x_ul:
            M_u = 0.87 * self.f_y * self.A_st * (self.d - 0.42 * x_u)
        else:
            M_u = 0.36 * (x_ul / self.d) * (1 - 0.42 * (x_ul / self.d)) * self.b * (self.d ** 2) * self.f_ck
            
        return M_u / 1e6  # Direct transformation to kNm

    def verify_design(self, M_u_applied: float) -> str:
        M_ur = self.ultimate_moment_capacity()
        state = self.is_under_or_over_reinforced()
        
        if state == "Over-reinforced":
            return f"FAIL (Over-reinforced): IS 456 prohibits over-reinforced sections. Redesign required."
            
        if M_ur >= M_u_applied:
            return f"SAFE ({state}): Capacity {M_ur:.2f} kNm >= Applied {M_u_applied:.2f} kNm."
            
        return f"FAIL ({state}): Capacity {M_ur:.2f} kNm < Applied {M_u_applied:.2f} kNm."

    def design_doubly_reinforced(self, M_u_applied: float) -> dict:
        x_max = self.limiting_neutral_axis()
        
        # Calculate limiting moment capacity (M_u,lim) for balanced section
        M_u_lim = (0.36 * (x_max / self.d) * (1 - 0.42 * (x_max / self.d)) * self.b * (self.d ** 2) * self.f_ck) / 1e6
        
        if M_u_applied <= M_u_lim:
            return {"status": "Singly Reinforced Sufficient", "A_sc": 0, "A_st_total": self.A_st}
            
        # M_u2 is the excess moment to be resisted by compression steel
        M_u2 = M_u_applied - M_u_lim
        
        # Approximation of f_sc (stress in compression steel) for prototype
        f_sc = 0.87 * self.f_y
        
        # Required Compression Steel (A_sc)
        A_sc = (M_u2 * 1e6) / (f_sc * (self.d - self.d_prime))
        
        # Additional Tension Steel (A_st2)
        A_st2 = (A_sc * f_sc) / (0.87 * self.f_y)
        
        # Limiting Tension Steel (A_st,lim) for the balanced concrete section
        A_st_lim = (0.36 * self.f_ck * self.b * x_max) / (0.87 * self.f_y)
        
        return {
            "status": "Requires Doubly Reinforced Design", 
            "A_sc": A_sc, 
            "A_st_total": A_st_lim + A_st2
        }