# worlds/voidling_bound/Items.py
from typing import TYPE_CHECKING, Dict, NamedTuple

from BaseClasses import Item, ItemClassification

if TYPE_CHECKING:
    from . import VoidlingBoundWorld


class VoidlingBoundItem(Item):
    game: str = "Voidling Bound"


class ItemData(NamedTuple):
    code: int
    classification: ItemClassification
    group: str


# IDs are part of the network protocol: never renumber or reuse an ID once a version has been released.
# 840011 (Mutation Perk Slot) and 840022 (Polychrome Crystals) are retired, they don't exist in the game.
item_table: Dict[str, ItemData] = {
    # Progression / Welten-Zugang
    "Planet Access: Sector 2 (W02)": ItemData(840001, ItemClassification.progression, "Planet Access"),
    "Planet Access: Sector 3 (W03)": ItemData(840002, ItemClassification.progression, "Planet Access"),
    "Planet Access: Sector 4 (W04)": ItemData(840003, ItemClassification.progression, "Planet Access"),
    "Abyss Access": ItemData(840004, ItemClassification.progression, "Planet Access"),

    # Nützliche Upgrades & Katalysatoren
    "DNA Catalyzer Bundle": ItemData(840010, ItemClassification.useful, "Upgrades"),
    "Golden Egg": ItemData(840012, ItemClassification.useful, "Upgrades"),
    "Ability Points": ItemData(840013, ItemClassification.useful, "Upgrades"),

    # Filler / Ressourcen
    "Research Points (500)": ItemData(840020, ItemClassification.filler, "Resources"),
    "Mutagen Pack": ItemData(840021, ItemClassification.filler, "Resources"),
    "Voidling Egg": ItemData(840023, ItemClassification.filler, "Resources"),
}

# How many copies of each useful item go into the pool, the rest is filled with weighted filler.
useful_counts: Dict[str, int] = {
    "DNA Catalyzer Bundle": 3,
    "Golden Egg": 3,
    "Ability Points": 4,
}

filler_weights: Dict[str, int] = {
    "Research Points (500)": 50,
    "Mutagen Pack": 35,
    "Voidling Egg": 15,
}

item_name_groups: Dict[str, set] = {}
for _name, _data in item_table.items():
    item_name_groups.setdefault(_data.group, set()).add(_name)


def get_random_filler_item_name(world: "VoidlingBoundWorld") -> str:
    names = list(filler_weights)
    return world.random.choices(names, weights=[filler_weights[n] for n in names])[0]
