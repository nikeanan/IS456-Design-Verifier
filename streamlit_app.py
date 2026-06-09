import streamlit as st
import ezdxf
import io
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from app import RCBeamVerifier
from fpdf import FPDF

def render_beam_visualizer(b, d, xu, xu_max):
    """Generates a dynamic IS 456 beam cross-section plot."""
    fig, ax = plt.subplots(figsize=(6, 8))
    total_depth = d + 50
    beam_rect = patches.Rectangle((0, -total_depth), b, total_depth, linewidth=2, edgecolor='white', facecolor='none')
    ax.add_patch(beam_rect)
    ax.axhline(y=-xu, color='#ff4b4b', linestyle='-', linewidth=2, label=f'Actual NA ($x_u$): {xu:.2f} mm')
    ax.axhline(y=-xu_max, color='#3182ce', linestyle='--', linewidth=2, label=f'Limiting NA ($x_{{u,max}}$): {xu_max:.2f} mm')
    comp_zone = patches.Rectangle((0, -xu), b, xu, facecolor='gray', alpha=0.3, hatch='//')
    ax.add_patch(comp_zone)
    bar_spacing = b / 4
    ax.scatter([bar_spacing, 2*bar_spacing, 3*bar_spacing], [-d, -d, -d], color='white', s=150, zorder=5, label='Tension Steel')
    ax.set_aspect('equal')
    ax.legend(loc='upper right', bbox_to_anchor=(1.05, 1.15))
    plt.axis('off')
    return fig

# --- Matplotlib Plotting Function ---
def plot_beam_cross_section(b, d, x_u, x_max):
    fig, ax = plt.subplots(figsize=(4, 6))
    D = d + 50  
    beam_rect = patches.Rectangle((0, 0), b, D, linewidth=2, edgecolor='black', facecolor='none')
    ax.add_patch(beam_rect)
    comp_rect = patches.Rectangle((0, 0), b, x_u, linewidth=0, facecolor='lightgray', hatch='///', alpha=0.7)
    ax.add_patch(comp_rect)
    ax.axhline(y=x_u, color='red', linestyle='-', linewidth=2, label='Actual NA')
    ax.axhline(y=x_max, color='blue', linestyle='--', linewidth=1.5, label='Limit NA')
    bar_spacing = b / 4
    for i in range(1, 4):
        ax.plot(bar_spacing * i, d, marker='o', markersize=12, markerfacecolor='black', markeredgecolor='white', markeredgewidth=1)
    ax.invert_yaxis()  
    ax.set_aspect('equal')
    ax.set_xlabel("Width (mm)")
    ax.set_ylabel("Depth (mm)")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, linestyle=':', alpha=0.6)
    return fig

