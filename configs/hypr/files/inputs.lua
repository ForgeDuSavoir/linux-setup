hl.config({ input = {
    kb_layout = "us",
    kb_variant = "intl",

    numlock_by_default = true,

    repeat_delay = 250,
    repeat_rate = 35,

    accel_profile = "flat",

    natural_scroll = true,

    special_fallthrough = true,
    mouse_refocus = false,
    follow_mouse = 2,

    touchpad = {
        natural_scroll = true,
        disable_while_typing = true,
        clickfinger_behavior = true,
        scroll_factor = 0.5,
    },
}})

hl.gesture({
    fingers = 3,
    direction = "horizontal",
    action = "workspace",
})

hl.gesture({
    fingers = 3,
    direction = "pinchin",
    action = "float",
    arg = "tile",
})

hl.gesture({
    fingers = 3,
    direction = "pinchout",
    action = "float",
    arg = "float",
})