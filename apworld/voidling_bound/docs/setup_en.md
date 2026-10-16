# Voidling Bound Setup Guide

## Required software

- [Voidling Bound](https://store.steampowered.com/search/?term=Voidling%20Bound) (Steam or Epic)
- [Archipelago](https://github.com/ArchipelagoMW/Archipelago/releases) 0.6.4 or newer
- [UE4SS](https://github.com/UE4SS-RE/RE-UE4SS/releases) (the experimental build if the release doesn't load)
- `voidling_bound.apworld` and the `Voidlingpelago` mod folder from this project

## Installation

1. Double click `voidling_bound.apworld`, or copy it to `Archipelago/custom_worlds/`.
2. Extract UE4SS into `<game folder>/<project name>/Binaries/Win64/`, next to the game's `-Win64-Shipping.exe`.
3. Copy the `Voidlingpelago` folder into `Binaries/Win64/ue4ss/Mods/` (older UE4SS builds: `Binaries/Win64/Mods/`).
4. Start the game once and check `UE4SS.log` for the line `[Voidlingpelago] Loaded`.

## Playing

1. Open the Archipelago Launcher, start the **Voidling Bound Client** and connect to the room.
2. Start Voidling Bound. The client and the mod talk through `%APPDATA%\Voidlingpelago\`.
3. Use a fresh save for every new multiworld.
