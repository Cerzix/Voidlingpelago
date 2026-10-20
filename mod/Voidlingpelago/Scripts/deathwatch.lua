-- Notices when the player's creature dies, for DeathLink.
--
-- The creature the player controls is PlayerController.Pawn. Its UDamageableAbilitySystemComponent says whether it's
-- alive (IsAlive), so every poll compares that with the last poll. When the game swaps to the next creature right
-- after a death, the previous creature's component is checked too, so that death isn't missed.
--
-- Hooks on UActivitySubsystem:OnPlayerCreatureDeath and TriggerActivityFailure report deaths as well, in case they
-- fire. UE4SS only sees native functions called through Unreal's reflection, which is why polling is the main source.
-- All sources go through report(), which sends at most one death per COOLDOWN_SECONDS and none right after a
-- received DeathLink killed the creature.

local tracker = require("tracker")

local M = {}

local COOLDOWN_SECONDS = 10
local ASC_CLASS_PATH = "/Script/VoidlingWrangler.DamageableAbilitySystemComponent"
local HOOKS = {
    "/Script/VoidlingWrangler.ActivitySubsystem:OnPlayerCreatureDeath",
    "/Script/VoidlingWrangler.ActivitySubsystem:TriggerActivityFailure",
}

local events, log
local quiet_until = 0 -- no deaths are sent before this time
local watched = nil -- { pawn = name, asc = component, alive = bool }
local asc_class = nil

local function valid(obj)
    if obj == nil then return false end
    local ok, result = pcall(function() return obj:IsValid() end)
    return ok and result == true
end

local function report(source)
    local now = os.time()
    if now < quiet_until then return end
    quiet_until = now + COOLDOWN_SECONDS
    log("Death detected (" .. source .. "), sending DeathLink")
    events.death()
end

-- A received DeathLink kills the creature, that death must not go back out.
function M.ignore_for(seconds)
    quiet_until = math.max(quiet_until, os.time() + seconds)
end

local function creature_component(pawn)
    if not valid(asc_class) then
        asc_class = StaticFindObject(ASC_CLASS_PATH)
        if not valid(asc_class) then return nil end
    end
    local ok, asc = pcall(function() return pawn:GetComponentByClass(asc_class) end)
    if ok and valid(asc) then return asc end
    return nil
end

local function is_alive(asc)
    if not valid(asc) then return nil end
    local ok, alive = pcall(function() return asc:IsAlive() end)
    if ok and type(alive) == "boolean" then return alive end
    return nil
end

function M.init(event_api, logger)
    events, log = event_api, logger
    for _, path in ipairs(HOOKS) do
        local ok = pcall(RegisterHook, path, function(context, tag, count)
            -- OnPlayerCreatureDeath gets a tag count, which drops to 0 when the death tag goes away again.
            if count ~= nil then
                local got, value = pcall(function() return count:get() end)
                if got and type(value) == "number" and value <= 0 then return end
            end
            report(path:match(":(.+)$"))
        end)
        if not ok then log("Could not hook " .. path) end
    end
end

-- Called every poll on the game thread.
function M.poll()
    local controller = tracker.instance("PlayerController")
    local pawn = controller and select(2, pcall(function() return controller.Pawn end))
    if not valid(pawn) then
        -- No creature right now (loading, menus): if the watched one died meanwhile, that's still a death.
        if watched and watched.alive and is_alive(watched.asc) == false then report("creature died") end
        watched = nil
        return
    end

    local name = tracker.name_of(pawn)
    if not watched or watched.pawn ~= name then
        -- Another creature: the previous one may have died right before the swap.
        if watched and watched.alive and is_alive(watched.asc) == false then report("creature died") end
        local asc = creature_component(pawn)
        watched = { pawn = name, asc = asc, alive = is_alive(asc) }
        return
    end

    local alive = is_alive(watched.asc)
    if alive == nil then
        watched.asc = creature_component(pawn)
        return
    end
    if watched.alive == true and alive == false then report("creature died") end
    watched.alive = alive
end

return M
