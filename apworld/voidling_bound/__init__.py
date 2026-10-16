# worlds/voidling_bound/__init__.py
from typing import Any, Dict

from BaseClasses import ItemClassification, Region, Tutorial
from worlds.AutoWorld import WebWorld, World
from worlds.LauncherComponents import Component, Type, components, launch

from .Items import VoidlingBoundItem, get_random_filler_item_name, item_name_groups, item_table, useful_counts
from .Locations import (ABYSS, AULIS, FINAL_MISSION, MISSIONS, PLANETS, SOLUM, VIREO, VoidlingBoundLocation,
                        abyss_depths, get_active_locations, location_name_groups, location_table)
from .Options import Goal, VoidlingBoundOptions


def launch_client(*args: str) -> None:
    from .Client import launch_voidling_client
    launch(launch_voidling_client, name="Voidling Bound Client", args=args)


components.append(Component("Voidling Bound Client", func=launch_client, game_name="Voidling Bound",
                            component_type=Type.CLIENT, supports_uri=True))


class VoidlingBoundWeb(WebWorld):
    theme = "partyTime"
    tutorials = [Tutorial(
        "Multiworld Setup Guide",
        "A guide to setting up Voidling Bound with Archipelago and UE4SS.",
        "English",
        "setup_en.md",
        "setup/en",
        ["Cerzix"]
    )]


class VoidlingBoundWorld(World):
    """
    Voidling Bound is a sci-fi creature-taming shooter. Hatch, mutate and evolve Voidlings,
    cleanse infested planets and dive into the ever-deepening Abyss.
    """
    game = "Voidling Bound"
    web = VoidlingBoundWeb()
    options_dataclass = VoidlingBoundOptions
    options: VoidlingBoundOptions

    item_name_to_id = {name: data.code for name, data in item_table.items()}
    location_name_to_id = {name: data.code for name, data in location_table.items()}
    item_name_groups = item_name_groups
    location_name_groups = location_name_groups

    def create_item(self, name: str) -> VoidlingBoundItem:
        data = item_table[name]
        return VoidlingBoundItem(name, data.classification, data.code, self.player)

    def get_filler_item_name(self) -> str:
        return get_random_filler_item_name(self)

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        regions = {name: Region(name, self.player, self.multiworld) for name in PLANETS + [ABYSS]}
        self.multiworld.regions += [menu, *regions.values()]

        for name, data in get_active_locations(self).items():
            region = regions[data.region]
            region.locations.append(VoidlingBoundLocation(self.player, name, data.code, region))

        menu.connect(regions[VIREO])
        regions[VIREO].connect(regions[SOLUM], rule=lambda state: state.has("Planet Access: Solum", self.player))
        regions[SOLUM].connect(regions[AULIS], rule=lambda state: state.has("Planet Access: Aulis", self.player))
        # The Abyss is entered through the altar on Aulis.
        regions[AULIS].connect(regions[ABYSS], rule=lambda state: state.has("Abyss Access", self.player))

        # The goal is an event, so it never holds a real item and the server releases nothing on it.
        goal_region = regions[ABYSS] if self.options.goal == Goal.option_abyss_depth else regions[AULIS]
        victory = VoidlingBoundLocation(self.player, "Victory", None, goal_region)
        victory.place_locked_item(VoidlingBoundItem("Victory", ItemClassification.progression, None, self.player))
        goal_region.locations.append(victory)

    def create_items(self) -> None:
        itempool = [self.create_item(name) for name, data in item_table.items()
                    if data.classification == ItemClassification.progression]
        total_locations = len(self.multiworld.get_unfilled_locations(self.player))

        for name, count in useful_counts.items():
            for _ in range(count):
                if len(itempool) < total_locations:
                    itempool.append(self.create_item(name))
        while len(itempool) < total_locations:
            itempool.append(self.create_item(self.get_filler_item_name()))

        self.multiworld.itempool += itempool

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda state: state.has("Victory", self.player)

    def fill_slot_data(self) -> Dict[str, Any]:
        return {
            **self.options.as_dict("goal", "abyss_goal_depth", "bonus_objectives", "wrangler_rank_checks", "death_link"),
            "abyss_depths": abyss_depths(self),
            "final_mission": FINAL_MISSION,
            # The mod locks missions whose region isn't reachable yet.
            "mission_regions": {mission.name: mission.planet for mission in MISSIONS},
        }