# --- PDF Report Generator ---
def create_pdf(b, d, f_ck, f_y, A_st, x_max, x_u, M_ur, status):
    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("helvetica", 'B', 16)
    pdf.cell(0, 10, "IS 456 Structural Design Verification Report", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(10)
    
    # 1. Input Parameters
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, "1. Input Parameters", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", '', 11)
    pdf.cell(0, 8, f"Width (b): {b} mm", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Effective Depth (d): {d} mm", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Concrete Grade (f_ck): M{f_ck} MPa", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Steel Grade (f_y): Fe{f_y} MPa", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Tension Steel Area (A_st): {A_st} mm^2", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # 2. Structural Analysis
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, "2. Structural Analysis", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", '', 11)
    pdf.cell(0, 8, f"Limiting Neutral Axis (x_max): {x_max:.2f} mm", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Actual Neutral Axis (x_u): {x_u:.2f} mm", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Ultimate Moment Capacity (M_ur): {M_ur:.2f} kNm", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # 3. Compliance Status
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, "3. Compliance Status", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", '', 11)
    pdf.multi_cell(0, 8, status, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # 4. Step-by-Step Verification (THE NEW SECTION)
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, "4. Step-by-Step Verification (IS 456:2000 Annex G)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("courier", '', 10) 
    
    calc_text = f"""
Step A: Actual Neutral Axis Depth (x_u)
Formula: x_u = (0.87 * f_y * A_st) / (0.36 * f_ck * b)
Substituted: x_u = (0.87 * {f_y} * {A_st}) / (0.36 * {f_ck} * {b})
Result: x_u = {x_u:.2f} mm

Step B: Limiting Neutral Axis Depth (x_max)
Result: x_max = {x_max:.2f} mm

Step C: Section Classification
Condition: Is x_u <= x_max?
Check: {x_u:.2f} mm <= {x_max:.2f} mm 
Conclusion: {'Under-Reinforced (Safe)' if x_u <= x_max else 'Over-Reinforced (Redesign Required)'}

Step D: Ultimate Moment of Resistance (M_ur)
Formula: M_ur = 0.87 * f_y * A_st * d * [1 - (A_st * f_y) / (b * d * f_ck)]
Substituted: M_ur = 0.87 * {f_y} * {A_st} * {d} * [1 - ({A_st} * {f_y}) / ({b} * {d} * {f_ck})]
Result: M_ur = {M_ur:.2f} kNm
    """
    pdf.multi_cell(0, 5, calc_text, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    
    # Footer Disclaimer
    pdf.set_font("helvetica", 'I', 8)
    pdf.cell(0, 8, "This report is generated for preliminary verification only and must be independently reviewed.", new_x="LMARGIN", new_y="NEXT")      
    return pdf.output()

# --- Streamlit UI Setup ---
st.set_page_config(page_title="IS 456 Verifier", layout="centered")
st.title("Automated IS 456 Design Verifier")

# Create Tabs
tab1, tab2 = st.tabs(["🏗️ Single Beam Analyzer", "📂 Batch CSV Processor"])

# ==========================================
# TAB 1: SINGLE BEAM ANALYZER
# ==========================================
# No spaces here
with tab1:
    # Exactly 4 spaces here
    with st.sidebar:
        # Exactly 8 spaces here
        st.header("BIM Integration")
        dxf_file = st.file_uploader("Upload Beam DXF", type=['dxf'])
        
        # Default values before upload
        dxf_b = 230.0
        dxf_d = 450.0
        
        if dxf_file is not None:
            try:
                # Parse the DXF file in memory
                doc = ezdxf.read(io.BytesIO(dxf_file.read()))
                msp = doc.modelspace()
                found = False
                
                # Search for the specific AutoCAD block
                for insert in msp.query('INSERT'):
                    if insert.dxf.name == 'BEAM_DIMENSIONS':
                        for attrib in insert.attribs:
                            if attrib.dxf.tag == 'b':
                                dxf_b = float(attrib.dxf.text)
                            elif attrib.dxf.tag == 'd':
                                dxf_d = float(attrib.dxf.text)
                        found = True
                        break
                
                if found:
                    st.success(f"CAD Data Synced: b={dxf_b}mm, d={dxf_d}mm")
                else:
                    st.warning("BEAM_DIMENSIONS block not found in drawing.")
            except Exception as e:
                st.error("Error parsing DXF file. Ensure it is a valid format.")
                
        st.divider()

        # --- Design Parameters ---
        st.header("Design Parameters")
        
        # The values here now dynamically update if a DXF is uploaded!
        b = st.number_input("Width (b) [mm]", value=dxf_b, min_value=10.0, max_value=2000.0)
        d = st.number_input("Effective Depth (d) [mm]", value=dxf_d, min_value=10.0, max_value=2500.0)

        # --- ML Predictor Integration ---
        st.markdown("**Materials Science Integration**")
        use_ml = st.toggle("🤖 Predict f_ck via ML Model")
        
        if use_ml:
            st.caption("Input mix proportions (kg/m³) to predict compressive strength.")
            cement = st.number_input("Cement", value=350.0, step=10.0)
            water = st.number_input("Water", value=180.0, step=5.0)
            fine_agg = st.number_input("Fine Aggregate", value=700.0, step=10.0)
            coarse_agg = st.number_input("Coarse Aggregate", value=1000.0, step=10.0)
            
            # Prototype ML Placeholder (Abram's Law approximation)
            # You will replace this with: model.predict([[cement, water, fine_agg, coarse_agg]])
            wc_ratio = water / cement
            predicted_fck = max(15.0, min(60.0, 110.0 / (4 ** wc_ratio))) 
            
            st.success(f"Predicted Grade: **M{predicted_fck:.2f}**")
            f_ck = predicted_fck
        else:
            f_ck = st.number_input("Concrete Grade (f_ck) [MPa]", value=25.0, min_value=15.0, max_value=60.0)
        # --------------------------------
        f_y = st.selectbox("Steel Grade (f_y) [MPa]", options=[250, 415, 500], index=1)
        A_st = st.number_input("Tension Steel Area (A_st) [mm²]", value=1000.0, min_value=50.0, max_value=10000.0)
        st.divider()
        M_u_applied = st.number_input("Applied Factored Moment [kNm]", value=120.0, min_value=1.0, max_value=1000.0)

    verifier = RCBeamVerifier(b, d, f_ck, f_y, A_st)
    x_max = verifier.limiting_neutral_axis()
    x_u = (0.87 * f_y * A_st) / (0.36 * f_ck * b)
    M_ur = verifier.ultimate_moment_capacity()
    verification_status = verifier.verify_design(M_u_applied)

    st.subheader("Structural Analysis", anchor=False)
    text_col, plot_col = st.columns([1.5, 1])
    # Assuming your variables are currently named b, d, actual_xu, and limiting_xu
    st.write("### Cross-Section Visualization")
    fig = render_beam_visualizer(b, d, x_u, x_max)
    st.pyplot(fig)

    with text_col:
        st.metric("Limiting NA ($x_{max}$)", f"{x_max:.2f} mm")
        st.metric("Actual NA ($x_u$)", f"{x_u:.2f} mm")
        st.metric("Capacity ($M_{ur}$)", f"{M_ur:.2f} kNm")

    with plot_col:
        fig = plot_beam_cross_section(b, d, x_u, x_max)
        st.pyplot(fig)

    st.subheader("Compliance & Design Actions", anchor=False)
    if "SAFE" in verification_status:
        st.success(verification_status)
    else:
        st.error(verification_status)
        if "Over-reinforced" in verification_status:
            st.warning("⚠️ Applied moment exceeds the balanced capacity. Initiating Doubly Reinforced Design Protocol...")
            design_results = verifier.design_doubly_reinforced(M_u_applied)
            with st.expander("View Doubly Reinforced Design Details", expanded=True):
                st.markdown("To safely carry this load, compression steel must be added to the top of the beam.")
                colA, colB = st.columns(2)
                colA.metric("Required Top Steel ($A_{sc}$)", f"{design_results['A_sc']:.2f} mm²")
                colB.metric("Required Bottom Steel ($A_{st, total}$)", f"{design_results['A_st_total']:.2f} mm²")

    st.divider()
    st.subheader("Generate Documentation", anchor=False)
    pdf_bytes = create_pdf(b, d, f_ck, f_y, A_st, x_max, x_u, M_ur, verification_status)
    st.download_button(label="📄 Download PDF Report", data=bytes(pdf_bytes), file_name="IS456_Design_Report.pdf", mime="application/pdf")

# ==========================================
# TAB 2: BATCH CSV PROCESSOR
# ==========================================
with tab2:
    st.header("Enterprise Batch Verification", anchor=False)
    st.markdown("Upload a CSV file exported from your structural analysis software to verify hundreds of beams instantly.")
    
    st.info("**Required CSV Columns:** `Beam_ID`, `b`, `d`, `f_ck`, `f_y`, `A_st`, `M_u_applied`")
    
    uploaded_file = st.file_uploader("Upload Structural Data (CSV)", type="csv")
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.write("Data Preview:")
            st.dataframe(df.head())
            
            if st.button("Run Bulk IS 456 Verification", type="primary"):
                results = []
                
                # Iterate through the uploaded dataframe
                for index, row in df.iterrows():
                    batch_verifier = RCBeamVerifier(
                        b=row['b'], d=row['d'], f_ck=row['f_ck'], f_y=row['f_y'], A_st=row['A_st']
                    )
                    cap = batch_verifier.ultimate_moment_capacity()
                    stat = batch_verifier.verify_design(row['M_u_applied'])
                    
                    results.append({
                        "Beam_ID": row.get('Beam_ID', f"Beam_{index+1}"),
                        "Capacity_kNm": round(cap, 2),
                        "IS456_Status": stat
                    })
                
                # Merge results back with original data
                results_df = pd.DataFrame(results)
                final_df = pd.concat([df, results_df[['Capacity_kNm', 'IS456_Status']]], axis=1)
                
                st.success(f"✅ Successfully processed {len(final_df)} beams!")
                st.dataframe(final_df)
                
                # Provide the download button for the new dataset
                csv = final_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Verified Dataset (CSV)",
                    data=csv,
                    file_name='Verified_Batch_Results.csv',
                    mime='text/csv',
                )
        except Exception as e:
            st.error(f"Error processing file. Please ensure columns match the required format. Details: {e}")