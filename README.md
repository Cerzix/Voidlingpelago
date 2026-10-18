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
| Every unlocked Voidling variant (filler only) | 294 | `collection_checks: variants` (default) or `both` |
| Every unlocked gene (filler only) | up to 1,042 | `collection_checks: genes` or `both`, `gene_types` |

Mission data comes from the [Voidling Bound wiki](https://voidlingbound.wiki.gg/wiki/Missions).
Progression items are Planet Access: Solum, Planet Access: Aulis and Abyss Access (entered through the altar on
Aulis). The goal is either End to the Unknown or a target Abyss depth.

## Status

- [x] apworld with the real missions, generates and passes Archipelago's generic tests and its own tests
- [x] client <-> mod file protocol, item delivery that survives restarts, DeathLink plumbing
- [x] developer tools to find the game's classes and functions (`mod/devtools`, not in the release)
- [x] missions, golden egg / mutagen stars, Wrangler rank and Abyss depth are read from the game's state
- [x] research points, mutagens, species / golden / random eggs and DNA Catalyzers are granted
- [x] missions on locked planets are locked, DeathLink works both ways
- [ ] everything above needs confirming in the real game, see the latest release notes

## Developer tools

The released mod has no debug keys. For development, copy `mod/devtools/discovery.lua` into the installed mod's
`Scripts` folder; `main.lua` loads it when it's there. Output goes to `%APPDATA%\Voidlingpelago\`.

| Key | What it does |
|---|---|
| F5 | `genes.txt` and `variants.txt`: every gene and every variant in the game, for the lists below |
| F6 | `discovery.txt`: every loaded game class with a relevant name, with functions, parameters and properties |
| F7 | starts/stops `trace.txt`: every call to those classes' functions, with object and arguments |
| F8 | `state.txt`: the player's progress as the game stores it, and every loaded mission, planet, resource and species |
| F9 | sends a "Faint Signal" check, to test the client connection (only in a test room) |

### Updating the gene and variant lists

1. In game with a save loaded and the developer tools installed, press **F5**.
2. Run `python tools/import_genes.py "%APPDATA%\Voidlingpelago\genes.txt"` and
   `python tools/import_variants.py "%APPDATA%\Voidlingpelago\variants.txt"`.
3. Commit the changed `apworld/voidling_bound/data/genes.json` and `variants.json`.

Genes and variants keep their ID across imports, so a dump from a newer game version only adds the new ones.

## Testing

- World: copy `apworld/voidling_bound` into an Archipelago source checkout's `worlds/` and run
  `python -m pytest worlds/voidling_bound/test test/general`.
- Mod: `pip install lupa`, then `python mod/tests/test_mod.py` runs the Lua mod against stubbed UE4SS functions.
- Import tools: `python tools/test_import_genes.py` and `python tools/test_import_variants.py`.
