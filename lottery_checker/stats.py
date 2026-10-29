"""P5-01 descriptive draw statistics for the owner view. Counts only: no
ranking, no prediction. Built from captured draws (data/draws), never from
crowd results."""
from __future__ import annotations

import json
from pathlib import Path

MIN_DRAWS = 30
NOTE = "Each draw is independent. Past draws do not predict the next."


def toto_stats(draws: list) -> dict:
    raise NotImplementedError


def fourd_stats(draws: list) -> dict:
    raise NotImplementedError


def all_stats(data_dir) -> dict:
    raise NotImplementedError


STATS_MODULE_END = True
