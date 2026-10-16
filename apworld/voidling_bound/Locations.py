# worlds/voidling_bound/Locations.py
from typing import TYPE_CHECKING, Dict, List, NamedTuple

from BaseClasses import Location

if TYPE_CHECKING:
    from . import VoidlingBoundWorld


class VoidlingBoundLocation(Location):
    game: str = "Voidling Bound"


class LocationData(NamedTuple):
    code: int
    region: str


SECTORS = ["Sector 1", "Sector 2", "Sector 3", "Sector 4"]
ABYSS = "Abyss"
MAX_ABYSS_DEPTH = 50
MAX_WRANGLER_RANK = 21

# TODO-verify: these mission names are placeholders and NOT the real in-game names.
# Replace them with the real missions once they've been read from the game (UE4SS object dump / FModel).
# Only the names change, keep the IDs. The client maps the mod's internal mission keys to these names.
# (mission name, sector, ID)
MISSIONS: List[tuple] = [
    ("Tutorial: Island Cleared", "Sector 1", 841001),
    ("W01: Crashsite Survival", "Sector 1", 841002),
    ("W01: Clifftop Cleansing", "Sector 1", 841003),
    ("W02: Crater Survival", "Sector 2", 841004),
    ("W02: Frozen Lake Cleansing", "Sector 2", 841005),
    ("W02: Magma Caves Cleansing", "Sector 2", 841006),
    ("W03: Canyon Cleansing", "Sector 3", 841007),
    ("W03: Oasis Survival", "Sector 3", 841008),
    ("W03: Stormlands Night Cleansing", "Sector 3", 841009),
    ("W04: Breach Cleansing", "Sector 4", 841010),
    ("W04: Abyss Incursion", "Sector 4", 841011),
]
FINAL_MISSION = MISSIONS[-1][0]
# Missions without collectibles don't get bonus objective checks.
NO_BONUS_OBJECTIVES = {"Tutorial: Island Cleared"}


def golden_eggs_name(mission: str) -> str:
    return f"{mission} - All Golden Eggs"


def bonus_mutagens_name(mission: str) -> str:
    return f"{mission} - All Bonus Mutagens"


def wrangler_rank_name(rank: int) -> str:
    return f"Wrangler Rank {rank}"


def abyss_depth_name(depth: int) -> str:
    return f"Abyss: Reach Depth {depth}"


def wrangler_rank_region(rank: int) -> str:
    # Ranks 2-6 are expected in Sector 1, 7-11 in Sector 2, and so on.
    return SECTORS[min((rank - 2) // 5, len(SECTORS) - 1)]


# Every location that can ever exist, so IDs are stable regardless of options.
location_table: Dict[str, LocationData] = {}
for _index, (_mission, _sector, _code) in enumerate(MISSIONS):
    location_table[_mission] = LocationData(_code, _sector)
    if _mission not in NO_BONUS_OBJECTIVES:
        location_table[golden_eggs_name(_mission)] = LocationData(842000 + _index, _sector)
        location_table[bonus_mutagens_name(_mission)] = LocationData(842100 + _index, _sector)
for _rank in range(2, MAX_WRANGLER_RANK + 1):
    location_table[wrangler_rank_name(_rank)] = LocationData(843000 + _rank, wrangler_rank_region(_rank))
for _depth in range(1, MAX_ABYSS_DEPTH + 1):
    location_table[abyss_depth_name(_depth)] = LocationData(844000 + _depth, ABYSS)


def abyss_depths(world: "VoidlingBoundWorld") -> List[int]:
    goal_depth = world.options.abyss_goal_depth.value
    interval = world.options.abyss_check_interval.value
    depths = list(range(interval, goal_depth + 1, interval))
    if depths[-1:] != [goal_depth]:
        depths.append(goal_depth)
    return depths


def get_active_locations(world: "VoidlingBoundWorld") -> Dict[str, LocationData]:
    names = [mission for mission, _, _ in MISSIONS]
    if world.options.bonus_objectives:
        for mission, _, _ in MISSIONS:
            if mission not in NO_BONUS_OBJECTIVES:
                names += [golden_eggs_name(mission), bonus_mutagens_name(mission)]
    names += [wrangler_rank_name(rank) for rank in range(2, world.options.wrangler_rank_checks.value + 2)]
    names += [abyss_depth_name(depth) for depth in abyss_depths(world)]
    return {name: location_table[name] for name in names}


location_name_groups: Dict[str, set] = {
    "Missions": {mission for mission, _, _ in MISSIONS},
    "Bonus Objectives": {name for name in location_table if name.endswith(("Golden Eggs", "Bonus Mutagens"))},
    "Wrangler Ranks": {name for name in location_table if name.startswith("Wrangler Rank")},
    "Abyss": {name for name, data in location_table.items() if data.region == ABYSS},
}
