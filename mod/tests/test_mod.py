"""Usage: python mod/tests/test_mod.py  (needs: pip install lupa)

Runs the Voidlingpelago Lua mod against stubbed UE4SS globals to test the file protocol and discovery tools."""
import os
import sys
import tempfile

import lupa

SCRIPTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "Voidlingpelago", "Scripts")
appdata = tempfile.mkdtemp()
os.environ["APPDATA"] = appdata
exchange = os.path.join(appdata, "Voidlingpelago")
os.makedirs(exchange)

STUBS = r"""
Key = { F5 = 116, F6 = 117, F7 = 118, F8 = 119, F9 = 120 }
loops, keybinds, hooks, map_hooks, log_lines = {}, {}, {}, {}, {}
function LoopInGameThreadWithDelay(ms, fn) loops[#loops + 1] = fn end
function ExecuteInGameThread(fn) fn() end
function RegisterKeyBind(key, fn) keybinds[key] = fn end
function RegisterLoadMapPostHook(fn) map_hooks[#map_hooks + 1] = fn end
function RegisterHook(path, fn) hooks[path] = fn; return 1, 2 end
function UnregisterHook(path) hooks[path] = nil end
instances = {}
function FindAllOf(name) return instances[name] end
function FindFirstOf(name) return instances[name] and instances[name][1] end
local real_print = print
function print(msg) log_lines[#log_lines + 1] = msg end

local function fname(s) return { ToString = function() return s end } end
local function fake_fn(path, short)
    return { GetFullName = function() return "Function " .. path end, GetFName = function() return fname(short) end }
end
local function fake_class(path, short, fns)
    return {
        IsClass = function() return true end,
        GetFullName = function() return "BlueprintGeneratedClass " .. path end,
        GetFName = function() return fname(short) end,
        GetSuperStruct = function() return nil end,
        ForEachFunction = function(self, cb) for _, f in ipairs(fns) do cb(f) end end,
        ForEachProperty = function(self, cb) end,
    }
end
local objects = {
    fake_class("/Game/Missions/BP_MissionManager.BP_MissionManager_C", "BP_MissionManager_C", {
        fake_fn("/Game/Missions/BP_MissionManager.BP_MissionManager_C:OnMissionCompleted", "OnMissionCompleted"),
        fake_fn("/Game/Missions/BP_MissionManager.BP_MissionManager_C:GetMissionData", "GetMissionData"),
        fake_fn("/Game/Missions/BP_MissionManager.BP_MissionManager_C:ReceiveTick", "ReceiveTick"),
    }),
    fake_class("/Script/Engine.SaveGame", "SaveGame", {}),           -- engine class, must be skipped
    fake_class("/Game/UI/WBP_Button.WBP_Button_C", "WBP_Button_C", {}), -- no keyword, must be skipped
}
function ForEachUObject(cb) for _, o in ipairs(objects) do cb(o) end end

-- A fake loaded save: progression, resources inventory, resource assets and the cheat manager.
function object(name, fields)
    fields.IsValid = function() return true end
    fields.GetFName = function() return fname(name) end
    fields.GetFullName = function() return "Object /Engine/Transient." .. name end
    return fields
end
completed, stars, wrangler_level, abyss_level = {}, {}, 0, 0
instances.PlayerController = { object("PlayerController_1", {}) }
stored, eggs_added, kills = {}, 0, 0
instances.ProgressionSubsystem = { object("Default__ProgressionSubsystem", {}), object("ProgressionSubsystem_1", {
    ActivitiesTimeCompletion = { ForEach = function(self, cb)
        for _, key in ipairs(completed) do
            cb({ get = function() return object(key, {
                Name = fname((key:gsub("^DA_Activity_", ""))),
                IsStarUnlocked = function(self, context, index) return (stars[key] or {})[index] == true end,
            }) end },
               { get = function() return 12.5 end })
        end
    end },
    GetWranglerLevel = function(self, out) return wrangler_level end,
    IsDataUnlocked = function(self, asset) return unlocked_genes[asset:GetFName():ToString()] == true end,
}) }
unlocked_genes = {}
instances.AbyssSubsystem = { object("AbyssSubsystem_1", {
    IsInsideAbyss = function() return abyss_level > 0 end,
    GetAbyssLevel = function() return abyss_level end,
}) }
local inventory = object("ResourcesInventory_1", {
    StoreResource = function(self, asset, amount)
        stored[#stored + 1] = asset.ResourceName:ToString() .. " x" .. amount
    end,
})
instances.PlayerProgression = { object("PlayerProgression_1", { ResourcesInventory = inventory }) }
instances.ResourceDataAsset = {}
for _, name in ipairs({ "Research Points", "Organic Mutagen", "Pyro Mutagen", "Polychrome Mutagen" }) do
    table.insert(instances.ResourceDataAsset, object("DA_" .. name, { ResourceName = fname(name) }))
end
-- Eggs: AddEgg only accepts creature class names ("BP_Kwipeck_C"), like the real cheat might.
eggs = {}
inventory.EggCount = function(self, include_pending) return #eggs end
instances.VWCheatManager = { object("VWCheatManager_1", {
    AddRandomEgg = function(self, count) eggs_added = eggs_added + count; table.insert(eggs, "random") end,
    AddEgg = function(self, egg_type, class_name, count)
        if class_name:match("^BP_%a+_C$") then table.insert(eggs, egg_type .. ":" .. class_name) end
    end,
    KillPlayerCreature = function() kills = kills + 1 end,
}) }
instances.SpeciesDataAsset = {}
for _, name in ipairs({ "Kwipeck", "Ur-Sek" }) do
    local short = name:gsub("-", "")
    table.insert(instances.SpeciesDataAsset, object("DA_Species_" .. short, {
        SpeciesName = fname(name),
        CreatureClass = fname("/Game/Creatures/BP_" .. short .. ".BP_" .. short .. "_C"),
    }))
end
local egg_enum = object("EEggType", {
    ForEachName = function(self, cb)
        cb(fname("EEggType::Normal"), 0); cb(fname("EEggType::Golden"), 1); cb(fname("EEggType::EEggType_MAX"), 2)
    end,
})
catalyzer = object("DA_Catalyzer_Swift", { ResourceName = fname("Swift Catalyzer") })
local catalyzer_cdo = object("Default__DNACatalyzerDefinition", {
    GetRandomCatalyzer = function(self, context, quality, min, max, try_new) return catalyzer end,
})
-- Genes: three in the Asset Registry (one of them loaded), one only loaded, plus a species asset
function FName(text) return fname(text) end
local function gene_object(path, class, name)
    local short = path:match("([^%.]+)$")
    local gene = object(short, {
        GeneName = fname(name),
        GetClass = function() return { GetFName = function() return fname(class) end } end,
        IsCollectible = function() return name ~= "Huge" end,
        IsClass = function() return false end,
        IsA = function(self, class_path) return class_path == "/Script/VoidlingWrangler.GeneDataAsset" end,
    })
    gene.GetFullName = function() return class .. " " .. path end
    return gene
end
local G = "/Game/Data/Creatures/RL01/Genes/"
gene_files = {
    [G .. "Eyes/DA_Gene_Eye_RL01_00.DA_Gene_Eye_RL01_00"] = { "EyeGeneDataAsset", "Starry" },
    [G .. "Colors/DA_Gene_Color_RL01_03.DA_Gene_Color_RL01_03"] = { "ColorGeneDataAsset", "Crimson" },
    [G .. "Perks/DA_Gene_Perk_RL01_01.DA_Gene_Perk_RL01_01"] = { "PerkGeneDataAsset", "Thick Skin" },
}
-- Traps: a Blueprint and a module path that resolves to a non-gene object. Calling gene functions on them is
-- what crashed the real game.
gene_call_on_wrong_object = false
local not_a_gene_path = G .. "Modules/RareModules/DA_RL01_RareModule_00.DA_RL01_RareModule_00"
local not_a_gene = object("DA_RL01_RareModule_00", {
    IsClass = function() return false end,
    IsA = function() return false end,
    IsCollectible = function() gene_call_on_wrong_object = true end,
})
not_a_gene.GeneName = setmetatable({}, { __index = function() gene_call_on_wrong_object = true end })
loaded_assets = {}
loaded_assets[G .. "Eyes/DA_Gene_Eye_RL01_00.DA_Gene_Eye_RL01_00"] = true
function LoadAsset(path) loaded_assets[path] = true end
instances.EyeGeneDataAsset = { gene_object(G .. "Eyes/DA_Gene_Eye_RL01_00.DA_Gene_Eye_RL01_00", "EyeGeneDataAsset", "Starry") }
instances.ColorGeneDataAsset = { gene_object(G .. "Colors/DA_Gene_Color_RL01_03.DA_Gene_Color_RL01_03", "ColorGeneDataAsset", "Crimson") }
instances.SizeGeneDataAsset = { gene_object(G .. "Sizes/DA_Gene_Size_RL01_02.DA_Gene_Size_RL01_02", "SizeGeneDataAsset", "Huge") }
local species_path = "/Game/Data/Creatures/RL01/DA_Species_RL01.DA_Species_RL01"
local registry = {
    GetAssetsByPath = function(self, path, out, recursive, on_disk_only)
        local all = { species_path, not_a_gene_path,
                      G .. "AbilityVariants/DA_AV_RL01_A1.DA_AV_RL01_A1" }
        for gene_path in pairs(gene_files) do all[#all + 1] = gene_path end
        for _, full in ipairs(all) do
            local package, name = full:match("^(.-)%.([^%.]+)$")
            out[#out + 1] = { PackageName = fname(package), AssetName = fname(name) }
        end
    end,
}
local registry_helpers = object("Default__AssetRegistryHelpers", { GetAssetRegistry = function() return registry end })

function StaticFindObject(path)
    if path == "/Script/VoidlingWrangler.EEggType" then return egg_enum end
    if path == "/Script/VoidlingWrangler.Default__DNACatalyzerDefinition" then return catalyzer_cdo end
    if path == "/Script/AssetRegistry.Default__AssetRegistryHelpers" then return registry_helpers end
    if gene_files[path] and loaded_assets[path] then return gene_object(path, gene_files[path][1], gene_files[path][2]) end
    if path == not_a_gene_path then return not_a_gene end
    if path:find("DA_AV_RL01_A1", 1, true) then gene_call_on_wrong_object = true end
    if path == species_path and loaded_assets[path] then return object("DA_Species_RL01", { SpeciesName = fname("Kwipeck") }) end
    return nil
end

-- Activities on every planet, for the gating
local activity_type = object("DA_ActivityType_Cleanse", {})
local abyss_type = object("DA_ActivityType_AbyssalIncursion", {})
instances.ActivityDataAsset = {}
for _, entry in ipairs({
    { "Faint Signal", activity_type }, { "Search and Rescue", activity_type }, { "Storm Breaker", activity_type },
    { "Operation: Void Strike", abyss_type }, { "Tutorial Flight", activity_type }, { "Abyss Dive", abyss_type },
}) do
    table.insert(instances.ActivityDataAsset, object("DA_Activity_" .. entry[1]:gsub("[^%w]", ""), {
        Name = fname(entry[1]), Type = entry[2], WranglerLevelRequirement = 2,
    }))
end
-- An array property that throws on any access, like UE4SS's TArray does for unknown members
array_touched = false
local first_activity = instances.ActivityDataAsset[1]
first_activity.RandomLevels = setmetatable({}, { __index = function() array_touched = true; error("TArray") end })
local function fake_property(name, kind)
    return { GetFName = function() return fname(name) end,
             GetClass = function() return { GetFName = function() return fname(kind) end } end }
end
first_activity.GetClass = function() return { ForEachProperty = function(self, cb)
    cb(fake_property("Name", "TextProperty"))
    cb(fake_property("RandomLevels", "ArrayProperty"))
end } end

function requirement(name)
    for _, asset in ipairs(instances.ActivityDataAsset) do
        if asset.Name:ToString() == name then return asset.WranglerLevelRequirement end
    end
end
"""

