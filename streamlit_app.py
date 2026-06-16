import streamlit as st
import importlib
import pandas as pd
import tempfile
import os
# Assuming your new file is in an 'engine' folder:
from engine.ifc_parser import BIMExtractor
from report_generator import create_pdf_report
from elements.beam import RCBeamVerifier
from elements.column import RCColumnVerifier
from elements.slab import RCSlabVerifier
from elements.footing import RCFootingVerifier
from visualizer import render_cross_section
from boq_engine import calculate_boq
# ==========================================
# 1. PAGE CONFIGURATIONS (Must be first)
# ==========================================
st.set_page_config(page_title="Enterprise IS 456 Verifier", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .metric-card { 
        background-color: #1e293b; 
        padding: 15px; 
        border-radius: 8px; 
        border: 1px solid #334155; 
        margin-bottom: 15px;
        color: #f8fafc;  
    }
    .status-safe { color: #22c55e; font-weight: bold; }
    .status-fail { color: #ef4444; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. THE SIDEBAR (Declares element_choice)
# ==========================================
with st.sidebar:
    st.header("Enterprise IS 456")
    st.subheader("Structural Verifier", anchor=False)
    
    element_choice = st.radio("Select Module", [
        "RC Beams", 
        "RC Columns", 
        "RC Slabs", 
        "Isolated Footings", 
        "Batch CSV Processor",
        "BIM (IFC) Integration"
    ])
    
    st.divider()
    
    st.header("Eco-Material ML Predictor")
    use_ml = st.toggle("🤖 Predict f_ck via ML Model")
    
    if use_ml:
        st.markdown("**Recycled Fine Aggregate (RFA) Model**")
        st.caption("Predicts 28-day compressive strength based on sustainable mix proportions.")
        
        target_grade = st.number_input("Target Design Grade (e.g., M30)", value=30.0, step=5.0)
        rfa_percent = st.slider("RFA Replacement (%)", min_value=0, max_value=100, value=25)
        
        # Simulated ML Inference
        base_strength = target_grade + 2.5  
        if rfa_percent <= 30:
            predicted_fck = base_strength + (rfa_percent * 0.05) 
        else:
            penalty = ((rfa_percent - 30) / 100) * 0.25 
            predicted_fck = base_strength * (1 - penalty)
            
        st.success(f"Predicted f_ck: **{predicted_fck:.2f} MPa**")
        f_ck = predicted_fck 
        
    else:
        f_ck = st.number_input("f_ck [MPa] (Concrete Grade)", value=30.0, step=5.0)

    f_y = st.selectbox("Steel Grade (f_y) [MPa]", [415, 500, 550])


# ==========================================
# 3. MAIN WORKSPACE (Strictly un-indented)
# ==========================================
st.title(f"{element_choice} Design Verifier")

if element_choice == "RC Beams":
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Design & Loading Parameters")
        b = st.number_input("Width [mm]", value=250.0)
        D = st.number_input("Overall Depth (D) [mm]", value=450.0) 
        d = st.number_input("Effective Depth (d) [mm]", value=400.0)
        L = st.number_input("Total Span Length [mm]", value=5000.0)
        A_st = st.number_input("Tension Steel Area (A_st) [mm²]", value=1000.0)
        
        st.markdown("##### Factored Loads")
        row1 = st.columns(3)
        M_u = row1[0].number_input("Moment [kNm]", value=120.0)
        V_u = row1[1].number_input("Shear [kN]", value=80.0)
        T_u = row1[2].number_input("Torsion [kNm]", value=15.0)

    with col2:
        st.subheader("Structural & Cost Analysis")
        
        # 1. Calculate Equivalent Loads dynamically (IS 456 Clause 41.4.2)
        M_eq = M_u + (T_u * (1 + D / b) / 1.7) if b > 0 else M_u
        V_eq = V_u + (1.6 * (T_u / b) * 1000) if b > 0 else V_u
        
        # 2. Instantiate the Verifier 
        verifier = RCBeamVerifier(
            element_id="B1", b=b, d=d, D=D, L=L, 
            f_ck=f_ck, f_y=f_y, A_st=A_st, M_eq=M_eq, V_eq=V_eq
        )
        
        # 3. Evaluate Compliance
        is_safe = verifier.evaluate_compliance()
        cap_M = getattr(verifier, 'M_ur', 0) / 1e6
        
        # 4. Render Visuals
        fig = render_cross_section(verifier, element_type="Beam")
        st.write("### Cross-Section Visualization")
        st.pyplot(fig, transparent=True)
        
        # 5. Render Status Card
        status_color = "status-safe" if cap_M >= M_eq else "status-fail"
        status_text = "SAFE" if cap_M >= M_eq else "FAIL"
        
        st.markdown(f"""
        <div class="metric-card">
            <div>Equivalent Moment (Flexure + Torsion): <b>{M_eq:.1f} kNm</b></div>
            <div>Status: <span class="{status_color}">{status_text}: Capacity {cap_M:.1f} {'≥' if cap_M >= M_eq else '<'} Applied {M_eq:.1f}</span></div>
        </div>
        """, unsafe_allow_html=True)
        
        # 6. BOQ & Cost Optimization
        st.subheader("Automated Bill of Quantities (BOQ)")
        boq = calculate_boq("Beam", b, D, L, A_st, f_y, f_ck)
        
        if boq['total_cost'] > 40000:
            st.error("⚠️ High Material Cost Alert! This beam design may be uneconomical. Immediate redesign is recommended.")
            st.write("Consider consulting with a structural engineer to explore alternative cross-sections that meet safety requirements at a lower cost.")
        elif boq['total_cost'] > 20000:
            st.warning("💡 Consider optimizing the beam design to reduce material costs. Suggestions may include modifying width (b), depth (D), or tension steel (A_st).")
            st.write("Optimizing designs can lead to significant cost savings while ensuring safety and compliance with IS 456.")
        else:
            st.success("✅ Material costs are within an acceptable baseline range.")
            
        # Structural check before claiming compliance
        if is_safe:
            st.write("This beam design is cost-effective and structurally compliant with IS 456.")
        else:
            st.write("While material volumes are low, this design **FAILS structural compliance**. Redesign required.")
            st.warning("⚠️ **Status: Redesign Required** — Costs below reflect the current (non-compliant) design and will change upon structural correction.")
            
        # Display the BOQ table cleanly
        st.table({
            "Parameter": ["Concrete Volume (m³)", "Steel Weight (kg)", "Total Material Cost (₹)"],
            "Value": [round(boq['volume_m3'], 2), round(boq['steel_kg'], 2), round(boq['total_cost'], 2)]
        })
        
        st.write("### Detailed Breakdown of Costs:")
        st.write(f"- Concrete Volume: **{boq['volume_m3']} m³** at ₹ {boq['concrete_cost_per_m3']:,.2f} per m³")
        st.write(f"- Steel Weight: **{boq['steel_kg']} kg** at ₹ {boq['steel_cost_per_kg']:,.2f} per kg")
        cost_per_m = boq['total_cost'] / (L / 1000)
        st.write(f"- Total Cost per Meter Span: **₹ {cost_per_m:,.2f} per m**")
        
        # 7. PDF Report & CAD Export
        from engine.dxf_exporter import CADExporter
        
        st.write("---")
        btn_col1, btn_col2 = st.columns(2)
        
        with btn_col1:
            # Generate and download PDF
            pdf_bytes = create_pdf_report(verifier, boq, fig)
            st.download_button(
                label="📄 Download Official PDF Report", 
                data=pdf_bytes, 
                file_name="IS456_Report_Beam.pdf", 
                mime="application/pdf", 
                type="primary"
            )
            
        with btn_col2:
            # Generate and download AutoCAD .dxf
            dxf_file = CADExporter.generate_cross_section_dxf(verifier.element_id, b, D, "Beam")
            with open(dxf_file, "rb") as f:
                st.download_button(
                    label="📐 Download CAD (.dxf)", 
                    data=f, 
                    file_name=f"Beam_{verifier.element_id}.dxf", 
                    mime="application/dxf",
                    type="secondary"
                )
elif element_choice == "RC Columns":
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Column Parameters")
        b = st.number_input("Width [mm]", value=300.0)
        D = st.number_input("Depth [mm]", value=450.0)
        L_eff = st.number_input("Effective Length [mm]", value=3000.0)
        A_sc = st.number_input("A_sc (Steel Area) [mm²]", value=1200.0)
        P_u = st.number_input("Applied Axial Load [kN]", value=1500.0)
        M_u = st.number_input("Applied Moment [kNm]", value=30.0) # Ensure moment input exists
        
    with col2:
        st.subheader("Structural Analysis")
        
        # 1. Instantiate and Evaluate
        verifier = RCColumnVerifier("C1", b, D, L_eff, f_ck, f_y, A_sc, P_u, M_u)
        is_safe = verifier.evaluate_compliance()
        pm_status = verifier.checks.get("P-M Interaction (Uniaxial)", "UNKNOWN")
        
        # 2. Render Visuals
        fig = render_cross_section(verifier, element_type="Column")
        st.write("### Cross-Section")
        st.pyplot(fig, transparent=True)
        
        # 3. Status Card
        status_color = "status-safe" if "PASS" in pm_status else "status-fail"
        st.markdown(f"""
        <div class="metric-card">
            <div>Classification: <b>{getattr(verifier, 'classification', 'Unknown')}</b></div>
            <br>
            <div>Overall Status: <span class="{status_color}">{pm_status}</span></div>
        </div>
        """, unsafe_allow_html=True)
        
        # 4. BOQ & Cost Optimization
        st.subheader("Automated Bill of Quantities (BOQ)")
        boq = calculate_boq("Column", b, D, L_eff, A_sc, f_y, f_ck)
        
        if boq['total_cost'] > 50000:
            st.error("⚠️ High Material Cost Alert! This column design may be uneconomical.")
            st.write("Consider alternative layouts or higher grade concrete (f_ck).")
        elif boq['total_cost'] > 25000:
            st.warning("💡 Consider optimizing the column design to reduce material costs.")
            st.write("Modifying dimensions (b, D) or vertical steel area (A_sc) may help.")
        else:
            st.success("✅ Material costs are within an acceptable baseline range.")
            
        # P-M Interaction Specific Logic
        if "PASS" in pm_status and is_safe:
            st.write("This column design is cost-effective and structurally compliant with IS 456.")
        elif "ACTION REQUIRED" in pm_status:
            st.write("While material volumes are low, this design requires **advanced SP-16 verification** before claiming structural compliance.")
            st.warning("⚠️ **Status: Verification Pending** — Costs below reflect the preliminary design and may change if SP-16 charts demand a larger section.")
        else:
            st.write("While material volumes are low, this design **FAILS structural compliance**. Redesign required.")
            st.warning("⚠️ **Status: Redesign Required** — Costs below reflect the current (non-compliant) design and will change upon structural correction.")
            
        st.table({
            "Parameter": ["Concrete Volume (m³)", "Steel Weight (kg)", "Total Material Cost (₹)"],
            "Value": [round(boq['volume_m3'], 2), round(boq['steel_kg'], 2), round(boq['total_cost'], 2)]
        })
        
        st.write("### Detailed Breakdown of Costs:")
        st.write(f"- Concrete Volume: **{boq['volume_m3']} m³** at ₹ {boq['concrete_cost_per_m3']:,.2f} per m³")
        st.write(f"- Steel Weight: **{boq['steel_kg']} kg** at ₹ {boq['steel_cost_per_kg']:,.2f} per kg")
        cost_per_m = boq['total_cost'] / (L_eff / 1000)
        st.write(f"- Total Cost per Meter Height: **₹ {cost_per_m:,.2f} per m**")
        
        # 5. PDF Report
        pdf_bytes = create_pdf_report(verifier, boq, fig)
        st.download_button(label="📄 Download Official PDF Report", data=pdf_bytes, file_name="IS456_Report_Column.pdf", mime="application/pdf", type="primary")

elif element_choice == "RC Slabs":
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Slab Parameters (1m Strip)")
        L_x = st.number_input("Short Span (L_x) [mm]", value=3000.0)
        L_y = st.number_input("Long Span (L_y) [mm]", value=4000.0)
        D = st.number_input("Overall Thickness (D) [mm]", value=150.0)
        d = st.number_input("Effective Depth (d) [mm]", value=125.0)
        A_st = st.number_input("Main Steel Area [mm²/m]", value=300.0)
        w_u = st.number_input("Factored Load (w_u) [kN/m²]", value=12.0)
        
    with col2:
        st.subheader("Structural Analysis")
        
        verifier = RCSlabVerifier("S1", L_x, L_y, D, d, f_ck, f_y, A_st, w_u)
        is_safe = verifier.evaluate_compliance()
        
        fig = render_cross_section(verifier, element_type="Slab")
        st.write("### Slab Cross-Section Strip")
        st.pyplot(fig, transparent=True)
        
        status_color = "status-safe" if is_safe else "status-fail"
        status_text = "SAFE" if is_safe else "ACTION REQUIRED"
        
        st.markdown(f"""
        <div class="metric-card">
            <div>Slab Classification: <b>{getattr(verifier, 'classification', 'Unknown')}</b></div>
            <div>Overall Status: <span class="{status_color}">{status_text}</span></div>
        </div>
        """, unsafe_allow_html=True)
        
        st.subheader("Automated Bill of Quantities (BOQ)")
        boq = calculate_boq("Slab", L_x, D, L_y, A_st * (L_y/1000), f_y, f_ck)
        
        if boq['total_cost'] > 120000:
            st.error("⚠️ High Material Cost Alert! This slab design may be uneconomical. Immediate redesign is recommended.")
        elif boq['total_cost'] > 60000:
            st.warning("💡 Consider optimizing the slab design to reduce material costs. Suggestions may include modifying overall thickness (D).")
        else:
            st.success("✅ Material costs are within an acceptable baseline range.")
            
        if is_safe:
            st.write("This slab design is cost-effective and structurally compliant with IS 456.")
        else:
            st.write("While material volumes are low, this design **FAILS structural compliance**. Redesign required.")
            st.warning("⚠️ **Status: Redesign Required** — Costs below reflect the current (non-compliant) design.")
            
        st.table({
            "Parameter": ["Concrete Volume (m³)", "Steel Weight (kg)", "Total Material Cost (₹)"],
            "Value": [round(boq['volume_m3'], 2), round(boq['steel_kg'], 2), round(boq['total_cost'], 2)]
        })
        
        st.write("### Detailed Breakdown of Costs:")
        st.write(f"- Concrete Volume: **{boq['volume_m3']} m³** at ₹ {boq['concrete_cost_per_m3']:,.2f} per m³")
        st.write(f"- Steel Weight: **{boq['steel_kg']} kg** at ₹ {boq['steel_cost_per_kg']:,.2f} per kg")
        area_m2 = (L_x / 1000) * (L_y / 1000)
        cost_per_m2 = boq['total_cost'] / area_m2
        st.write(f"- Total Cost per Square Meter: **₹ {cost_per_m2:,.2f} per m²**")

        pdf_bytes = create_pdf_report(verifier, boq, fig)
        st.download_button(label="📄 Download Official PDF Report", data=pdf_bytes, file_name="IS456_Report_Slab.pdf", mime="application/pdf", type="primary")


elif element_choice == "Isolated Footings":
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Footing Geometry")
        L = st.number_input("Footing Length (L) [mm]", value=2000.0)
        B = st.number_input("Footing Width (B) [mm]", value=2000.0)
        D = st.number_input("Overall Depth (D) [mm]", value=450.0)
        d = st.number_input("Effective Depth (d) [mm]", value=400.0)
        
        st.subheader("Column & Loading")
        col_L = st.number_input("Column Length [mm]", value=300.0)
        col_B = st.number_input("Column Width [mm]", value=300.0)
        P_u = st.number_input("Factored Axial Load (P_u) [kN]", value=1200.0)
        A_st = st.number_input("Base Steel Area [mm²]", value=1500.0)
        
    with col2:
        st.subheader("Structural Analysis")
        
        verifier = RCFootingVerifier("F1", L, B, D, d, col_L, col_B, f_ck, f_y, A_st, P_u)
        is_safe = verifier.evaluate_compliance()
        
        fig = render_cross_section(verifier, element_type="Footing")
        st.write("### Footing Plan View")
        st.pyplot(fig, transparent=True)
        
        status_color = "status-safe" if is_safe else "status-fail"
        status_text = "SAFE" if is_safe else "ACTION REQUIRED"
        
        st.markdown(f"""
        <div class="metric-card">
            <div>Factored Upward Pressure: <b>{getattr(verifier, 'p_u', 0):.3f} N/mm²</b></div>
            <div>Overall Status: <span class="{status_color}">{status_text}</span></div>
        </div>
        """, unsafe_allow_html=True)
        
        st.subheader("Automated Bill of Quantities (BOQ)")
        boq = calculate_boq("Footing", B, D, L, A_st, f_y, f_ck)
        
        if boq['total_cost'] > 100000:
            st.error("⚠️ High Material Cost Alert! This footing design may be uneconomical.")
        elif boq['total_cost'] > 50000:
            st.warning("💡 Consider optimizing the footing design to reduce material costs.")
        else:
            st.success("✅ Material costs are within an acceptable baseline range.")
            
        if is_safe:
            st.write("This footing design is cost-effective and structurally compliant with IS 456.")
        else:
            st.write("While material volumes are low, this design **FAILS structural compliance**. Redesign required.")
            st.warning("⚠️ **Status: Redesign Required** — Costs below reflect the current (non-compliant) design.")
            
        st.table({
            "Parameter": ["Concrete Volume (m³)", "Steel Weight (kg)", "Total Material Cost (₹)"],
            "Value": [round(boq['volume_m3'], 2), round(boq['steel_kg'], 2), round(boq['total_cost'], 2)]
        })
        
        st.write("### Detailed Breakdown of Costs:")
        st.write(f"- Concrete Volume: **{boq['volume_m3']} m³** at ₹ {boq['concrete_cost_per_m3']:,.2f} per m³")
        st.write(f"- Steel Weight: **{boq['steel_kg']} kg** at ₹ {boq['steel_cost_per_kg']:,.2f} per kg")
        st.write(f"- Total Material Cost: **₹ {boq['total_cost']:,.2f}**")
        st.write(f"- **Total Cost per Unit Length: ₹ {boq['total_cost']/L:,.2f} per mm**")
        
        pdf_bytes = create_pdf_report(verifier, boq, fig)
        st.download_button(label="📄 Download Official PDF Report", data=pdf_bytes, file_name="IS456_Report_Footing.pdf", mime="application/pdf", type="primary")

elif element_choice == "Batch CSV Processor":
    st.header("Enterprise Batch Verification", anchor=False)
    st.markdown("Upload a CSV file exported from your structural analysis software to verify hundreds of elements instantly against IS 456.")
    
    # 1. Element Type Selector
    batch_type = st.selectbox("Select Element Type for Batch Processing", ["RC Beams", "RC Columns", "RC Slabs", "Isolated Footings"])
    
    # 2. Dynamic Schema & Templates based on selection
    if batch_type == "RC Beams":
        req_cols = "`Beam_ID`, `b`, `d`, `D`, `L`, `f_ck`, `f_y`, `A_st`, `M_u`, `V_u`, `T_u`"
        sample_csv = "Beam_ID,b,d,D,L,f_ck,f_y,A_st,M_u,V_u,T_u\nB-101,250,400,450,5000,30,415,1000,120.0,80.0,15.0\nB-102,300,500,550,6000,25,500,1200,190.0,110.0,20.0"
    elif batch_type == "RC Columns":
        req_cols = "`Column_ID`, `b`, `D`, `L_eff`, `f_ck`, `f_y`, `A_sc`, `P_u`, `M_u_applied`"
        sample_csv = "Column_ID,b,D,L_eff,f_ck,f_y,A_sc,P_u,M_u_applied\nC-101,300,450,3000,30,415,1200,1500.0,30.0\nC-102,400,400,3200,35,500,2000,2200.0,45.0"
    elif batch_type == "RC Slabs":
        req_cols = "`Slab_ID`, `L_x`, `L_y`, `D`, `d`, `f_ck`, `f_y`, `A_st_main`, `w_u`"
        sample_csv = "Slab_ID,L_x,L_y,D,d,f_ck,f_y,A_st_main,w_u\nS-101,3000,4000,150,125,30,415,300,12.0\nS-102,4000,4500,175,150,25,415,450,15.0"
    elif batch_type == "Isolated Footings":
        req_cols = "`Footing_ID`, `L`, `B`, `D`, `d`, `col_L`, `col_B`, `f_ck`, `f_y`, `A_st`, `P_u`"
        sample_csv = "Footing_ID,L,B,D,d,col_L,col_B,f_ck,f_y,A_st,P_u\nF-101,2000,2000,450,400,300,300,30,415,1500,1200.0\nF-102,2500,2500,500,450,400,400,35,500,2200,1800.0"

    st.info(f"**Required CSV Columns:** {req_cols}")
    st.download_button(f"📥 Download {batch_type} Sample CSV", data=sample_csv, file_name=f"IS456_Batch_{batch_type.replace(' ', '_')}.csv", mime="text/csv")
    
    uploaded_file = st.file_uploader(f"Upload {batch_type} Data (CSV)", type="csv")
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.write("### Data Preview")
            st.dataframe(df.head(), width="stretch")
            
            if st.button(f"🚀 Run Bulk IS 456 Verification ({batch_type})", type="primary"):
                results = []
                progress_bar = st.progress(0)
                total_rows = len(df)
                
                for index, row in df.iterrows():
                    # --- BEAM PROCESSING ---
                    if batch_type == "RC Beams":
                        b_val = float(row['b'])
                        D_val = float(row['D'])
                        M_u, V_u, T_u = float(row['M_u']), float(row['V_u']), float(row['T_u'])
                        
                        M_eq = M_u + (T_u * (1 + D_val / b_val) / 1.7)
                        V_eq = V_u + (1.6 * (T_u / b_val) * 1000) if b_val > 0 else V_u

                        verifier = RCBeamVerifier(
                            element_id=str(row.get('Beam_ID', f"Beam_{index+1}")),
                            b=b_val, d=float(row['d']), D=D_val, L=float(row['L']),
                            f_ck=float(row['f_ck']), f_y=float(row['f_y']), A_st=float(row['A_st']), 
                            M_eq=M_eq, V_eq=V_eq
                        )
                        is_safe = verifier.evaluate_compliance()
                        results.append({
                            "Element_ID": verifier.element_id,
                            "Flexure_Status": verifier.checks.get("Flexure Capacity", "ERROR"),
                            "Shear_Status": verifier.checks.get("Shear & Torsion (tau_v)", "ERROR"),
                            "Deflection_Status": verifier.checks.get("Deflection (L/d)", "ERROR"),
                            "Overall_IS456_Compliance": "PASS" if is_safe else "FAIL"
                        })

                    # --- COLUMN PROCESSING ---
                    elif batch_type == "RC Columns":
                        verifier = RCColumnVerifier(
                            element_id=str(row.get('Column_ID', f"Col_{index+1}")),
                            b=float(row['b']), D=float(row['D']), L_eff=float(row['L_eff']),
                            f_ck=float(row['f_ck']), f_y=float(row['f_y']), A_sc=float(row['A_sc']),
                            P_u=float(row['P_u']), M_u_applied=float(row['M_u_applied'])
                        )
                        is_safe = verifier.evaluate_compliance()
                        results.append({
                            "Element_ID": verifier.element_id,
                            "Slenderness": verifier.checks.get("Slenderness Limit", "ERROR"),
                            "P-M_Interaction": verifier.checks.get("P-M Interaction (Uniaxial)", "ERROR"),
                            "Overall_IS456_Compliance": "PASS" if is_safe else "FAIL"
                        })
                        
                    # --- SLAB PROCESSING ---
                    elif batch_type == "RC Slabs":
                        verifier = RCSlabVerifier(
                            element_id=str(row.get('Slab_ID', f"Slab_{index+1}")),
                            L_x=float(row['L_x']), L_y=float(row['L_y']), D=float(row['D']), d=float(row['d']),
                            f_ck=float(row['f_ck']), f_y=float(row['f_y']), A_st_main=float(row['A_st_main']),
                            w_u=float(row['w_u'])
                        )
                        is_safe = verifier.evaluate_compliance()
                        results.append({
                            "Element_ID": verifier.element_id,
                            "Aspect_Ratio": verifier.classification,
                            "Deflection_Limit": verifier.checks.get("Deflection (L_x/d)", "ERROR"),
                            "Flexure_Strip": verifier.checks.get("Strip Flexure Capacity", "ERROR"),
                            "Overall_IS456_Compliance": "PASS" if is_safe else "FAIL"
                        })

                    # --- FOOTING PROCESSING ---
                    elif batch_type == "Isolated Footings":
                        verifier = RCFootingVerifier(
                            element_id=str(row.get('Footing_ID', f"Foot_{index+1}")),
                            L=float(row['L']), B=float(row['B']), D=float(row['D']), d=float(row['d']),
                            col_L=float(row['col_L']), col_B=float(row['col_B']),
                            f_ck=float(row['f_ck']), f_y=float(row['f_y']), A_st=float(row['A_st']),
                            P_u=float(row['P_u'])
                        )
                        is_safe = verifier.evaluate_compliance()
                        results.append({
                            "Element_ID": verifier.element_id,
                            "Base_Flexure": verifier.checks.get("Base Flexure Capacity", "ERROR"),
                            "Punching_Shear": verifier.checks.get("Two-Way (Punching) Shear", "ERROR"),
                            "One_Way_Shear": verifier.checks.get("One-Way Shear", "ERROR"),
                            "Overall_IS456_Compliance": "PASS" if is_safe else "FAIL"
                        })
                    
                    progress_bar.progress((index + 1) / total_rows)
                
                # --- RENDER RESULTS DASHBOARD ---
                results_df = pd.DataFrame(results)
                
                total_passed = len(results_df[results_df['Overall_IS456_Compliance'] == "PASS"])
                total_failed = len(results_df) - total_passed
                
                col1, col2 = st.columns(2)
                col1.metric("Elements Passed", total_passed, delta_color="normal")
                col2.metric("Elements Failed", total_failed, delta="-", delta_color="inverse")
                
                st.success(f"✅ Successfully processed {len(df)} {batch_type.lower()} through the IS 456 engine!")
                
                def color_compliance(val):
                    color = '#15803d' if val == 'PASS' else '#b91c1c'
                    return f'background-color: {color}'
                
                st.dataframe(results_df.style.map(color_compliance, subset=['Overall_IS456_Compliance']), width="stretch")
                
                csv_export = results_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label=f"📥 Download Verified Dataset (CSV)",
                    data=csv_export,
                    file_name=f'Verified_{batch_type.replace(" ", "_")}_Results.csv',
                    mime='text/csv',
                    type="primary"
                )
                
        except Exception as e:
            st.error(f"Error processing file. Please ensure columns exactly match the required format for {batch_type}. Details: {str(e)}")
        
elif element_choice == "BIM (IFC) Integration":
    st.header("BIM / IFC Integration", anchor=False)
    st.markdown("Upload a Structural Industry Foundation Classes (`.ifc`) file exported from Revit or Tekla. The engine will auto-extract structural inventories and material grades directly from the 3D model.")
    
    uploaded_ifc = st.file_uploader("Upload Structural BIM Model (.ifc)", type="ifc")
    
    if uploaded_ifc is not None:
        # --- 1. ISOLATED PARSING ENGINE ---
        parse_success = False
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp_file:
                tmp_file.write(uploaded_ifc.getvalue())
                tmp_path = tmp_file.name
                
            st.success("✅ IFC Model loaded and parsed successfully!")
            extractor = BIMExtractor(tmp_path)
            df_beams = extractor.get_beams_dataframe()
            df_columns = extractor.get_columns_dataframe()
            df_slabs = extractor.get_slabs_dataframe()
            df_footings = extractor.get_footings_dataframe()
            os.remove(tmp_path)
            parse_success = True
            
        except Exception as e:
            st.error(f"Error parsing IFC file. The model geometry may be corrupted or unsupported. Details: {str(e)}")

        # --- 2. UI & VERIFICATION ENGINE (Only runs if parsing succeeded) ---
        if parse_success:
            if df_beams.empty and df_columns.empty and df_slabs.empty and df_footings.empty:
                st.warning("⚠️ **No recognizable structural elements were found.**")
                st.write("Please upload a **Structural discipline export (`STR`)** containing defined analytical entities.")
            else:
                st.write("### Extracted BIM Inventory")
                st.info("Geometry and concrete grades (f_ck) have been auto-extracted where possible. Values showing '0.0' indicate missing metadata. You MUST manually input spans and loads before verifying.")
                
                t_beam, t_col, t_slab, t_foot = st.tabs([
                    f"Beams ({len(df_beams)})", f"Columns ({len(df_columns)})",
                    f"Slabs ({len(df_slabs)})", f"Footings ({len(df_footings)})"
                ])
                
                # --- BEAMS TAB ---
                with t_beam:
                    if not df_beams.empty:
                        edited_beams = st.data_editor(df_beams, width="stretch", num_rows="dynamic", column_config={"Beam_ID": st.column_config.TextColumn(disabled=True), "b": st.column_config.NumberColumn(disabled=True), "D": st.column_config.NumberColumn(disabled=True), "f_ck": st.column_config.NumberColumn(disabled=True)})
                        if st.button("🚀 Verify BIM Beams", type="primary"):
                            if (edited_beams['b'] <= 0).any() or (edited_beams['D'] <= 0).any():
                                st.error("⚠️ Validation Error: All beams must have Width (b) and Depth (D) greater than 0.")
                            else:
                                results = []
                                for index, row in edited_beams.iterrows():
                                    b_val, D_val = float(row['b']), float(row['D'])
                                    M_u, V_u, T_u = float(row['M_u']), float(row['V_u']), float(row['T_u'])
                                    M_eq = M_u + (T_u * (1 + D_val / b_val) / 1.7) if b_val > 0 else M_u
                                    V_eq = V_u + (1.6 * (T_u / b_val) * 1000) if b_val > 0 else V_u
                                    verifier = RCBeamVerifier(str(row['Beam_ID']), b_val, float(row['d']), D_val, float(row['L']), float(row['f_ck']), float(row['f_y']), float(row['A_st']), M_eq, V_eq)
                                    results.append({"Element_ID": verifier.element_id, "Status": "PASS" if verifier.evaluate_compliance() else "FAIL"})
                                st.dataframe(pd.DataFrame(results), width="stretch")

                # --- COLUMNS TAB ---
                with t_col:
                    if not df_columns.empty:
                        edited_cols = st.data_editor(df_columns, width="stretch", num_rows="dynamic", column_config={"Column_ID": st.column_config.TextColumn(disabled=True), "b": st.column_config.NumberColumn(disabled=True), "D": st.column_config.NumberColumn(disabled=True), "f_ck": st.column_config.NumberColumn(disabled=True)})
                        if st.button("🚀 Verify BIM Columns", type="primary"):
                            if (edited_cols['b'] <= 0).any() or (edited_cols['D'] <= 0).any():
                                st.error("⚠️ Validation Error: All columns must have width (b) and depth (D) greater than 0.")
                            else:
                                results = []
                                for index, row in edited_cols.iterrows():
                                    verifier = RCColumnVerifier(str(row['Column_ID']), float(row['b']), float(row['D']), float(row['L_eff']), float(row['f_ck']), float(row['f_y']), float(row['A_sc']), float(row['P_u']), float(row['M_u_applied']))
                                    results.append({"Element_ID": verifier.element_id, "Status": "PASS" if verifier.evaluate_compliance() else "FAIL"})
                                st.dataframe(pd.DataFrame(results), width="stretch")

                # --- SLABS TAB ---
                with t_slab:
                    if not df_slabs.empty:
                        edited_slabs = st.data_editor(df_slabs, width="stretch", num_rows="dynamic", column_config={"Slab_ID": st.column_config.TextColumn(disabled=True), "f_ck": st.column_config.NumberColumn(disabled=True)})
                        if st.button("🚀 Verify BIM Slabs", type="primary"):
                            if (edited_slabs['L_x'] <= 0).any() or (edited_slabs['L_y'] <= 0).any() or (edited_slabs['d'] <= 0).any():
                                st.error("⚠️ Validation Error: You must replace all 0.0 spans (L_x, L_y) and depths (d) with actual values before verifying.")
                            else:
                                results = []
                                for index, row in edited_slabs.iterrows():
                                    verifier = RCSlabVerifier(str(row['Slab_ID']), float(row['L_x']), float(row['L_y']), float(row['D']), float(row['d']), float(row['f_ck']), float(row['f_y']), float(row['A_st_main']), float(row['w_u']))
                                    results.append({"Element_ID": verifier.element_id, "Status": "PASS" if verifier.evaluate_compliance() else "FAIL"})
                                st.dataframe(pd.DataFrame(results), width="stretch")

                # --- FOOTINGS TAB ---
                with t_foot:
                    if not df_footings.empty:
                        edited_footings = st.data_editor(df_footings, width="stretch", num_rows="dynamic", column_config={"Footing_ID": st.column_config.TextColumn(disabled=True), "f_ck": st.column_config.NumberColumn(disabled=True)})
                        if st.button("🚀 Verify BIM Footings", type="primary"):
                            if (edited_footings['L'] <= 0).any() or (edited_footings['B'] <= 0).any() or (edited_footings['d'] <= 0).any():
                                st.error("⚠️ Validation Error: You must replace all 0.0 dimensions (L, B, d) with actual values before verifying.")
                            else:
                                results = []
                                for index, row in edited_footings.iterrows():
                                    verifier = RCFootingVerifier(str(row['Footing_ID']), float(row['L']), float(row['B']), float(row['D']), float(row['d']), float(row['col_L']), float(row['col_B']), float(row['f_ck']), float(row['f_y']), float(row['A_st']), float(row['P_u']))
                                    results.append({"Element_ID": verifier.element_id, "Status": "PASS" if verifier.evaluate_compliance() else "FAIL"})
                                st.dataframe(pd.DataFrame(results), width="stretch")