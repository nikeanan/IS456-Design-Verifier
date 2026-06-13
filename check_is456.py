def check_is456_min_reinforcement(b, d, fy):
    """
    Calculates the minimum area of tension reinforcement (Ast) 
    as per IS 456:2000 (Cl. 26.5.1.1).
    
    Parameters:
    b  (float): Width of the beam in mm
    d  (float): Effective depth of the beam in mm
    fy (float): Characteristic yield strength of steel in N/mm^2
    
    Returns:
    float: Minimum area of tension reinforcement (Ast) in mm^2
    """
    # Formula: Ast / (b * d) = 0.85 / fy
    ast_min = (0.85 * b * d) / fy
    return ast_min

# Example usage for testing:
if __name__ == "__main__":
    width = 250   # mm
    depth = 400   # mm
    fy = 415      # N/mm^2 (Fe 415)
    
    result = check_is456_min_reinforcement(width, depth, fy)
    print(f"Minimum tension reinforcement required: {result:.2f} mm^2")