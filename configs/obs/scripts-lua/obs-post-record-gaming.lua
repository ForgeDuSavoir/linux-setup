obs = obslua

local recording_context = "global"

local function shell_quote(value)
    return "'" .. value:gsub("'", "'\\''") .. "'"
end

local function capture_context()
    -- Bound synchronous capture so a broken service cannot stall OBS indefinitely.
    local pipe = io.popen("/usr/bin/timeout 2s /usr/bin/env agora-notify capture 2>/dev/null")
    if pipe == nil then return "global" end
    local value = pipe:read("*a") or ""
    pipe:close()
    value = value:gsub("%s+$", "")
    if value == "global" or value == "neutral" or value:match("^session:[0-9a-f%-]+$") then
        return value
    end
    return "global"
end

function on_event(event)
    if event == obs.OBS_FRONTEND_EVENT_RECORDING_STARTED then
        recording_context = capture_context()
    elseif event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED then
        local path = obs.obs_frontend_get_last_recording()
        if path ~= nil and path ~= "" then
            os.execute("/usr/bin/env obs-post-record-gaming.sh " .. shell_quote(path) .. " " .. shell_quote(recording_context) .. " &")
        end
        recording_context = "global"
    end
end

function script_load(settings)
    obs.obs_frontend_add_event_callback(on_event)
end
