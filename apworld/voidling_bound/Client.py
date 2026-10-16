# worlds/voidling_bound/Client.py
# Bridges the Archipelago server and the UE4SS Lua mod through plain text files in the exchange folder:
#   events.txt    mod -> client, one event per line, append only:
#                   mission_complete <MissionKey> | golden_eggs <MissionKey> | bonus_mutagens <MissionKey>
#                   wrangler_rank <N> | abyss_depth <N> | gene <GeneAssetName> | death
#   items.txt     client -> mod, first line "session <seed> <slot>", then "<index> <item id> <item name>" per item
#   slot.txt      client -> mod, "key=value" lines from slot_data (lists as "a,b", dicts as "k=v|k=v")
#   deathlink.txt client -> mod, exists while a DeathLink is waiting to be applied, the mod deletes it
import asyncio
import os
from typing import Dict, List, Optional, Set

import Utils
from CommonClient import ClientCommandProcessor, CommonContext, get_base_parser, gui_enabled, handle_url_arg, \
    logger, server_loop
from NetUtils import ClientStatus

from .Genes import GENES_BY_ASSET
from .Locations import MAX_ABYSS_DEPTH, MAX_WRANGLER_RANK, MISSIONS, abyss_depth_name, bonus_mutagens_name, \
    golden_eggs_name, location_table, wrangler_rank_name

GAME = "Voidling Bound"
POLL_INTERVAL = 0.5

# The mod reports missions by the game's activity asset name. The game names its data assets after their
# title (e.g. the quest "Cracking the Future" is DA_Quest_CrackingtheFuture_Demo), so asset names are matched
# to missions by comparing letters and digits only. Assets that don't follow that pattern go in MISSION_KEYS.
MISSION_KEYS: Dict[str, str] = {}
ASSET_PREFIXES = ("da_activity_", "da_mission_", "da_")
ASSET_SUFFIXES = ("_demo",)


def normalize_key(key: str) -> str:
    key = key.lower()
    for prefix in ASSET_PREFIXES:
        if key.startswith(prefix):
            key = key[len(prefix):]
            break
    for suffix in ASSET_SUFFIXES:
        if key.endswith(suffix):
            key = key[:-len(suffix)]
    return "".join(char for char in key if char.isalnum())


MISSION_BY_NORMALIZED_KEY: Dict[str, str] = {normalize_key(mission.name): mission.name for mission in MISSIONS}


def mission_for_key(key: str) -> Optional[str]:
    return MISSION_KEYS.get(key) or MISSION_BY_NORMALIZED_KEY.get(normalize_key(key))


def default_exchange_dir() -> str:
    return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Voidlingpelago")


class VoidlingCommandProcessor(ClientCommandProcessor):
    def _cmd_exchange(self) -> bool:
        """Show the folder used to talk to the game mod."""
        self.output(f"Exchange folder: {self.ctx.exchange_dir}")
        return True


