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
Key = { F6 = 117, F7 = 118, F9 = 120 }
loops, keybinds, hooks, map_hooks, log_lines = {}, {}, {}, {}, {}
function LoopAsync(ms, fn) loops[#loops + 1] = fn end
function ExecuteInGameThread(fn) fn() end
function RegisterKeyBind(key, fn) keybinds[key] = fn end
function RegisterLoadMapPostHook(fn) map_hooks[#map_hooks + 1] = fn end
function RegisterHook(path, fn) hooks[path] = fn; return 1, 2 end
function UnregisterHook(path) hooks[path] = nil end
function FindFirstOf(name) return nil end
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
write("items.txt", "session OTHER 2\n0 840031 Pyro Mutagens (3)\n")
poll()
check("new session applies its first item", read("applied_session_OTHER_2.txt") == "1")

# DeathLink file is consumed
write("deathlink.txt", "Somebody")
poll()
check("deathlink file consumed", read("deathlink.txt") is None)

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

print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
