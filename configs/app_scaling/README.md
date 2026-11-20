# Scaling par application : Steam, ArtCraft et VLC

`install_app_scaling.sh` est appelé par `configs/install_configs.sh` après l'installation des paquets. Il conserve `xwayland.force_zero_scaling = true` (pas de mise à l'échelle floue par Hyprland) et crée des lanceurs par application dans `~/.local/bin/` :

- 13 applications ArtCraft : `WINIT_X11_SCALE_FACTOR=1.5` uniquement pour Winit sous X11/XWayland. Leur rendu Wayland n'est pas affecté.
- Steam : `STEAM_FORCE_DESKTOPUI_SCALING=1.5` pour **l'interface Steam** ; aucune variable GDK, Qt ou Winit n'est imposée aux jeux.
- VLC, si installé : interface Qt 5/XWayland conservée (`QT_QPA_PLATFORM=xcb`), `QT_SCALE_FACTOR=1.5`, `QT_AUTO_SCREEN_SCALE_FACTOR=0`, `QT_SCREEN_SCALE_FACTORS=1`. Le facteur par écran unitaire remplace le DPI automatique et évite de multiplier deux facteurs de scaling. Ces variables sont limitées au processus VLC et à ses enfants, pas aux autres applications.

Les entrées `.desktop` utilisateur sont régénérées depuis les entrées officielles à chaque installation : commandes redirigées vers les lanceurs, noms, associations MIME et actions du menu Steam conservés. Les entrées `filmcraft-ai.desktop` et `photocraft-ai.desktop` continuent de lancer leurs commandes par le `PATH`, où `~/.local/bin` précède `/usr/bin`. Les commandes lancées directement dans un terminal passent aussi par ces lanceurs, tant que `~/.local/bin` est dans le `PATH`. Un appel explicite à `/usr/bin/<app>` les contourne.

## VLC : diagnostic et installation ciblée

Vérification sur la fenêtre réelle le 2026-11-20, sans lire son titre ni les médias :
`xwayland: true`, plugin Qt `libqxcb.so`, Qt 5, facteur écran Hyprland 1,5 et
`force_zero_scaling=true`. VLC héritait de `QT_AUTO_SCREEN_SCALE_FACTOR=1` sans
facteur explicite et son entrée système appelait directement `/usr/bin/vlc`.

```sh
bash configs/app_scaling/install_app_scaling.sh --vlc-only
```

Ce mode installe uniquement le lien `~/.local/bin/vlc`, met à jour le lanceur
commun (les branches Steam/ArtCraft restent inchangées), et crée la surcharge
`~/.local/share/applications/vlc.desktop`. Noms, icônes, `--started-from-file`, `%U`,
associations MIME et autres champs de l’entrée officielle sont conservés.
Les autres entrées `.desktop` ne sont pas réécrites. L’installation normale inclut
VLC si son exécutable est présent, sans le rendre obligatoire pour Steam/ArtCraft.

Déploiement ciblé effectué ; sauvegarde privée du lanceur précédent sous
`~/.local/state/linux-setup/app-scaling-upgrades/20261120T142936Z-RmafakqO`.
Le lanceur commun est remplacé atomiquement, pour ne pas tronquer un script
potentiellement en cours de lecture. Ancêtres de destination symlinkés et
surcharges VLC personnelles non gérées sont refusés.

**Quitter complètement VLC puis le rouvrir**, y compris une éventuelle instance
en zone de notification : les nouvelles variables ne changent pas un processus
déjà lancé, et l’ouverture d’un autre fichier peut simplement réutiliser celui-ci.
Aucune fenêtre VLC n’a été fermée/relancée automatiquement. Ses réglages, listes
de lecture et historiques n’ont pas été lus/modifiés. Pas de reload Hyprland.
Le facteur est fixe à 1,5 pour l’écran actuel, pas une adaptation multi-écran.
Pour un essai Wayland explicite, utiliser le binaire système afin de contourner
le lanceur qui conserve volontairement le backend XWayland confirmé.

Tests : faux exécutables et HOME/état/cache temporaires, transmission littérale
avec espaces/guillemets/métacaractères, remplacement des facteurs hérités, MIME,
installation ciblée/idempotence et refus d’une surcharge personnelle. Régressions
Steam/ArtCraft réussies. Une sonde **Qt 5 réelle hors écran**, avec les attributs
high-DPI utilisés par VLC, mesure `devicePixelRatio=1.5` ; aucune application VLC
ni connexion à l’affichage réel n’est utilisée par ce test. Validation visuelle
sur VLC après relance encore à faire. L’index Git et les entrées précédentes ont
été vérifiés inchangés lors de l’installation.

L'installateur refuse d'écraser un lanceur ou une entrée `.desktop` utilisateur qu'il ne gère pas. Pour tester sans modifier la machine : `bash configs/app_scaling/test_app_scaling.sh`. Quitter puis relancer une application déjà ouverte pour observer le changement ; le résultat visuel de Steam et des autres applications ArtCraft doit encore être confirmé dans leurs fenêtres.
