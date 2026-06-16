import ezdxf

class CADExporter:
    @staticmethod
    def generate_cross_section_dxf(element_id, b, D, element_type="Beam"):
        # Create a new DXF document
        doc = ezdxf.new(dxfversion='R2010')
        msp = doc.modelspace()
        
        # Define Engineering CAD Layers
        doc.layers.add("CONCRETE", color=7)  # White/Black
        doc.layers.add("REBAR", color=1)     # Red
        doc.layers.add("DIMENSIONS", color=2) # Yellow
        doc.layers.add("TEXT", color=3)       # Green
        
        # 1. Draw Concrete Outline
        msp.add_lwpolyline([(0, 0), (b, 0), (b, D), (0, D), (0, 0)], dxfattribs={'layer': 'CONCRETE'})
        
        # 2. Draw Stirrup/Tie (assuming 40mm clear cover)
        cover = 40
        if b > 2*cover and D > 2*cover:
            msp.add_lwpolyline([
                (cover, cover), (b - cover, cover), 
                (b - cover, D - cover), (cover, D - cover), (cover, cover)
            ], dxfattribs={'layer': 'REBAR'})
            
            # 3. Draw Main Rebar Nodes
            bar_radius = 8
            if element_type == "Beam":
                # 3 bottom tension bars
                spacing = (b - 2*cover - 2*bar_radius) / 2
                for i in range(3):
                    msp.add_circle((cover + bar_radius + i*spacing, cover + bar_radius), bar_radius, dxfattribs={'layer': 'REBAR'})
                # 2 top compression/anchor bars
                msp.add_circle((cover + bar_radius, D - cover - bar_radius), bar_radius, dxfattribs={'layer': 'REBAR'})
                msp.add_circle((b - cover - bar_radius, D - cover - bar_radius), bar_radius, dxfattribs={'layer': 'REBAR'})
            else:
                # 4 corner bars for Columns
                msp.add_circle((cover + bar_radius, cover + bar_radius), bar_radius, dxfattribs={'layer': 'REBAR'})
                msp.add_circle((b - cover - bar_radius, cover + bar_radius), bar_radius, dxfattribs={'layer': 'REBAR'})
                msp.add_circle((cover + bar_radius, D - cover - bar_radius), bar_radius, dxfattribs={'layer': 'REBAR'})
                msp.add_circle((b - cover - bar_radius, D - cover - bar_radius), bar_radius, dxfattribs={'layer': 'REBAR'})

        # 4. Dimension Lines (Manually drawn to ensure universal AutoCAD compatibility)
        # Width Dimension
        dim_offset_b = -40
        msp.add_line((0, dim_offset_b/2), (0, dim_offset_b*1.5), dxfattribs={'layer': 'DIMENSIONS'})
        msp.add_line((b, dim_offset_b/2), (b, dim_offset_b*1.5), dxfattribs={'layer': 'DIMENSIONS'})
        msp.add_line((0, dim_offset_b), (b, dim_offset_b), dxfattribs={'layer': 'DIMENSIONS'})
        msp.add_text(f"b = {b} mm", dxfattribs={'height': 20, 'layer': 'TEXT'}).set_placement((b/2, dim_offset_b - 25), align='CENTER')

        # Depth Dimension
        dim_offset_D = -40
        msp.add_line((dim_offset_D/2, 0), (dim_offset_D*1.5, 0), dxfattribs={'layer': 'DIMENSIONS'})
        msp.add_line((dim_offset_D/2, D), (dim_offset_D*1.5, D), dxfattribs={'layer': 'DIMENSIONS'})
        msp.add_line((dim_offset_D, 0), (dim_offset_D, D), dxfattribs={'layer': 'DIMENSIONS'})
        msp.add_text(f"D = {D} mm", dxfattribs={'height': 20, 'layer': 'TEXT'}).set_placement((dim_offset_D - 25, D/2), align='MIDDLE_CENTER', rotation=90)

        # Title
        msp.add_text(f"{element_type} Section: {element_id}", dxfattribs={'height': 30, 'layer': 'TEXT'}).set_placement((b/2, D + 40), align='BOTTOM_CENTER')

        # Save File
        safe_id = str(element_id).replace(':', '_').replace(' ', '_')
        filepath = f"CAD_{element_type}_{safe_id}.dxf"
        doc.saveas(filepath)
        return filepath