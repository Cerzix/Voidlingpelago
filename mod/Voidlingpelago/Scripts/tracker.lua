-- Reads the game's own progress state and reports what changed, instead of hooking individual functions.
-- That way nothing is missed while the client is closed, and a restart simply reports the state again
-- (the client ignores locations that are already checked).
--
-- Sources (from the discovery scans and the UE4SS type dump of the demo):
--   ProgressionSubsystem.ActivitiesTimeCompletion   TMap<UActivityDataAsset, float>, completed missions
--   UActivityDataAsset.Name                         the mission's display name, e.g. "Centennial Bloom"
--   UActivityDataAsset:IsStarUnlocked(World, Index) star objectives, see STAR_* below
--   ProgressionSubsystem:GetWranglerLevel(out NextLevelRatio)
--   AbyssSubsystem:IsInsideAbyss() / GetAbyssLevel()

local M = {}

-- Star objective order as the wiki lists it: complete, find mutagens, find golden egg(s), finish in time.
-- Verify with the F8 state dump after a mission where only some stars were earned.
M.STAR_MUTAGENS = 1
M.STAR_GOLDEN_EGGS = 2

M.GENE_CLASSES = {
    "GeneDataAsset", "ColorGeneDataAsset", "EyeGeneDataAsset", "PatternGeneDataAsset", "SizeGeneDataAsset",
    "ElementGeneDataAsset", "PerkGeneDataAsset", "AbilityVariantGeneDataAsset", "CosmeticModuleDataAsset",
}
local GENE_POLL_SECONDS = 3
local GENE_LIST_SECONDS = 60

local reported_missions = {}
local reported_stars = {}
local reported_genes = {}
local last_gene_poll = -math.huge
local reported_rank = 0
local reported_depth = 0

local function valid(obj)
    if obj == nil then return false end
    local ok, result = pcall(function() return obj:IsValid() end)
    return ok and result
end

-- FindFirstOf can return the class default object, which has no real state.
local function find_instance(class_name)
    local ok, objects = pcall(FindAllOf, class_name)
    if not ok or not objects then return nil end
    for _, obj in ipairs(objects) do
        local name = M.name_of(obj)
        if valid(obj) and not name:find("^Default__") then return obj end
    end
    return nil
end

-- Short name of whatever the game hands us: an object, an FName, an FString or a plain value.
function M.name_of(value)
    if value == nil then return "nil" end
    local kind = type(value)
    if kind == "string" or kind == "number" or kind == "boolean" then return tostring(value) end
    for _, getter in ipairs({
        function() return value:GetFName():ToString() end,
        function() return value:ToString() end,
        function() return value:get():GetFName():ToString() end,
    }) do
        local ok, result = pcall(getter)
        if ok and type(result) == "string" and result ~= "" then return result end
    end
    return tostring(value)
end

-- FindAllOf walks every object, so instances are cached and only searched again once they become invalid
-- (map change, back to the main menu), and at most every RETRY_SECONDS.
local RETRY_SECONDS = 5
local cache = {}

local function cached_instance(class_name)
    local entry = cache[class_name]
    if entry and entry.object and valid(entry.object) then return entry.object end
    if entry and os.time() - entry.searched < RETRY_SECONDS then return nil end
    local object = find_instance(class_name)
    cache[class_name] = { object = object, searched = os.time() }
    return object
end

-- Forget cached instances, e.g. after a map load, so they are looked up again right away.
function M.reset()
    cache = {}
end

function M.instance(class_name)
    return cached_instance(class_name)
end

function M.progression()
    return cached_instance("ProgressionSubsystem")
end

function M.abyss()
    return cached_instance("AbyssSubsystem")
end

-- Display name of an activity asset, falling back to the asset name.
function M.activity_name(asset)
    local ok, name = pcall(function() return asset.Name:ToString() end)
    if ok and type(name) == "string" and name ~= "" then return name end
    return M.name_of(asset)
end

