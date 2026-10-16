# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-10-16

### Added
- Voidling Bound apworld for Archipelago 0.6.4+
  - Progression items: Planet Access for Sectors 2-4 and Abyss Access
  - Useful items (DNA Catalyzer Bundle, Golden Egg, Ability Points) and weighted filler (Research Points,
    Mutagen Pack, Voidling Egg)
  - Checks for mission completion, all golden eggs / all bonus mutagens per mission, Wrangler rank-ups and Abyss
    depth milestones
  - Options: goal (campaign or Abyss depth), Abyss goal depth and check interval, bonus objectives,
    Wrangler rank checks, DeathLink
  - Item and location name groups
  - Game info page and English setup guide
  - Logic tests
- Voidling Bound Client, launchable from the Archipelago Launcher, with archipelago:// URI support. It exchanges
  events, items, slot data and DeathLinks with the game mod through text files in `%APPDATA%\Voidlingpelago`
- UE4SS Lua mod with the client protocol, received items that are applied exactly once across restarts,
  rebuilt planet unlocks and DeathLink handling
- `build_release.py` to build `voidling_bound.apworld` and `Voidlingpelago.zip`
- GitHub Actions workflow that tests every push and publishes a GitHub release for `v*` tags

### Known limitations
- Mission names are placeholders until the real ones are read from the game (`TODO-verify` in `Locations.py`)
- The in-game hooks in `game_hooks.lua` are stubs: missions, ranks, Abyss depth, planet gating, resource
  rewards and DeathLink kills aren't connected to the game yet, so the mod doesn't send or apply anything in game

[1.0.0]: https://github.com/Cerzix/Voidlingpelago/releases/tag/v1.0.0
