--[[
  OdstranPauzy.lua  —  DaVinci Resolve (Lua) skript
  -------------------------------------------------------------------------
  Spraví z aktuálneho timeline novú verziu s HARDCUTMI bez páuz a ticha.

  Ako to funguje:
    1. Vezme klipy z aktuálneho timeline (video stopa V1, v poradí).
    2. Pre každý zdrojový súbor spustí ffmpeg "silencedetect" a nájde ticho.
    3. Z každého klipu ponechá len časti, kde sa hovorí (+ malý padding).
    4. Vytvorí NOVÝ timeline "<pôvodný názov> - bez pauz" a časti tam poskladá
       tesne za seba (hardcuty, žiadne medzery). Pôvodný timeline ostane nedotknutý.

  Čo potrebuješ:
    - DaVinci Resolve 18+ (testované na API z verzie 19/20/21; Free aj Studio)
    - ffmpeg nainštalovaný v systéme
        Mac:     brew install ffmpeg      (bude v /opt/homebrew/bin/ffmpeg)
        Windows: https://www.gyan.dev/ffmpeg/builds/  -> nastav FFMPEG nižšie
    - Media súbory musia byť online (nie "Media Offline") na ceste,
      ktorú vidí Resolve.

  Inštalácia:
    Mac:     ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Edit/
    Windows: %APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Edit\
    Linux:   ~/.local/share/DaVinciResolve/Fusion/Scripts/Edit/
    Potom v Resolve: Workspace -> Scripts -> Edit -> OdstranPauzy
    (Výstup/log uvidíš vo Workspace -> Console.)
]]

---------------------------------------------------------------------------
-- NASTAVENIA (tu si to dolaď podľa videa)
---------------------------------------------------------------------------
local CONFIG = {
    -- Hlasitosť, pod ktorou sa zvuk berie ako ticho. Viac záporné = citlivejšie
    -- (menej sa vystrihne). Pri šumnom prostredí skús -30, pri tichej miestnosti -40.
    NOISE_DB        = -35,

    -- Minimálna dĺžka pauzy (sekundy), ktorá sa vystrihne.
    -- 0.35–0.5 = dynamický "talking head" štýl na Reels/TikTok.
    MIN_SILENCE     = 0.4,

    -- Koľko sekúnd nechať pred a po reči, aby slová neboli odseknuté.
    PAD_BEFORE      = 0.08,
    PAD_AFTER       = 0.12,

    -- Kúsky reči kratšie než toto (sekundy) zahodí (kliky, nádychy).
    MIN_KEEP        = 0.25,

    -- Z ktorej video stopy brať klipy.
    VIDEO_TRACK     = 1,

    -- Ktorá audio stopa zo súboru sa analyzuje (0 = prvá).
    AUDIO_STREAM    = 0,

    -- Cesta k ffmpeg. nil = skúsi automaticky nájsť.
    FFMPEG          = nil,

    -- true = iba vypíše, čo by sa strihalo, timeline nevytvorí.
    DRY_RUN         = false,
}

