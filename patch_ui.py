import re

with open("streamlit_app.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update Global CSS
old_css = '''st.markdown("""
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
""", unsafe_allow_html=True)'''

new_css = '''st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    .stApp { 
        background-color: #0b0f19; 
        font-family: 'Inter', sans-serif;
    }
    .metric-card { 
        background: rgba(30, 41, 59, 0.6); 
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        padding: 20px; 
        border-radius: 12px; 
        border: 1px solid rgba(255, 255, 255, 0.08); 
        margin-bottom: 20px;
        color: #f8fafc;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
        border-color: rgba(255, 255, 255, 0.2);
    }
    .status-safe { 
        color: #10b981; 
        font-weight: 700; 
        text-shadow: 0 0 12px rgba(16,185,129,0.4); 
    }
    .status-fail { 
        color: #ef4444; 
        font-weight: 700; 
        text-shadow: 0 0 12px rgba(239,68,68,0.4); 
    }
    
    /* Enhance Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(255, 255, 255, 0.05);
    }
    </style>
""", unsafe_allow_html=True)'''

content = content.replace(old_css, new_css)

# 2. Update ML Predictor Sidebar
old_ml = '''    # --- Real ML Concrete Predictor ---
    st.markdown("#### 🤖 ML Concrete Predictor")
    ml_bundle = load_ml_model()
    use_ml = st.toggle("Predict f_ck via ML Model", disabled=(ml_bundle is None))
    if ml_bundle is None:
        st.caption("⚠️ Model not found. Run `python ml/train_model.py` first.")

    if use_ml and ml_bundle is not None:
        import numpy as np
        st.caption(
            f"GradientBoostingRegressor · R²={ml_bundle['r2']:.3f} · "
            f"MAE={ml_bundle['mae']:.2f} MPa"
        )
        cement_ml  = st.number_input("Cement (kg/m³)", 250.0, 500.0, 350.0, 10.0)
        water_ml   = st.number_input("Water (kg/m³)",  140.0, 210.0, 175.0, 5.0)
        fa_ml      = st.number_input("Fine Agg. (kg/m³)", 500.0, 900.0, 720.0, 10.0)
        ca_ml      = st.number_input("Coarse Agg. (kg/m³)", 800.0, 1200.0, 1050.0, 10.0)
        rfa_pct_ml = st.slider("RFA Replacement (%)", 0, 100, 25)
        cure_ml    = st.selectbox("Curing Days", [3, 7, 14, 28, 56], index=3)

        X_pred = np.array([[cement_ml, water_ml, fa_ml, ca_ml, rfa_pct_ml, cure_ml]])
        predicted_fck = float(ml_bundle["pipeline"].predict(X_pred)[0])
        sigma = ml_bundle["train_std"] * 0.15   # approximate 1σ interval

        st.success(
            f"**Predicted f_ck: {predicted_fck:.1f} MPa** "
            f"(±{sigma:.1f} MPa, 68% CI)"
        )
        f_ck = predicted_fck
    else:
        f_ck = st.number_input("f_ck [MPa] (Concrete Grade)", value=30.0, step=5.0)

    f_y = st.selectbox("Steel Grade (f_y) [MPa]", [415, 500, 550])'''

new_ml = '''    # --- Real ML Concrete Predictor ---
    ml_bundle = load_ml_model()
    
    with st.expander("🤖 ML Concrete Predictor", expanded=False):
        st.caption("Use Machine Learning to predict concrete strength based on mix design.")
        use_ml = st.toggle("Enable ML Prediction", disabled=(ml_bundle is None))
        if ml_bundle is None:
            st.caption("⚠️ Model not found. Run `python ml/train_model.py` first.")

        if use_ml and ml_bundle is not None:
            import numpy as np
            st.caption(
                f"GradientBoostingRegressor · R²={ml_bundle['r2']:.3f} · "
                f"MAE={ml_bundle['mae']:.2f} MPa"
            )
            cement_ml  = st.number_input("Cement (kg/m³)", 250.0, 500.0, 350.0, 10.0, help="Amount of cement in the mix")
            water_ml   = st.number_input("Water (kg/m³)",  140.0, 210.0, 175.0, 5.0, help="Amount of water in the mix")
            fa_ml      = st.number_input("Fine Agg. (kg/m³)", 500.0, 900.0, 720.0, 10.0, help="Fine aggregate (sand) content")
            ca_ml      = st.number_input("Coarse Agg. (kg/m³)", 800.0, 1200.0, 1050.0, 10.0, help="Coarse aggregate (gravel) content")
            rfa_pct_ml = st.slider("RFA Replacement (%)", 0, 100, 25, help="Recycled Fine Aggregate percentage")
            cure_ml    = st.selectbox("Curing Days", [3, 7, 14, 28, 56], index=3, help="Duration of concrete curing")

            X_pred = np.array([[cement_ml, water_ml, fa_ml, ca_ml, rfa_pct_ml, cure_ml]])
            predicted_fck = float(ml_bundle["pipeline"].predict(X_pred)[0])
            sigma = ml_bundle["train_std"] * 0.15   # approximate 1σ interval

            st.success(
                f"**Predicted f_ck: {predicted_fck:.1f} MPa** "
                f"(±{sigma:.1f} MPa, 68% CI)"
            )
            f_ck = predicted_fck
        else:
            f_ck = st.number_input("f_ck [MPa] (Concrete Grade)", value=30.0, step=5.0, help="Characteristic compressive strength of concrete at 28 days")

    st.markdown("### Material Grades")
    if not (use_ml and ml_bundle is not None):
        f_ck = st.number_input("f_ck [MPa] (Concrete Grade)", value=30.0, step=5.0, help="Characteristic compressive strength of concrete at 28 days", key="f_ck_main")
    f_y = st.selectbox("Steel Grade (f_y) [MPa]", [415, 500, 550], help="Characteristic yield strength of reinforcing steel")'''

content = content.replace(old_ml, new_ml)

# 3. Refactor Beams (Columns -> Tabs)
old_beams = '''if element_choice == "RC Beams":
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
        status_color = "status-safe" if is_safe else "status-fail"
        status_text = "SAFE" if is_safe else "FAIL"
        
        st.markdown(f"""
        <div class="metric-card">
            <div>Equivalent Moment (Flexure + Torsion): <b>{M_eq:.1f} kNm</b></div>
            <div>Overall Status: <span class="{status_color}">{status_text} (Capacity {cap_M:.1f} {'≥' if cap_M >= M_eq else '<'} Applied {M_eq:.1f})</span></div>
        </div>
        """, unsafe_allow_html=True)

        # 5b. IS 456 Checks Breakdown
        st.subheader("IS 456:2000 Checks Summary")
        render_checks_table(verifier)
        render_calculation_expander(verifier)
        render_suggestions_expander(verifier)

        # 6. BOQ & Cost Optimization
        st.subheader("Automated Bill of Quantities (BOQ)")
        boq = calculate_boq("Beam", b, D, L, A_st, f_y, f_ck)

        if boq['total_cost'] > 40000:
            st.error("⚠️ High Material Cost Alert! This beam design may be uneconomical.")
        elif boq['total_cost'] > 20000:
            st.warning("💡 Optimize b, D, or A_st to reduce material costs.")
        else:
            st.success("✅ Material costs within acceptable range.")

        if not is_safe:
            st.warning("⚠️ **Status: Redesign Required** — costs reflect a non-compliant design.")

        st.dataframe(pd.DataFrame({
            "Parameter": ["Concrete Volume (m³)", "Steel Weight (kg)", "Total Material Cost (₹)", "Cost per Metre Span (₹/m)"],
            "Value": [
                f"{boq['volume_m3']:.3f}",
                f"{boq['steel_kg']:.2f}",
                f"₹ {boq['total_cost']:,.0f}",
                f"₹ {boq['total_cost'] / (L / 1000):,.0f}"
            ]
        }), use_container_width=True, hide_index=True)

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
            try:
                with open(dxf_file, "rb") as f:
                    dxf_bytes = f.read()
                st.download_button(
                    label="📐 Download CAD (.dxf)", 
                    data=dxf_bytes, 
                    file_name=f"Beam_{verifier.element_id}.dxf", 
                    mime="application/dxf",
                    type="secondary"
                )
            finally:
                if os.path.exists(dxf_file):
                    os.remove(dxf_file)'''

new_beams = '''if element_choice == "RC Beams":
    tab1, tab2, tab3 = st.tabs(["⚙️ Input Parameters", "📊 Structural Analysis", "💰 BOQ & Reports"])
    
    with tab1:
        st.subheader("Design & Loading Parameters")
        
        col_geom, col_load = st.columns(2)
        with col_geom:
            st.markdown("##### Geometry & Reinforcement")
            b = st.number_input("Width [mm]", value=250.0, help="Width of the beam cross-section")
            D = st.number_input("Overall Depth (D) [mm]", value=450.0, help="Total depth from top to bottom") 
            d = st.number_input("Effective Depth (d) [mm]", value=400.0, help="Depth from extreme compression fiber to centroid of tension steel")
            L = st.number_input("Total Span Length [mm]", value=5000.0, help="Clear span of the beam")
            A_st = st.number_input("Tension Steel Area (A_st) [mm²]", value=1000.0, help="Total area of main tension reinforcement")
            
        with col_load:
            st.markdown("##### Factored Loads")
            M_u = st.number_input("Moment [kNm]", value=120.0, help="Factored bending moment")
            V_u = st.number_input("Shear [kN]", value=80.0, help="Factored shear force")
            T_u = st.number_input("Torsion [kNm]", value=15.0, help="Factored torsional moment")
            
            # Calculate Equivalent Loads dynamically (IS 456 Clause 41.4.2)
            M_eq = M_u + (T_u * (1 + D / b) / 1.7) if b > 0 else M_u
            V_eq = V_u + (1.6 * (T_u / b) * 1000) if b > 0 else V_u
            
            st.info(f"**Equivalent Bending Moment:** {M_eq:.1f} kNm  \\n**Equivalent Shear Force:** {V_eq:.1f} kN")

    # Instantiate the Verifier (needed for subsequent tabs)
    verifier = RCBeamVerifier(
        element_id="B1", b=b, d=d, D=D, L=L, 
        f_ck=f_ck, f_y=f_y, A_st=A_st, M_eq=M_eq, V_eq=V_eq
    )
    
    # Evaluate Compliance
    with st.spinner("Analyzing structural capacity..."):
        is_safe = verifier.evaluate_compliance()
        cap_M = getattr(verifier, 'M_ur', 0) / 1e6
        fig = render_cross_section(verifier, element_type="Beam")

    with tab2:
        st.subheader("Structural Analysis")
        
        # Render Status Card
        status_color = "status-safe" if is_safe else "status-fail"
        status_text = "SAFE" if is_safe else "FAIL"
        
        st.markdown(f"""
        <div class="metric-card">
            <h4 style="margin-top:0;">Analysis Results</h4>
            <div>Equivalent Moment (Flexure + Torsion): <b>{M_eq:.1f} kNm</b></div>
            <div>Overall Status: <span class="{status_color}">{status_text} (Capacity {cap_M:.1f} {'≥' if cap_M >= M_eq else '<'} Applied {M_eq:.1f})</span></div>
        </div>
        """, unsafe_allow_html=True)
        
        col_fig, col_checks = st.columns([1, 1.5])
        with col_fig:
            st.write("### Cross-Section")
            st.pyplot(fig, transparent=True)
            
        with col_checks:
            st.write("### IS 456:2000 Checks")
            render_checks_table(verifier)
            render_calculation_expander(verifier)
            render_suggestions_expander(verifier)

    with tab3:
        st.subheader("Bill of Quantities (BOQ) & Reports")
        boq = calculate_boq("Beam", b, D, L, A_st, f_y, f_ck)

        if boq['total_cost'] > 40000:
            st.error("⚠️ High Material Cost Alert! This beam design may be uneconomical.")
        elif boq['total_cost'] > 20000:
            st.warning("💡 Optimize b, D, or A_st to reduce material costs.")
        else:
            st.success("✅ Material costs within acceptable range.")

        if not is_safe:
            st.warning("⚠️ **Status: Redesign Required** — costs reflect a non-compliant design.")

        st.dataframe(pd.DataFrame({
            "Parameter": ["Concrete Volume (m³)", "Steel Weight (kg)", "Total Material Cost (₹)", "Cost per Metre Span (₹/m)"],
            "Value": [
                f"{boq['volume_m3']:.3f}",
                f"{boq['steel_kg']:.2f}",
                f"₹ {boq['total_cost']:,.0f}",
                f"₹ {boq['total_cost'] / (L / 1000):,.0f}"
            ]
        }), use_container_width=True, hide_index=True)

        # PDF Report & CAD Export
        from engine.dxf_exporter import CADExporter
        
        st.write("---")
        st.markdown("### Export Outputs")
        btn_col1, btn_col2 = st.columns(2)
        
        with btn_col1:
            pdf_bytes = create_pdf_report(verifier, boq, fig)
            st.download_button(
                label="📄 Download Official PDF Report", 
                data=pdf_bytes, 
                file_name="IS456_Report_Beam.pdf", 
                mime="application/pdf", 
                type="primary",
                use_container_width=True
            )
            
        with btn_col2:
            dxf_file = CADExporter.generate_cross_section_dxf(verifier.element_id, b, D, "Beam")
            try:
                with open(dxf_file, "rb") as f:
                    dxf_bytes = f.read()
                st.download_button(
                    label="📐 Download CAD (.dxf)", 
                    data=dxf_bytes, 
                    file_name=f"Beam_{verifier.element_id}.dxf", 
                    mime="application/dxf",
                    type="secondary",
                    use_container_width=True
                )
            finally:
                if os.path.exists(dxf_file):
                    os.remove(dxf_file)'''

content = content.replace(old_beams, new_beams)

with open("streamlit_app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Streamlit UI patched successfully!")
