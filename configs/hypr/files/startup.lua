-- See https://wiki.hypr.land/Configuring/Basics/Autostart/

-- Autostart necessary processes (like notifications daemons, status bars, etc.)

-- Environment variables

hl.env("XDG_CURRENT_DESKTOP", "Hyprland")
hl.env("XDG_SESSION_TYPE", "wayland")

-- QT

hl.env("QT_QPA_PLATFORMTHEME", "qt6ct")
hl.env("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
hl.env("QT_WAYLAND_DISABLE_WINDOWDECORATION", "1")

-- Electron

hl.env("ELECTRON_OZONE_PLATFORM_HINT", "wayland")

-- Startup applications

hl.on("hyprland.start", function () 
    hl.exec_cmd("quickshell")
    hl.exec_cmd("hypridle")
    hl.exec_cmd("hyprpaper")
    -- hl.exec_cmd("hyprpolkitagent")
end)
