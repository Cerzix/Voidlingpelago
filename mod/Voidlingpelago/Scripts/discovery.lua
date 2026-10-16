-- Developer tools to find what game_hooks.lua has to hook, since Voidling Bound ships without an SDK.
--
-- Scan (F6): lists every loaded game class whose name matches KEYWORDS, with its functions and properties,
--            plus the current map, game mode, game state, player controller and pawn -> discovery.txt
-- Trace (F7): hooks every function of those classes and logs each call with its object and parameters
--            -> trace.txt. Press F7 again to stop.
--
-- Workflow: start a mission, press F6, press F7, do the thing you want to hook (finish the mission, pick up a
-- golden egg, rank up, dive deeper in the Abyss, die), press F7 again. The function that fired at that moment is
-- the one to hook. Classes only show up once they are loaded, so scan inside the situation you care about.

local M = {}

local KEYWORDS = {
    "Mission", "Objective", "Abyss", "Wrangler", "Rank", "Egg", "Mutagen", "Research", "Catalyzer", "Reward",
    "Quest", "Planet", "Voidling", "Lesion", "Cleans", "Survival", "Star", "Collect", "Unlock", "Progress",
    "Save", "Inventory", "Currency", "Hatch", "Death", "Revive", "Health",
}

-- Engine and plugin modules, their classes are never what we're looking for.
local ENGINE_MODULES = {
    "Engine", "CoreUObject", "UMG", "Slate", "SlateCore", "Niagara", "NiagaraCore", "AIModule", "GameplayTasks",
    "NavigationSystem", "Chaos", "ChaosSolverEngine", "MovieScene", "MovieSceneTracks", "LevelSequence",
    "Landscape", "Foliage", "PhysicsCore", "AudioMixer", "MetasoundEngine", "MetasoundFrontend", "EnhancedInput",
    "CommonUI", "CommonInput", "InputCore", "MediaAssets", "Paper2D", "GameplayAbilities", "GameplayTags",
    "DeveloperSettings", "AnimGraphRuntime", "Renderer", "NetCore", "OnlineSubsystem", "OnlineSubsystemUtils",
    "Water", "GeometryCollectionEngine", "ClothingSystemRuntimeInterface", "AudioExtensions", "Synthesis",
    "SignificanceManager", "ModelViewViewModel", "StateTreeModule", "GameplayStateTreeModule", "MassEntity",
}

-- Called constantly by UI bindings, animation or every frame, they would drown the trace.
local NOISY_FUNCTION = { "^Get", "^Is", "^Has", "^Can", "Tick", "^ExecuteUbergraph", "Anim", "^OnRep_Mesh" }
local MAX_LOGGED_CALLS = 25

local out_dir, log
local trace_file = nil
local hooks = {}
local call_counts = {}

