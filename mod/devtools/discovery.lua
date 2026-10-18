-- Developer tools, not part of the released mod. To use them, copy this file into the mod's Scripts folder
-- (ue4ss/Mods/Voidlingpelago/Scripts/), main.lua loads it when it's there. Output goes to %APPDATA%\Voidlingpelago.
--
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

-- The game calls missions "Activities" internally (AActivity, ACleanseActivity, ASurvivalActivity,
-- UActivitySubsystem), and the planet select is the AGalacticMapManager. Names found in the game's exe.
local KEYWORDS = {
    "Activity", "Mission", "Objective", "Abyss", "Wrangler", "Rank", "Egg", "Mutagen", "Research", "Catalyzer",
    "Reward", "Quest", "Planet", "Galactic", "Voidling", "Lesion", "Corruption", "Cleans", "Survival", "Star",
    "Collect", "Unlock", "Progress", "Save", "Inventory", "Currency", "Resource", "Shop", "Hatch", "Breeding",
    "GameFlow", "Creature", "Squad", "Defeat", "Death", "Revive", "Health", "VW",
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
                local params = {}
                safe(function()
                    fn:ForEachProperty(function(param)
                        local kind = safe(function() return param:GetClass():GetFName():ToString() end, "?")
                        params[#params + 1] = short_name(param) .. ": " .. kind
                    end)
                end)
                lines[#lines + 1] = "   fn   " .. short_name(fn) .. "(" .. table.concat(params, ", ") .. ")"
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

-- State dump ---------------------------------------------------------------------------------------
-- F8: what the game currently knows about the player's progress, to map assets to AP missions and items.

local DATA_ASSET_CLASSES = {
    "ActivityDataAsset", "ActivityTypeDataAsset", "PlanetDataAsset", "ResourceDataAsset", "QuestDataAsset",
    "SpeciesDataAsset",
}

-- Values are only read in ways their type supports. Calling a method a UE4SS value doesn't have (say :ToString() on
-- an array) throws an error, and UE4SS's error handler has crashed the game on such errors, even inside pcall.
local READERS = {
    plain = function(value) return tostring(value) end,
    object = function(value) return object_path(value) end,
    text = function(value) return value:ToString() end, -- FString, FName, FText
}

local function describe_value(value, kind)
    local lua_type = type(value)
    if lua_type == "nil" then return "nil" end
    if lua_type == "number" or lua_type == "boolean" or lua_type == "string" then return tostring(value) end
    local reader = READERS[kind or "object"]
    if not reader then return "<" .. kind .. ">" end
    return safe(function() return reader(value) end, "?")
end

-- kinds: how to read keys (and values for maps), "count" only counts the entries.
local function dump_container(lines, label, container, key_kind, value_kind)
    local entries, count = {}, 0
    local ok = pcall(function()
        container:ForEach(function(a, b)
            count = count + 1
            if key_kind ~= "count" then
                local key = describe_value(safe(function() return a:get() end, a), key_kind)
                if b ~= nil and value_kind then
                    key = key .. " = " .. describe_value(safe(function() return b:get() end, b), value_kind)
                end
                entries[#entries + 1] = key
            end
        end)
    end)
    if not ok then
        lines[#lines + 1] = "  " .. label .. ": <not iterable with this UE4SS build>"
        return
    end
    lines[#lines + 1] = "  " .. label .. ": " .. count .. " entries"
    for _, entry in ipairs(entries) do lines[#lines + 1] = "    " .. entry end
end

-- Property type -> how to read it. Containers and structs are only named, not read.
local PROPERTY_KINDS = {
    BoolProperty = "plain", IntProperty = "plain", Int64Property = "plain", FloatProperty = "plain",
    DoubleProperty = "plain", ByteProperty = "plain", EnumProperty = "plain", UInt32Property = "plain",
    StrProperty = "text", NameProperty = "text", TextProperty = "text",
    ObjectProperty = "object", ClassProperty = "object",
}

-- Simple property values of an object, so data assets show their display names, planets, rewards, ...
local function dump_properties(lines, obj)
    safe(function()
        obj:GetClass():ForEachProperty(function(prop)
            local name = short_name(prop)
            local prop_type = safe(function() return prop:GetClass():GetFName():ToString() end, "?")
            local kind = PROPERTY_KINDS[prop_type]
            local shown
            if kind then
                shown = describe_value(safe(function() return obj[name] end, nil), kind)
            else
                shown = "<" .. prop_type .. ">"
            end
            lines[#lines + 1] = "      " .. name .. " = " .. shown
        end)
    end)
end

function M.dump_state()
    local tracker = require("tracker")
    local lines = { "Voidlingpelago state dump, " .. os.date("%Y-%m-%d %H:%M:%S"), "" }

    local progression = tracker.progression()
    lines[#lines + 1] = "ProgressionSubsystem: " .. (progression and object_path(progression) or "not found")
    if progression then
        lines[#lines + 1] = "  WranglerLevel: " .. tostring(tracker.wrangler_level(progression))
        local done, source = tracker.completed_activities(progression)
        local names = {}
        for _, activity in ipairs(done) do names[#names + 1] = activity.name end
        lines[#lines + 1] = "  Completed activities (via " .. source .. "): " .. table.concat(names, ", ")
        local genes = tracker.unlocked_genes(progression)
        lines[#lines + 1] = "  Loaded gene assets: " .. #tracker.gene_assets() .. ", unlocked: " .. #genes .. "  "
            .. table.concat(genes, ", ")
        dump_container(lines, "ActivitiesTimeCompletion", progression.ActivitiesTimeCompletion, "object", "plain")
        dump_container(lines, "UnlockedDataAssets", progression.UnlockedDataAssets, "count")
        dump_container(lines, "CollectedActors", progression.CollectedActors, "count")
        dump_container(lines, "ProgressionVariablesCounter", progression.ProgressionVariablesCounter, "text", "plain")
    end
    lines[#lines + 1] = "Abyss depth: " .. tostring(tracker.abyss_depth())
    local egg_types = safe(function() return require("rewards").egg_types() end, nil)
    local type_names = {}
    for name, value in pairs(egg_types or {}) do type_names[#type_names + 1] = name .. "=" .. value end
    lines[#lines + 1] = "EEggType: " .. (#type_names > 0 and table.concat(type_names, ", ") or "not readable")
    lines[#lines + 1] = ""

    local inventory = safe(function() return FindFirstOf("PlayerProgression").ResourcesInventory end, nil)
    lines[#lines + 1] = "ResourcesInventory: " .. (inventory and object_path(inventory) or "not found")
    if inventory then
        dump_container(lines, "CollectedResources", inventory.CollectedResources, "object", "plain")
        dump_container(lines, "Eggs", inventory.Eggs, "count")
    end
    lines[#lines + 1] = ""

    for _, class_name in ipairs(DATA_ASSET_CLASSES) do
        local objects = safe(function() return FindAllOf(class_name) end, {}) or {}
        lines[#lines + 1] = "== " .. class_name .. ": " .. #objects .. " loaded"
        for _, obj in ipairs(objects) do
            local status = {}
            if progression then
                status[#status + 1] = "unlocked=" .. describe_value(safe(function()
                    return progression:IsDataUnlocked(obj)
                end, nil))
                if class_name == "ActivityDataAsset" then
                    status[#status + 1] = "name=\"" .. tracker.activity_name(obj) .. "\""
                    status[#status + 1] = "time=" .. describe_value(safe(function()
                        return progression:GetActivityTimeCompletion(obj)
                    end, nil))
                    local stars = {}
                    for star = 0, 3 do stars[#stars + 1] = describe_value(tracker.is_star_unlocked(obj, star)) end
                    status[#status + 1] = "stars[0-3]=" .. table.concat(stars, "/")
                end
            end
            if class_name == "ResourceDataAsset" then
                status[#status + 1] = "name=\"" .. describe_value(safe(function()
                    return obj.ResourceName:ToString()
                end, nil)) .. "\""
            end
            lines[#lines + 1] = "   " .. object_path(obj) .. "   " .. table.concat(status, " ")
            dump_properties(lines, obj)
        end
    end

    local f = io.open(out_dir .. "state.txt", "w")
    if not f then
        log("Could not write state.txt")
        return
    end
    f:write(table.concat(lines, "\n") .. "\n")
    f:close()
    log("State dump written to " .. out_dir .. "state.txt")
end

-- Gene dump ----------------------------------------------------------------------------------------
-- F5: every gene in the game, for tools/import_genes.py. The Asset Registry knows all assets, also the ones
-- that aren't loaded; genes that are only found there get loaded to read their name. Loaded genes are added
-- too, in case the Asset Registry can't be queried from Lua.

local CREATURES_PATH = "/Game/Data/Creatures"

local function registry_assets()
    local found = {}
    local ok, err = pcall(function()
        local helpers = StaticFindObject("/Script/AssetRegistry.Default__AssetRegistryHelpers")
        local registry = helpers:GetAssetRegistry()
        local out = {}
        registry:GetAssetsByPath(FName(CREATURES_PATH), out, true, false)
        for _, data in pairs(out) do
            local asset = safe(function() return data:get() end, data)
            local package = asset.PackageName:ToString()
            local name = asset.AssetName:ToString()
            found[#found + 1] = package .. "." .. name
        end
    end)
    if not ok then log("Asset Registry query failed: " .. tostring(err)) end
    return found
end

-- Data assets in a species' Genes, Perk or Perks folder: colors, eyes, patterns, ability variants, modules, perks.
-- Textures and materials live there too, which is why only "DA_" assets count and the dump checks the gene name.
-- Only the asset name patterns the game uses for genes: DA_Gene_*, DA_Perk_* and DA_<species>_<tier>Module_NN.
-- Other DA_ assets live in those folders too (e.g. the DA_AV_* ability variant Blueprints), and calling gene
-- functions on them crashed the game.
local function is_gene_path(path, name)
    if not (path:find("/Genes/", 1, true) or path:find("/Perks?/")) then return false end
    return name:find("^DA_Gene_") ~= nil or name:find("^DA_Perk_") ~= nil or name:find("^DA_.*Module_%d+$") ~= nil
end

-- Game functions must only be called on real gene instances: a class, a default object or an object of another
-- type makes the game read garbage, which crashes natively and can't be caught.
local GENE_CLASS_PATH = "/Script/VoidlingWrangler.GeneDataAsset"

local function is_gene_object(obj)
    if not obj or not safe(function() return obj:IsValid() end, false) then return false end
    if safe(function() return obj:IsClass() end, true) then return false end
    if short_name(obj):find("^Default__") then return false end
    return safe(function() return obj:IsA(GENE_CLASS_PATH) end, false) == true
end

local function species_code(path)
    return path:match(CREATURES_PATH .. "/([^/]+)/") or ""
end

local function load_object(path)
    local obj = StaticFindObject(path)
    if obj and obj:IsValid() then return obj end
    pcall(LoadAsset, path)
    obj = StaticFindObject(path)
    if obj and obj:IsValid() then return obj end
    return nil
end

-- Variants: the game's evolutions (UEvolutionDataAsset), written to variants.txt for tools/import_variants.py.
local EVOLUTION_CLASS_PATH = "/Script/VoidlingWrangler.EvolutionDataAsset"
local SPECIES_CLASS_PATH = "/Script/VoidlingWrangler.SpeciesDataAsset"

local function is_object_of(obj, class_path)
    if not obj or not safe(function() return obj:IsValid() end, false) then return false end
    if safe(function() return obj:IsClass() end, true) then return false end
    if short_name(obj):find("^Default__") then return false end
    return safe(function() return obj:IsA(class_path) end, false) == true
end

local function text_of(value)
    if type(value) == "string" then return value end
    return safe(function() return value:ToString() end, "")
end

local function dump_variants(registry)
    local variants = {} -- path -> object or false (not loaded yet)
    local from_registry = 0
    for _, path in ipairs(registry) do
        local name = path:match("([^%.]+)$")
        if path:find("/Evolutions/", 1, true) and name:find("^DA_Evolution_") then
            variants[path] = false
            from_registry = from_registry + 1
        end
    end
    for _, obj in ipairs(safe(function() return FindAllOf("EvolutionDataAsset") end, {}) or {}) do
        if is_object_of(obj, EVOLUTION_CLASS_PATH) then variants[object_path(obj)] = obj end
    end

    local paths = {}
    for path in pairs(variants) do paths[#paths + 1] = path end
    table.sort(paths)
    log("Variant dump: reading " .. #paths .. " variants (" .. from_registry .. " from the Asset Registry)")
    local lines = { "# Voidlingpelago variant dump, " .. os.date("%Y-%m-%d %H:%M:%S"),
        "# asset path\tevolution name\tcreature name\tspecies code\tspecies name\trarity\tcost" }
    local written = 0
    for _, path in ipairs(paths) do
        local obj = variants[path] or load_object(path)
        if is_object_of(obj, EVOLUTION_CLASS_PATH) then
            local evolution_name = safe(function() return obj.EvolutionName:ToString() end, "")
            local species = safe(function() return obj.ParentSpecies end, nil)
            local species_name, creature_name = "", ""
            if is_object_of(species, SPECIES_CLASS_PATH) then
                species_name = safe(function() return species.SpeciesName:ToString() end, "")
                creature_name = text_of(safe(function() return species:GetCreatureName(obj) end, ""))
            end
            local rarity = safe(function() return obj.Rarity end, "")
            local cost = safe(function() return obj.Cost end, "")
            lines[#lines + 1] = table.concat({ path, evolution_name, creature_name, species_code(path), species_name,
                tostring(rarity), tostring(cost) }, "\t")
            written = written + 1
        end
    end
    local f = io.open(out_dir .. "variants.txt", "w")
    if not f then
        log("Could not write variants.txt")
        return
    end
    f:write(table.concat(lines, "\n") .. "\n")
    f:close()
    log("Variant dump: " .. written .. " variants in " .. out_dir .. "variants.txt")
end

function M.dump_genes()
    local tracker = require("tracker")
    log("Gene dump started")
    local genes = {} -- path -> object or false (not loadable)
    local species_names = {} -- species code -> display name

    local registry = registry_assets()
    local from_registry = 0
    for _, path in ipairs(registry) do
        local name = path:match("([^%.]+)$")
        if is_gene_path(path, name) then
            genes[path] = false
            from_registry = from_registry + 1
        elseif name:find("Species") then
            local species = load_object(path)
            local display = species and safe(function() return species.SpeciesName:ToString() end, nil)
            if display and display ~= "" then species_names[species_code(path)] = display end
        end
    end

    log("Gene dump: " .. from_registry .. " genes in the Asset Registry, now adding loaded genes")
    local from_loaded = 0
    for _, class_name in ipairs(tracker.GENE_CLASSES) do
        for _, obj in ipairs(safe(function() return FindAllOf(class_name) end, {}) or {}) do
            local path = object_path(obj)
            if not genes[path] and is_gene_object(obj) then
                if genes[path] == nil then from_loaded = from_loaded + 1 end
                genes[path] = obj
            end
        end
    end
    for _, obj in ipairs(safe(function() return FindAllOf("SpeciesDataAsset") end, {}) or {}) do
        local display = safe(function() return obj.SpeciesName:ToString() end, nil)
        local code = species_code(object_path(obj))
        if display and display ~= "" and code ~= "" then species_names[code] = display end
    end

    local lines = { "# Voidlingpelago gene dump, " .. os.date("%Y-%m-%d %H:%M:%S")
        .. ", Asset Registry: " .. from_registry .. ", only loaded: " .. from_loaded,
        "# asset path\tgene class\tgene name\tspecies code\tspecies name\tcollectible" }
    local paths = {}
    for path in pairs(genes) do paths[#paths + 1] = path end
    table.sort(paths)
    log("Gene dump: reading " .. #paths .. " genes")
    local unreadable, skipped = 0, 0
    for _, path in ipairs(paths) do
        local obj = genes[path] or load_object(path)
        local not_a_gene = obj ~= nil and not is_gene_object(obj)
        if not_a_gene then obj = nil end
        local class_name, gene_name, collectible = "", "", ""
        if obj then
            class_name = safe(function() return short_name(obj:GetClass()) end, "")
            gene_name = safe(function() return obj.GeneName:ToString() end, "")
            -- Genes that can't be collected would be impossible checks, the import skips them.
            local can_collect = safe(function() return obj:IsCollectible() end, nil)
            collectible = type(can_collect) == "boolean" and tostring(can_collect) or ""
        elseif not not_a_gene then
            unreadable = unreadable + 1
        end
        local code = species_code(path)
        -- A loaded asset without a gene name isn't a gene, just a data asset that lives in a Genes folder.
        if not not_a_gene and (not obj or gene_name ~= "") then
            lines[#lines + 1] = table.concat({ path, class_name, gene_name, code, species_names[code] or "", collectible }, "\t")
        else
            skipped = skipped + 1
        end
    end

    local f = io.open(out_dir .. "genes.txt", "w")
    if not f then
        log("Could not write genes.txt")
        return
    end
    f:write(table.concat(lines, "\n") .. "\n")
    f:close()
    log(string.format("Gene dump: %d genes (%d from the Asset Registry, %d only loaded, %d unreadable, %d not genes) in %sgenes.txt",
        #paths - skipped, from_registry, from_loaded, unreadable, skipped, out_dir))
    dump_variants(registry)
    -- Loading assets can let the garbage collector free objects the tracker still holds on to.
    tracker.reset()
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

-- F9 sends a "Faint Signal completed" event to test the client connection. It sends a real check to the
-- multiworld, so only use it in a test room.
function M.init(exchange_dir, logger, events)
    out_dir, log = exchange_dir, logger
    RegisterKeyBind(Key.F5, function() ExecuteInGameThread(M.dump_genes) end)
    RegisterKeyBind(Key.F6, function() ExecuteInGameThread(M.scan) end)
    RegisterKeyBind(Key.F7, function() ExecuteInGameThread(M.toggle_trace) end)
    RegisterKeyBind(Key.F8, function() ExecuteInGameThread(M.dump_state) end)
    RegisterKeyBind(Key.F9, function() events.mission_complete("Faint Signal") end)
    log("Developer tools loaded: F5 gene and variant dump, F6 scan, F7 trace, F8 state dump, F9 test check")
end

return M
