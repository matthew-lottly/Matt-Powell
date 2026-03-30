"""CLI interface for sports-sim — run simulations from the command line."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from sports_sim.core.engine import Simulation
from sports_sim.core.models import Environment, SimulationConfig, SportType, Weather


@click.group()
@click.version_option()
def cli():
    """Sports simulation engine — run and analyse game simulations."""


@cli.command()
@click.option("--sport", type=click.Choice(["soccer", "basketball", "baseball"]), default="soccer")
@click.option("--seed", type=int, default=None, help="Random seed for reproducibility.")
@click.option("--fidelity", type=click.Choice(["fast", "medium", "high"]), default="medium")
@click.option("--ticks", type=int, default=10, help="Ticks per second.")
@click.option("--no-fatigue", is_flag=True, help="Disable fatigue model.")
@click.option("--no-injuries", is_flag=True, help="Disable injury model.")
@click.option("--no-weather", is_flag=True, help="Disable weather effects.")
@click.option("--no-momentum", is_flag=True, help="Disable momentum model.")
@click.option("--weather", "weather_type", type=click.Choice([w.value for w in Weather]), default="clear")
@click.option("--temperature", type=float, default=22.0, help="Temperature in °C.")
@click.option("--wind", type=float, default=0.0, help="Wind speed in kph.")
@click.option("--output", "-o", type=click.Path(), default=None, help="Write JSON results to file.")
@click.option("--verbose", "-v", is_flag=True, help="Print every game event.")
def run(sport, seed, fidelity, ticks, no_fatigue, no_injuries, no_weather, no_momentum,
        weather_type, temperature, wind, output, verbose):
    """Run a single game simulation."""
    env = Environment(
        weather=Weather(weather_type),
        temperature_c=temperature,
        wind_speed_kph=wind,
    )
    config = SimulationConfig(
        sport=SportType(sport),
        seed=seed,
        ticks_per_second=ticks,
        fidelity=fidelity,
        enable_fatigue=not no_fatigue,
        enable_injuries=not no_injuries,
        enable_weather=not no_weather,
        enable_momentum=not no_momentum,
        environment=env,
    )

    click.echo(f"Running {sport} simulation (fidelity={fidelity}, seed={seed})...")

    sim = Simulation(config)
    for state, events in sim.stream():
        if verbose:
            for ev in events:
                click.echo(f"  [{ev.type.value:>18}] {ev.description}")

    click.echo()
    click.secho(f"FINAL SCORE: {sim.state.score_summary}", fg="green", bold=True)
    click.echo(f"Total events: {len(sim.state.events)}")
    click.echo(f"Home avg stamina: {sim.state.home_team.avg_stamina:.2f}")
    click.echo(f"Away avg stamina: {sim.state.away_team.avg_stamina:.2f}")

    if output:
        path = Path(output)
        result = {
            "sport": sport,
            "seed": seed,
            "final_score": {
                "home": {"name": sim.state.home_team.name, "score": sim.state.home_team.score},
                "away": {"name": sim.state.away_team.name, "score": sim.state.away_team.score},
            },
            "total_events": len(sim.state.events),
            "events": [
                {"type": e.type.value, "time": round(e.time, 2), "period": e.period,
                 "description": e.description}
                for e in sim.state.events
            ],
        }
        path.write_text(json.dumps(result, indent=2))
        click.echo(f"Results saved to {path}")


@cli.command()
@click.option("--sport", type=click.Choice(["soccer", "basketball", "baseball"]), default="soccer")
@click.option("--count", "-n", type=int, default=10, help="Number of simulations.")
@click.option("--seed", type=int, default=None, help="Base seed (incremented per run).")
@click.option("--fidelity", type=click.Choice(["fast", "medium", "high"]), default="fast")
def batch(sport, count, seed, fidelity):
    """Run multiple simulations and show aggregate stats."""
    home_wins = 0
    away_wins = 0
    draws = 0
    total_home_score = 0
    total_away_score = 0

    for i in range(count):
        s = seed + i if seed is not None else None
        config = SimulationConfig(sport=SportType(sport), seed=s, fidelity=fidelity, ticks_per_second=10)
        sim = Simulation(config)
        sim.run()
        total_home_score += sim.state.home_team.score
        total_away_score += sim.state.away_team.score
        if sim.state.home_team.score > sim.state.away_team.score:
            home_wins += 1
        elif sim.state.away_team.score > sim.state.home_team.score:
            away_wins += 1
        else:
            draws += 1

    click.echo(f"\n{'=' * 50}")
    click.secho(f"Batch: {count} {sport} simulations", bold=True)
    click.echo(f"{'=' * 50}")
    click.echo(f"Home wins:  {home_wins}  ({home_wins / count * 100:.1f}%)")
    click.echo(f"Away wins:  {away_wins}  ({away_wins / count * 100:.1f}%)")
    click.echo(f"Draws:      {draws}  ({draws / count * 100:.1f}%)")
    click.echo(f"Avg score:  {total_home_score / count:.1f} - {total_away_score / count:.1f}")


@cli.command()
def sports():
    """List available sports."""
    for s in SportType:
        click.echo(f"  {s.value}")


def main():
    cli()


if __name__ == "__main__":
    main()
