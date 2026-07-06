import ezdxf
import os

def create_mock_dxf(filename, beam_width, layer="BEAM"):
    doc = ezdxf.new('R2010')
    doc.layers.add(layer)
    msp = doc.modelspace()
    
    # Create a simple polyline representing a beam cross section
    # Depth = 450mm, Width = beam_width
    points = [(0, 0), (beam_width, 0), (beam_width, 450), (0, 450)]
    msp.add_lwpolyline(points, dxfattribs={'layer': layer, 'closed': True})
    
    doc.saveas(filename)

def main():
    folder = "test_batch_dxfs"
    os.makedirs(folder, exist_ok=True)
    
    # Create 5 mock drawings with varying properties
    # B1, B3, B4 will likely pass minimum geometry rules
    # B2, B5 might fail if they are too thin and result in over-reinforced states
    create_mock_dxf(f"{folder}/project_A_beam1.dxf", 230)
    create_mock_dxf(f"{folder}/project_A_beam2.dxf", 100)
    create_mock_dxf(f"{folder}/project_B_beam1.dxf", 300)
    create_mock_dxf(f"{folder}/project_C_beam1.dxf", 250)
    create_mock_dxf(f"{folder}/project_D_beam1.dxf", 150)
    
    print(f"Generated 5 mock DXF files in '{folder}/'")

if __name__ == "__main__":
    main()
