"""Real-world infrastructure dataset loader using ACTIVSg200 power grid.

Downloads the ACTIVSg200 synthetic-but-realistic 200-bus power grid from the
MATPOWER repository and constructs a heterogeneous infrastructure graph with
three utility types: power, water, and telecom.

The power layer uses the real ACTIVSg200 bus topology and attributes.  Water
and telecom layers are derived from demand centres (population-correlated)
using standard network topologies.

Reference
---------
A.B. Birchfield, T. Xu, K.M. Gegner, K.S. Shetye, T.J. Overbye,
"Grid Structural Characteristics as Validation Criteria for Synthetic
Networks," IEEE Transactions on Power Systems, vol. 32, no. 4,
pp. 3258-3265, July 2017.  doi: 10.1109/TPWRS.2016.2616385

Licensed under Creative Commons Attribution 4.0 International.
"""

from __future__ import annotations

import math
import re
import ssl
import urllib.request
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np

from .graph import (
    HeteroInfraGraph,
    _generate_cross_edges,
    _generate_grid_mesh_edges,
    _generate_star_hub_edges,
    _simulate_cascade_labels,
    _split_masks,
)

ACTIVSG200_URL = (
    "https://raw.githubusercontent.com/"
    "MATPOWER/matpower/master/data/case_ACTIVSg200.m"
)

IEEE118_URL = (
    "https://raw.githubusercontent.com/"
    "MATPOWER/matpower/master/data/case118.m"
)

# Central Illinois city coordinates (lat, lon) for geocoding bus names.
# Coordinates are approximate centroids sufficient for spatial analysis.
_CITY_COORDS: Dict[str, Tuple[float, float]] = {
    "PEORIA": (40.6936, -89.5890),
    "SPRINGFIELD": (39.7817, -89.6501),
    "CHAMPAIGN": (40.1164, -88.2434),
    "BLOOMINGTON": (40.4842, -88.9937),
    "DECATUR": (39.8403, -88.9548),
    "NORMAL": (40.5142, -88.9906),
    "URBANA": (40.1106, -88.2073),
    "PEKIN": (40.5675, -89.6445),
    "CLINTON": (40.1537, -88.9634),
    "LINCOLN": (40.1484, -89.3649),
    "RANTOUL": (40.3086, -88.1559),
    "WASHINGTON": (40.7036, -89.4345),
    "MORTON": (40.6128, -89.4598),
    "EAST PEORIA": (40.6661, -89.5802),
    "BARTONVILLE": (40.6450, -89.6520),
    "PEORIA HEIGHTS": (40.7250, -89.5840),
    "CREVE COEUR": (40.6328, -89.5922),
    "DELAVAN": (40.3719, -89.5457),
    "TREMONT": (40.5275, -89.4914),
    "HANNA CITY": (40.6917, -89.7942),
    "METAMORA": (40.7903, -89.3600),
    "EUREKA": (40.7214, -89.2726),
    "EL PASO": (40.7392, -89.0172),
    "PRINCEVILLE": (40.9300, -89.7585),
    "BRIMFIELD": (40.8414, -89.8786),
    "MASON CITY": (40.2023, -89.6985),
    "GREENVIEW": (39.7439, -89.7403),
    "SAVOY": (40.0581, -88.2528),
    "TOLONO": (39.9864, -88.2592),
    "MANSFIELD": (40.2006, -88.5231),
    "HOMER": (40.0342, -87.9578),
    "FISHER": (40.3139, -88.3506),
    "SAINT JOSEPH": (40.1117, -88.0417),
    "MONTICELLO": (40.0278, -88.5734),
    "MAHOMET": (40.1953, -88.4042),
    "GIBSON CITY": (40.4586, -88.3853),
    "PAXTON": (40.4603, -88.0957),
    "LE ROY": (40.3506, -88.7656),
    "HEYWORTH": (40.3131, -88.9731),
    "COLFAX": (40.5667, -88.6153),
    "HUDSON": (40.6028, -88.9886),
    "CARLOCK": (40.5817, -89.1042),
    "TOWANDA": (40.5614, -88.9000),
    "ELLSWORTH": (40.4614, -88.7292),
    "CONGERVILLE": (40.6167, -89.2028),
    "DUNLAP": (40.8581, -89.6785),
    "MANITO": (40.4222, -89.7820),
    "LEXINGTON": (40.6417, -88.7831),
    "MACKINAW": (40.5362, -89.3577),
    "MINIER": (40.4339, -89.3117),
    "PLEASANT PLAINS": (39.8731, -89.8264),
    "ATHENS": (39.9614, -89.7244),
    "AUBURN": (39.5917, -89.7453),
    "WELDON": (40.1206, -88.7542),
    "BEMENT": (39.9217, -88.5708),
    "BUFFALO": (39.8597, -89.4131),
    "MT ZION": (39.7728, -88.8744),
    "MOUNT ZION": (39.7728, -88.8744),
    "NIANTIC": (39.8467, -89.1669),
    "PETERSBURG": (39.9986, -89.8485),
    "CHATHAM": (39.6764, -89.7125),
    "WAPELLA": (40.2186, -88.9581),
    "MACON": (39.7128, -88.9958),
    "ROANOKE": (40.7975, -89.1978),
    "LOVINGTON": (39.7136, -88.6367),
    "ILLIOPOLIS": (39.8567, -89.2436),
    "RANKIN": (40.4614, -87.8953),
    "MOUNT PULASKI": (40.0103, -89.2828),
    "GREEN VALLEY": (40.4100, -89.6400),
    "KENNEY": (40.0978, -89.1000),
    "VILLA GROVE": (39.8631, -88.1617),
    "WHITE HEATH": (40.0869, -88.5372),
    "GIFFORD": (40.3064, -88.0208),
    "MAPLETON": (40.5833, -89.7236),
    "HOPEDALE": (40.4231, -89.4250),
    "SHERMAN": (39.8939, -89.6025),
    "TUSCOLA": (39.7989, -88.2831),
}


