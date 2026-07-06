import re

with open("streamlit_app.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Refactor Columns (Columns -> Tabs)
old_cols = '''elif element_choice == "RC Columns":
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

        # 3b. IS 456 Checks
        st.subheader("IS 456:2000 Checks Summary")
        render_checks_table(verifier)
        render_calculation_expander(verifier)
        render_suggestions_expander(verifier)

        # 4. BOQ
        st.subheader("Automated Bill of Quantities (BOQ)")
        boq = calculate_boq("Column", b, D, L_eff, A_sc, f_y, f_ck)

        if boq['total_cost'] > 50000:
            st.error("⚠️ High Material Cost Alert! Consider higher grade concrete or alternative layouts.")
        elif boq['total_cost'] > 25000:
            st.warning("💡 Optimize b, D, or A_sc to reduce costs.")
        else:
            st.success("✅ Material costs within acceptable range.")

        if "ACTION REQUIRED" in pm_status:
            st.warning("⚠️ **Verification Pending** — SP-16 charts required for final compliance.")
        elif not is_safe:
            st.warning("⚠️ **Redesign Required** — costs reflect a non-compliant design.")

        cost_per_m = boq['total_cost'] / (L_eff / 1000)
        st.dataframe(pd.DataFrame({
            "Parameter": ["Concrete Volume (m³)", "Steel Weight (kg)", "Total Material Cost (₹)", "Cost per Metre Height (₹/m)"],
            "Value": [
                f"{boq['volume_m3']:.3f}",
                f"{boq['steel_kg']:.2f}",
                f"₹ {boq['total_cost']:,.0f}",
                f"₹ {cost_per_m:,.0f}"
            ]
        }), use_container_width=True, hide_index=True)

        # 5. PDF Report + CAD export
        from engine.dxf_exporter import CADExporter
        st.write("---")
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            pdf_bytes = create_pdf_report(verifier, boq, fig)
            st.download_button(label="📄 Download Official PDF Report", data=pdf_bytes, file_name="IS456_Report_Column.pdf", mime="application/pdf", type="primary")
        with btn_c2:
            dxf_file = CADExporter.generate_cross_section_dxf(verifier.element_id, b, D, "Column")
            try:
                with open(dxf_file, "rb") as _f:
                    dxf_bytes = _f.read()
                st.download_button(label="📐 Download CAD (.dxf)", data=dxf_bytes, file_name=f"Column_{verifier.element_id}.dxf", mime="application/dxf", type="secondary")
            finally:
                if os.path.exists(dxf_file):
                    os.remove(dxf_file)'''

new_cols = '''elif element_choice == "RC Columns":
    tab1, tab2, tab3 = st.tabs(["⚙️ Input Parameters", "📊 Structural Analysis", "💰 BOQ & Reports"])
    
    with tab1:
        col_geom, col_load = st.columns(2)
        with col_geom:
            st.subheader("Column Geometry")
            b = st.number_input("Width [mm]", value=300.0, help="Width of the column cross-section")
            D = st.number_input("Depth [mm]", value=450.0, help="Depth of the column cross-section")
            L_eff = st.number_input("Effective Length [mm]", value=3000.0, help="Effective length for buckling consideration")
            A_sc = st.number_input("A_sc (Steel Area) [mm²]", value=1200.0, help="Total area of longitudinal steel")
        with col_load:
            st.subheader("Applied Factored Loads")
            P_u = st.number_input("Applied Axial Load [kN]", value=1500.0, help="Factored axial compressive load")
            M_u = st.number_input("Applied Moment [kNm]", value=30.0, help="Factored bending moment on the column")
            
    # Evaluate
    verifier = RCColumnVerifier("C1", b, D, L_eff, f_ck, f_y, A_sc, P_u, M_u)
    with st.spinner("Analyzing column capacity and slenderness..."):
        is_safe = verifier.evaluate_compliance()
        pm_status = verifier.checks.get("P-M Interaction (Uniaxial)", "UNKNOWN")
        fig = render_cross_section(verifier, element_type="Column")

    with tab2:
        st.subheader("Structural Analysis")
        status_color = "status-safe" if "PASS" in pm_status else "status-fail"
        
        st.markdown(f"""
        <div class="metric-card">
            <h4 style="margin-top:0;">Analysis Results</h4>
            <div>Classification: <b>{getattr(verifier, 'classification', 'Unknown')}</b></div>
            <br>
            <div>Overall Status: <span class="{status_color}">{pm_status}</span></div>
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
        boq = calculate_boq("Column", b, D, L_eff, A_sc, f_y, f_ck)

        if boq['total_cost'] > 50000:
            st.error("⚠️ High Material Cost Alert! Consider higher grade concrete or alternative layouts.")
        elif boq['total_cost'] > 25000:
            st.warning("💡 Optimize b, D, or A_sc to reduce costs.")
        else:
            st.success("✅ Material costs within acceptable range.")

        if "ACTION REQUIRED" in pm_status:
            st.warning("⚠️ **Verification Pending** — SP-16 charts required for final compliance.")
        elif not is_safe:
            st.warning("⚠️ **Redesign Required** — costs reflect a non-compliant design.")

        cost_per_m = boq['total_cost'] / (L_eff / 1000)
        st.dataframe(pd.DataFrame({
            "Parameter": ["Concrete Volume (m³)", "Steel Weight (kg)", "Total Material Cost (₹)", "Cost per Metre Height (₹/m)"],
            "Value": [
                f"{boq['volume_m3']:.3f}",
                f"{boq['steel_kg']:.2f}",
                f"₹ {boq['total_cost']:,.0f}",
                f"₹ {cost_per_m:,.0f}"
            ]
        }), use_container_width=True, hide_index=True)

        from engine.dxf_exporter import CADExporter
        st.write("---")
        st.markdown("### Export Outputs")
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            pdf_bytes = create_pdf_report(verifier, boq, fig)
            st.download_button(label="📄 Download Official PDF Report", data=pdf_bytes, file_name="IS456_Report_Column.pdf", mime="application/pdf", type="primary", use_container_width=True)
        with btn_c2:
            dxf_file = CADExporter.generate_cross_section_dxf(verifier.element_id, b, D, "Column")
            try:
                with open(dxf_file, "rb") as _f:
                    dxf_bytes = _f.read()
                st.download_button(label="📐 Download CAD (.dxf)", data=dxf_bytes, file_name=f"Column_{verifier.element_id}.dxf", mime="application/dxf", type="secondary", use_container_width=True)
            finally:
                if os.path.exists(dxf_file):
                    os.remove(dxf_file)'''
                    
content = content.replace(old_cols, new_cols)


# 2. Refactor Slabs
old_slabs = '''elif element_choice == "RC Slabs":
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

        st.subheader("IS 456:2000 Checks Summary")
        render_checks_table(verifier)
        render_calculation_expander(verifier)
        render_suggestions_expander(verifier)

        st.subheader("Automated Bill of Quantities (BOQ)")
        boq = calculate_boq("Slab", L_x, D, L_y, A_st * (L_y/1000), f_y, f_ck)

        if boq['total_cost'] > 120000:
            st.error("⚠️ High Material Cost Alert! Increase D or use lower steel grade.")
        elif boq['total_cost'] > 60000:
            st.warning("💡 Optimize slab thickness (D) to reduce costs.")
        else:
            st.success("✅ Material costs within acceptable range.")

        if not is_safe:
            st.warning("⚠️ **Redesign Required** — costs reflect a non-compliant design.")

        area_m2 = (L_x / 1000) * (L_y / 1000)
        cost_per_m2 = boq['total_cost'] / area_m2 if area_m2 > 0 else 0
        st.dataframe(pd.DataFrame({
            "Parameter": ["Concrete Volume (m³)", "Steel Weight (kg)", "Total Material Cost (₹)", "Cost per m² (₹/m²)"],
            "Value": [
                f"{boq['volume_m3']:.3f}",
                f"{boq['steel_kg']:.2f}",
                f"₹ {boq['total_cost']:,.0f}",
                f"₹ {cost_per_m2:,.0f}"
            ]
        }), use_container_width=True, hide_index=True)

        pdf_bytes = create_pdf_report(verifier, boq, fig)
        st.download_button(label="📄 Download Official PDF Report", data=pdf_bytes, file_name="IS456_Report_Slab.pdf", mime="application/pdf", type="primary")'''

new_slabs = '''elif element_choice == "RC Slabs":
    tab1, tab2, tab3 = st.tabs(["⚙️ Input Parameters", "📊 Structural Analysis", "💰 BOQ & Reports"])
    
    with tab1:
        col_geom, col_load = st.columns(2)
        with col_geom:
            st.subheader("Slab Geometry (1m Strip)")
            L_x = st.number_input("Short Span (L_x) [mm]", value=3000.0, help="Shorter side span of the slab")
            L_y = st.number_input("Long Span (L_y) [mm]", value=4000.0, help="Longer side span of the slab")
            D = st.number_input("Overall Thickness (D) [mm]", value=150.0, help="Total depth/thickness of the slab")
            d = st.number_input("Effective Depth (d) [mm]", value=125.0, help="Depth from extreme compression fiber to centroid of tension steel")
            A_st = st.number_input("Main Steel Area [mm²/m]", value=300.0, help="Area of main reinforcement per meter width")
        with col_load:
            st.subheader("Slab Loads")
            w_u = st.number_input("Factored Load (w_u) [kN/m²]", value=12.0, help="Total factored load acting on the slab area")
            
    verifier = RCSlabVerifier("S1", L_x, L_y, D, d, f_ck, f_y, A_st, w_u)
    with st.spinner("Analyzing slab behavior..."):
        is_safe = verifier.evaluate_compliance()
        fig = render_cross_section(verifier, element_type="Slab")
        
    with tab2:
        st.subheader("Structural Analysis")
        status_color = "status-safe" if is_safe else "status-fail"
        status_text = "SAFE" if is_safe else "ACTION REQUIRED"
        
        st.markdown(f"""
        <div class="metric-card">
            <h4 style="margin-top:0;">Analysis Results</h4>
            <div>Slab Classification: <b>{getattr(verifier, 'classification', 'Unknown')}</b></div>
            <div>Overall Status: <span class="{status_color}">{status_text}</span></div>
        </div>
        """, unsafe_allow_html=True)

        col_fig, col_checks = st.columns([1, 1.5])
        with col_fig:
            st.write("### Cross-Section Strip")
            st.pyplot(fig, transparent=True)
            
        with col_checks:
            st.write("### IS 456:2000 Checks")
            render_checks_table(verifier)
            render_calculation_expander(verifier)
            render_suggestions_expander(verifier)

    with tab3:
        st.subheader("Bill of Quantities (BOQ) & Reports")
        boq = calculate_boq("Slab", L_x, D, L_y, A_st * (L_y/1000), f_y, f_ck)

        if boq['total_cost'] > 120000:
            st.error("⚠️ High Material Cost Alert! Increase D or use lower steel grade.")
        elif boq['total_cost'] > 60000:
            st.warning("💡 Optimize slab thickness (D) to reduce costs.")
        else:
            st.success("✅ Material costs within acceptable range.")

        if not is_safe:
            st.warning("⚠️ **Redesign Required** — costs reflect a non-compliant design.")

        area_m2 = (L_x / 1000) * (L_y / 1000)
        cost_per_m2 = boq['total_cost'] / area_m2 if area_m2 > 0 else 0
        st.dataframe(pd.DataFrame({
            "Parameter": ["Concrete Volume (m³)", "Steel Weight (kg)", "Total Material Cost (₹)", "Cost per m² (₹/m²)"],
            "Value": [
                f"{boq['volume_m3']:.3f}",
                f"{boq['steel_kg']:.2f}",
                f"₹ {boq['total_cost']:,.0f}",
                f"₹ {cost_per_m2:,.0f}"
            ]
        }), use_container_width=True, hide_index=True)

        st.markdown("### Export Outputs")
        pdf_bytes = create_pdf_report(verifier, boq, fig)
        st.download_button(label="📄 Download Official PDF Report", data=pdf_bytes, file_name="IS456_Report_Slab.pdf", mime="application/pdf", type="primary", use_container_width=True)'''

content = content.replace(old_slabs, new_slabs)


# 3. Refactor Footings
old_footings = '''elif element_choice == "Isolated Footings":
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

        st.subheader("IS 456:2000 Checks Summary")
        render_checks_table(verifier)
        render_calculation_expander(verifier)
        render_suggestions_expander(verifier)

        st.subheader("Automated Bill of Quantities (BOQ)")
        boq = calculate_boq("Footing", B, D, L, A_st, f_y, f_ck)

        if boq['total_cost'] > 100000:
            st.error("⚠️ High Material Cost! Increase concrete grade or reduce footing size.")
        elif boq['total_cost'] > 50000:
            st.warning("💡 Optimize footing dimensions (L, B, D) to reduce costs.")
        else:
            st.success("✅ Material costs within acceptable range.")

        if not is_safe:
            st.warning("⚠️ **Redesign Required** — costs reflect a non-compliant design.")

        st.dataframe(pd.DataFrame({
            "Parameter": ["Concrete Volume (m³)", "Steel Weight (kg)", "Total Material Cost (₹)", "Cost per m² Base (₹/m²)"],
            "Value": [
                f"{boq['volume_m3']:.3f}",
                f"{boq['steel_kg']:.2f}",
                f"₹ {boq['total_cost']:,.0f}",
                f"₹ {boq['total_cost'] / ((L/1000)*(B/1000)):,.0f}"
            ]
        }), use_container_width=True, hide_index=True)

        pdf_bytes = create_pdf_report(verifier, boq, fig)
        st.download_button(label="📄 Download Official PDF Report", data=pdf_bytes, file_name="IS456_Report_Footing.pdf", mime="application/pdf", type="primary")'''

new_footings = '''elif element_choice == "Isolated Footings":
    tab1, tab2, tab3 = st.tabs(["⚙️ Input Parameters", "📊 Structural Analysis", "💰 BOQ & Reports"])
    
    with tab1:
        col_geom, col_load = st.columns(2)
        with col_geom:
            st.subheader("Footing Geometry")
            L = st.number_input("Footing Length (L) [mm]", value=2000.0, help="Length of the footing base")
            B = st.number_input("Footing Width (B) [mm]", value=2000.0, help="Width of the footing base")
            D = st.number_input("Overall Depth (D) [mm]", value=450.0, help="Total depth of the footing pad")
            d = st.number_input("Effective Depth (d) [mm]", value=400.0, help="Depth from top to the centroid of reinforcement")
            A_st = st.number_input("Base Steel Area [mm²]", value=1500.0, help="Area of steel provided in the footing base")
            
        with col_load:
            st.subheader("Column & Loading")
            col_L = st.number_input("Column Length [mm]", value=300.0, help="Length of the supported column")
            col_B = st.number_input("Column Width [mm]", value=300.0, help="Width of the supported column")
            P_u = st.number_input("Factored Axial Load (P_u) [kN]", value=1200.0, help="Total factored load from column")
            
    verifier = RCFootingVerifier("F1", L, B, D, d, col_L, col_B, f_ck, f_y, A_st, P_u)
    with st.spinner("Analyzing foundation soil pressure and shear..."):
        is_safe = verifier.evaluate_compliance()
        fig = render_cross_section(verifier, element_type="Footing")
        
    with tab2:
        st.subheader("Structural Analysis")
        status_color = "status-safe" if is_safe else "status-fail"
        status_text = "SAFE" if is_safe else "ACTION REQUIRED"
        
        st.markdown(f"""
        <div class="metric-card">
            <h4 style="margin-top:0;">Analysis Results</h4>
            <div>Factored Upward Pressure: <b>{getattr(verifier, 'p_u', 0):.3f} N/mm²</b></div>
            <div>Overall Status: <span class="{status_color}">{status_text}</span></div>
        </div>
        """, unsafe_allow_html=True)
        
        col_fig, col_checks = st.columns([1, 1.5])
        with col_fig:
            st.write("### Plan View")
            st.pyplot(fig, transparent=True)
            
        with col_checks:
            st.write("### IS 456:2000 Checks")
            render_checks_table(verifier)
            render_calculation_expander(verifier)
            render_suggestions_expander(verifier)

    with tab3:
        st.subheader("Bill of Quantities (BOQ) & Reports")
        boq = calculate_boq("Footing", B, D, L, A_st, f_y, f_ck)

        if boq['total_cost'] > 100000:
            st.error("⚠️ High Material Cost! Increase concrete grade or reduce footing size.")
        elif boq['total_cost'] > 50000:
            st.warning("💡 Optimize footing dimensions (L, B, D) to reduce costs.")
        else:
            st.success("✅ Material costs within acceptable range.")

        if not is_safe:
            st.warning("⚠️ **Redesign Required** — costs reflect a non-compliant design.")

        st.dataframe(pd.DataFrame({
            "Parameter": ["Concrete Volume (m³)", "Steel Weight (kg)", "Total Material Cost (₹)", "Cost per m² Base (₹/m²)"],
            "Value": [
                f"{boq['volume_m3']:.3f}",
                f"{boq['steel_kg']:.2f}",
                f"₹ {boq['total_cost']:,.0f}",
                f"₹ {boq['total_cost'] / ((L/1000)*(B/1000)):,.0f}"
            ]
        }), use_container_width=True, hide_index=True)

        st.markdown("### Export Outputs")
        pdf_bytes = create_pdf_report(verifier, boq, fig)
        st.download_button(label="📄 Download Official PDF Report", data=pdf_bytes, file_name="IS456_Report_Footing.pdf", mime="application/pdf", type="primary", use_container_width=True)'''

content = content.replace(old_footings, new_footings)

with open("streamlit_app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Streamlit UI Part 2 patched successfully!")
