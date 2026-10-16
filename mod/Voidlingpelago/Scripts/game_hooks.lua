-- Everything that touches Voidling Bound itself lives here. Class and function names come from the UE4SS type
-- dump of the game module (/Script/VoidlingWrangler) and the discovery scans of the demo.
--
--   progress     tracker.lua reads missions, stars, Wrangler rank and Abyss depth from the game's state
--   gating       gating.lua locks missions on planets that aren't unlocked yet
--   resources    UResourcesInventory:StoreResource(UResourceDataAsset, Quantity)
--   eggs, DNA    rewards.lua, through UVWCheatManager (enabled by UE4SS's bundled CheatManagerEnablerMod)
--   DeathLink    UActivitySubsystem:TriggerActivityFailure() out, UVWCheatManager:KillPlayerCreature() in

local tracker = require("tracker")
local gating = require("gating")
local rewards = require("rewards")

local M = {}
local events, log
local slot_data = {}

-- Item IDs, must match apworld/voidling_bound/Items.py
local ITEMS = {
    SOLUM = 840001, AULIS = 840002, ABYSS = 840004,
    CATALYZERS = 840010, GOLDEN_EGG = 840012, POLYCHROME = 840014, RESEARCH_POINTS_LARGE = 840015,
    RESEARCH_POINTS = 840020, EGG = 840023,
    ORGANIC = 840030, PYRO = 840031, CRYO = 840032, CYBER = 840033, PLASMA = 840034,
}

local SPECIES_EGGS = {
    [840040] = "Kwipeck", [840041] = "Kerapin", [840042] = "Gilick", [840043] = "Gwigoon",
    [840044] = "Nimiod", [840045] = "Anami", [840046] = "Ur-Sek", [840047] = "Morfang",
}

-- Resource items, by the game's asset name (the display names differ, research points are "Collectable Plant").
local RESOURCE_ITEMS = {
    [ITEMS.RESEARCH_POINTS] = { asset = "DA_Resource_ResearchPoint", amount = 500 },
    [ITEMS.RESEARCH_POINTS_LARGE] = { asset = "DA_Resource_ResearchPoint", amount = 1500 },
    [ITEMS.ORGANIC] = { asset = "DA_Resource_Mutagen_Organic", amount = 3 },
    [ITEMS.PYRO] = { asset = "DA_Resource_Mutagen_Pyro", amount = 3 },
    [ITEMS.CRYO] = { asset = "DA_Resource_Mutagen_Cryo", amount = 3 },
    [ITEMS.CYBER] = { asset = "DA_Resource_Mutagen_Cyber", amount = 3 },
    [ITEMS.PLASMA] = { asset = "DA_Resource_Mutagen_Plasma", amount = 3 },
    [ITEMS.POLYCHROME] = { asset = "DA_Resource_Mutagen_Polychrome", amount = 1 },
}

local FAILURE_FUNCTION = "/Script/VoidlingWrangler.ActivitySubsystem:TriggerActivityFailure"

-- A DeathLink we apply fails the mission, which must not be sent back out as our own death.
local ignore_failure_until = 0

function M.init(event_api, logger)
    events, log = event_api, logger

    local ok, err = pcall(RegisterHook, FAILURE_FUNCTION, function()
        if os.time() >= ignore_failure_until then events.death() end
    end)
    if not ok then log("Could not hook mission failure, DeathLink won't send: " .. tostring(err)) end

    gating.init(log)
    rewards.init(log)
end

-- Called every poll on the game thread.
function M.poll()
    tracker.poll(events)
    gating.poll()
end

function M.set_slot_data(data)
    slot_data = data
    gating.set_mission_regions(data.mission_regions)
end

local function resources_inventory()
    local ok, inventory = pcall(function() return tracker.instance("PlayerProgression").ResourcesInventory end)
    if ok and inventory and inventory:IsValid() then return inventory end
    return nil
end

-- Items are only granted in a loaded save, not in the main menu or while loading.
function M.can_receive_items()
    return tracker.progression() ~= nil and resources_inventory() ~= nil
end

local function cheat_manager()
    local cheats = tracker.instance("VWCheatManager")
    if not cheats then error("the cheat manager isn't available, is UE4SS's CheatManagerEnablerMod enabled?") end
    return cheats
end

-- Called when the item list belongs to another seed or slot than before.
function M.on_session_changed()
    gating.reset_access()
end

function M.is_unlock(id)
    return id == ITEMS.SOLUM or id == ITEMS.AULIS or id == ITEMS.ABYSS
end

-- Called for every unlock item on every poll, must be idempotent.
function M.apply_unlock(id)
    if id == ITEMS.SOLUM then gating.set_access("Solum", true)
    elseif id == ITEMS.AULIS then gating.set_access("Aulis", true)
    elseif id == ITEMS.ABYSS then gating.set_access("Abyss", true)
    end
end

-- Grant one item, called exactly once per received item.
-- Raise an error if it can't be granted right now, it will be retried. Items the mod can't grant yet are
-- logged and skipped, so they don't hold up the items after them.
function M.apply_item(id, name)
    if M.is_unlock(id) then return end

    local resource = RESOURCE_ITEMS[id]
    if resource then
        local asset = rewards.find_resource(resource.asset)
        if not asset then error(resource.asset .. " isn't loaded yet") end
        rewards.give_resource(asset, resource.amount)
        return
    end

    if SPECIES_EGGS[id] then
        rewards.give_species_egg(SPECIES_EGGS[id])
        return
    end
    if id == ITEMS.EGG then
        rewards.give_random_egg()
        return
    end
    if id == ITEMS.GOLDEN_EGG then
        rewards.give_golden_egg()
        return
    end
    if id == ITEMS.CATALYZERS then
        rewards.give_catalyzer()
        return
    end

    log("Can't grant " .. name .. " (" .. id .. ") in game yet, skipped")
end

function M.kill_player()
    ignore_failure_until = os.time() + 10
    cheat_manager():KillPlayerCreature()
end

return M
