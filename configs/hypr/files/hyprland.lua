-- This is the "Forge du Savoir" Hyprland Lua config file, 
-- created from the example file from the official Hyprland wiki.
-- Refer to the wiki for more information.
-- https://wiki.hypr.land/Configuring/Start/


------------------
---- MONITORS ----
------------------

require("monitors")

-------------------
---- AUTOSTART ----
-------------------

require("startup")


-----------------------
----- PERMISSIONS -----
-----------------------

-- See https://wiki.hypr.land/Configuring/Advanced-and-Cool/Permissions/
-- Please note permission changes here require a Hyprland restart and are not applied on-the-fly
-- for security reasons

-- hl.config({
--   ecosystem = {
--     enforce_permissions = true,
--   },
-- })

-- hl.permission("/usr/(bin|local/bin)/grim", "screencopy", "allow")
-- hl.permission("/usr/(lib|libexec|lib64)/xdg-desktop-portal-hyprland", "screencopy", "allow")
-- hl.permission("/usr/(bin|local/bin)/hyprpm", "plugin", "allow")


-----------------------
---- LOOK AND FEEL ----
-----------------------

dofile(os.getenv("HOME") .. "/.config/hypr/layouts/fit-scroller/init.lua")
require("visuals")


----------------
----  MISC  ----
----------------

hl.config({
    misc = {
        force_default_wallpaper = 0,    -- Set to 0 or 1 to disable the anime mascot wallpapers
        disable_hyprland_logo   = true, -- If true disables the random hyprland logo / anime girl background. :(
    },
})

---------------
---- INPUT ----
---------------

require("inputs")

---------------------
---- KEYBINDINGS ----
---------------------

require("keybinds")

--------------------------------
---- WINDOWS AND WORKSPACES ----
--------------------------------

require("windowrules")