lua = lupa.LuaRuntime(unpack_returned_tuples=True)
lua.execute(STUBS)
lua.execute(f'package.path = [[{SCRIPTS}]] .. "/?.lua;" .. package.path')
lua.execute(open(os.path.join(SCRIPTS, "main.lua"), encoding="utf-8").read())
poll = lua.globals().loops[1]
results = []


def check(name, condition):
    results.append(condition)
    print(("PASS " if condition else "FAIL ") + name)


def write(name, text):
    with open(os.path.join(exchange, name), "w", encoding="utf-8") as f:
        f.write(text)


def read(name):
    path = os.path.join(exchange, name)
    return open(path, encoding="utf-8").read() if os.path.exists(path) else None


def received():
    return [line for line in lua.globals().log_lines.values() if "Received" in str(line)]


# Items: three items, the first is an unlock
write("items.txt", "session SEED 1\n0 840001 Planet Access: Solum\n1 840030 Organic Mutagens (3)\n2 840020 Research Points (500)\n")
poll()
check("all 3 items applied", len(received()) == 3)
check("applied counter persisted", read("applied_session_SEED_1.txt") == "3")
poll()
check("items not applied twice", len(received()) == 3)
check("resources stored in the inventory", list(lua.globals().stored.values()) == ["Organic Mutagen x3", "Research Points x500"])

