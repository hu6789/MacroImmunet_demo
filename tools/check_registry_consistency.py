# tools/check_registry_consistency.py
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from scan_master.label_names import LABEL_REGISTRY
from scan_master.receptor_registry import RECEPTOR_REGISTRY

def check():
    labels = set(k.upper() for k in LABEL_REGISTRY.keys())
    problems = []

    # 1) 所有 receptor.binds 必须指向 LABEL_REGISTRY 中存在的 canonical 名称（或至少 warn）
    for rname, rmeta in RECEPTOR_REGISTRY.items():
        for lig in rmeta.get("binds", []):
            if lig.upper() not in labels:
                problems.append(f"RECEPTOR {rname} binds '{lig}' -> MISSING in LABEL_REGISTRY")

    # 2) 列出 label types for each bound ligand
    for rname, rmeta in RECEPTOR_REGISTRY.items():
        for lig in rmeta.get("binds", []):
            meta = LABEL_REGISTRY.get(lig.upper())
            ltype = meta.get("type") if meta else None
            print(f"{rname:12} binds {lig:20} -> label_type={ltype}")

    if problems:
        print("\nProblems found:")
        for p in problems:
            print("  -", p)
    else:
        print("\nNo missing binds detected. All receptor binds map to labels present in LABEL_REGISTRY.")

if __name__ == "__main__":
    check()

