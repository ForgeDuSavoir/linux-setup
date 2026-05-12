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
- test master script in Niri
