with open('dxf_commit.py', 'r', encoding='utf-16') as f:
    lines = f.readlines()

dxf_start = -1
for i, line in enumerate(lines):
    if "elif element_choice == \"CAD (DXF) Integration\":" in line:
        dxf_start = i
        break

if dxf_start != -1:
    print("".join(lines[dxf_start:dxf_start+60]))
else:
    print("Not found")
