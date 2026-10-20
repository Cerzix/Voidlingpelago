# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [2.4.0] - 2026-10-18

### Added
- Variant checks: every Voidling variant you unlock (hatching or evolving) is a check. The list comes from the full
  game: 294 variants, 32 to 34 per species, each species' evolution tree plus its unique golden egg variants.
  Variants are the game's evolutions, which it unlocks like genes, so the mod reports them with `IsDataUnlocked`.
  Like genes they only hold filler and are in logic once their species' eggs can drop
- The developer tools' F5 also writes `variants.txt` with the game's creature names, and
  `tools/import_variants.py` turns it into `data/variants.json` with stable IDs from 847001
- Pre-releases include the developer tools (`discovery.lua`) for testers

### Fixed
- DeathLink never sent a death: the mod only hooked the mission failing, and UE4SS doesn't see that native call. It
  now watches the creature the player controls (`PlayerController.Pawn`) and asks its ability system component
  `IsAlive()` every poll, also catching a death right before the game swaps to the next creature. One death is sent
  at most every 10 seconds, and the death a received DeathLink causes is never sent back

### Changed
- **Breaking for YAMLs:** the `gene_checks` toggle is replaced by `collection_checks`, which picks the collection
  that sends checks: `variants` (default, 294 checks), `genes` (1,042 checks, as `gene_checks` did) or `off`. `gene_types` still picks the gene kinds

## [2.3.1] - 2026-10-17

### Fixed
- Received research points and mutagens never arrived. Resources were looked up by their in-game name, but
  research points are called "Collectable Plant" in game, so they were never found, and an item that couldn't be
  granted was retried forever, which held up every item received after it. Resources are now looked up by their
  asset name (e.g. `DA_Resource_Mutagen_Cryo`), and items stuck since 2.3.0 are granted after updating
- The mod checks that a received resource shows up in the inventory the HUD shows. If it only landed in the
  activity storage, it's moved over, and the result is logged either way
- An item that still can't be granted after 30 seconds is skipped (and logged), so it can't hold up the items
  received after it

 - 2026-10-17

### Added
- Gene checks: every gene you unlock sends a check (option `gene_checks`, off by default). The list comes from the
  full game: 1,042 collectible genes across all nine species (294 Color, 186 Eye, 179 Module, 159 Perk,
  150 Ability Variant, 74 Pattern). `gene_types` picks which kinds count