class VoidlingContext(CommonContext):
    game = GAME
    command_processor = VoidlingCommandProcessor
    items_handling = 0b111  # receive items from other worlds, our own world and the starting inventory

    def __init__(self, server_address: Optional[str], password: Optional[str], exchange_dir: str):
        super().__init__(server_address, password)
        self.exchange_dir = exchange_dir
        self.slot_data: dict = {}
        self.events_read = 0
        self.items_written = -1
        self.goal_sent = False
        self.unknown_mission_keys: Set[str] = set()
        os.makedirs(self.exchange_dir, exist_ok=True)

    def path(self, name: str) -> str:
        return os.path.join(self.exchange_dir, name)

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_package(self, cmd: str, args: dict):
        if cmd == "RoomInfo":
            # CommonContext doesn't keep the seed name, but the session key the mod relies on needs it.
            self.seed_name = args["seed_name"]
        elif cmd == "Connected":
            self.slot_data = args.get("slot_data", {})
            self.events_read = 0
            self.items_written = -1
            self.goal_sent = False
            self.start_session()
            if self.slot_data.get("death_link"):
                Utils.async_start(self.update_death_link(True))

    def start_session(self):
        # A new seed or slot means old events belong to another game, so the events file is cleared.
        session = f"session {self.seed_name} {self.slot}"
        items_path = self.path("items.txt")
        previous = None
        if os.path.exists(items_path):
            with open(items_path, encoding="utf-8") as f:
                previous = f.readline().strip()
        if previous != session and os.path.exists(self.path("events.txt")):
            os.remove(self.path("events.txt"))
        with open(self.path("slot.txt"), "w", encoding="utf-8") as f:
            for key, value in self.slot_data.items():
                if isinstance(value, list):
                    value = ",".join(str(v) for v in value)
                elif isinstance(value, dict):
                    value = "|".join(f"{k}={v}" for k, v in value.items())
                f.write(f"{key}={value}\n")

    def on_deathlink(self, data: dict):
        super().on_deathlink(data)
        with open(self.path("deathlink.txt"), "w", encoding="utf-8") as f:
            f.write(data.get("source", ""))

    def write_items(self):
        if len(self.items_received) == self.items_written:
            return
        lines = [f"session {self.seed_name} {self.slot}"]
        for index, item in enumerate(self.items_received):
            lines.append(f"{index} {item.item} {self.item_names.lookup_in_game(item.item)}")
        tmp = self.path("items.txt.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        os.replace(tmp, self.path("items.txt"))  # atomic, so the mod never sees a half written file
        self.items_written = len(self.items_received)

    def read_new_events(self) -> List[str]:
        path = self.path("events.txt")
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
        # Only complete lines, the mod could be halfway through writing the last one.
        new = [line.strip() for line in lines[self.events_read:] if line.strip()]
        self.events_read = len(lines)
        return new

    def locations_for_event(self, event: str) -> Set[str]:
        kind, _, arg = event.partition(" ")
        if kind in ("mission_complete", "golden_eggs", "bonus_mutagens"):
            mission = mission_for_key(arg)
            if mission is None:
                # Tutorial and demo-only activities aren't locations, so this is informational.
                if arg not in self.unknown_mission_keys:
                    self.unknown_mission_keys.add(arg)
                    logger.info(f"Activity {arg} isn't an Archipelago location (add it to MISSION_KEYS if it should be)")
                return set()
            return {{"mission_complete": mission, "golden_eggs": golden_eggs_name(mission),
                     "bonus_mutagens": bonus_mutagens_name(mission)}[kind]}
        if kind == "wrangler_rank" and arg.isdigit():
            return {wrangler_rank_name(rank) for rank in range(2, min(int(arg), MAX_WRANGLER_RANK) + 1)}
        if kind == "abyss_depth" and arg.isdigit():
            return {abyss_depth_name(depth) for depth in range(1, min(int(arg), MAX_ABYSS_DEPTH) + 1)}
        if kind == "gene":
            # Genes that aren't in data/genes.json yet (e.g. new in the full game) simply aren't locations.
            gene = GENES_BY_ASSET.get(arg)
            return {gene.name} if gene else set()
        if kind == "death":
            if "DeathLink" in self.tags:
                Utils.async_start(self.send_death("died in Voidling Bound."))
            return set()
        logger.warning(f"Unknown event from the mod: {event}")
        return set()

    def goal_reached(self) -> bool:
        if self.slot_data.get("goal") == 1:
            goal_location = abyss_depth_name(self.slot_data["abyss_goal_depth"])
        else:
            goal_location = self.slot_data.get("final_mission")
        return goal_location in location_table and location_table[goal_location].code in self.checked_locations

    async def poll_game(self):
        events = self.read_new_events()
        new_locations = set()
        for event in events:
            for name in self.locations_for_event(event):
                # Locations that are disabled by options, or bonus objectives a mission doesn't have,
                # simply don't exist in this slot.
                if name in location_table and location_table[name].code in self.missing_locations:
                    new_locations.add(location_table[name].code)
        if new_locations:
            await self.check_locations(new_locations)
        self.write_items()
        if not self.goal_sent and self.goal_reached():
            await self.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
            self.goal_sent = True

    def make_gui(self):
        class VoidlingManager(super().make_gui()):
            base_title = "Archipelago Voidling Bound Client"
        return VoidlingManager


async def game_watcher(ctx: VoidlingContext):
    while not ctx.exit_event.is_set():
        if ctx.server and ctx.slot is not None:
            try:
                await ctx.poll_game()
            except OSError as e:
                logger.warning(f"Could not access the exchange folder: {e}")
        await asyncio.sleep(POLL_INTERVAL)


async def main(args):
    ctx = VoidlingContext(args.connect, args.password, args.exchange_dir)
    ctx.auth = args.name
    ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
    if gui_enabled:
        ctx.run_gui()
    ctx.run_cli()
    watcher = asyncio.create_task(game_watcher(ctx), name="game watcher")
    await ctx.exit_event.wait()
    ctx.server_address = None
    await ctx.shutdown()
    await watcher


def launch_voidling_client(*args: str):
    import colorama

    parser = get_base_parser()
    parser.add_argument("--name", default=None, help="Slot name to connect as.")
    parser.add_argument("--exchange-dir", default=default_exchange_dir(), help="Folder shared with the game mod.")
    parser.add_argument("url", nargs="?", help="Archipelago connection url")
    parsed = handle_url_arg(parser.parse_args(args))

    colorama.just_fix_windows_console()
    asyncio.run(main(parsed))
    colorama.deinit()
