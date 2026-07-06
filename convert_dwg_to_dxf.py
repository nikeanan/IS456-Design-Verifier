import os
import subprocess
import sys
import argparse

def convert_dwg_to_dxf(input_dir, output_dir, oda_path=None):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Common installation paths for ODA File Converter
    possible_oda_paths = [
        "ODAFileConverter", # If in PATH (Linux/Mac/WSL)
        r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
        r"C:\Program Files\ODA\ODAFileConverter 25.1.0\ODAFileConverter.exe",
        r"C:\Program Files\ODA\ODAFileConverter 24.11.0\ODAFileConverter.exe",
        r"C:\Program Files (x86)\ODA\ODAFileConverter\ODAFileConverter.exe"
    ]
    
    if oda_path:
        possible_oda_paths.insert(0, oda_path)
        
    executable = None
    for path in possible_oda_paths:
        # Check if the path is a valid file or if it's the bare command string for PATH resolution
        if os.path.isfile(path) or path == "ODAFileConverter":
            executable = path
            # We can't guarantee "ODAFileConverter" is in PATH just because it's a string,
            # but subprocess will tell us when we try to run it. 
            # It's safest to prioritize known Windows paths if we suspect it's on Windows.
            if path != "ODAFileConverter" or os.name != 'nt': 
                break
            
    if not executable:
        print("Error: ODA File Converter executable not found in default paths.")
        print("Please download and install it for free from: https://www.opendesign.com/guestfiles/oda_file_converter")
        sys.exit(1)
        
    # ODAFileConverter Syntax:
    # ODAFileConverter <Input Folder> <Output Folder> <Output Version> <Output File Type> <Recurse> <Audit>
    # e.g., "ACAD2018", "DXF"
    cmd = [
        executable,
        os.path.abspath(input_dir),
        os.path.abspath(output_dir),
        "ACAD2013", # Widely compatible output version
        "DXF",
        "0", # Recurse (0=No, 1=Yes)
        "1"  # Audit (0=No, 1=Yes)
    ]
    
    print(f"Attempting to use ODA File Converter at: {executable}")
    print(f"Running command: {' '.join(cmd)}\n")
    
    try:
        subprocess.run(cmd, check=True)
        print("\n[SUCCESS] Conversion completed successfully!")
        print(f"Converted DXF files are saved in: {os.path.abspath(output_dir)}")
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Error during conversion: {e}")
    except FileNotFoundError:
        print("\n[ERROR] Command not found. The ODA File Converter is either not installed or not in your system PATH.")
        print("Please download it from: https://www.opendesign.com/guestfiles/oda_file_converter")
        print("Or pass the exact path using --oda \"C:\\Path\\To\\ODAFileConverter.exe\"")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch convert a folder of DWG files to DXF using ODA File Converter.")
    parser.add_argument("--input", default="CAD dwg", help="Input directory containing .dwg files")
    parser.add_argument("--output", default="CAD dxf", help="Output directory for .dxf files")
    parser.add_argument("--oda", help="Explicit path to ODAFileConverter executable (optional)")
    
    args = parser.parse_args()
    
    convert_dwg_to_dxf(args.input, args.output, args.oda)
