"""Prepare a tiny development dataset; never overrides formal B0 readiness."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.b0_feasibility import prepare


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feasibility-only",action="store_true",required=True)
    parser.add_argument("--config",type=Path,default=ROOT/"configs/b0_feasibility.json")
    parser.add_argument("--output",type=Path,default=ROOT/"data/processed/b0_feasibility_2026-11-16")
    args=parser.parse_args()
    print(json.dumps(prepare(ROOT,args.config,args.output),ensure_ascii=False,indent=2))
