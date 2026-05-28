obs = obslua

function on_event(event)
    if event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED then
        local path = obs.obs_frontend_get_last_recording()
        if path ~= nil and path ~= "" then
            os.execute('/usr/bin/env obs-post-record-gaming.sh "' .. path .. '" &')
        end
    end
end

function script_load(settings)
    obs.obs_frontend_add_event_callback(on_event)
end