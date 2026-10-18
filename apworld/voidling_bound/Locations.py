# worlds/voidling_bound/Locations.py
from typing import TYPE_CHECKING, Dict, List, NamedTuple

from BaseClasses import Location

from .Genes import GENES, GENE_TYPES, SPECIES_REGIONS, gene_region
from .Variants import VARIANTS

if TYPE_CHECKING:
    from . import VoidlingBoundWorld


class VoidlingBoundLocation(Location):
    game: str = "Voidling Bound"


class LocationData(NamedTuple):
    code: int
    region: str


class Mission(NamedTuple):
    name: str
    planet: str
    golden_eggs: int  # 0 means the mission has no star collectibles
    mutagens: int


VIREO = "Vireo"
SOLUM = "Solum"
AULIS = "Aulis"
ABYSS = "The Abyss"
PLANETS = [VIREO, SOLUM, AULIS]
MAX_ABYSS_DEPTH = 50
MAX_WRANGLER_RANK = 21

# Mission list from the Voidling Bound wiki (voidlingbound.wiki.gg/wiki/Missions), in game order.
# End to the Unknown takes place in the Abyss but is entered through the altar on Aulis, so it belongs to Aulis.
# Operation: Void Strike is the Abyssal Incursion that opens up after slaying an Overlord in the Abyss.
MISSIONS: List[Mission] = [
    Mission("Faint Signal", VIREO, 0, 0),
    Mission("Save the Cauldrons", VIREO, 0, 0),
    Mission("Stranded Lead", VIREO, 0, 0),
    Mission("Centennial Bloom", VIREO, 1, 6),
    Mission("Secret Stronghold", VIREO, 2, 4),
    Mission("On the Precipice", VIREO, 0, 0),
    Mission("Last Stand", VIREO, 0, 0),
    Mission("On Night Watch", VIREO, 0, 0),
    Mission("Genetic Pursuit", VIREO, 0, 0),
    Mission("Back to Square One", VIREO, 0, 0),
    Mission("Search and Rescue", SOLUM, 2, 4),
    Mission("Reclaim Sanctuary", SOLUM, 0, 0),
    Mission("Cleaning the Eyrie", SOLUM, 2, 5),
    Mission("Subterranean Expedition", SOLUM, 1, 4),
    Mission("Ruin Delver", SOLUM, 0, 0),
    Mission("Drawing Fire", SOLUM, 0, 0),
    Mission("Survive the Storm", SOLUM, 0, 0),
    Mission("Safe Passage", SOLUM, 0, 0),
    Mission("Stay on Track", AULIS, 0, 0),
    Mission("Storm Breaker", AULIS, 1, 3),
    Mission("Navigate the Maze", AULIS, 2, 5),
    Mission("Pull the Plug", AULIS, 1, 4),
    Mission("Machine Non Grata", AULIS, 0, 0),
    Mission("On the Brink of Ruin", AULIS, 0, 0),
    Mission("Calm Before the Storm", AULIS, 0, 0),
    Mission("End to the Unknown", AULIS, 2, 4),
    Mission("Operation: Void Strike", ABYSS, 0, 0),
]
FINAL_MISSION = "End to the Unknown"


def golden_eggs_name(mission: str) -> str:
    return f"{mission} - All Golden Eggs"


def bonus_mutagens_name(mission: str) -> str:
    return f"{mission} - All Bonus Mutagens"


def wrangler_rank_name(rank: int) -> str:
    return f"Wrangler Rank {rank}"


def abyss_depth_name(depth: int) -> str:
    return f"Abyss: Reach Depth {depth}"


def wrangler_rank_region(rank: int) -> str:
    # Ranks 2-8 are expected on Vireo, 9-15 on Solum and the rest on Aulis.
    return PLANETS[min((rank - 2) // 7, len(PLANETS) - 1)]


# Every location that can ever exist, so IDs are stable regardless of options.
# IDs changed in 1.1.0 when the placeholder missions were replaced, 1.0.0 seeds are not compatible.
location_table: Dict[str, LocationData] = {}
for _index, _mission in enumerate(MISSIONS):
    location_table[_mission.name] = LocationData(841001 + _index, _mission.planet)
    if _mission.golden_eggs:
        location_table[golden_eggs_name(_mission.name)] = LocationData(842001 + _index, _mission.planet)
        location_table[bonus_mutagens_name(_mission.name)] = LocationData(842101 + _index, _mission.planet)
for _rank in range(2, MAX_WRANGLER_RANK + 1):
    location_table[wrangler_rank_name(_rank)] = LocationData(843000 + _rank, wrangler_rank_region(_rank))
for _depth in range(1, MAX_ABYSS_DEPTH + 1):
    location_table[abyss_depth_name(_depth)] = LocationData(844000 + _depth, ABYSS)
# Genes use 845000+, assigned by tools/import_genes.py
for _gene in GENES:
    location_table[_gene.name] = LocationData(_gene.code, gene_region(_gene))
# Variants use 847000+, assigned by tools/import_variants.py. Like genes, a variant is reachable once its
# species' eggs can drop.
for _variant in VARIANTS:
    location_table[_variant.name] = LocationData(_variant.code, SPECIES_REGIONS.get(_variant.species, AULIS))


def abyss_depths(world: "VoidlingBoundWorld") -> List[int]:
    goal_depth = world.options.abyss_goal_depth.value
    interval = world.options.abyss_check_interval.value
    depths = list(range(interval, goal_depth + 1, interval))
    if depths[-1:] != [goal_depth]:
        depths.append(goal_depth)
    return depths


def get_active_locations(world: "VoidlingBoundWorld") -> Dict[str, LocationData]:
    names = [mission.name for mission in MISSIONS]
    if world.options.bonus_objectives:
        for mission in MISSIONS:
            if mission.golden_eggs:
                names += [golden_eggs_name(mission.name), bonus_mutagens_name(mission.name)]
    names += [wrangler_rank_name(rank) for rank in range(2, world.options.wrangler_rank_checks.value + 2)]
    names += [abyss_depth_name(depth) for depth in abyss_depths(world)]
    collection = world.options.collection_checks
    if collection == collection.option_variants:
        names += [variant.name for variant in VARIANTS]
    elif collection == collection.option_genes:
        names += [gene.name for gene in GENES if gene.type in world.options.gene_types.value]
    return {name: location_table[name] for name in names}


location_name_groups: Dict[str, set] = {
    "Missions": {mission.name for mission in MISSIONS},
    "Bonus Objectives": {name for name in location_table if name.endswith(("Golden Eggs", "Bonus Mutagens"))},
    "Wrangler Ranks": {name for name in location_table if name.startswith("Wrangler Rank")},
    "Abyss Depths": {name for name in location_table if name.startswith("Abyss: Reach Depth")},
    **{planet: {name for name, data in location_table.items() if data.region == planet} for planet in PLANETS},
    **({"Genes": {gene.name for gene in GENES}} if GENES else {}),
    **({"Variants": {variant.name for variant in VARIANTS}} if VARIANTS else {}),
    **{f"{species} Variants": {variant.name for variant in VARIANTS if variant.species == species}
       for species in {variant.species for variant in VARIANTS}},
    **{f"{gene_type} Genes": {gene.name for gene in GENES if gene.type == gene_type}
       for gene_type in GENE_TYPES if any(gene.type == gene_type for gene in GENES)},
    **{f"{species} Genes": {gene.name for gene in GENES if gene.species == species}
       for species in {gene.species for gene in GENES}},
}
