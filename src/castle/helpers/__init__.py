"""Pure offline, cross-platform device helpers powered by Sirius."""

from castle.helpers.buddy_toys import (
    SNACKS,
    cosmic_oracle,
    feed_sirius,
    flip_coin,
    poke_sirius,
    roll_dice,
)
from castle.helpers.ports import PortReport, inspect_ports
from castle.helpers.repo import RepoReport, inspect_workspace
from castle.helpers.sweep import SweepReport, clean_safe_caches, format_bytes, scan_clutter
from castle.helpers.vitals import SystemVitals, format_vitals_report, gather_vitals

__all__ = [
    "SNACKS",
    "PortReport",
    "RepoReport",
    "SweepReport",
    "SystemVitals",
    "clean_safe_caches",
    "cosmic_oracle",
    "feed_sirius",
    "flip_coin",
    "format_bytes",
    "format_vitals_report",
    "gather_vitals",
    "inspect_ports",
    "inspect_workspace",
    "poke_sirius",
    "roll_dice",
    "scan_clutter",
]
