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
| Mission completed | 11 | always |
| All golden eggs / all bonus mutagens in a mission | 2 per mission | `bonus_objectives` |
| Wrangler rank 2 - N | 0-20 | `wrangler_rank_checks` |
| Abyss depth every X levels up to the goal depth | varies | `abyss_goal_depth`, `abyss_check_interval` |

Progression items are the planet access unlocks for Sectors 2-4 and Abyss Access. Goal is either the final
campaign mission or a target Abyss depth.

## Status

- [x] apworld generates and passes Archipelago's generic tests and its own tests
- [x] client <-> mod file protocol, item delivery that survives restarts, DeathLink plumbing
- [ ] **real mission names** - the names in `Locations.py` are placeholders (search for `TODO-verify`)
- [ ] **game hooks** - every `TODO` in `mod/Voidlingpelago/Scripts/game_hooks.lua` needs the real class and
      function names, which have to be dumped from the game with UE4SS

## Testing

Copy `apworld/voidling_bound` into an Archipelago source checkout's `worlds/` and run
`python -m pytest worlds/voidling_bound/test test/general`.
