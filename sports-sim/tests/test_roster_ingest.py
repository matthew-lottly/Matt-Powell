import json
from pathlib import Path

from sports_sim.data import roster_ingest


def test_ingest_creates_json(tmp_path: Path):
    src_dir = Path("data/seeds_raw")
    dst_dir = tmp_path / "out"
    # run main pointing to sample CSVs
    rc = roster_ingest.main(src_dir, dst_dir)
    assert rc == 0
    # check that epl.json and mls.json were written
    epl = dst_dir / "epl.json"
    mls = dst_dir / "mls.json"
    assert epl.exists()
    assert mls.exists()
    d = json.loads(epl.read_text(encoding="utf-8"))
    assert "teams" in d and isinstance(d["teams"], list)
    # sanity check one player entry
    found = False
    for team in d["teams"]:
        for p in team["players"]:
            if p.get("name") == "Bukayo Saka":
                found = True
                assert p["rating"] == 85.0
    assert found
