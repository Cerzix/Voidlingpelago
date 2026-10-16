-- Everything that touches Voidling Bound itself lives here.
-- The game has no published SDK. Use the discovery tools (discovery.lua, F6 scan / F7 trace) to find the
-- class and function behind each TODO below, then replace the TODO with a RegisterHook call.
--
-- Candidates from the reflection names in VoidlingWrangler-Win64-Shipping.exe (module /Script/VoidlingWrangler),
-- which class owns each function still needs a scan to confirm:
--   missions:  AActivity / ACleanseActivity / ASurvivalActivity, UActivitySubsystem, UActivityDataAsset,
--              CompleteActivity, FinishActivity, ConfirmActivitySuccess, GetCurrentActivity, MissionComplete,
--              bIsMainMission, StarObjectiveTexts, IsStarUnlocked, CollectibleClassesForObjective
--   ranks:     GetWranglerLevel, WranglerLevelChanged (delegate)
--   abyss:     UAbyssSubsystem, AbyssDepthCompleted, OnAbyssLevelFinished, GetAbyssLevel, IsInsideAbyss
--   planets:   AGalacticMapManager, GalacticMapTravel, GetAllPlanets, GetCurrentPlanet, OnPlanetChanged
--   rewards:   GiveMutagen, GiveResearchPoint, GiveRewards, AddEgg, AddRandomEgg, HatchEgg, GetRandomCatalyzer
--   failure:   Defeat

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

-- Vireo is always open, the mission select hook should block missions on planets that aren't unlocked.
local unlocked = { Vireo = true, Solum = false, Aulis = false }
local abyss_unlocked = false

-- The client accepts mission names with spaces replaced by underscores, e.g. "Centennial_Bloom".
-- Use it to translate whatever the game calls a mission into the AP name, or map the game's own IDs in
-- Client.py MISSION_KEYS and pass them through unchanged.
function M.mission_key(mission_name)
    return (mission_name:gsub(" ", "_"))
end

function M.init(event_api, logger)
    events, log = event_api, logger

    -- TODO: mission completion. Trace finishing a mission and hook the function that fires, e.g.
    -- RegisterHook("<path from trace.txt>", function(context, ...)
    --     local key = ...  -- the mission's ID or display name, read from the context or a parameter
    --     events.mission_complete(key)
    --     if all golden eggs were collected  then events.golden_eggs(key) end
    --     if all bonus mutagens were found   then events.bonus_mutagens(key) end
    -- end)
    -- Missions with collectibles show them as star objectives, so the star state is likely what to read.

    -- TODO: Wrangler rank. Hook the rank-up function and call events.wrangler_rank(newRank).

    -- TODO: Abyss. Hook "Dive Deeper" (or entering the next Abyss level) and call events.abyss_depth(depth).

    -- TODO: player death, only matters with DeathLink. Call events.death() when the run fails.

    -- TODO: planet gating. Hook planet / mission selection and refuse planets where unlocked[planet] is false,
    -- and the Abyss while abyss_unlocked is false. Show a message telling the player what's missing.
end

function M.set_slot_data(data)
    slot_data = data
end

-- Return false while items can't be granted, e.g. in the main menu or a loading screen.
function M.can_receive_items()
    -- TODO: e.g. check that the player's save/profile object exists
    return true
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
-- Raise an error (error("...")) if it can't be granted right now, it will be retried.
function M.apply_item(id, name)
    if M.is_unlock(id) then return end
    -- TODO: grant resources through the player's inventory / save game object. Trace picking up a mutagen,
    -- hatching an egg and finishing a mission to see which functions add research points, mutagens and eggs.
    log("No game handler yet for " .. name .. " (" .. id .. ")")
end

function M.kill_player()
    -- TODO: kill or down the player's Voidling.
    log("DeathLink received, but killing the player isn't implemented yet")
end

return M
