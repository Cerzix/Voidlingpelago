# Voidling Bound Setup Guide

## Required software

- [Voidling Bound](https://store.steampowered.com/search/?term=Voidling%20Bound) (Steam)
- [Archipelago](https://github.com/ArchipelagoMW/Archipelago/releases) 0.6.4 or newer
- [UE4SS](https://github.com/UE4SS-RE/RE-UE4SS/releases/tag/experimental-latest), the **experimental** build
  (`UE4SS_v3.0.1-…zip`, not the `zDEV-` one). The regular 3.0.1 release is too old for the game's Unreal Engine 5.7
- `voidling_bound.apworld` and `Voidlingpelago.zip` from the
  [latest release](https://github.com/Cerzix/Voidlingpelago/releases/latest)

## Installation

1. Double click `voidling_bound.apworld`, or copy it to `Archipelago/custom_worlds/`.
2. In Steam, right click Voidling Bound, Manage, Browse local files. Open `VoidlingWrangler/Binaries/Win64/`, the
   folder with `VoidlingWrangler-Win64-Shipping.exe`, and extract UE4SS there. You should now have a `dwmapi.dll`
   and a `ue4ss` folder next to the exe.
3. Extract `Voidlingpelago.zip` into `VoidlingWrangler/Binaries/Win64/ue4ss/Mods/`, so you end up with
   `ue4ss/Mods/Voidlingpelago/Scripts/main.lua`.
4. Leave UE4SS's own `CheatManagerEnablerMod` enabled (it is by default). The mod uses the game's cheat manager to
   give you eggs and DNA Catalyzers and for DeathLink.
5. Start the game once and check `ue4ss/UE4SS.log` for the line `[Voidlingpelago] Loaded`.

## Your YAML

Besides the usual settings, Voidling Bound has these options:

- `goal`: `campaign` (beat End to the Unknown) or `abyss_depth` (reach `abyss_goal_depth` in the Abyss)
- `bonus_objectives`: checks for collecting all golden eggs and all bonus mutagens in a mission
- `wrangler_rank_checks`: how many Wrangler rank-ups send a check
- `abyss_goal_depth`, `abyss_check_interval`: Abyss depth checks
- `gene_checks` (off by default): every gene you unlock is a check, up to 1,042. These checks only ever hold
  filler, so a gene that won't hatch never blocks anyone. `gene_types` picks which kinds count
- `death_link`

## Playing

1. Open the Archipelago Launcher, start the **Voidling Bound Client** and connect to the room.
2. Start Voidling Bound and load a **fresh save** for every new multiworld. Progress already on a save is sent as
   checks right away.
3. The client and the mod talk through `%APPDATA%\Voidlingpelago\`, nothing else to set up.

## What to expect in game

- Missions on Solum, Aulis and in the Abyss stay locked until you receive their Planet Access or Abyss Access item.
  A locked mission shows a **Wrangler level requirement of 99**, the real requirement comes back with the item.
- Completing missions, earning their golden egg and mutagen stars, ranking up, reaching new Abyss depths and, with
  `gene_checks`, unlocking genes all send checks.
- Received research points and mutagens go straight into your inventory, eggs into your egg storage, DNA
  Catalyzers into your catalyzers.
- With DeathLink, failing a mission sends a death, and a received death kills your active Voidling.