---------------------------------------------------------------------------
-- Pomocné funkcie
---------------------------------------------------------------------------
local function log(...)
    local parts = {}
    for i = 1, select("#", ...) do parts[#parts + 1] = tostring(select(i, ...)) end
    print("[OdstranPauzy] " .. table.concat(parts, " "))
end

local IS_WINDOWS = package.config:sub(1, 1) == "\\"

local function fileExists(path)
    local f = io.open(path, "rb")
    if f then f:close() return true end
    return false
end

local function shellQuote(s)
    if IS_WINDOWS then
        return '"' .. s:gsub('"', '\\"') .. '"'
    end
    return "'" .. s:gsub("'", "'\\''") .. "'"
end

local function findFfmpeg()
    if CONFIG.FFMPEG and CONFIG.FFMPEG ~= "" then return CONFIG.FFMPEG end
    local candidates = IS_WINDOWS and {
        "C:\\ffmpeg\\bin\\ffmpeg.exe",
        "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe",
    } or {
        "/opt/homebrew/bin/ffmpeg",   -- Mac Apple Silicon (Homebrew)
        "/usr/local/bin/ffmpeg",      -- Mac Intel (Homebrew)
        "/usr/bin/ffmpeg",            -- Linux
    }
    for _, p in ipairs(candidates) do
        if fileExists(p) then return p end
    end
    -- Posledná šanca: ffmpeg v PATH
    return "ffmpeg"
end

-- Spustí ffmpeg silencedetect na celý súbor a vráti zoznam tichých úsekov
-- v sekundách od začiatku súboru: { {s=..., e=...}, ... }
local silenceCache = {}
local function detectSilence(ffmpeg, filePath)
    if silenceCache[filePath] then return silenceCache[filePath] end

    local filter = string.format("silencedetect=noise=%ddB:d=%s", CONFIG.NOISE_DB, tostring(CONFIG.MIN_SILENCE))
    local cmd = string.format('%s -hide_banner -nostats -i %s -map 0:a:%d -af %s -f null - 2>&1',
        shellQuote(ffmpeg), shellQuote(filePath), CONFIG.AUDIO_STREAM, filter)
    if IS_WINDOWS then cmd = '"' .. cmd .. '"' end

    log("Analyzujem zvuk:", filePath)
    local pipe = io.popen(cmd)
    if not pipe then
        log("CHYBA: nepodarilo sa spustiť ffmpeg.")
        return nil
    end
    local output = pipe:read("*a")
    pipe:close()

    local silences, openStart = {}, nil
    for line in output:gmatch("[^\r\n]+") do
        local s = line:match("silence_start:%s*([%-%d%.]+)")
        if s then openStart = math.max(0, tonumber(s)) end
        local e = line:match("silence_end:%s*([%-%d%.]+)")
        if e and openStart then
            silences[#silences + 1] = { s = openStart, e = tonumber(e) }
            openStart = nil
        end
    end
    -- Ticho trvá až do konca súboru
    if openStart then silences[#silences + 1] = { s = openStart, e = math.huge } end

    if #silences == 0 and not output:find("silencedetect") then
        log("CHYBA: ffmpeg nevrátil výsledok. Výstup:\n" .. output:sub(1, 1500))
        return nil
    end

    silenceCache[filePath] = silences
    log(string.format("  nájdených tichých úsekov: %d", #silences))
    return silences
end

-- Z rozsahu [srcStart, srcEnd) (sekundy v súbore) vráti úseky s rečou.
local function speechRanges(silences, srcStart, srcEnd)
    local ranges, cursor = {}, srcStart
    for _, sil in ipairs(silences) do
        if sil.e > srcStart and sil.s < srcEnd then
            local keepEnd = math.min(sil.s + CONFIG.PAD_AFTER, srcEnd)
            if keepEnd > cursor then ranges[#ranges + 1] = { s = cursor, e = keepEnd } end
            cursor = math.max(cursor, sil.e - CONFIG.PAD_BEFORE)
        end
    end
    if cursor < srcEnd then ranges[#ranges + 1] = { s = cursor, e = srcEnd } end

    -- Zlúč prekrývajúce sa úseky (kvôli paddingu) a vyhoď príliš krátke
    local merged = {}
    for _, r in ipairs(ranges) do
        local last = merged[#merged]
        if last and r.s <= last.e then
            last.e = math.max(last.e, r.e)
        else
            merged[#merged + 1] = { s = r.s, e = r.e }
        end
    end
    local result = {}
    for _, r in ipairs(merged) do
        if r.e - r.s >= CONFIG.MIN_KEEP then result[#result + 1] = r end
    end
    return result
end

local function parseFps(value, fallback)
    local n = tonumber(tostring(value or ""):match("[%d%.]+"))
    if not n or n <= 0 then return fallback end
    -- Resolve niekedy hlási "29.97" namiesto 30000/1001 — oprav na presné hodnoty
    if math.abs(n - 23.976) < 0.01 then return 24000 / 1001 end
    if math.abs(n - 29.97) < 0.01 then return 30000 / 1001 end
    if math.abs(n - 59.94) < 0.01 then return 60000 / 1001 end
    return n
end

---------------------------------------------------------------------------
-- Hlavná časť
---------------------------------------------------------------------------
local function main()
    local res = resolve or (Resolve and Resolve())
    if not res then log("CHYBA: Resolve API nie je dostupné.") return end

    local project = res:GetProjectManager():GetCurrentProject()
    if not project then log("CHYBA: nie je otvorený projekt.") return end

    local timeline = project:GetCurrentTimeline()
    if not timeline then log("CHYBA: nie je otvorený žiadny timeline.") return end

    local mediaPool = project:GetMediaPool()
    local timelineFps = parseFps(timeline:GetSetting("timelineFrameRate"), 30)
    local ffmpeg = findFfmpeg()
    log("Timeline:", timeline:GetName(), "| fps:", string.format("%.3f", timelineFps), "| ffmpeg:", ffmpeg)

    local items = timeline:GetItemListInTrack("video", CONFIG.VIDEO_TRACK) or {}
    if #items == 0 then log("CHYBA: na stope V" .. CONFIG.VIDEO_TRACK .. " nie sú žiadne klipy.") return end

    -- GetItemListInTrack nemusí vracať v poradí — zoraď podľa pozície
    table.sort(items, function(a, b) return a:GetStart() < b:GetStart() end)

    local clipInfos = {}
    local totalBefore, totalAfter = 0, 0

    for idx, item in ipairs(items) do
        local mpi = item:GetMediaPoolItem()
        if not mpi then
            log(string.format("Klip %d (%s) nemá media pool položku (titulok/generátor?) — preskakujem.", idx, item:GetName()))
        else
            local filePath = mpi:GetClipProperty("File Path")
            local clipFps = parseFps(mpi:GetClipProperty("FPS"), timelineFps)

            -- Zdrojový in/out v snímkach od začiatku súboru
            local srcIn, srcOut
            if item.GetSourceStartFrame then
                srcIn = item:GetSourceStartFrame()
                srcOut = item:GetSourceEndFrame() + 1   -- end je vrátane -> exkluzívny
            end
            if not srcIn then
                srcIn = item:GetLeftOffset()
                srcOut = srcIn + item:GetDuration()
            end

            local srcStartSec = srcIn / clipFps
            local srcEndSec = srcOut / clipFps
            totalBefore = totalBefore + (srcEndSec - srcStartSec)

            log(string.format("Klip %d: %s  [%.2fs – %.2fs]", idx, item:GetName(), srcStartSec, srcEndSec))

            if not filePath or filePath == "" or not fileExists(filePath) then
                log("  VAROVANIE: súbor nie je dostupný (offline?) — klip nechávam celý.")
                clipInfos[#clipInfos + 1] = { mediaPoolItem = mpi, startFrame = srcIn, endFrame = srcOut - 1 }
                totalAfter = totalAfter + (srcEndSec - srcStartSec)
            else
                local silences = detectSilence(ffmpeg, filePath)
                if not silences then return end

                local ranges = speechRanges(silences, srcStartSec, srcEndSec)
                for _, r in ipairs(ranges) do
                    local sf = math.max(srcIn, math.floor(r.s * clipFps + 0.5))
                    local ef = math.min(srcOut, math.floor(r.e * clipFps + 0.5))
                    if ef > sf then
                        -- endFrame je v Resolve API posledná snímka (vrátane)
                        clipInfos[#clipInfos + 1] = { mediaPoolItem = mpi, startFrame = sf, endFrame = ef - 1 }
                        totalAfter = totalAfter + (ef - sf) / clipFps
                        log(string.format("  ponechávam %7.2fs – %7.2fs", sf / clipFps, ef / clipFps))
                    end
                end
            end
        end
    end

    log(string.format("Dĺžka pred: %.1fs | po: %.1fs | vystrihnuté: %.1fs | počet strihov: %d",
        totalBefore, totalAfter, totalBefore - totalAfter, #clipInfos))

    if #clipInfos == 0 then log("Nič na ponechanie — skús znížiť NOISE_DB (napr. -45).") return end
    if CONFIG.DRY_RUN then log("DRY_RUN = true, timeline nevytváram.") return end

    -- Nový timeline s unikátnym názvom
    local baseName = timeline:GetName() .. " - bez pauz"
    local name, n = baseName, 2
    local existing = {}
    for i = 1, project:GetTimelineCount() do existing[project:GetTimelineByIndex(i):GetName()] = true end
    while existing[name] do name = baseName .. " " .. n; n = n + 1 end

    local newTimeline = mediaPool:CreateEmptyTimeline(name)
    if not newTimeline then log("CHYBA: nepodarilo sa vytvoriť timeline.") return end
    project:SetCurrentTimeline(newTimeline)

    -- Pridávaj po dávkach, pri stovkách strihov je to stabilnejšie
    local BATCH = 50
    for i = 1, #clipInfos, BATCH do
        local batch = {}
        for j = i, math.min(i + BATCH - 1, #clipInfos) do batch[#batch + 1] = clipInfos[j] end
        local added = mediaPool:AppendToTimeline(batch)
        if not added or #added == 0 then
            log("CHYBA: AppendToTimeline zlyhal pri dávke od " .. i)
            return
        end
    end

    log("HOTOVO ✔  Nový timeline: " .. name)
end

main()
