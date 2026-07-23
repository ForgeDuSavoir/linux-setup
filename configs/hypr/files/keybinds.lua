-- Example binds, see https://wiki.hypr.land/Configuring/Basics/Binds/ for more

local mainMod = "SUPER"

local terminal = "alacritty"
local editor = "mousepad"
local explorer = "thunar"
local browser = "firefox"

-- Applications

hl.bind(mainMod .. " + RETURN", hl.dsp.exec_cmd(terminal))
hl.bind(mainMod .. " + E", hl.dsp.exec_cmd(explorer))
hl.bind(mainMod .. " + V", hl.dsp.exec_cmd(editor))
hl.bind(mainMod .. " + B", hl.dsp.exec_cmd(browser))

-- Shell

hl.bind(mainMod .. " + D", hl.dsp.exec_cmd("quickshell ipc call launcher toggle"))
hl.bind(mainMod .. " + L", hl.dsp.exec_cmd("hyprlock"))
hl.bind(mainMod .. " + O", hl.dsp.exec_cmd("quickshell ipc call controlCenter toggle"))
hl.bind(mainMod .. " + H", hl.dsp.exec_cmd("quickshell ipc call keybinds toggle"))


-- Window Management

hl.bind(mainMod .. " + Q", hl.dsp.window.close())
hl.bind(mainMod .. " + W", hl.dsp.window.float({ action = "toggle" }))
hl.bind(mainMod .. " + F", hl.dsp.window.fullscreen())

hl.bind(mainMod .. " + TAB", hl.dsp.focus({ workspace = "m+1" }))
hl.bind(mainMod .. " + SHIFT + TAB", hl.dsp.focus({ workspace = "m-1" }))

hl.bind(mainMod .. " + LEFT", hl.dsp.focus({ direction = "left" }))
hl.bind(mainMod .. " + RIGHT", hl.dsp.focus({ direction = "right" }))
hl.bind(mainMod .. " + UP", hl.dsp.focus({ direction = "up" }))
hl.bind(mainMod .. " + DOWN", hl.dsp.focus({ direction = "down" }))

hl.bind(mainMod .. " + Z", hl.dsp.layout("focus previous"))
hl.bind(mainMod .. " + X", hl.dsp.layout("focus next"))

hl.bind(mainMod .. " + SHIFT + Z", hl.dsp.layout("move previous"))
hl.bind(mainMod .. " + SHIFT + X", hl.dsp.layout("move next"))

hl.bind(mainMod .. " + C", hl.dsp.layout("toggle dimension"))


-- hl.bind(mainMod .. " + LEFT", hl.dsp.exec_cmd([[hyprctl dispatch "movefocus l" && hyprctl eval 'hl.dispatch(hl.dsp.layout("follow"))']]))
-- hl.bind(mainMod .. " + RIGHT", hl.dsp.exec_cmd([[hyprctl dispatch "movefocus r" && hyprctl eval 'hl.dispatch(hl.dsp.layout("follow"))']]))
-- hl.bind(mainMod .. " + UP", hl.dsp.exec_cmd([[hyprctl dispatch "movefocus u" && hyprctl eval 'hl.dispatch(hl.dsp.layout("follow"))']]))
-- hl.bind(mainMod .. " + DOWN", hl.dsp.exec_cmd([[hyprctl dispatch "movefocus d" && hyprctl eval 'hl.dispatch(hl.dsp.layout("follow"))']]))

hl.bind("ALT + TAB", hl.dsp.exec_cmd("hyprctl dispatch cyclenext"))

--hl.bind(mainMod .. " + SHIFT + RIGHT", hl.dsp.window.resize({ x = 30, y = 0 }))
--hl.bind(mainMod .. " + SHIFT + LEFT", hl.dsp.window.resize({ x = -30, y = 0 }))
--hl.bind(mainMod .. " + SHIFT + UP", hl.dsp.window.resize({ x = 0, y = -30 }))
--hl.bind(mainMod .. " + SHIFT + DOWN", hl.dsp.window.resize({ x = 0, y = 30 }))

local moveActiveWindow = [[
grep -q "true" <<< "$(hyprctl activewindow -j | jq -r .floating)" \
&& hyprctl dispatch moveactive
]]

hl.bind(mainMod .. " + SHIFT + CONTROL + LEFT", hl.dsp.exec_cmd(moveActiveWindow .. " -30 0 || hyprctl dispatch movewindow l"))
hl.bind(mainMod .. " + SHIFT + CONTROL + RIGHT", hl.dsp.exec_cmd(moveActiveWindow .. " 30 0 || hyprctl dispatch movewindow r"))
hl.bind(mainMod .. " + SHIFT + CONTROL + UP", hl.dsp.exec_cmd(moveActiveWindow .. " 0 -30 || hyprctl dispatch movewindow u"))
hl.bind(mainMod .. " + SHIFT + CONTROL + DOWN", hl.dsp.exec_cmd(moveActiveWindow .. " 0 30 || hyprctl dispatch movewindow d"))


