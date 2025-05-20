"""Utility helpers for incentives."""
from typing import Iterable, Optional
from dataclasses import dataclass


@dataclass
class Incentive:
    """Simple incentive record used for tests or utilities."""
    incentive_type: str
    amount: float


def calculate_total_incentives(incentives: Iterable[Incentive], incentive_type: Optional[str] = None) -> float:
    """Calculate the total amount of incentives.

    Args:
        incentives: Iterable of Incentive records.
        incentive_type: Optional type filter.
    """
    total = 0.0
    for inc in incentives:
        if incentive_type and inc.incentive_type != incentive_type:
            continue
        total += inc.amount
    return total
