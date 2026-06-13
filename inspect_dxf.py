import ezdxf
import os

def inspect_dxf(file_path):
    doc = ezdxf.readfile(file_path)
    layers = set()
    for entity in doc.modelspace():
        layer = entity.dxf.layer
        if layer not in layers:
            print(f"Layer: {layer}, Entity Type: {entity.dxftype()}")
            layers.add(layer)

if __name__ == "__main__":
    file_path = 'sample_plan.dxf'
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
    else:
        inspect_dxf(file_path)
