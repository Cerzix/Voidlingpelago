# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [2.0.0] - 2026-10-16

### Changed
- **Breaking:** the placeholder missions are replaced by the game's real 27 missions from the Voidling Bound wiki,
  across Vireo (10), Solum (8), Aulis (7 plus End to the Unknown) and the Abyss (Operation: Void Strike).
  Location IDs changed, so seeds generated with 1.0.0 can't be played with this version
- **Breaking:** the four sectors are replaced by the three real planets. Planet Access: Solum and
  Planet Access: Aulis replace the Sector 2-4 items, and the Abyss is entered from Aulis
- The campaign goal is now End to the Unknown
- Golden egg and bonus mutagen checks only exist for the 9 missions that have those objectives (18 checks)
- Mutagen filler is split into the real types (Organic, Pyro, Cryo, Cyber, Plasma), with Polychrome Mutagen as
  a useful item

### Added
- One egg item for each of the eight known Voidling species
- Location groups per planet
- Discovery tools in the mod: F6 dumps relevant game classes with their functions and properties, and F7 traces
  which of those functions fire. They exist to find the game hooks
- `config.lua` for the mod, with an optional F9 key that sends a test check
- Lua mod tests against stubbed UE4SS functions, run in CI

### Fixed
- The client no longer crashes when the mod reports a bonus objective for a mission that has none
- The mod builds the exchange folder path with the platform's separator, which fixes the Linux CI tests

### Known limitations
- The in-game hooks in `game_hooks.lua` are still stubs: missions, ranks, Abyss depth, planet gating, resource
  rewards and DeathLink kills aren't connected to the game yet. Use the F6/F7 discovery tools to find them
- What you can test in game: the mod loading, the client connection, the discovery dumps, and with
  `debug_events = true` in `config.lua` the F9 test check that travels all the way to the server

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

[2.0.0]: https://github.com/Cerzix/Voidlingpelago/releases/tag/v2.0.0
[1.0.0]: https://github.com/Cerzix/Voidlingpelago/releases/tag/v1.0.0
