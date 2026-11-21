"""
Script:   run_all.py
Project:  Forkly food delivery analytics (2021-2025)
Author:   [Your Name]
Created:  [Date]
Purpose:  Run the full pipeline: clean -> analysis tables -> 5-page dashboard
          python run_all.py               scripts only (about 15 seconds)
          python run_all.py --notebooks   also re-runs the three notebooks
Input:    Forkly/Data/*.csv
Output:   Forkly/Data_clean/, Forkly/output/tables/,
          Forkly/output/dashboard/ (Forkly_dashboard.html, .pdf, 5 PNG pages)
"""
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.append(str(BASE / "src"))

import analysis  # noqa: E402
import clean  # noqa: E402
import dashboard  # noqa: E402

NOTEBOOKS = ["01_cleaning.ipynb", "02_exploration.ipynb", "03_analysis.ipynb"]


def step(name, func, *args):
    print(f"\n== {name} ==")
    start = time.time()
    result = func(*args)
    print(f"   done in {time.time() - start:.1f}s")
    return result


def run_notebooks():
    for nb in NOTEBOOKS:
        print(f"   running {nb}")
        subprocess.run([sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute",
                        "--inplace", str(BASE / "notebooks" / nb)], check=True, cwd=BASE / "notebooks")


if __name__ == "__main__":
    t0 = time.time()
    step("1/3 Clean raw data", clean.run)
    tables = step("2/3 Build analysis tables", analysis.build_all)
    step("3/3 Build dashboard", dashboard.run, tables)
    if "--notebooks" in sys.argv:
        step("Notebooks", run_notebooks)
    print(f"\nPipeline finished in {time.time() - t0:.1f}s. Open: {BASE / 'output' / 'dashboard' / 'Forkly_dashboard.html'}")
