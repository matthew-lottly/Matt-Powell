"""Download inputs into data/raw (not committed). Usage: python src/fetch_data.py [dest]"""
import json, subprocess, sys, zipfile
from pathlib import Path
RAW = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "data" / "raw"
(RAW / "nlcd").mkdir(parents=True, exist_ok=True)
def get(url, dest):
    if not dest.exists(): subprocess.run(["curl", "-sL", "--retry", "5", "-C", "-", "-o", str(dest), url], check=True)
# County boundaries (Census cartographic boundaries, redistributed by plotly/datasets)
get("https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json", RAW / "counties.json")
# USGS modeled backcast 1938-1992 (ScienceBase 59d3c73de4b05fe04cc3d1d1, DOI 10.5066/F7KK99RR)
item = json.loads(subprocess.check_output(["curl", "-s", "https://www.sciencebase.gov/catalog/item/59d3c73de4b05fe04cc3d1d1?format=json"]))
for f in item["files"]:
    if f["name"].endswith(".tif") and f["name"][-8:-4] in {"1938", "1950", "1970", "1985", "1992"}:
        get(f["url"], RAW / f["name"])
# Annual NLCD Collection 1.1 (DOI 10.5066/P94UXNTS); each CONUS zip is ~1.4 GB
for y in (1985, 2024):
    n = f"Annual_NLCD_LndCov_{y}_CU_C1V1"
    z = RAW / "nlcd" / f"{n}.zip"
    get(f"https://www.mrlc.gov/downloads/sciweb1/shared/mrlc/data-bundles/{n}.zip", z)
    if not (RAW / "nlcd" / f"{n}.tif").exists():
        with zipfile.ZipFile(z) as zf: zf.extract(f"{n}.tif", RAW / "nlcd")
