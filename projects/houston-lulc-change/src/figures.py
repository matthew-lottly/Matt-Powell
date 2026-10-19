"""Maps + chart from outputs/layers.npz (run analyze.py first)."""
import json
from pathlib import Path
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / "outputs"
L = np.load(OUT / "layers_coarse.npz")
C = [("Nodata / outside area", "#ffffff"), ("Open water", "#476ba1"), ("Developed", "#d1271e"), ("Barren", "#b3ac9f"),
     ("Forest + woody wetland", "#1c5f2c"), ("Shrub/grass", "#ccb879"), ("Agriculture (crops + pasture)", "#dcd939"),
     ("Herbaceous wetland", "#6c9fb8")]
cm = ListedColormap([c[1] for c in C])
panels = [("Backcast_1938", "1938 (modeled backcast, 250 m)"), ("Backcast_1970", "1970 (modeled backcast, 250 m)"),
          ("Backcast_1992", "1992 (modeled backcast, 250 m)"), ("NLCD_2024", "2024 (Annual NLCD, resampled to 250 m)")]
fig, ax = plt.subplots(1, 4, figsize=(20, 5.6))
for a, (k, t) in zip(ax, panels):
    a.imshow(L[k], cmap=cm, vmin=0, vmax=7, interpolation="nearest"); a.set_title(t, fontsize=11); a.axis("off")
fig.legend(handles=[Patch(color=c[1], label=c[0]) for c in C[1:]], loc="lower center", ncol=4, frameon=False)
fig.suptitle("Harris County (Houston), TX - harmonized land cover, 1938-2024", fontsize=14)
fig.text(0.5, 0.012, "1938-1992 panels are MODELED (USGS FORE-SCE backcast); 2024 is satellite-derived. Classes not in both products = nodata.", ha="center", fontsize=8)
fig.tight_layout(rect=(0, 0.14, 1, 0.95)); fig.savefig(OUT / "fig1_landcover_maps.png", dpi=150); plt.close(fig)

a, b = L["Backcast_1938"], L["NLCD_2024"]
ok = (a > 0) & (b > 0)
ch = np.zeros(a.shape, np.uint8)
ch[ok & (a == b)] = 1
ch[ok & (a != b) & (b == 2)] = 2          # became developed
ch[ok & (a != b) & (a == 2)] = 3          # developed -> other (rare)
ch[ok & (a != b) & (b != 2) & (a != 2)] = 4   # other class change
cc = ListedColormap(["#ffffff", "#e6e6e6", "#d1271e", "#7b3294", "#f4a582"])
fig, ax = plt.subplots(figsize=(8, 7))
ax.imshow(ch, cmap=cc, vmin=0, vmax=4, interpolation="nearest"); ax.axis("off")
ax.set_title("Change in land cover class, 1938 -> 2024 (comparable cells only)")
ax.legend(handles=[Patch(color=c, label=l) for c, l in zip(["#e6e6e6", "#d1271e", "#7b3294", "#f4a582"],
          ["No class change", "Converted to Developed", "Developed -> other", "Other class change"])], loc="lower left", fontsize=8)
fig.tight_layout(); fig.savefig(OUT / "fig2_change_map.png", dpi=150); plt.close(fig)

t = pd.read_csv(OUT / "class_area_coarse_km2.csv").set_index("class")
fig, ax = plt.subplots(figsize=(10, 5.5))
t.T.plot(kind="bar", stacked=True, ax=ax, color=[c[1] for c in C[1:]], width=0.7, edgecolor="white", linewidth=0.3)
ax.set_ylabel("Area (km2)"); ax.set_title("Harmonized class area through time (coarse scheme)")
ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8, frameon=False); plt.xticks(rotation=0)
fig.tight_layout(); fig.savefig(OUT / "fig3_class_area.png", dpi=150)
