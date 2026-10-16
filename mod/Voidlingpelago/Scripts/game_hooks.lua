-- Everything that touches Voidling Bound itself lives here.
-- None of the class or function names are known yet. To find them:
--   1. Install UE4SS, enable the console and GuiConsole in UE4SS-settings.ini.
--   2. Play a mission, then use the Live View tab to search for things like "Mission", "Objective",
--      "Abyss", "Wrangler", "Egg", "Mutagen", "Catalyzer", "ResearchPoints".
--   3. Dump the SDK with Ctrl+H (CXX header dump) or the Lua type dump to read the real function names.
-- Each TODO below says what we need to hook or call.

local M = {}
local events, log
local slot_data = {}

-- Item IDs, must match apworld/voidling_bound/Items.py
local ITEMS = {
    SECTOR_2 = 840001, SECTOR_3 = 840002, SECTOR_4 = 840003, ABYSS = 840004,
    CATALYZERS = 840010, GOLDEN_EGG = 840012, ABILITY_POINTS = 840013,
    RESEARCH_POINTS = 840020, MUTAGENS = 840021, EGG = 840023,
}

-- Unlocked access is kept here, the mission select hook blocks anything that isn't unlocked.
local unlocked = { [1] = true }
local abyss_unlocked = false

function M.init(event_api, logger)
    events, log = event_api, logger

    -- TODO: mission completion. Hook the function that runs when a mission is won, e.g.
    -- RegisterHook("/Script/VoidlingBound.MissionManager:OnMissionCompleted", function(self, ...)
    --     local key = self:get():GetMissionId():ToString()   -- whatever identifies the level
    --     events.mission_complete(key)
    --     if all golden eggs collected  then events.golden_eggs(key) end
    --     if all bonus mutagens collected then events.bonus_mutagens(key) end
    -- end)
    -- Until the real keys are mapped in Client.py MISSION_KEYS, report the AP mission name with spaces
    -- replaced by underscores, e.g. events.mission_complete("W01:_Crashsite_Survival").

    -- TODO: Wrangler rank. Hook the rank-up function and call events.wrangler_rank(newRank).

    -- TODO: Abyss. Hook the "level cleared" or "dive deeper" step and call events.abyss_depth(depth).

    -- TODO: player death, only matters when DeathLink is on. Call events.death() when the whole team falls.

    -- TODO: planet gating. Hook planet / mission selection and refuse sectors where unlocked[n] is nil,
    -- and the Abyss while abyss_unlocked is false. Show a message telling the player what's missing.
end

function M.set_slot_data(data)
    slot_data = data
end

-- Return false while items can't be granted, e.g. in the main menu or a loading screen.
function M.can_receive_items()
    -- TODO: e.g. return FindFirstOf("VoidlingPlayerController"):IsValid()
    return true
end

function M.is_unlock(id)
    return id >= ITEMS.SECTOR_2 and id <= ITEMS.ABYSS
end

-- Called for every unlock item on every poll, must be idempotent.
function M.apply_unlock(id)
    if id == ITEMS.SECTOR_2 then unlocked[2] = true
    elseif id == ITEMS.SECTOR_3 then unlocked[3] = true
    elseif id == ITEMS.SECTOR_4 then unlocked[4] = true
    elseif id == ITEMS.ABYSS then abyss_unlocked = true
    end
end

-- Grant one item, called exactly once per received item.
-- Raise an error (error("...")) if it can't be granted right now, it will be retried.
function M.apply_item(id, name)
    if M.is_unlock(id) then return end
    -- TODO: grant resources through the player's inventory / save game object:
    -- Catalyzers, Golden Egg, Ability Points, Research Points (500), Mutagen Pack, Voidling Egg.
    log("No game handler yet for " .. name .. " (" .. id .. ")")
end

function M.kill_player()
    -- TODO: kill or down the player's Voidling.
    log("DeathLink received, but killing the player isn't implemented yet")
end

return M
