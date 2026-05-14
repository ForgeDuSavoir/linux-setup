### TODO
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
- Fix clipboard plugins (install cliphist)
- Fix desktop toolkit plugin
- Everything is too big (content does not fit in split screen)



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

## linux-setup repo
### To do
- commit push

### Thing's that are not good yet
#### Mousepad
- By default, text files open with Micro instead of Mousepad
- Mousepad has no colored text for .md
#### Noctalia
- Can't pick a wallpaper
- Theme not applied -> maybe add noctalia-colors.conf from hyprland.conf
- Noctalia plugins don't have their settings
- Personnal themes not downloaded
- Keybinds plugin is not working
- Clipboard history plugin is not working
#### Thunar
- Can't click in path to jump to folder
- Can't "expand/collapse" folders in lsit view
#### Other
- Volume and brightness keys
- "About Xfce" app in launcher ?? -> I think it s because my login screen is Xfce
- Kwallet opens when openning brave or other apps
- KDENLIVE PROJECT !!!
