"""Houston (Harris County, TX) land use / land cover change, 1938 -> 2024.

Inputs (downloaded by fetch_data.py, not committed):
  * USGS modeled historical LULC backcast, 1938-1992, 250 m, EPSG:5070
  * Annual NLCD Collection 1.1, 1985-2024, 30 m, Albers
Everything is put on the 250 m backcast grid, reduced to classes present in
BOTH products, and anything else is nodata (0).
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd, rasterio
from rasterio import features
from rasterio.warp import reproject, Resampling, transform_geom
from rasterio.windows import from_bounds
from shapely.geometry import shape, mapping

ROOT = Path(__file__).resolve().parents[1]
RAW = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "raw"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

# Harmonized classes (id, name, hex colour). 0 = nodata.
CLASSES = [(1, "Open water", "#476ba1"), (2, "Developed", "#d1271e"),
           (3, "Barren", "#b3ac9f"), (4, "Forest", "#1c5f2c"),
           (5, "Shrubland", "#ccb879"), (6, "Grassland", "#dfdfc2"),
           (7, "Hay/Pasture", "#dcd939"), (8, "Cultivated crops", "#ab6c28"),
           (9, "Woody wetland", "#b8d9eb"), (10, "Herbaceous wetland", "#6c9fb8")]
NAMES = {c[0]: c[1] for c in CLASSES}
# Backcast legend (USGS metadata): 6 Mining and 17 Ice have no common
# counterpart, 3-5 unused  -> nodata.
BACK = {1: 1, 2: 2, 7: 3, 8: 4, 9: 4, 10: 4, 12: 5, 11: 6, 14: 7, 13: 8, 16: 9, 15: 10}
# Annual NLCD legend. 12 ice, 51-74 absent in Annual NLCD / not shared.
NLCD = {11: 1, 21: 2, 22: 2, 23: 2, 24: 2, 31: 3, 41: 4, 42: 4, 43: 4,
        52: 5, 71: 6, 81: 7, 82: 8, 90: 9, 95: 10}

def lut(m):
    t = np.zeros(256, np.uint8)
    for k, v in m.items(): t[k] = v
    return t
BACK_LUT, NLCD_LUT = lut(BACK), lut(NLCD)

# --- study area: Harris County, TX (FIPS 48201) --------------------------
gj = json.load(open(RAW / "counties.json"))
geom = shape([f for f in gj["features"] if f["id"] == "48201"][0]["geometry"])

def grid_from_backcast():
    with rasterio.open(RAW / "CONUS_Backcasting_y1992.tif") as s:
        g = transform_geom("EPSG:4326", s.crs, mapping(geom))
        win = from_bounds(*shape(g).bounds, s.transform).round_offsets().round_lengths()
        tr = s.window_transform(win)
        mask = features.rasterize([(g, 1)], (win.height, win.width), transform=tr, dtype="uint8").astype(bool)
        return s.crs, tr, (win.height, win.width), mask
CRS, TR, SHAPE, MASK = grid_from_backcast()
CELL_KM2 = 0.25 * 0.25

def load_back(y):
    with rasterio.open(RAW / f"CONUS_Backcasting_y{y}.tif") as s:
        win = rasterio.windows.Window(round((TR.c - s.transform.c) / 250), round((s.transform.f - TR.f) / 250), SHAPE[1], SHAPE[0])
        a = s.read(1, window=win)
    return np.where(MASK, BACK_LUT[a], 0).astype(np.uint8)

def load_nlcd(y):
    p = next((RAW / "nlcd").glob(f"*LndCov_{y}_CU_C1V1.tif"))
    out = np.zeros(SHAPE, np.uint8)
    with rasterio.open(p) as s:
        bounds = rasterio.transform.array_bounds(*SHAPE, TR)
        win = from_bounds(*bounds, s.transform).round_offsets().round_lengths()
        a = s.read(1, window=win)
        src_tr = s.window_transform(win)
    # Majority (mode) resample of 30 m classes onto the 250 m grid.
    reproject(NLCD_LUT[a], out, src_transform=src_tr, src_crs=s.crs,
              dst_transform=TR, dst_crs=CRS, resampling=Resampling.mode)
    return np.where(MASK, out, 0).astype(np.uint8)

LAYERS = {}
for y in (1938, 1950, 1970, 1992):
    LAYERS[f"Backcast {y}"] = load_back(y)
LAYERS["Backcast 1985"] = load_back(1985)
LAYERS["NLCD 1985"] = load_nlcd(1985)
LAYERS["NLCD 2024"] = load_nlcd(2024)

def area_table(keys):
    rows = []
    for cid, name, _ in CLASSES:
        rows.append({"class": name, **{k: round(float((LAYERS[k] == cid).sum() * CELL_KM2), 1) for k in keys}})
    df = pd.DataFrame(rows)
    df["valid_km2_total"] = None
    return df.drop(columns="valid_km2_total")

def transition(a, b):
    both = (a > 0) & (b > 0)
    m = np.zeros((10, 10))
    np.add.at(m, (a[both] - 1, b[both] - 1), CELL_KM2)
    names = [NAMES[i] for i in range(1, 11)]
    return pd.DataFrame(m.round(1), index=names, columns=names), both

# --- harmonized timeline: backcast through 1992, then NLCD 2024 ----------
timeline = ["Backcast 1938", "Backcast 1950", "Backcast 1970", "Backcast 1992", "NLCD 2024"]
at = area_table(timeline)
# Pixels valid in ALL timeline layers => apples-to-apples footprint.
valid = np.all([LAYERS[k] > 0 for k in timeline], axis=0)
at.to_csv(OUT / "class_area_km2.csv", index=False)
T, both = transition(LAYERS["Backcast 1938"], LAYERS["NLCD 2024"])
T.to_csv(OUT / "transition_1938_to_2024_km2.csv")
T2, _ = transition(LAYERS["Backcast 1992"], LAYERS["NLCD 2024"])
T2.to_csv(OUT / "transition_1992_to_2024_km2.csv")

# --- consistency check where the two products overlap in time -----------
chk = []
for lab, a, b in (("1985", "Backcast 1985", "NLCD 1985"), ("1992", "Backcast 1992", None)):
    if b is None: continue
    ok = (LAYERS[a] > 0) & (LAYERS[b] > 0)
    chk.append({"year": lab, "valid_cells": int(ok.sum()),
                "overall_agreement_pct": round(100 * float((LAYERS[a][ok] == LAYERS[b][ok]).mean()), 1),
                "developed_km2_backcast": round(float(((LAYERS[a] == 2) & ok).sum() * CELL_KM2), 1),
                "developed_km2_nlcd": round(float(((LAYERS[b] == 2) & ok).sum() * CELL_KM2), 1)})
pd.DataFrame(chk).to_csv(OUT / "overlap_check_1985.csv", index=False)

stats = {"cell_km2": CELL_KM2, "study_cells": int(MASK.sum()),
         "cells_valid_1938_and_2024": int(both.sum()),
         "pct_study_area_comparable": round(100 * float(both.sum() / MASK.sum()), 1),
         "pct_cells_changed_class_1938_2024": round(100 * float((LAYERS["Backcast 1938"][both] != LAYERS["NLCD 2024"][both]).mean()), 1)}
json.dump(stats, open(OUT / "summary.json", "w"), indent=2)

# --- coarse scheme: the primary, defensible comparison -------------------
# The 1985 overlap check shows the backcast and NLCD disagree most on forest vs
# woody wetland, shrub vs grass, and pasture vs developed, so those are merged.
COARSE_NAMES = {1: "Open water", 2: "Developed", 3: "Barren", 4: "Forest + woody wetland",
                5: "Shrub/grass", 6: "Agriculture (crops + pasture)", 7: "Herbaceous wetland"}
CO = np.zeros(256, np.uint8)
for k, v in {1: 1, 2: 2, 3: 3, 4: 4, 9: 4, 5: 5, 6: 5, 7: 6, 8: 6, 10: 7}.items(): CO[k] = v
COARSE = {k: CO[v] for k, v in LAYERS.items()}
rows = [{"class": n, **{k: round(float((COARSE[k] == i).sum() * CELL_KM2), 1) for k in timeline}} for i, n in COARSE_NAMES.items()]
pd.DataFrame(rows).to_csv(OUT / "class_area_coarse_km2.csv", index=False)
ok85 = (COARSE["Backcast 1985"] > 0) & (COARSE["NLCD 1985"] > 0)
cm85 = pd.crosstab(pd.Series(COARSE["Backcast 1985"][ok85], name="backcast_1985"), pd.Series(COARSE["NLCD 1985"][ok85], name="nlcd_1985")) * CELL_KM2
cm85.index = [COARSE_NAMES[i] for i in cm85.index]; cm85.columns = [COARSE_NAMES[i] for i in cm85.columns]
cm85.round(1).to_csv(OUT / "overlap_1985_confusion_coarse_km2.csv")
stats["coarse_agreement_1985_pct"] = round(100 * float((COARSE["Backcast 1985"][ok85] == COARSE["NLCD 1985"][ok85]).mean()), 1)
stats["detailed_agreement_1985_pct"] = chk[0]["overall_agreement_pct"]
json.dump(stats, open(OUT / "summary.json", "w"), indent=2)
mm = np.zeros((7, 7)); b2 = (COARSE["Backcast 1938"] > 0) & (COARSE["NLCD 2024"] > 0)
np.add.at(mm, (COARSE["Backcast 1938"][b2] - 1, COARSE["NLCD 2024"][b2] - 1), CELL_KM2)
nm = [COARSE_NAMES[i] for i in range(1, 8)]
pd.DataFrame(mm.round(1), index=nm, columns=nm).to_csv(OUT / "transition_coarse_1938_to_2024_km2.csv")
np.savez_compressed(OUT / "layers_coarse.npz", **{k.replace(" ", "_"): v for k, v in COARSE.items()})
print(pd.DataFrame(rows).to_string(index=False)); print(stats)

np.savez_compressed(ROOT / "outputs" / "layers.npz", **{k.replace(" ", "_"): v for k, v in LAYERS.items()})
json.dump({"transform": list(TR)[:6], "crs": CRS.to_string()}, open(OUT / "grid.json", "w"))
print(at.to_string(index=False)); print(pd.DataFrame(chk)); print(stats)
