-- Locks missions on planets the player hasn't received access to yet.
--
-- Every UActivityDataAsset has a WranglerLevelRequirement, which the mission select checks
-- (UActivityDataAsset:AreRequirementsMet). Locked missions get LOCK_LEVEL as requirement, the original value
-- comes back once the planet's item arrives. Only the loaded data assets in memory are changed, nothing is saved.
--
-- Which mission belongs to which region comes from the apworld (slot data "mission_regions"), so the game
-- follows the same logic as the generator: Solum needs Planet Access: Solum, Aulis also needs Planet Access:
-- Aulis, and the Abyss needs both plus Abyss Access. Activities that aren't locations (tutorials, demo-only
-- missions) are left alone, except Abyss activities, which also need Abyss Access.

local tracker = require("tracker")

local M = {}

M.LOCK_LEVEL = 99
local REFRESH_SECONDS = 5

local access = { Solum = false, Aulis = false, Abyss = false }
local mission_regions = {} -- normalized mission name -> region
local original_requirement = {} -- asset path -> requirement before we locked it
local last_refresh = -math.huge
local log = function() end

-- Same normalization as the client: lowercase letters and digits only.
function M.normalize(name)
    return (name:lower():gsub("[^%w]", ""))
end

function M.init(logger)
    log = logger
end

-- "Faint Signal=Vireo|Search and Rescue=Solum|..." from slot.txt
local mission_regions_source = nil

function M.set_mission_regions(value)
    if value == mission_regions_source then return end -- slot.txt is read every poll
    mission_regions_source = value
    last_refresh = -math.huge
    mission_regions = {}
    for entry in (value or ""):gmatch("[^|]+") do
        local name, region = entry:match("^(.-)=(.*)$")
        if name then mission_regions[M.normalize(name)] = region end
    end
end

function M.set_access(key, value)
    if access[key] ~= value then
        access[key] = value
        last_refresh = -math.huge -- apply right away
    end
end

-- A new session (seed or slot) starts without any access, the items are applied again after this.
function M.reset_access()
    for key in pairs(access) do M.set_access(key, false) end
end

function M.region_open(region)
    if region == "Solum" then return access.Solum end
    if region == "Aulis" then return access.Solum and access.Aulis end
    if region == "The Abyss" then return access.Solum and access.Aulis and access.Abyss end
    return true -- Vireo and anything unknown
end

local function is_abyss_activity(asset)
    local ok, type_name = pcall(function() return tracker.name_of(asset.Type) end)
    return ok and type_name:lower():find("abyss", 1, true) ~= nil
end

-- The region an activity belongs to, or nil if it isn't gated.
function M.region_of(asset)
    local region = mission_regions[M.normalize(tracker.activity_name(asset))]
    if region then return region end
    if is_abyss_activity(asset) then return "The Abyss" end
    return nil
end

local function path_of(asset)
    local ok, path = pcall(function() return asset:GetFullName() end)
    return ok and path or tostring(asset)
end

local function apply_to(asset)
    local region = M.region_of(asset)
    if not region then return end
    local path = path_of(asset)
    if not M.region_open(region) then
        local ok, requirement = pcall(function() return asset.WranglerLevelRequirement end)
        if not ok or type(requirement) ~= "number" then return end
        -- A reloaded asset has its original value again, so compare with the current value.
        if requirement ~= M.LOCK_LEVEL then
            if original_requirement[path] == nil then
                log("Locked " .. tracker.activity_name(asset) .. " (" .. region .. ")")
            end
            original_requirement[path] = requirement
            asset.WranglerLevelRequirement = M.LOCK_LEVEL
        end
    elseif original_requirement[path] ~= nil then
        asset.WranglerLevelRequirement = original_requirement[path]
        original_requirement[path] = nil
        log("Unlocked " .. tracker.activity_name(asset) .. " (" .. region .. ")")
    end
end

-- Called every poll, re-applies to all loaded activities every REFRESH_SECONDS or after an access change.
-- Data assets can be unloaded and reloaded, which resets them, so this keeps going.
function M.poll()
    if next(mission_regions) == nil then return end -- not connected yet
    if os.time() - last_refresh < REFRESH_SECONDS then return end
    last_refresh = os.time()
    local ok, assets = pcall(FindAllOf, "ActivityDataAsset")
    if not ok or not assets then return end
    for _, asset in ipairs(assets) do
        if not tracker.name_of(asset):find("^Default__") then
            local applied, err = pcall(apply_to, asset)
            if not applied then log("Gating failed for " .. path_of(asset) .. ": " .. tostring(err)) end
        end
    end
end

return M
