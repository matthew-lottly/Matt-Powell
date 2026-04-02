from pathlib import Path

from sports_sim.data.roster_ingest import ingest_csv_to_json


def test_ingest_csv_to_json(tmp_path: Path):
    csv_file = tmp_path / "sample.csv"
    csv_file.write_text(
        "team_name,player_name,position,number,age,nationality,rating\n"
        "TeamA,Player1,Forward,9,25,USA,7.5\n"
        "TeamA,Player2,Midfield,8,27,ENG,6.8\n"
    )
    out_json = tmp_path / "out.json"
    res = ingest_csv_to_json(csv_file, out_json)
    assert res.exists()
    text = out_json.read_text()
    assert "TeamA" in text and "Player1" in text
