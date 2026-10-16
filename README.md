# Voidlingpelago

An [Archipelago](https://archipelago.gg/) multiworld integration for Voidling Bound (Hatchery Games, Unreal Engine).

## Layout

- `apworld/voidling_bound/` - the Archipelago world (items, locations, options, logic) and the Voidling Bound Client
- `mod/Voidlingpelago/` - the UE4SS Lua mod that runs inside the game
- `build_release.py` - builds `dist/voidling_bound.apworld` and `dist/Voidlingpelago.zip`

## How it fits together

```
Voidling Bound + UE4SS mod  <-- text files in %APPDATA%\Voidlingpelago -->  Voidling Bound Client  <-- websocket -->  AP server
```

The mod reports game events (`mission_complete <key>`, `abyss_depth 15`, ...) and the client turns them into
location checks. The client writes every received item to `items.txt` and the mod grants the new ones.
The full protocol is described at the top of `apworld/voidling_bound/Client.py`.

## Checks

| Check | Count | Option |
|---|---|---|
| Mission completed (Vireo 10, Solum 8, Aulis 7, End to the Unknown, Operation: Void Strike) | 27 | always |
| All golden eggs / all bonus mutagens, on the 9 missions that have them | 18 | `bonus_objectives` |
| Wrangler rank 2 - N | 0-20 | `wrangler_rank_checks` |
| Abyss depth every X levels up to the goal depth | varies | `abyss_goal_depth`, `abyss_check_interval` |

Mission data comes from the [Voidling Bound wiki](https://voidlingbound.wiki.gg/wiki/Missions).
Progression items are Planet Access: Solum, Planet Access: Aulis and Abyss Access (entered through the altar on
Aulis). The goal is either End to the Unknown or a target Abyss depth.

## Status

- [x] apworld with the real missions, generates and passes Archipelago's generic tests and its own tests
- [x] client <-> mod file protocol, item delivery that survives restarts, DeathLink plumbing
- [x] discovery tools in the mod to find the game's classes and functions (F6 scan, F7 trace, F8 state dump)
- [x] missions, golden egg / mutagen stars, Wrangler rank and Abyss depth are read from the game's state
- [x] research points, mutagens and eggs are granted, DeathLink works both ways
- [ ] planet gating, golden and species eggs, Catalyzers, ability points

## Finding the hooks

Voidling Bound runs on Unreal Engine 5.7, so it needs the **experimental** UE4SS build. With the mod installed
and `discovery = true` in `Scripts/config.lua`:

1. Start a mission and press **F6**. `%APPDATA%\Voidlingpelago\discovery.txt` lists every loaded game class
   whose name looks relevant (Mission, Objective, Abyss, Egg, Mutagen, Rank, ...) with its functions and properties.
2. Press **F7** to start a trace, then do exactly one thing: finish the mission, pick up a golden egg, rank up,
   dive deeper in the Abyss or die. Press **F7** again.
3. `trace.txt` shows which functions fired at that moment, on which object and with which arguments.
   Those are the functions to hook in `game_hooks.lua`.

Send both files along with what you did during the trace, one trace per action.

## Testing

- World: copy `apworld/voidling_bound` into an Archipelago source checkout's `worlds/` and run
  `python -m pytest worlds/voidling_bound/test test/general`.
- Mod: `pip install lupa`, then `python mod/tests/test_mod.py` runs the Lua mod against stubbed UE4SS functions.
