-- Everything that touches Voidling Bound itself lives here. Class and function names come from the UE4SS type
-- dump of the game module (/Script/VoidlingWrangler) and the discovery scans of the demo.
--
--   progress     tracker.lua reads missions, stars, Wrangler rank and Abyss depth from the game's state
--   resources    UResourcesInventory:StoreResource(UResourceDataAsset, Quantity)
--   eggs         UVWCheatManager:AddRandomEgg(Count), enabled by UE4SS's bundled CheatManagerEnablerMod
--   DeathLink    UActivitySubsystem:TriggerActivityFailure() out, UVWCheatManager:KillPlayerCreature() in
--
-- Still open: planet gating (GalacticMapManager / QuestSubsystem:SetPlanetToTravel), golden and species eggs
-- (UVWCheatManager:AddEgg(EEggType, ClassName, Count) needs the enum values and class names), Catalyzers and
-- ability points.

local tracker = require("tracker")

local M = {}
local events, log
local slot_data = {}

-- Item IDs, must match apworld/voidling_bound/Items.py
local ITEMS = {
    SOLUM = 840001, AULIS = 840002, ABYSS = 840004,
    CATALYZERS = 840010, GOLDEN_EGG = 840012, ABILITY_POINTS = 840013, POLYCHROME = 840014,
    RESEARCH_POINTS = 840020, EGG = 840023,
    ORGANIC = 840030, PYRO = 840031, CRYO = 840032, CYBER = 840033, PLASMA = 840034,
    -- Species eggs: 840040 Kwipeck, 840041 Kerapin, 840042 Gilick, 840043 Gwigoon,
    --               840044 Nimiod, 840045 Anami, 840046 Ur-Sek, 840047 Morfang
}

-- Resource items: every word must appear in the resource's in-game ResourceName.
local RESOURCE_ITEMS = {
    [ITEMS.RESEARCH_POINTS] = { words = { "research" }, amount = 500 },
    [ITEMS.ORGANIC] = { words = { "organic", "mutagen" }, amount = 3 },
    [ITEMS.PYRO] = { words = { "pyro", "mutagen" }, amount = 3 },
    [ITEMS.CRYO] = { words = { "cryo", "mutagen" }, amount = 3 },
    [ITEMS.CYBER] = { words = { "cyber", "mutagen" }, amount = 3 },
    [ITEMS.PLASMA] = { words = { "plasma", "mutagen" }, amount = 3 },
    [ITEMS.POLYCHROME] = { words = { "polychrome" }, amount = 1 },
}

local FAILURE_FUNCTION = "/Script/VoidlingWrangler.ActivitySubsystem:TriggerActivityFailure"

-- Vireo is always open, the mission select hook should block missions on planets that aren't unlocked.
local unlocked = { Vireo = true, Solum = false, Aulis = false }
local abyss_unlocked = false
-- A DeathLink we apply fails the mission, which must not be sent back out as our own death.
local ignore_failure_until = 0

-- Turns a mission name into an event key, used by the F9 debug key.
function M.mission_key(mission_name)
    return (mission_name:gsub(" ", "_"))
end

function M.init(event_api, logger)
    events, log = event_api, logger

    local ok, err = pcall(RegisterHook, FAILURE_FUNCTION, function()
        if os.time() >= ignore_failure_until then events.death() end
    end)
    if not ok then log("Could not hook mission failure, DeathLink won't send: " .. tostring(err)) end

    -- TODO: planet gating. Quests unlock planets through ProgressionSubsystem:UnlockData(PlanetDataAsset); block
    -- travel to planets where unlocked[planet] is false (GalacticMapManager / QuestSubsystem:SetPlanetToTravel),
    -- and the Abyss while abyss_unlocked is false.
end

-- Called every poll on the game thread.
function M.poll()
    tracker.poll(events)
end

function M.set_slot_data(data)
    slot_data = data
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

local resource_assets = { list = nil, searched = -math.huge }

local function find_resource(words)
    if not resource_assets.list or os.time() - resource_assets.searched > 10 then
        local ok, assets = pcall(FindAllOf, "ResourceDataAsset")
        resource_assets = { list = (ok and assets) or {}, searched = os.time() }
    end
    for _, asset in ipairs(resource_assets.list) do
        local ok, name = pcall(function() return asset.ResourceName:ToString():lower() end)
        if ok then
            local matches = true
            for _, word in ipairs(words) do
                if not name:find(word, 1, true) then matches = false end
            end
            if matches then return asset end
        end
    end
    return nil
end

local function cheat_manager()
    local cheats = tracker.instance("VWCheatManager")
    if not cheats then error("the cheat manager isn't available, is UE4SS's CheatManagerEnablerMod enabled?") end
    return cheats
end

function M.is_unlock(id)
    return id == ITEMS.SOLUM or id == ITEMS.AULIS or id == ITEMS.ABYSS
end

-- Called for every unlock item on every poll, must be idempotent.
function M.apply_unlock(id)
    if id == ITEMS.SOLUM then unlocked.Solum = true
    elseif id == ITEMS.AULIS then unlocked.Aulis = true
    elseif id == ITEMS.ABYSS then abyss_unlocked = true
    end
end

-- Grant one item, called exactly once per received item.
-- Raise an error if it can't be granted right now, it will be retried. Items the mod can't grant yet are
-- logged and skipped, so they don't hold up the items after them.
function M.apply_item(id, name)
    if M.is_unlock(id) then return end

    local resource = RESOURCE_ITEMS[id]
    if resource then
        local asset = find_resource(resource.words)
        if not asset then error("resource for " .. name .. " isn't loaded yet") end
        resources_inventory():StoreResource(asset, resource.amount)
        return
    end

    if id == ITEMS.EGG or (id >= 840040 and id <= 840047) then
        -- Species eggs are random eggs until the AddEgg class names are known.
        cheat_manager():AddRandomEgg(1)
        return
    end

    log("Can't grant " .. name .. " (" .. id .. ") in game yet, skipped")
end

function M.kill_player()
    ignore_failure_until = os.time() + 10
    cheat_manager():KillPlayerCreature()
end

return M
