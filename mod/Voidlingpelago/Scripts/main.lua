-- Voidlingpelago: UE4SS Lua side of the Voidling Bound Archipelago integration.
-- Talks to the Voidling Bound Client (apworld/voidling_bound/Client.py) through text files, see the
-- protocol description at the top of Client.py. Everything game specific is in game_hooks.lua.

local hooks = require("game_hooks")

local SEP = package.config:sub(1, 1) -- "\" on Windows, "/" elsewhere (the CI tests run on Linux)
local EXCHANGE_DIR = (os.getenv("APPDATA") or ".") .. SEP .. "Voidlingpelago" .. SEP
local POLL_MS = 500

local function log(msg)
    print("[Voidlingpelago] " .. tostring(msg) .. "\n")
end

local function ensure_exchange_dir()
    local probe = io.open(EXCHANGE_DIR .. "probe.tmp", "w")
    if probe then
        probe:close()
        os.remove(EXCHANGE_DIR .. "probe.tmp")
        return
    end
    os.execute('mkdir "' .. EXCHANGE_DIR:sub(1, -2) .. '"')
end

local function read_lines(name)
    local f = io.open(EXCHANGE_DIR .. name, "r")
    if not f then return nil end
    local lines = {}
    for line in f:lines() do lines[#lines + 1] = line end
    f:close()
    return lines
end

local function write_text(name, text)
    local f = io.open(EXCHANGE_DIR .. name, "w")
    if not f then return false end
    f:write(text)
    f:close()
    return true
end

-- Events -------------------------------------------------------------------------------------------

local function send_event(event)
    local f = io.open(EXCHANGE_DIR .. "events.txt", "a")
    if not f then
        log("Could not write events.txt, is the client running? Event lost: " .. event)
        return
    end
    f:write(event .. "\n")
    f:close()
    log("Event: " .. event)
end

-- game_hooks.lua calls these when something check-worthy happens in game.
local events = {
    mission_complete = function(mission_key) send_event("mission_complete " .. mission_key) end,
    golden_eggs = function(mission_key) send_event("golden_eggs " .. mission_key) end,
    bonus_mutagens = function(mission_key) send_event("bonus_mutagens " .. mission_key) end,
    wrangler_rank = function(rank) send_event("wrangler_rank " .. math.floor(rank)) end,
    abyss_depth = function(depth) send_event("abyss_depth " .. math.floor(depth)) end,
    gene = function(asset_name) send_event("gene " .. asset_name) end,
    death = function() send_event("death") end,
}

-- Items --------------------------------------------------------------------------------------------
-- The client always writes the full item list. We remember how many we already applied per session
-- (seed + slot), so items are applied exactly once even across game and client restarts.

local session = nil
local applied = 0

local function applied_file()
    return "applied_" .. session:gsub("[^%w]", "_") .. ".txt"
end

local function load_applied()
    local lines = read_lines(applied_file())
    applied = (lines and tonumber(lines[1])) or 0
end

local function save_applied()
    write_text(applied_file(), tostring(applied))
end

local STUCK_SECONDS = 30
local stuck = nil -- { index, since } of an item that keeps failing

local function poll_items()
    local lines = read_lines("items.txt")
    if not lines or #lines == 0 then return end
    if lines[1] ~= session then
        session = lines[1]
        hooks.on_session_changed()
        load_applied()
        log("Session " .. session .. ", " .. applied .. " items already applied")
    end
    local can_receive = hooks.can_receive_items()
    for i = 2, #lines do
        local index, id, name = lines[i]:match("^(%d+) (%d+) (.*)$")
        index, id = tonumber(index), tonumber(id)
        -- Unlocks aren't stored in the save, so they're rebuilt from the full list every time.
        if id and hooks.is_unlock(id) then
            hooks.apply_unlock(id)
        end
        if index and index >= applied and can_receive then
            local ok, err = pcall(hooks.apply_item, id, name)
            if ok then
                applied = index + 1
                save_applied()
                stuck = nil
                log("Received " .. name)
            elseif not stuck or stuck.index ~= index then
                stuck = { index = index, since = os.time() }
                log("Applying " .. name .. " failed, will retry: " .. tostring(err))
                return
            elseif os.time() - stuck.since >= STUCK_SECONDS then
                -- One item that can't be granted must never hold up everything received after it.
                log("Skipped " .. name .. ", it still couldn't be applied after " .. STUCK_SECONDS .. " seconds: "
                    .. tostring(err))
                applied = index + 1
                save_applied()
                stuck = nil
            else
                return
            end
        end
    end
end

-- Slot data and DeathLink -------------------------------------------------------------------------

local function poll_slot_data()
    local lines = read_lines("slot.txt")
    if not lines then return end
    local slot_data = {}
    for _, line in ipairs(lines) do
        local key, value = line:match("^([^=]+)=(.*)$")
        if key then slot_data[key] = value end
    end
    hooks.set_slot_data(slot_data)
end

local function poll_deathlink()
    local lines = read_lines("deathlink.txt")
    if not lines then return end
    os.remove(EXCHANGE_DIR .. "deathlink.txt")
    log("DeathLink from " .. (lines[1] or "someone"))
    hooks.kill_player()
end

-- Main loop ----------------------------------------------------------------------------------------

ensure_exchange_dir()
hooks.init(events, log)

-- Developer tools (mod/devtools in the repository) only load when discovery.lua was copied next to this file.
local discovery = nil
if package.searchpath("discovery", package.path) then
    discovery = require("discovery")
    discovery.init(EXCHANGE_DIR, log, events)
end

RegisterLoadMapPostHook(function(engine, world)
    require("tracker").reset()
    if discovery then discovery.on_map_loaded(world:get()) end
end)

local function poll()
    local ok, err = pcall(function()
        poll_slot_data()
        poll_items()
        poll_deathlink()
        hooks.poll()
    end)
    if not ok then log("Poll error: " .. tostring(err)) end
end

-- All Lua must run on the game thread: UE4SS's Lua state isn't thread safe, and a LoopAsync thread running next
-- to a long developer tools dump on the game thread corrupted it and crashed the game. LoopInGameThreadWithDelay (UE4SS
-- 3.0.1 experimental and newer) runs the timer itself on the game thread, LoopAsync is the fallback for older builds.
if LoopInGameThreadWithDelay then
    LoopInGameThreadWithDelay(POLL_MS, poll)
else
    LoopAsync(POLL_MS, function()
        ExecuteInGameThread(poll)
        return false -- keep looping
    end)
end

log("Loaded, exchange folder: " .. EXCHANGE_DIR)