# Restart: a fresh Lua state must not re-grant items, but must rebuild unlocks
lua2 = lupa.LuaRuntime(unpack_returned_tuples=True)
lua2.execute(STUBS)
lua2.execute(f'package.path = [[{SCRIPTS}]] .. "/?.lua;" .. package.path')
lua2.execute(open(os.path.join(SCRIPTS, "main.lua"), encoding="utf-8").read())
write("items.txt", read("items.txt") + "3 840004 Abyss Access\n")
lua2.globals().loops[1]()
log2 = [str(line) for line in lua2.globals().log_lines.values()]
check("after restart only the new item is applied", sum("Received" in line for line in log2) == 1)
check("restart reports 3 already applied", any("3 items already applied" in line for line in log2))

# New session resets the counter
write("items.txt", "session OTHER 2\n0 840031 Pyro Mutagens (3)\n1 840010 DNA Catalyzer Bundle\n2 840023 Voidling Egg\n")
poll()
check("new session applies its items", read("applied_session_OTHER_2.txt") == "3")
check("an item the mod can't grant doesn't block the next one", lua.globals().eggs_added == 1)

# DeathLink file is consumed
write("deathlink.txt", "Somebody")
poll()
check("deathlink file consumed", read("deathlink.txt") is None)
check("deathlink kills the player creature", lua.globals().kills == 1)
failure = "/Script/VoidlingWrangler.ActivitySubsystem:TriggerActivityFailure"
write("events.txt", "")
lua.globals().hooks[failure]()
check("the failure caused by a received DeathLink isn't sent back", (read("events.txt") or "") == "")
lua.execute("local real_time = os.time; os.time = function() return real_time() + 60 end")
lua.globals().hooks[failure]()
check("a real mission failure sends a death", (read("events.txt") or "").splitlines() == ["death"])

