# Scaling XWayland : Steam et ArtCraft uniquement

`install_app_scaling.sh` est appelé par `configs/install_configs.sh` après l'installation des paquets. Il conserve `xwayland.force_zero_scaling = true` (pas de mise à l'échelle floue par Hyprland) et crée des lanceurs par application dans `~/.local/bin/` :

- 13 applications ArtCraft : `WINIT_X11_SCALE_FACTOR=1.5` uniquement pour Winit sous X11/XWayland. Leur rendu Wayland n'est pas affecté.
- Steam : `STEAM_FORCE_DESKTOPUI_SCALING=1.5` pour **l'interface Steam** ; aucune variable GDK, Qt ou Winit n'est imposée aux jeux.

Les entrées `.desktop` utilisateur sont régénérées depuis les entrées officielles à chaque installation : commandes redirigées vers les lanceurs, noms, associations MIME et actions du menu Steam conservés. Les entrées `filmcraft-ai.desktop` et `photocraft-ai.desktop` continuent de lancer leurs commandes par le `PATH`, où `~/.local/bin` précède `/usr/bin`. Les commandes lancées directement dans un terminal passent aussi par ces lanceurs, tant que `~/.local/bin` est dans le `PATH`. Un appel explicite à `/usr/bin/<app>` les contourne.

L'installateur refuse d'écraser un lanceur ou une entrée `.desktop` utilisateur qu'il ne gère pas. Pour tester sans modifier la machine : `bash configs/app_scaling/test_app_scaling.sh`. Quitter puis relancer une application déjà ouverte pour observer le changement ; le résultat visuel de Steam et des autres applications ArtCraft doit encore être confirmé dans leurs fenêtres.
