# worlds/voidling_bound/Client.py
# Bridges the Archipelago server and the UE4SS Lua mod through plain text files in the exchange folder:
#   events.txt    mod -> client, one event per line, append only:
#                   mission_complete <MissionKey> | golden_eggs <MissionKey> | bonus_mutagens <MissionKey>
#                   wrangler_rank <N> | abyss_depth <N> | death
#   items.txt     client -> mod, first line "session <seed> <slot>", then "<index> <item id> <item name>" per item
#   slot.txt      client -> mod, "key=value" lines from slot_data
#   deathlink.txt client -> mod, exists while a DeathLink is waiting to be applied, the mod deletes it
import asyncio
import os
from typing import Dict, List, Optional, Set

import Utils
from CommonClient import ClientCommandProcessor, CommonContext, get_base_parser, gui_enabled, handle_url_arg, \
    logger, server_loop
from NetUtils import ClientStatus

from .Locations import MAX_ABYSS_DEPTH, MAX_WRANGLER_RANK, MISSIONS, abyss_depth_name, bonus_mutagens_name, \
    golden_eggs_name, location_table, wrangler_rank_name

GAME = "Voidling Bound"
POLL_INTERVAL = 0.5

# TODO-verify: the mod reports missions by their internal key (e.g. the level asset name).
# Fill this with the real keys once they're known. Until then the mod can report the AP mission name directly,
# with spaces replaced by underscores, which also resolves through MISSION_BY_KEY below.
MISSION_KEYS: Dict[str, str] = {}
MISSION_BY_KEY: Dict[str, str] = {
    **{mission.replace(" ", "_"): mission for mission, _, _ in MISSIONS},
    **MISSION_KEYS,
}


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
        os.makedirs(self.exchange_dir, exist_ok=True)

    def path(self, name: str) -> str:
        return os.path.join(self.exchange_dir, name)

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_package(self, cmd: str, args: dict):
        if cmd == "Connected":
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
            mission = MISSION_BY_KEY.get(arg)
            if mission is None:
                logger.warning(f"Unknown mission key from the mod: {arg}")
                return set()
            return {{"mission_complete": mission, "golden_eggs": golden_eggs_name(mission),
                     "bonus_mutagens": bonus_mutagens_name(mission)}[kind]}
        if kind == "wrangler_rank" and arg.isdigit():
            return {wrangler_rank_name(rank) for rank in range(2, min(int(arg), MAX_WRANGLER_RANK) + 1)}
        if kind == "abyss_depth" and arg.isdigit():
            return {abyss_depth_name(depth) for depth in range(1, min(int(arg), MAX_ABYSS_DEPTH) + 1)}
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
                loc_id = location_table[name].code
                # Locations that are disabled by options simply don't exist in this slot.
                if loc_id in self.missing_locations:
                    new_locations.add(loc_id)
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
