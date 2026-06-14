# boq_engine.py

def calculate_boq(element_type, width, depth, length, steel_area, steel_grade, concrete_grade):
    """
    Calculates Bill of Quantities and estimated cost for a structural element.
    Dimensions should be in mm, areas in mm^2.
    """
    # Unit weights and base rates (Standard Indian Construction Rates - Customizable)
    unit_weight_steel = 7850  # kg/m^3
    
    # Base material rates (INR)
    rate_concrete_per_m3 = 4500 + (concrete_grade - 20) * 100  # Scales with grade
    rate_steel_per_kg = 65 + (steel_grade - 415) * 0.05        # Scales with grade
    
    # Volume conversions (mm^3 to m^3)
    vol_concrete_m3 = (width * depth * length) / 1e9
    
    # Steel weight conversion (Area * Length * Density)
    vol_steel_m3 = (steel_area * length) / 1e9
    weight_steel_kg = vol_steel_m3 * unit_weight_steel
    
    # Cost Calculations
    cost_concrete = vol_concrete_m3 * rate_concrete_per_m3
    cost_steel = weight_steel_kg * rate_steel_per_kg
    total_cost = cost_concrete + cost_steel
    
    return {
        "volume_m3": round(vol_concrete_m3, 2),
        "steel_kg": round(weight_steel_kg, 2),
        "total_cost": round(total_cost, 2),
        "concrete_cost_per_m3": round(rate_concrete_per_m3, 2), # <-- Added
        "steel_cost_per_kg": round(rate_steel_per_kg, 2)        # <-- Added
    }