- A gene is in logic once its species' eggs can drop: Kwipeck, Kerapin, Gilick and Gwigoon on Vireo,
  Nimiod, Anami and Ur-Sek on Solum, Morfang on Aulis (from the wiki's mission rewards). Packuran, the ninth species
  the wiki doesn't name, counts as Aulis
- Gene checks only ever hold filler, never progression or useful items: many genes come from random hatches,
  so a stubborn last gene can't block or hold back anyone
- F5 gene dump in the mod (`genes.txt`): every gene, module and perk via the Asset Registry, plus loaded ones,
  with name, type, species and whether it can be collected
- `tools/import_genes.py` turns the dump into `apworld/voidling_bound/data/genes.json`. Existing genes keep their
  ID, new ones are appended, genes the game marks as not collectible are skipped, curly quotes are straightened
- The mod reports unlocked genes with `ProgressionSubsystem:IsDataUnlocked` on the loaded gene assets. The F8
  state dump shows how many are loaded and unlocked

### Removed
- The debug keys (F5 gene dump, F6 scan, F7 trace, F8 state dump, F9 test check) and `config.lua` are no longer
  part of the released mod. They live in `mod/devtools/discovery.lua` for development, see the README

### Changed
- The setup guide covers the install paths, the YAML options and what to expect in game
- Releases include a player options template, `Voidling Bound.yaml`

### Fixed
- Crash when pressing F5 or F8: the mod's poll ran on its own thread (`LoopAsync`) while the dumps ran on the game
  thread, and UE4SS's Lua isn't thread safe. Everything now runs on the game thread
  (`LoopInGameThreadWithDelay`, with `LoopAsync` as fallback for older UE4SS builds)
- Fewer errors inside UE4SS: the F8 dump reads values by their known type instead of probing them, the
  unreadable `UnlockedDataAssets` set isn't probed anymore, and the working `GetWranglerLevel` call is remembered.
  Each such error went through the UE4SS error handler that crashed
- "Save the Cauldrons" was named "Save the Cauldron" (as on the wiki), so it sent no check. Its ID is unchanged
- F5 crashed the full game every time (beta 2): the dump called gene functions on objects that weren't genes,
  such as the ability variant Blueprints in the gene folders, which crashes inside the game where Lua can't catch
  it. The dump now only takes the game's gene name patterns and checks every object's class first. Cached game
  objects (genes, resources, activities) are checked for validity before use, and F5 logs its progress to
  UE4SS.log

## [2.2.0] - 2026-10-17

### Added
- Planet gating: missions on Solum, Aulis and in the Abyss stay locked until their Planet Access / Abyss
  Access items arrive. Locked missions show a Wrangler level requirement of 99 in the mission select; the
  real requirement comes back with the item. Only the loaded game data is changed, never the save. Which
  mission belongs to which planet comes from the apworld (slot data `mission_regions`), so the game follows the
  generator's logic
- Species eggs give an egg of that species and Golden Egg gives a golden egg (`UVWCheatManager:AddEgg`). The
  egg type is read from the game's `EEggType` enum and the class name format is found by checking the egg count,
  with a random egg as fallback
- DNA Catalyzer Bundle gives a random catalyzer (`UDNACatalyzerDefinition:GetRandomCatalyzer`)
- New useful item Research Points (1500)
- The F8 state dump lists species assets and the egg types

### Changed
- Ability Points are removed, the game has no such resource: ability upgrades are bought with research points.
  Research Points (1500) takes their place in the item pool

### Fixed
- Planet unlocks from a previous seed carried over when connecting to another seed without restarting the game

## [2.1.0] - 2026-10-16

The first version that does something in game. Class and function names come from the discovery scans
and the UE4SS type dump of the demo.

### Added
- The mod detects progress by reading the game's own state instead of hooks (`tracker.lua`), so nothing is
  missed while the client is closed and progress made before connecting is sent on connect:
  - completed missions from `ProgressionSubsystem.ActivitiesTimeCompletion`, by their in-game name
  - golden egg and bonus mutagen checks from the missions' star objectives (`IsStarUnlocked`). The star order
    (1 = mutagens, 2 = golden eggs) is taken from the wiki and still needs confirming in game
  - Wrangler rank from `GetWranglerLevel` and Abyss depth from `AbyssSubsystem`
- Received research points and mutagens (Organic, Pyro, Cryo, Cyber, Plasma, Polychrome) are added to the
  inventory with `ResourcesInventory:StoreResource`
- Received Voidling eggs are added with the game's cheat manager (`AddRandomEgg`). Species eggs are random
  eggs for now
- DeathLink: a failed mission sends a death, a received death kills the player's creature
  (`KillPlayerCreature`). Needs UE4SS's bundled CheatManagerEnablerMod, which is on by default
- The client matches mission names and activity asset names (e.g. `DA_Activity_CentennialBloom`) to missions.
  Activities that aren't locations are logged once and ignored
- F8 state dump (`state.txt`): progression, completed missions with their star states, unlocked data assets,
  collected actors, resources, and every loaded activity, planet, resource and quest asset
- The F6 scan lists function parameters

### Fixed
- The client never stored the seed name, so every multiworld used the session "None" and a new seed could
  skip items that an older seed had already applied

### Known limitations
- Planets and the Abyss aren't locked yet, so Planet Access items have no effect in game
- Golden eggs, species eggs, DNA Catalyzers and ability points can't be granted yet and are skipped
- Items that can't be granted are skipped instead of holding up the queue

## [2.0.1] - 2026-10-16

### Fixed
- The discovery tools now find the classes that matter. The game calls missions "Activities" internally
  (AActivity, ACleanseActivity, ASurvivalActivity, UActivitySubsystem), and the old keywords missed them, the
  galactic map (planet select), corruption, hatchery, breeding, shop and the VW game mode and controller

### Added
- `game_hooks.lua` lists the hook candidates found in the game's reflection data for each TODO

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

[2.4.0]: https://github.com/Cerzix/Voidlingpelago/releases/tag/v2.4.0-beta.2
[2.3.1]: https://github.com/Cerzix/Voidlingpelago/releases/tag/v2.3.1
[2.3.0]: https://github.com/Cerzix/Voidlingpelago/releases/tag/v2.3.0-beta.1
[2.2.0]: https://github.com/Cerzix/Voidlingpelago/releases/tag/v2.2.0
[2.1.0]: https://github.com/Cerzix/Voidlingpelago/releases/tag/v2.1.0
[2.0.1]: https://github.com/Cerzix/Voidlingpelago/releases/tag/v2.0.1
[2.0.0]: https://github.com/Cerzix/Voidlingpelago/releases/tag/v2.0.0
[1.0.0]: https://github.com/Cerzix/Voidlingpelago/releases/tag/v1.0.0
