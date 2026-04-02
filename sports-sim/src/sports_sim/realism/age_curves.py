"""Age curves and performance progression.

Applies realistic age-based modifiers to player attributes. Athletes peak at
different ages depending on the attribute:
 - Speed/endurance peak ~24-27, decline after 30
 - Skill/decision-making peak ~28-32, decline after 34
 - Strength peaks ~26-30, slow decline after 32
"""

from __future__ import annotations

import math

from sports_sim.core.models import Player


def _bell_curve(age: int, peak: float, width: float) -> float:
    """Gaussian-style multiplier centered at *peak* with spread *width*.

    Returns a value in (0, 1] where 1.0 is the peak age.
    """
    return math.exp(-0.5 * ((age - peak) / width) ** 2)


# Attribute → (peak_age, spread)
_AGE_CURVES: dict[str, tuple[float, float]] = {
    "speed": (26.0, 12.0),
    "endurance": (27.0, 12.0),
    "strength": (28.0, 13.0),
    "accuracy": (29.0, 14.0),
    "skill": (30.0, 15.0),
    "decision_making": (31.0, 16.0),
    "composure": (32.0, 17.0),
    "aggression": (27.0, 15.0),  # relatively flat
}


def age_modifier(age: int, attribute: str) -> float:
    """Return a 0-1 multiplier for *attribute* at the given *age*.

    >>> 0.95 < age_modifier(25, 'speed') <= 1.0
    True
    >>> age_modifier(40, 'speed') < 0.7
    True
    """
    peak, width = _AGE_CURVES.get(attribute, (28.0, 7.0))
    return _bell_curve(age, peak, width)


def apply_age_curve(player: Player) -> None:
    """Scale a player's attributes in-place based on their age.

    Call this once during roster setup.  The raw attribute values represent
    the player's *peak* capability; the age curve scales them down for
    younger/older players.
    """
    age = player.age
    attrs = player.attributes

    for attr_name in (
        "speed",
        "endurance",
        "strength",
        "accuracy",
        "skill",
        "decision_making",
        "composure",
        "aggression",
    ):
        raw = getattr(attrs, attr_name, None)
        if raw is None:
            continue
        mod = age_modifier(age, attr_name)
        setattr(attrs, attr_name, max(0.05, min(1.0, raw * mod)))
