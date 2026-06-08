class RCBeamVerifier:
    def __init__(self, b: float, d: float, f_ck: float, f_y: float, A_st: float):
        # Standardizing units to mm and N/mm² (MPa) for IS 456 compliance
        self.b = b
        self.d = d
        self.f_ck = f_ck
        self.f_y = f_y
        self.A_st = A_st

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
        
        if M_ur >= M_u_applied:
            return f"SAFE ({state}): Capacity {M_ur:.2f} kNm >= Applied {M_u_applied:.2f} kNm."
        return f"FAIL ({state}): Capacity {M_ur:.2f} kNm < Applied {M_u_applied:.2f} kNm."
    
    
# --- BENCHMARK TEST ---
if __name__ == "__main__":
    # Test Case: b=230mm, d=450mm, M25 Concrete, Fe415 Steel, Ast=1000mm^2
    beam = RCBeamVerifier(b=230, d=450, f_ck=25, f_y=415, A_st=1000)
    
    print("--- IS 456 RC Beam Verification ---")
    print(f"Limiting Neutral Axis (x_max): {beam.limiting_neutral_axis():.2f} mm")
    print(f"Section Status: {beam.is_under_or_over_reinforced()}")
    print(f"Ultimate Capacity (M_ur): {beam.ultimate_moment_capacity():.2f} kNm")
    
    # Test against an applied factored load of 120 kNm
    print("\n--- Design Check ---")
    print(beam.verify_design(M_u_applied=120))
