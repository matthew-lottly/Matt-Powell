"""Quick demo — run one game of each sport and print results."""

from sports_sim.core.engine import Simulation
from sports_sim.core.models import SimulationConfig, SportType


def main():
    for sport in SportType:
        config = SimulationConfig(
            sport=sport,
            seed=42,
            fidelity="fast",
            ticks_per_second=10,
        )
        sim = Simulation(config)

        print(f"\n{'=' * 50}")
        print(f"  {sport.value.upper()} SIMULATION")
        print(f"{'=' * 50}")

        for state, events in sim.stream():
            for ev in events:
                print(f"  [{ev.type.value:>18}] {ev.description}")

        print(f"\n  FINAL: {sim.state.score_summary}")
        print(f"  Events: {len(sim.state.events)}")
        print(f"  Home stamina: {sim.state.home_team.avg_stamina:.2f}")
        print(f"  Away stamina: {sim.state.away_team.avg_stamina:.2f}")


if __name__ == "__main__":
    main()