-- Completed activities as { asset = UActivityDataAsset, name = "Centennial Bloom" }, plus how they were read.
function M.completed_activities(progression)
    local activities = {}
    local ok = pcall(function()
        progression.ActivitiesTimeCompletion:ForEach(function(key, _)
            local asset = key:get()
            activities[#activities + 1] = { asset = asset, name = M.activity_name(asset) }
        end)
    end)
    if ok then return activities, "ActivitiesTimeCompletion" end
    -- Fallback for UE4SS builds without TMap iteration: ask about every loaded activity asset.
    activities = {}
    if not cache.activities or os.time() - cache.activities.searched > 30 then
        local found, assets = pcall(FindAllOf, "ActivityDataAsset")
        cache.activities = { list = (found and assets) or {}, searched = os.time() }
    end
    for _, asset in ipairs(cache.activities.list) do
        local done, time = pcall(function() return progression:GetActivityTimeCompletion(asset) end)
        if done and type(time) == "number" and time > 0 then
            activities[#activities + 1] = { asset = asset, name = M.activity_name(asset) }
        end
    end
    return activities, "GetActivityTimeCompletion"
end

function M.is_star_unlocked(asset, index)
    local context = cached_instance("PlayerController")
    if not context then return nil end
    local ok, unlocked = pcall(function() return asset:IsStarUnlocked(context, index) end)
    if ok and type(unlocked) == "boolean" then return unlocked end
    return nil
end

-- GetWranglerLevel has an out parameter (NextLevelRatio), UE4SS fills a table passed in its place.
local wrangler_calls = {
    function(progression) return progression:GetWranglerLevel({}) end,
    function(progression) return progression:GetWranglerLevel() end,
}
local wrangler_call = nil -- the variant that worked, so failing calls (which throw) happen at most once

function M.wrangler_level(progression)
    if wrangler_call then
        local ok, level = pcall(wrangler_call, progression)
        if ok and type(level) == "number" then return level end
        return nil
    end
    for _, call in ipairs(wrangler_calls) do
        local ok, level = pcall(call, progression)
        if ok and type(level) == "number" then
            wrangler_call = call
            return level
        end
    end
    return nil
end

function M.abyss_depth()
    local abyss = M.abyss()
    if not abyss then return nil end
    local ok, depth = pcall(function()
        if abyss:IsInsideAbyss() then return abyss:GetAbyssLevel() end
        return nil
    end)
    if ok and type(depth) == "number" then return depth end
    return nil
end

-- All loaded gene assets (also modules and perks), searched again at most every GENE_LIST_SECONDS.
-- ProgressionSubsystem.UnlockedDataAssets would list unlocked genes directly, but its soft pointers can't be read
-- with UE4SS 3.0.1, and probing them throws an error per entry, which can crash UE4SS's error handler.
function M.gene_assets()
    if cache.genes and os.time() - cache.genes.searched < GENE_LIST_SECONDS then return cache.genes.list end
    local list, seen = {}, {}
    for _, class_name in ipairs(M.GENE_CLASSES) do
        local found, assets = pcall(FindAllOf, class_name)
        for _, asset in ipairs((found and assets) or {}) do
            local name = M.name_of(asset)
            if not seen[name] and not name:find("^Default__") then
                seen[name] = true
                list[#list + 1] = { asset = asset, name = name }
            end
        end
    end
    cache.genes = { list = list, searched = os.time() }
    return list
end

-- Asset names of the unlocked genes, leaving out the ones in skip.
function M.unlocked_genes(progression, skip)
    local genes = {}
    for _, gene in ipairs(M.gene_assets()) do
        if not (skip and skip[gene.name]) then
            local checked, unlocked = pcall(function() return progression:IsDataUnlocked(gene.asset) end)
            if checked and unlocked == true then genes[#genes + 1] = gene.name end
        end
    end
    return genes
end

-- Called from the poll loop on the game thread.
function M.poll(events)
    local progression = M.progression()
    if not progression then return end -- main menu or loading

    for _, activity in ipairs((M.completed_activities(progression))) do
        local name = activity.name
        if not reported_missions[name] then
            reported_missions[name] = true
            events.mission_complete(name)
        end
        -- Stars can be earned on a later replay, so they're checked until reported.
        for star, send in pairs({ [M.STAR_MUTAGENS] = events.bonus_mutagens, [M.STAR_GOLDEN_EGGS] = events.golden_eggs }) do
            local key = name .. "#" .. star
            if not reported_stars[key] and M.is_star_unlocked(activity.asset, star) then
                reported_stars[key] = true
                send(name)
            end
        end
    end

    local level = M.wrangler_level(progression)
    if level and level > reported_rank then
        reported_rank = level
        events.wrangler_rank(level)
    end

    if os.time() - last_gene_poll >= GENE_POLL_SECONDS then
        last_gene_poll = os.time()
        for _, gene in ipairs(M.unlocked_genes(progression, reported_genes)) do
            reported_genes[gene] = true
            events.gene(gene)
        end
    end

    local depth = M.abyss_depth()
    if depth and depth > reported_depth then
        reported_depth = depth
        events.abyss_depth(depth)
    end
end

return M
