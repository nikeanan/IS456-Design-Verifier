# visualizer.py
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def render_cross_section(verifier, element_type="Beam"):
    fig, ax = plt.subplots(figsize=(5, 6))
    
    if element_type == "Beam":
        b = verifier.b
        d = verifier.d
        D = getattr(verifier, 'D', d + 50)
        x_u = getattr(verifier, 'x_u', 0)
        x_max = getattr(verifier, 'x_max', 0)

        # Concrete Outline
        ax.add_patch(patches.Rectangle((0, -D), b, D, linewidth=2, edgecolor='#e2e8f0', facecolor='#475569'))
        
        # Neutral Axes
        if x_u > 0:
            ax.axhline(y=-x_u, color='#ef4444', linestyle='-', linewidth=2, label=f'Actual NA: {x_u:.1f} mm')
            ax.add_patch(patches.Rectangle((0, -x_u), b, x_u, facecolor='#94a3b8', alpha=0.4, hatch='//'))
        if x_max > 0:
            ax.axhline(y=-x_max, color='#3b82f6', linestyle='--', linewidth=2, label=f'Limit NA: {x_max:.1f} mm')

        # Tension Steel
        bar_spacing = b / 4
        ax.scatter([bar_spacing, 2*bar_spacing, 3*bar_spacing], [-d, -d, -d], color='white', s=100, zorder=5)
        
    elif element_type == "Column":
        b = verifier.b
        D = verifier.D
        
        # Concrete Outline
        ax.add_patch(patches.Rectangle((0, 0), b, D, linewidth=2, edgecolor='#e2e8f0', facecolor='#64748b'))
        
        # 6 Rebars (3 Top, 3 Bottom)
        cover = 40
        x_bars = [cover, b/2, b-cover]
        y_bars_bottom = [cover, cover, cover]
        y_bars_top = [D-cover, D-cover, D-cover]
        
        ax.scatter(x_bars + x_bars, y_bars_bottom + y_bars_top, color='white', s=120, zorder=5, label='Main Steel')

    elif element_type == "Slab":
        # Simplified Slab Section
        D = verifier.D
        b = 1000 # 1m strip
        ax.add_patch(patches.Rectangle((0, 0), b, D, linewidth=2, edgecolor='#e2e8f0', facecolor='#475569'))
        ax.scatter([200, 400, 600, 800], [40, 40, 40, 40], color='white', s=80, label='Main Steel')
        ax.set_xlim(-100, 1100)
        ax.set_ylim(-50, D + 50)
        
    elif element_type == "Footing":
        # Simplified Pad Footing Plan View
        L, B = verifier.L, verifier.B
        cL, cB = verifier.col_L, verifier.col_B
        ax.add_patch(patches.Rectangle((0, 0), L, B, linewidth=2, edgecolor='#e2e8f0', facecolor='#64748b'))
        ax.add_patch(patches.Rectangle(((L-cL)/2, (B-cB)/2), cL, cB, linewidth=2, edgecolor='white', facecolor='#1e293b', hatch='//'))
        ax.set_xlim(-100, L + 100)
        ax.set_ylim(-100, B + 100)
            
    ax.set_aspect('equal')
    ax.set_aspect('equal')
    
    # --- NEW: Safely check for labels before drawing the legend ---
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=2, facecolor='#0e1117', edgecolor='white', labelcolor='white')
        
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    plt.axis('off')
    
    return fig
def render_bending_moment_diagram(verifier):
    fig, ax = plt.subplots(figsize=(6, 4))          
    x = [0, verifier.L]
    M = [0, verifier.M_u]   
    ax.plot(x, M, color='#ef4444', linewidth=3, label='Bending Moment Diagram')
    ax.fill_between(x, M, color='#ef4444', alpha=0.3)
    ax.set_xlabel('Length (mm)', color='white')
    ax.set_ylabel('Bending Moment (kNm)', color='white')
    ax.set_title('Bending Moment Diagram', color='white')
    ax.tick_params(colors='white')  
    ax.set_xlim(0, verifier.L)
    ax.set_ylim(0, max(M)*1.2)
    ax.grid(color='#334155', linestyle='--', linewidth=0.5)     
    ax.legend(facecolor='#0e1117', edgecolor='white', labelcolor='white')   
    fig.patch.set_facecolor('#0e1117')
    ax.patch.set_facecolor('#0e1117')
    ax.patch.set_alpha(0.0)
    plt.axis('off')
    return fig
def render_shear_force_diagram(verifier):
    fig, ax = plt.subplots(figsize=(6, 4))
    x = [0, verifier.L]
    V = [0, verifier.V_u]
    ax.plot(x, V, color='#ef4444', linewidth=3, label='Shear Force Diagram')
    ax.fill_between(x, V, color='#ef4444', alpha=0.3)
    ax.set_xlabel('Length (mm)', color='white')
    ax.set_ylabel('Shear Force (kN)', color='white')
    ax.set_title('Shear Force Diagram', color='white')
    ax.tick_params(colors='white')
    ax.set_xlim(0, verifier.L)
    ax.set_ylim(0, max(V)*1.2)
    ax.legend(loc='upper right', frameon=True, facecolor='#0e1117', edgecolor='white', labelcolor='white')
    ax.grid(color='#334155', linestyle='--', linewidth=0.5)
    fig.patch.set_facecolor('#0e1117')
    ax.patch.set_facecolor('#0e1117')
    ax.patch.set_alpha(0.0)
    plt.axis('off')
    return fig
def render_combined_diagram(verifier):      
    # MUST initialize the figure and axes first!
    fig, ax = plt.subplots(figsize=(6, 4))
    
    # ... (Your combined diagram drawing logic will go here) ...
    
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    plt.axis('off')
    
    return fig
    