# Events
check("mission_key replaces spaces", lua.eval('require("game_hooks").mission_key("Centennial Bloom")') == "Centennial_Bloom")

# Discovery scan
lua.globals().keybinds[117]()
scan = read("discovery.txt") or ""
check("scan lists the mission manager class", "BP_MissionManager_C" in scan and "fn   OnMissionCompleted" in scan)
check("scan skips engine and keyword-less classes", "/Script/Engine.SaveGame" not in scan and "WBP_Button" not in scan)

# Trace
lua.globals().keybinds[118]()
hooks = lua.globals().hooks
completed = "/Game/Missions/BP_MissionManager.BP_MissionManager_C:OnMissionCompleted"
check("trace hooks the interesting function", completed in hooks)
check("trace skips getters and tick", not any("GetMissionData" in k or "ReceiveTick" in k for k in hooks.keys()))
ctx = lua.eval('{ get = function() return { GetFullName = function() return "BP_MissionManager_C /Game/Maps/Vireo.Vireo:Manager" end } end }')
param = lua.eval('{ get = function() return 42 end }')
hooks[completed](ctx, param)
lua.globals().map_hooks[1](None, lua.eval('{ get = function() return { GetFullName = function() return "World /Game/Maps/Vireo_01.Vireo_01" end } end }'))
lua.globals().keybinds[118]()
trace = read("trace.txt") or ""
check("trace logs call with self and args", "OnMissionCompleted  self=/Game/Maps/Vireo.Vireo:Manager  args=(42)" in trace)
check("trace logs map loads", "Map loaded: /Game/Maps/Vireo_01.Vireo_01" in trace)
check("trace unhooks on stop", completed not in lua.globals().hooks)

# Tracker: reads progress from the fake ProgressionSubsystem / AbyssSubsystem
lua.execute('completed[1] = "DA_Activity_FaintSignal"; wrangler_level = 3; abyss_level = 7; require("tracker").reset()')
write("events.txt", "")
poll()
events = (read("events.txt") or "").splitlines()
check("tracker reports completed mission by display name", "mission_complete FaintSignal" in events)
check("tracker reports wrangler rank and abyss depth", "wrangler_rank 3" in events and "abyss_depth 7" in events)
check("tracker skips the class default object", len(events) == 3)
poll()
check("tracker doesn't repeat events", len((read("events.txt") or "").splitlines()) == 3)
lua.execute('completed[2] = "DA_Activity_CentennialBloom"; wrangler_level = 4')
poll()
events = (read("events.txt") or "").splitlines()
check("tracker reports new progress only", events[3:] == ["mission_complete CentennialBloom", "wrangler_rank 4"])
lua.execute('stars["DA_Activity_CentennialBloom"] = { [2] = true }')
poll()
events = (read("events.txt") or "").splitlines()
check("tracker reports a star earned later, once", events[5:] == ["golden_eggs CentennialBloom"])
poll()
check("star not reported twice", len((read("events.txt") or "").splitlines()) == 6)