local engine_prefixes = {}
for _, module in ipairs(ENGINE_MODULES) do
    engine_prefixes[#engine_prefixes + 1] = "/Script/" .. module .. "."
end

local function safe(fn, fallback)
    local ok, value = pcall(fn)
    if ok and value ~= nil then return value end
    return fallback
end

-- "BlueprintGeneratedClass /Game/A/BP_B.BP_B_C" -> "/Game/A/BP_B.BP_B_C"
local function object_path(obj)
    local full = safe(function() return obj:GetFullName() end, "?")
    return full:match("^%S+ (.+)$") or full
end

local function short_name(obj)
    return safe(function() return obj:GetFName():ToString() end, "?")
end

local function is_game_class(path)
    if path:sub(1, 6) == "/Game/" then return true end
    if path:sub(1, 8) ~= "/Script/" then return false end
    for _, prefix in ipairs(engine_prefixes) do
        if path:sub(1, #prefix) == prefix then return false end
    end
    return true
end

local function matches_keyword(name)
    for _, keyword in ipairs(KEYWORDS) do
        if name:find(keyword, 1, true) then return true end
    end
    return false
end

local function is_noisy(function_name)
    for _, pattern in ipairs(NOISY_FUNCTION) do
        if function_name:find(pattern) then return true end
    end
    return false
end

local function find_game_classes()
    local classes = {}
    ForEachUObject(function(obj)
        if safe(function() return obj:IsClass() end, false) then
            local path = object_path(obj)
            if is_game_class(path) and matches_keyword(short_name(obj)) then
                classes[#classes + 1] = { class = obj, path = path }
            end
        end
    end)
    table.sort(classes, function(a, b) return a.path < b.path end)
    return classes
end

-- Scan ---------------------------------------------------------------------------------------------

local function describe_context(lines)
    local function class_of(short_class_name)
        local obj = FindFirstOf(short_class_name)
        if not obj or not obj:IsValid() then return "not found" end
        return object_path(obj:GetClass()) .. "   (" .. object_path(obj) .. ")"
    end
    lines[#lines + 1] = "Map:              " .. safe(function()
        return object_path(FindFirstOf("PlayerController"):GetWorld())
    end, "unknown")
    lines[#lines + 1] = "GameMode:         " .. safe(function() return class_of("GameModeBase") end, "?")
    lines[#lines + 1] = "GameState:        " .. safe(function() return class_of("GameStateBase") end, "?")
    lines[#lines + 1] = "PlayerController: " .. safe(function() return class_of("PlayerController") end, "?")
    lines[#lines + 1] = "PlayerState:      " .. safe(function() return class_of("PlayerState") end, "?")
    lines[#lines + 1] = "Pawn:             " .. safe(function()
        return object_path(FindFirstOf("PlayerController").Pawn:GetClass())
    end, "?")
    lines[#lines + 1] = "SaveGame:         " .. safe(function() return class_of("SaveGame") end, "?")
    lines[#lines + 1] = ""
end

function M.scan()
    local lines = { "Voidlingpelago discovery scan, " .. os.date("%Y-%m-%d %H:%M:%S"), "" }
    describe_context(lines)
    local classes = find_game_classes()
    for _, entry in ipairs(classes) do
        local super = safe(function() return object_path(entry.class:GetSuperStruct()) end, "-")
        lines[#lines + 1] = "== " .. entry.path .. "   extends " .. super
        safe(function()
            entry.class:ForEachFunction(function(fn)
                lines[#lines + 1] = "   fn   " .. short_name(fn)
            end)
        end)
        safe(function()
            entry.class:ForEachProperty(function(prop)
                local kind = safe(function() return prop:GetClass():GetFName():ToString() end, "?")
                lines[#lines + 1] = "   prop " .. short_name(prop) .. " : " .. kind
            end)
        end)
    end
    local f = io.open(out_dir .. "discovery.txt", "w")
    if not f then
        log("Could not write discovery.txt")
        return
    end
    f:write(table.concat(lines, "\n") .. "\n")
    f:close()
    log("Discovery scan: " .. #classes .. " classes written to " .. out_dir .. "discovery.txt")
end

-- Trace --------------------------------------------------------------------------------------------

local function trace_line(text)
    if not trace_file then return end
    trace_file:write(string.format("[%10.3f] %s\n", os.clock(), text))
    trace_file:flush()
end

local function describe_param(param)
    local value = safe(function() return param:get() end, nil)
    if value == nil then return "?" end
    local kind = type(value)
    if kind == "number" or kind == "boolean" or kind == "string" then return tostring(value) end
    -- FString, FName and FText all have ToString, objects have GetFullName.
    return safe(function() return value:ToString() end, nil)
        or safe(function() return object_path(value) end, nil)
        or kind
end

local function on_call(function_path)
    return function(context, ...)
        local count = (call_counts[function_path] or 0) + 1
        call_counts[function_path] = count
        if count > MAX_LOGGED_CALLS then return end
        local params = {}
        for i, param in ipairs({ ... }) do params[i] = describe_param(param) end
        local self_path = safe(function() return object_path(context:get()) end, "?")
        trace_line(function_path .. "  self=" .. self_path .. "  args=(" .. table.concat(params, ", ") .. ")"
            .. (count == MAX_LOGGED_CALLS and "  [further calls not logged]" or ""))
    end
end

local function start_trace()
    trace_file = io.open(out_dir .. "trace.txt", "w")
    if not trace_file then
        log("Could not write trace.txt")
        return
    end
    call_counts = {}
    local hooked = 0
    for _, entry in ipairs(find_game_classes()) do
        safe(function()
            entry.class:ForEachFunction(function(fn)
                local name = short_name(fn)
                if not is_noisy(name) then
                    local path = object_path(fn)
                    local ok, pre_id, post_id = pcall(RegisterHook, path, on_call(path))
                    if ok then
                        hooks[#hooks + 1] = { path = path, pre = pre_id, post = post_id }
                        hooked = hooked + 1
                    end
                end
            end)
        end)
    end
    trace_line("Trace started, " .. hooked .. " functions hooked")
    log("Trace started, " .. hooked .. " functions hooked, writing " .. out_dir .. "trace.txt")
end

local function stop_trace()
    for _, hook in ipairs(hooks) do
        pcall(UnregisterHook, hook.path, hook.pre, hook.post)
    end
    hooks = {}
    trace_line("Trace stopped")
    local summary = {}
    for path, count in pairs(call_counts) do summary[#summary + 1] = { path = path, count = count } end
    table.sort(summary, function(a, b) return a.count > b.count end)
    trace_line("Call counts:")
    for _, entry in ipairs(summary) do trace_line(string.format("%8d  %s", entry.count, entry.path)) end
    trace_file:close()
    trace_file = nil
    log("Trace stopped")
end

function M.toggle_trace()
    if trace_file then stop_trace() else start_trace() end
end

function M.on_map_loaded(world)
    local path = safe(function() return object_path(world) end, "?")
    log("Map loaded: " .. path)
    trace_line("Map loaded: " .. path)
end

function M.init(config, exchange_dir, logger)
    out_dir, log = exchange_dir, logger
    RegisterKeyBind(config.scan_key, function() ExecuteInGameThread(M.scan) end)
    RegisterKeyBind(config.trace_key, function() ExecuteInGameThread(M.toggle_trace) end)
    log("Discovery tools enabled: F6 scan, F7 trace")
end

return M
