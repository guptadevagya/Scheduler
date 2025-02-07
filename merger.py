#!/usr/bin/env python3
import os
import pandas as pd

def merge(folder, out="merged.xlsx"):
    files = []
    for f in os.listdir(folder):
        # Ignore case for .xlsx
        if f.lower().endswith(".xlsx"):
            files.append(os.path.join(folder, f))

    if not files:
        print("No .xlsx files found in", folder)
        return

    dfs = []
    for f in files:
        print("Reading:", f)
        df = pd.read_excel(f)
        dfs.append(df)

    merged = pd.concat(dfs, ignore_index=True)
    merged.to_excel(out, index=False)
    print("Merged", len(files), "files into", out)

def main():
    # Adjust 'folder' to the name of the folder with your .xlsx files
    folder = "schedules"
    out = "schedules.xlsx"
    merge(folder, out)

if __name__ == "__main__":
    main()