hl.bind(mainMod .. " + mouse:272", hl.dsp.window.drag(), { mouse = true })
hl.bind(mainMod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true })

--hl.bind(mainMod .. " + Z", hl.dsp.exec_cmd("hyprctl dispatch movewindow"))
--hl.bind(mainMod .. " + X", hl.dsp.exec_cmd("hyprctl dispatch resizewindow"))

-- Screen Capture

-- Region screenshot
hl.bind("PRINT", hl.dsp.exec_cmd([[bash -lc 'mkdir -p "$HOME/Pictures"; grim -g "$(slurp)" - | satty --filename - --output-filename "$HOME/Pictures/Screenshot-$(date "+%Y%m%d-%H%M%S").png"']]))
-- Active window screenshot
hl.bind("SHIFT + PRINT", hl.dsp.exec_cmd([[bash -lc 'mkdir -p "$HOME/Pictures"; geom="$(hyprctl activewindow -j | jq -r '"'"'"\(.at[0]),\(.at[1]) \(.size[0])x\(.size[1])"'"'"')"; grim -g "$geom" - | satty --filename - --output-filename "$HOME/Pictures/Screenshot-$(date "+%Y%m%d-%H%M%S").png"']]))
-- Fullscreen screenshot
hl.bind("CTRL + PRINT", hl.dsp.exec_cmd([[bash -lc 'mkdir -p "$HOME/Pictures"; grim - | satty --filename - --output-filename "$HOME/Pictures/Screenshot-$(date "+%Y%m%d-%H%M%S").png"']]))

-- Layouts

hl.bind(mainMod .. " + Y", hl.dsp.exec_cmd([[hyprctl eval 'hl.config({ general = { layout = "scrolling" } })']]))
hl.bind(mainMod .. " + U", hl.dsp.exec_cmd([[hyprctl eval 'hl.config({ general = { layout = "lua:fit-scroller" } })']]))

hl.bind(mainMod .. " + Backslash", hl.dsp.layout("toggle_expand"))
hl.bind(mainMod .. " + BRACKETRIGHT", hl.dsp.layout("next"))
hl.bind(mainMod .. " + BRACKETLEFT", hl.dsp.layout("prev"))

-- Workspaces

hl.bind(mainMod .. " + S", hl.dsp.workspace.toggle_special(""))
hl.bind(mainMod .. " + SHIFT + S", hl.dsp.window.move({ workspace = "special" }))

hl.bind(mainMod .. " + A", hl.dsp.workspace.toggle_special("global"))
hl.bind(mainMod .. " + SHIFT + A", hl.dsp.window.move({ workspace = "special:global" }))

for i = 1, 10 do
    local key = i % 10

    hl.bind(mainMod .. " + " .. key, hl.dsp.focus({ workspace = i }))
    hl.bind(mainMod .. " + SHIFT + " .. key, hl.dsp.window.move({ workspace = i }))
end

hl.bind(mainMod .. " + CONTROL + RIGHT", hl.dsp.focus({ workspace = "r+1" }))
hl.bind(mainMod .. " + CONTROL + LEFT", hl.dsp.focus({ workspace = "r-1" }))
hl.bind(mainMod .. " + CONTROL + DOWN", hl.dsp.focus({ workspace = "empty" }))

hl.bind(mainMod .. " + mouse_down", hl.dsp.focus({ workspace = "e+1" }))
hl.bind(mainMod .. " + mouse_up", hl.dsp.focus({ workspace = "e-1" }))

hl.bind(mainMod .. " + CONTROL + ALT + RIGHT", hl.dsp.window.move({ workspace = "r+1" }))
hl.bind(mainMod .. " + CONTROL + ALT + LEFT", hl.dsp.window.move({ workspace = "r-1" }))

-- Hardware Controls

hl.bind("XF86AudioPlay", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioNext", hl.dsp.exec_cmd("playerctl next"), { locked = true })
hl.bind("XF86AudioPrev", hl.dsp.exec_cmd("playerctl previous"), { locked = true })

hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%+; quickshell ipc call osd volume"), { locked = true, repeating = true })
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-; quickshell ipc call osd volume"), { locked = true, repeating = true })
hl.bind("XF86AudioMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle; quickshell ipc call osd volume"), { locked = true, repeating = true })

hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd("brightnessctl set +5%; quickshell ipc call osd brightness"), { locked = true, repeating = true })
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd("brightnessctl set 5%-; quickshell ipc call osd brightness"), { locked = true, repeating = true })

-- Other

hl.bind(mainMod .. " + PERIOD", hl.dsp.exec_cmd("smile"))
