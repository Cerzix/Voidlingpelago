-- Grants the items that aren't plain resources: species eggs, golden eggs and DNA Catalyzers.
--
-- Eggs go through the game's cheat manager, UVWCheatManager:AddEgg(EEggType EggType, FString ClassName, int Count).
-- Neither the enum values nor the expected class name format are known up front, so the enum is read at runtime
-- by name and the class name is found by trying candidates from the species data asset, checking
-- ResourcesInventory:EggCount before and after. The format that works is remembered.
--
-- Catalyzers: UDNACatalyzerDefinition:GetRandomCatalyzer(...) picks one, and since a catalyzer definition is a
-- UResourceDataAsset it's stored like any other resource.

local tracker = require("tracker")

local M = {}
local log = function() end
local working_candidate = nil -- index into the candidate list that added an egg last time
local egg_types = nil

function M.init(logger)
    log = logger
end

local function inventory()
    local ok, inv = pcall(function() return tracker.instance("PlayerProgression").ResourcesInventory end)
    if ok and inv and inv:IsValid() then return inv end
    error("the resources inventory isn't loaded")
end

local function cheat_manager()
    local cheats = tracker.instance("VWCheatManager")
    if not cheats then error("the cheat manager isn't available, is UE4SS's CheatManagerEnablerMod enabled?") end
    return cheats
end

local function egg_count(inv)
    for _, call in ipairs({ function() return inv:EggCount(true) end, function() return inv:EggCount() end }) do
        local ok, count = pcall(call)
        if ok and type(count) == "number" then return count end
    end
    return nil
end

-- EEggType names to values, e.g. { ["EEggType::Golden"] = 1 }.
local function read_egg_types()
    if egg_types then return egg_types end
    local enum = StaticFindObject("/Script/VoidlingWrangler.EEggType")
    if not enum or not enum:IsValid() then return nil end
    local types = {}
    local ok = pcall(function()
        enum:ForEachName(function(name, value) types[name:ToString()] = value end)
    end)
    if not ok or next(types) == nil then
        for value = 0, 8 do
            local found, name = pcall(function() return enum:GetNameByValue(value):ToString() end)
            if found and name and name ~= "" and name ~= "None" then types[name] = value end
        end
    end
    if next(types) == nil then return nil end
    egg_types = types
    local names = {}
    for name, value in pairs(types) do names[#names + 1] = name .. "=" .. value end
    log("EEggType: " .. table.concat(names, ", "))
    return types
end

-- For the F8 state dump.
function M.egg_types()
    return read_egg_types()
end

-- The value of the first egg type whose name contains one of the words, or the lowest value.
function M.egg_type(words)
    local types = read_egg_types()
    if not types then return 0 end
    local lowest = nil
    for name, value in pairs(types) do
        local lower = name:lower()
        for _, word in ipairs(words) do
            if lower:find(word, 1, true) then return value end
        end
        if not lower:find("max", 1, true) and (lowest == nil or value < lowest) then lowest = value end
    end
    return lowest or 0
end

local function species_assets()
    local ok, assets = pcall(FindAllOf, "SpeciesDataAsset")
    if not ok or not assets then return {} end
    local list = {}
    for _, asset in ipairs(assets) do
        if not tracker.name_of(asset):find("^Default__") then list[#list + 1] = asset end
    end
    return list
end

local function species_name(asset)
    local ok, name = pcall(function() return asset.SpeciesName:ToString() end)
    return ok and name or ""
end

local function find_species(wanted)
    local normalized = wanted:lower():gsub("[^%w]", "")
    for _, asset in ipairs(species_assets()) do
        if species_name(asset):lower():gsub("[^%w]", "") == normalized then return asset end
    end
    return nil
end

-- Possible ClassName strings for AddEgg, from most to least likely.
local function class_name_candidates(asset)
    local candidates = { species_name(asset), tracker.name_of(asset) }
    local ok, class_path = pcall(function() return asset.CreatureClass:ToString() end)
    if ok and type(class_path) == "string" then
        local class = class_path:match("%.([^%.]+)$") -- "/Game/X/BP_Kwipeck.BP_Kwipeck_C" -> "BP_Kwipeck_C"
        if class then
            candidates[#candidates + 1] = class
            candidates[#candidates + 1] = (class:gsub("_C$", ""))
        end
    end
    return candidates
end

-- Adds one egg of the species (or a random species when nil) and egg type. Returns true if an egg was added.
local function add_egg(species, type_words)
    local inv = inventory()
    local cheats = cheat_manager()
    local egg_type = M.egg_type(type_words)
    if species == nil then
        local all = species_assets()
        if #all == 0 then return false end
        species = all[math.random(#all)]
    end
    local candidates = class_name_candidates(species)
    local order = {}
    if working_candidate and candidates[working_candidate] then order[1] = working_candidate end
    for index = 1, #candidates do
        if index ~= working_candidate then order[#order + 1] = index end
    end
    for _, index in ipairs(order) do
        local before = egg_count(inv)
        local ok = pcall(function() cheats:AddEgg(egg_type, candidates[index], 1) end)
        local after = egg_count(inv)
        if ok and before and after and after > before then
            if working_candidate ~= index then
                log("AddEgg works with class names like \"" .. candidates[index] .. "\"")
                working_candidate = index
            end
            return true
        end
    end
    return false
end

function M.give_species_egg(species_display_name)
    local species = find_species(species_display_name)
    if species and add_egg(species, { "normal", "common", "regular", "standard", "default" }) then return end
    log("Couldn't add a " .. species_display_name .. " egg, giving a random egg instead")
    cheat_manager():AddRandomEgg(1)
end

function M.give_golden_egg()
    if add_egg(nil, { "golden", "gold" }) then return end
    log("Couldn't add a golden egg, giving a random egg instead")
    cheat_manager():AddRandomEgg(1)
end

function M.give_random_egg()
    cheat_manager():AddRandomEgg(1)
end

-- Returns true if a catalyzer was stored.
function M.give_catalyzer()
    local inv = inventory()
    local cdo = StaticFindObject("/Script/VoidlingWrangler.Default__DNACatalyzerDefinition")
    local context = tracker.instance("PlayerController")
    if not cdo or not cdo:IsValid() or not context then error("catalyzer data isn't loaded") end
    -- WorldContext, Quality (-1 = any), MinQuality, MaxQuality, bTryToGiveNew
    local ok, catalyzer = pcall(function() return cdo:GetRandomCatalyzer(context, -1, 0, 3, true) end)
    if ok and catalyzer and type(catalyzer) ~= "number" then
        local definition = catalyzer
        local has_definition, inner = pcall(function() return catalyzer.Definition end)
        if has_definition and inner then definition = inner end
        local stored = pcall(function() inv:StoreResource(definition, 1) end)
        if stored then
            log("Stored catalyzer " .. tracker.name_of(definition))
            return true
        end
    end
    log("Couldn't create a DNA Catalyzer (" .. tostring(catalyzer) .. "), skipped")
    return false
end

return M
