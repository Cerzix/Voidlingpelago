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
# Retired: 840003 (Sector 4 access), 840011 (Mutation Perk Slot), 840021 (Mutagen Pack), 840022 (Polychrome Crystals)
item_table: Dict[str, ItemData] = {
    # Progression / Welten-Zugang
    "Planet Access: Solum": ItemData(840001, ItemClassification.progression, "Planet Access"),
    "Planet Access: Aulis": ItemData(840002, ItemClassification.progression, "Planet Access"),
    "Abyss Access": ItemData(840004, ItemClassification.progression, "Planet Access"),

    # Nützliche Upgrades & Katalysatoren
    "DNA Catalyzer Bundle": ItemData(840010, ItemClassification.useful, "Upgrades"),
    "Golden Egg": ItemData(840012, ItemClassification.useful, "Upgrades"),
    "Ability Points": ItemData(840013, ItemClassification.useful, "Upgrades"),
    "Polychrome Mutagen": ItemData(840014, ItemClassification.useful, "Mutagens"),

    # Filler / Ressourcen
    "Research Points (500)": ItemData(840020, ItemClassification.filler, "Resources"),
    "Voidling Egg": ItemData(840023, ItemClassification.filler, "Eggs"),
    "Organic Mutagens (3)": ItemData(840030, ItemClassification.filler, "Mutagens"),
    "Pyro Mutagens (3)": ItemData(840031, ItemClassification.filler, "Mutagens"),
    "Cryo Mutagens (3)": ItemData(840032, ItemClassification.filler, "Mutagens"),
    "Cyber Mutagens (3)": ItemData(840033, ItemClassification.filler, "Mutagens"),
    "Plasma Mutagens (3)": ItemData(840034, ItemClassification.filler, "Mutagens"),

    # Species eggs, from the wiki's mission rewards
    "Kwipeck Egg": ItemData(840040, ItemClassification.useful, "Eggs"),
    "Kerapin Egg": ItemData(840041, ItemClassification.useful, "Eggs"),
    "Gilick Egg": ItemData(840042, ItemClassification.useful, "Eggs"),
    "Gwigoon Egg": ItemData(840043, ItemClassification.useful, "Eggs"),
    "Nimiod Egg": ItemData(840044, ItemClassification.useful, "Eggs"),
    "Anami Egg": ItemData(840045, ItemClassification.useful, "Eggs"),
    "Ur-Sek Egg": ItemData(840046, ItemClassification.useful, "Eggs"),
    "Morfang Egg": ItemData(840047, ItemClassification.useful, "Eggs"),
}

# How many copies of each useful item go into the pool, the rest is filled with weighted filler.
useful_counts: Dict[str, int] = {
    "DNA Catalyzer Bundle": 3,
    "Golden Egg": 3,
    "Ability Points": 4,
    "Polychrome Mutagen": 2,
    **{name: 1 for name, data in item_table.items() if name.endswith(" Egg") and data.group == "Eggs"
       and data.classification == ItemClassification.useful},
}

filler_weights: Dict[str, int] = {
    "Research Points (500)": 30,
    "Voidling Egg": 10,
    "Organic Mutagens (3)": 12,
    "Pyro Mutagens (3)": 12,
    "Cryo Mutagens (3)": 12,
    "Cyber Mutagens (3)": 12,
    "Plasma Mutagens (3)": 12,
}

item_name_groups: Dict[str, set] = {}
for _name, _data in item_table.items():
    item_name_groups.setdefault(_data.group, set()).add(_name)


def get_random_filler_item_name(world: "VoidlingBoundWorld") -> str:
    names = list(filler_weights)
    return world.random.choices(names, weights=[filler_weights[n] for n in names])[0]
