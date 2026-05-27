#!/usr/bin/env python3
"""Simple packer: rebuild .docx from unpacked directory."""
import os
import zipfile

UNPACKED = "/Users/sandilyachimalamarri/Plateplanner/unpacked_template"
OUTPUT = "/Users/sandilyachimalamarri/Plateplanner/PlatePlanner_295B_Report_Filled.docx"

def pack():
    with zipfile.ZipFile(OUTPUT, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(UNPACKED):
            for f in files:
                full_path = os.path.join(root, f)
                arcname = os.path.relpath(full_path, UNPACKED)
                zf.write(full_path, arcname)
    print(f"Created {OUTPUT}")
    print(f"Size: {os.path.getsize(OUTPUT) / 1024:.1f} KB")

if __name__ == "__main__":
    pack()
