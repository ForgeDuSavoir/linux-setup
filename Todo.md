### TODO
- tester l'icone des webapp firefox sous hyprland
- concatener la creation de webapp brave
- Script d installation de webapp avec brave : 
    - Syncthing
    - FreshRSS
    - YouTube wherlicq
    - YouTube qmk
    - YouTube FDS
    - Gmail perso
    - Gmail pro
    - Google Agenda perso
    - Google Agenda pro



### Take a screenshot
``` bash
grim -g "$(slurp)" - | satty --filename - --copy-command wl-copy
```


### Webcam virtuel
``` bash
sudo modprobe v4l2loopback devices=1 video_nr=10 card_label="AndroidCam"
```

``` bash
scrcpy \
--video-source=camera \
--camera-facing=back \
--no-audio
```

### Issues to fix
#### Mousepad
- By default, text files open with Micro instead of Mousepad
- Mousepad has no colored text for .md
#### Noctalia
- Personnal themes not downloaded
- Theme not applied -> maybe add noctalia-colors.conf from hyprland.conf
- Noctalia plugins don't have their settings
- Keybinds plugin is not working -> by changing plugins settings (see issue above)
- Clipboard history plugin is not working -> install cliphist ?
- Desktop toolkit plugin
#### Thunar
- Can't click in path to jump to folder
- Can't "expand/collapse" folders in list view
#### Other
- Volume and brightness keys
- "About Xfce" app in launcher ?? -> I think it s because my login screen is Xfce ?
- Kwallet opens when openning brave or other apps
- KDENLIVE PROJECT !!!
