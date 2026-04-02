"""Tests for the CLI interface."""

from click.testing import CliRunner

from sports_sim.cli import cli


class TestCLI:
    def test_sports_list(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["sports"])
        assert result.exit_code == 0
        assert "soccer" in result.output

    def test_run_soccer(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--sport", "soccer", "--seed", "42", "--fidelity", "fast"])
        assert result.exit_code == 0
        assert "FINAL SCORE" in result.output

    def test_run_basketball(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--sport", "basketball", "--seed", "42", "--fidelity", "fast"])
        assert result.exit_code == 0
        assert "FINAL SCORE" in result.output

    def test_run_baseball(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--sport", "baseball", "--seed", "42", "--fidelity", "fast"])
        assert result.exit_code == 0
        assert "FINAL SCORE" in result.output

    def test_run_verbose(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--sport", "soccer", "--seed", "1", "--fidelity", "fast", "-v"])
        assert result.exit_code == 0
        assert "game_start" in result.output.lower() or "FINAL SCORE" in result.output

    def test_batch(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["batch", "--sport", "soccer", "-n", "3", "--seed", "10", "--fidelity", "fast"])
        assert result.exit_code == 0
        assert "Home wins" in result.output

    def test_run_with_output(self, tmp_path):
        out = tmp_path / "result.json"
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--sport", "soccer", "--seed", "5", "--fidelity", "fast", "-o", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        import json

        data = json.loads(out.read_text())
        assert "final_score" in data
