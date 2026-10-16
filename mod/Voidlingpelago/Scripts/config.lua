-- Voidlingpelago settings. Edit this file, then restart the game (or press Ctrl+R with the UE4SS console).
return {
    -- Developer tools to find the game's classes and functions, see discovery.lua.
    -- F6 writes discovery.txt, F7 starts/stops writing trace.txt. Both land in %APPDATA%\Voidlingpelago.
    discovery = true,
    scan_key = Key.F6,
    trace_key = Key.F7,

    -- F9 sends a "Faint Signal completed" event, to test the client connection without the real hooks.
    -- This sends a real check to the multiworld, so only enable it in a test room.
    debug_events = false,
    debug_key = Key.F9,
}