# ---------------------------------------------------------------------------
# Internal MATPOWER parsing helpers
# ---------------------------------------------------------------------------


def _download_matpower(url: str, cache_path: Optional[Path] = None) -> str:
    """Download MATPOWER case file (or return cached copy)."""
    if cache_path and cache_path.exists():
        return cache_path.read_text(encoding="utf-8")

    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "STRATA-Loader/1.0"})
    with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
        text = resp.read().decode("utf-8")

    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(text, encoding="utf-8")
    return text


def _parse_matrix(text: str, varname: str) -> np.ndarray:
    """Extract a numeric matrix ``mpc.<varname> = [ ... ];`` from MATPOWER text."""
    pattern = rf"mpc\.{varname}\s*=\s*\[\s*(.*?)\];"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        raise ValueError(f"Could not find mpc.{varname} in MATPOWER file")
    rows: list[list[float]] = []
    for line in match.group(1).strip().split("\n"):
        line = line.strip().rstrip(";")
        if not line or line.startswith("%"):
            continue
        vals = [float(x) for x in line.split()]
        if vals:
            rows.append(vals)
    return np.array(rows)


def _parse_cell_array(text: str, varname: str) -> list[str]:
    """Extract a cell array of strings ``mpc.<varname> = { ... };``."""
    pattern = rf"mpc\.{varname}\s*=\s*\{{(.*?)\}};"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return []
    items: list[str] = []
    for line in match.group(1).strip().split("\n"):
        m = re.search(r"'([^']*)'", line)
        if m:
            items.append(m.group(1))
    return items