# Gating: missions on planets without access get Wrangler level requirement 99
def requirements():
    return {name: lua.globals().requirement(name) for name in
            ["Faint Signal", "Search and Rescue", "Storm Breaker", "Operation: Void Strike", "Tutorial Flight", "Abyss Dive"]}


write("slot.txt", "goal=0\nmission_regions=Faint Signal=Vireo|Search and Rescue=Solum|Storm Breaker=Aulis|Operation: Void Strike=The Abyss\n")
write("items.txt", "session GATE 1\n")
poll()
check("missions without access are locked, others untouched", requirements() == {
    "Faint Signal": 2, "Search and Rescue": 99, "Storm Breaker": 99, "Operation: Void Strike": 99,
    "Tutorial Flight": 2, "Abyss Dive": 99})
write("items.txt", "session GATE 1\n0 840001 Planet Access: Solum\n0 840004 Abyss Access\n")
poll()
check("Solum unlocks, Aulis and the Abyss still need Aulis", requirements() == {
    "Faint Signal": 2, "Search and Rescue": 2, "Storm Breaker": 99, "Operation: Void Strike": 99,
    "Tutorial Flight": 2, "Abyss Dive": 99})
write("items.txt", "session GATE 1\n0 840001 Planet Access: Solum\n1 840004 Abyss Access\n2 840002 Planet Access: Aulis\n")
poll()
check("Aulis and the Abyss unlock with all their items", set(requirements().values()) == {2})

# Gating survives an asset reload, which resets the requirement
lua.execute("""
gate_locked_again = false
for _, asset in ipairs(instances.ActivityDataAsset) do asset.WranglerLevelRequirement = 2 end
""")
write("items.txt", "session GATE2 1\n")
lua.execute("local base = os.time; os.time = function() return base() + 600 end")
poll()
check("a fresh session locks again, also after a reload", requirements()["Storm Breaker"] == 99)

# Rewards: species egg, golden egg, catalyzer
write("items.txt", "session REWARD 1\n0 840046 Ur-Sek Egg\n1 840012 Golden Egg\n2 840010 DNA Catalyzer Bundle\n")
poll()
eggs = list(lua.globals().eggs.values())
check("species egg added with the class name AddEgg accepts", "0:BP_UrSek_C" in eggs)
check("golden egg uses the Golden egg type", any(egg.startswith("1:BP_") for egg in eggs))
check("catalyzer stored as a resource", "Swift Catalyzer x1" in list(lua.globals().stored.values()))

# Genes: unlocked genes are reported once, other unlocked data assets are ignored
lua.execute('''
unlocked_genes["DA_Gene_Eye_RL01_00"] = true
local base = os.time; os.time = function() return base() + 1200 end
''')
write("events.txt", "")
poll()
check("unlocked gene reported by asset name", (read("events.txt") or "").splitlines() == ["gene DA_Gene_Eye_RL01_00"])
lua.execute('unlocked_genes["DA_Gene_Color_RL01_03"] = true')
lua.execute("local base = os.time; os.time = function() return base() + 10 end")
poll()
check("newly unlocked gene reported, old one not again",
      (read("events.txt") or "").splitlines() == ["gene DA_Gene_Eye_RL01_00", "gene DA_Gene_Color_RL01_03"])

# Gene dump (F5)
lua.globals().keybinds[116]()
dump = read("genes.txt") or ""
check("gene dump has registry genes, loaded genes and species names",
      "/Game/Data/Creatures/RL01/Genes/Perks/DA_Gene_Perk_RL01_01.DA_Gene_Perk_RL01_01\tPerkGeneDataAsset\tThick Skin\tRL01\tKwipeck\ttrue" in dump
      and "DA_Gene_Size_RL01_02\tSizeGeneDataAsset\tHuge\tRL01\tKwipeck\tfalse" in dump)
check("gene dump never calls gene functions on non-gene objects", not lua.globals().gene_call_on_wrong_object)
check("gene dump lists every gene once", sum(1 for line in dump.splitlines() if not line.startswith("#")) == 4)

# State dump (F8)
lua.globals().keybinds[119]()
state = read("state.txt") or ""
check("state dump lists completed activities", "Completed activities (via ActivitiesTimeCompletion): FaintSignal, CentennialBloom" in state)
check("state dump reads text properties and only names arrays",
      "Name = Faint Signal" in state and "RandomLevels = <ArrayProperty>" in state and not lua.globals().array_touched)
check("state dump lists wrangler level and abyss depth", "WranglerLevel: 4" in state and "Abyss depth: 7" in state)

print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