def _geocode_bus(
    bus_name: str, rng: np.random.Generator
) -> Tuple[float, float]:
    """Return (lat, lon) for a bus name using the city coordinate lookup."""
    # Strip trailing numeric suffixes: "SPRINGFIELD 5 2" -> "SPRINGFIELD"
    city = re.sub(r"[\s]+\d+[\s]*\d*$", "", bus_name.strip()).strip()
    if city in _CITY_COORDS:
        lat, lon = _CITY_COORDS[city]
    else:
        # Fallback: Central Illinois centroid with larger jitter
        lat, lon = 40.15, -89.0
        lat += rng.normal(0, 0.1)
        lon += rng.normal(0, 0.1)
        return lat, lon
    # Small jitter so buses at the same city don't stack perfectly
    lat += rng.normal(0, 0.008)
    lon += rng.normal(0, 0.008)
    return lat, lon


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _load_matpower_case(
    case_name: str,
    url: str,
    cache_dir: Optional[str] = None,
    train_frac: float = 0.5,
    cal_frac: float = 0.25,
    coupling_prob: float = 0.4,
    coupling_radius: float = 0.12,
    seed: int = 42,
) -> HeteroInfraGraph:
    """Load a MATPOWER transmission case and derive a heterogeneous graph.

    Constructs a three-layer infrastructure graph:

    * **power** – All 200 buses from the ACTIVSg200 transmission network
      with real branch topology and power-flow attributes.
    * **water** – Demand-correlated junctions placed at electrical load
      centres (population drives both electricity and water demand).
    * **telecom** – Hub-spoke nodes placed at the highest-demand locations
      (communication infrastructure follows population density).

    Cross-utility coupling edges are generated based on geographic
    proximity between layers.

    Parameters
    ----------
    cache_dir : str, optional
        Directory to cache the downloaded MATPOWER file.  Defaults to
        ``data/`` inside the project root.
    train_frac, cal_frac : float
        Fraction of nodes for training and calibration sets.
    coupling_prob : float
        Probability of creating a cross-utility edge for nearby nodes.
    coupling_radius : float
        Max geographic distance (degrees) for cross-utility coupling.
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    HeteroInfraGraph
        Ready-to-use heterogeneous graph with real power topology.
    """
    rng = np.random.default_rng(seed)

    # ------------------------------------------------------------------
    # 1. Download and parse ACTIVSg200
    # ------------------------------------------------------------------
    file_name = f"case_{case_name}.m" if not case_name.startswith("case") else f"{case_name}.m"
    if cache_dir is None:
        cache_path = Path(__file__).resolve().parents[2] / "data" / file_name
    else:
        cache_path = Path(cache_dir) / file_name

    text = _download_matpower(url, cache_path)
    bus_data = _parse_matrix(text, "bus")
    branch_data = _parse_matrix(text, "branch")
    bus_names = _parse_cell_array(text, "bus_name")

    # ------------------------------------------------------------------
    # 2. Extract bus properties
    # ------------------------------------------------------------------
    n_buses = bus_data.shape[0]
    bus_ids = bus_data[:, 0].astype(int)
    bus_types = bus_data[:, 1].astype(int)      # 1=PQ, 2=PV, 3=slack
    Pd = bus_data[:, 2]                          # Active power demand (MW)
    Qd = bus_data[:, 3]                          # Reactive power demand (MVAr)
    Vm = bus_data[:, 7]                          # Voltage magnitude (p.u.)
    Va = bus_data[:, 8]                          # Voltage angle (degrees)
    baseKV = bus_data[:, 9]                      # Base voltage (kV)
    zone = bus_data[:, 10].astype(int)           # Zone

    id_to_idx = {int(bid): i for i, bid in enumerate(bus_ids)}

    # ------------------------------------------------------------------
    # 3. Geocode buses to lat/lon
    # ------------------------------------------------------------------
    positions = np.zeros((n_buses, 2), dtype=np.float32)
    for i in range(n_buses):
        name = bus_names[i] if i < len(bus_names) else f"BUS {bus_ids[i]}"
        lat, lon = _geocode_bus(name, rng)
        positions[i] = [lon, lat]  # match existing [lon, lat] convention

    # ------------------------------------------------------------------
    # 4. POWER layer – all 200 buses with real topology
    # ------------------------------------------------------------------
    pd_max = max(Pd.max(), 1.0)
    qd_max = max(np.abs(Qd).max(), 1.0)
    va_max = max(np.abs(Va).max(), 1.0)

    power_features = np.column_stack([
        Pd / pd_max,                              # normalised demand
        Qd / qd_max,                              # normalised reactive demand
        Vm,                                        # voltage magnitude (already ~1.0 p.u.)
        Va / va_max,                               # normalised voltage angle
        baseKV / 230.0,                            # normalised voltage level
        (bus_types >= 2).astype(np.float32),       # is-generator flag
        zone / zone.max(),                         # normalised zone
        rng.standard_normal(n_buses).astype(np.float32),  # noise feature
    ]).astype(np.float32)

    power_positions = positions.copy()

    # Real branch edges (undirected)
    psrc, pdst = [], []
    for row in branch_data:
        fbus, tbus = int(row[0]), int(row[1])
        if fbus in id_to_idx and tbus in id_to_idx:
            fi, ti = id_to_idx[fbus], id_to_idx[tbus]
            psrc.extend([fi, ti])
            pdst.extend([ti, fi])
    power_edges = (
        np.array([psrc, pdst], dtype=np.int64)
        if psrc
        else np.zeros((2, 0), dtype=np.int64)
    )

    # ------------------------------------------------------------------
    # 5. WATER layer – demand-correlated junctions
    # ------------------------------------------------------------------
    load_mask = Pd > 0
    load_idx = np.where(load_mask)[0]
    n_water = len(load_idx)

    water_positions = positions[load_idx].copy()
    water_positions[:, 0] += rng.normal(0, 0.005, n_water).astype(np.float32)
    water_positions[:, 1] += rng.normal(0, 0.005, n_water).astype(np.float32)

    water_demand = Pd[load_idx] / pd_max
    water_pressure = np.clip(Vm[load_idx] + rng.normal(0, 0.02, n_water), 0.8, 1.2)
    water_features = np.column_stack([
        water_demand,                                                    # demand
        water_pressure,                                                  # pressure proxy
        Qd[load_idx] / qd_max,                                         # reactive proxy
        zone[load_idx] / zone.max(),                                    # service area
        rng.standard_normal((n_water, 4)),                               # auxiliary
    ]).astype(np.float32)

    grid_w = max(1, int(math.sqrt(n_water)))
    water_edges = _generate_grid_mesh_edges(n_water, grid_w, rng)

    # ------------------------------------------------------------------
    # 6. TELECOM layer – hub-spoke at major demand centers
    # ------------------------------------------------------------------
    n_telecom = min(80, n_buses // 2)
    demand_rank = np.argsort(-Pd)[:n_telecom]

    telecom_positions = positions[demand_rank].copy()
    telecom_positions[:, 0] += rng.normal(0, 0.003, n_telecom).astype(np.float32)
    telecom_positions[:, 1] += rng.normal(0, 0.003, n_telecom).astype(np.float32)

    telecom_features = np.column_stack([
        Pd[demand_rank] / pd_max,                                       # traffic ~ demand
        rng.uniform(0.5, 1.0, n_telecom),                              # signal strength
        Vm[demand_rank],                                                # grid health
        zone[demand_rank] / zone.max(),                                 # zone
        rng.standard_normal((n_telecom, 4)),                            # auxiliary
    ]).astype(np.float32)

    n_hubs = max(3, n_telecom // 10)
    telecom_edges = _generate_star_hub_edges(n_telecom, n_hubs, rng)

    # ------------------------------------------------------------------
    # 7. Assemble HeteroInfraGraph
    # ------------------------------------------------------------------
    graph = HeteroInfraGraph()

    graph.node_features = {
        "power": power_features,
        "water": water_features,
        "telecom": telecom_features,
    }
    graph.node_positions = {
        "power": power_positions,
        "water": water_positions.astype(np.float32),
        "telecom": telecom_positions.astype(np.float32),
    }
    graph.edge_index = {
        ("power", "feeds", "power"): power_edges,
        ("water", "pipes", "water"): water_edges,
        ("telecom", "connects", "telecom"): telecom_edges,
    }

    # Cross-utility coupling
    for edge_type, src_type, dst_type in [
        (("power", "colocated", "water"), "power", "water"),
        (("water", "colocated", "telecom"), "water", "telecom"),
        (("power", "colocated", "telecom"), "power", "telecom"),
    ]:
        graph.edge_index[edge_type] = _generate_cross_edges(
            graph.node_positions[src_type],
            graph.node_positions[dst_type],
            coupling_prob,
            coupling_radius,
            rng,
        )

    # ------------------------------------------------------------------
    # 8. Cascading-failure risk labels
    # ------------------------------------------------------------------
    center = np.mean(power_positions, axis=0)
    graph.node_labels = _simulate_cascade_labels(
        graph,
        shock_center=center,
        shock_radius=0.4,
        propagation_decay=2.0,
        noise_std=0.1,
        rng=rng,
    )

    # ------------------------------------------------------------------
    # 9. Train / calibration / test splits
    # ------------------------------------------------------------------
    for ntype in graph.node_features:
        n = graph.node_features[ntype].shape[0]
        graph.node_masks[ntype] = _split_masks(n, train_frac, cal_frac, rng)

    return graph


def load_activsg200(
    cache_dir: Optional[str] = None,
    train_frac: float = 0.5,
    cal_frac: float = 0.25,
    coupling_prob: float = 0.4,
    coupling_radius: float = 0.12,
    seed: int = 42,
) -> HeteroInfraGraph:
    """Load the ACTIVSg200 power grid and derive a heterogeneous graph."""
    return _load_matpower_case(
        case_name="ACTIVSg200",
        url=ACTIVSG200_URL,
        cache_dir=cache_dir,
        train_frac=train_frac,
        cal_frac=cal_frac,
        coupling_prob=coupling_prob,
        coupling_radius=coupling_radius,
        seed=seed,
    )


def load_ieee118(
    cache_dir: Optional[str] = None,
    train_frac: float = 0.5,
    cal_frac: float = 0.25,
    coupling_prob: float = 0.4,
    coupling_radius: float = 0.12,
    seed: int = 42,
) -> HeteroInfraGraph:
    """Load the public IEEE 118-bus MATPOWER case and derive a heterogeneous graph.

    This provides a second public benchmark beyond ACTIVSg200 using the same
    heterogeneous construction strategy: real transmission topology plus derived
    water and telecom layers based on demand centres.
    """
    return _load_matpower_case(
        case_name="118",
        url=IEEE118_URL,
        cache_dir=cache_dir,
        train_frac=train_frac,
        cal_frac=cal_frac,
        coupling_prob=coupling_prob,
        coupling_radius=coupling_radius,
        seed=seed,
    )
