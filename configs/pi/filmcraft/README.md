# FilmCraft + Pi

`install_filmcraft_ai.sh` is called by `configs/install_configs.sh`. It installs:

- `~/.local/bin/filmcraft-ai [project.fcproj]` and its `filmcraft-ai-session` helper;
- `~/.local/share/applications/filmcraft-ai.desktop` as the default for `application/x-filmcraft` (`.fcproj`), without changing video/audio defaults;
- the user FilmCraft MIME override needed by Thunar/GIO to recognize a `.fcproj` as a FilmCraft project instead of generic JSON;
- the FilmCraft skill under `~/.agents/skills/filmcraft/`;
- a **disabled** `filmcraft_live` server in `~/.pi/agent/mcp.json`, enabled only by the dedicated Pi working directory `~/.local/share/filmcraft-ai/.pi/mcp.json`. PhotoCraft is disabled within that directory, and unaffected elsewhere.

## Usage

Double-click a `.fcproj` in Thunar, or run `filmcraft-ai '/path with spaces/project.fcproj'`. The launcher refuses a missing project, an already-running FilmCraft process or an occupied control port; close a normal FilmCraft window before launching assisted mode. The native FilmCraft desktop entry remains available via **Open With**. It starts FilmCraft on `127.0.0.1:9876` and opens Pi in Kitty. On first use, Pi asks you to trust the dedicated directory: review `~/.local/share/filmcraft-ai/.pi/mcp.json`, then approve if it matches this setup. Project trust is not a filesystem sandbox.

### Conversation per project

On the first assisted opening of a project, the launcher stores its Pi session ID in a private hidden sidecar beside the project: `.<project.fcproj>.pi-session` (mode 0600). On later openings it resumes exactly that session with `pi --session-id`, without sending the initial welcome prompt again. Move this sidecar together with the `.fcproj` and its media to retain the conversation after moving the folder; the actual history stays in `~/.pi/agent/sessions/`, so it will not transfer to another computer unless those Pi sessions are transferred too. A copy of the project *with* the sidecar deliberately shares the conversation; to give a copied project an independent session, replace its sidecar with a new `filmcraft-<UUID>` ID (for example `printf 'filmcraft-%s\n' "$(uuidgen | tr '[:upper:]' '[:lower:]')" > '.project.fcproj.pi-session'`). `/new` inside Pi does not change the sidecar. When adopting a project opened by the earlier launcher, the helper associates the **oldest** existing conversation whose initial prompt names that project; later duplicates remain accessible through Pi's `/resume`.

FilmCraft's TCP control channel **has no authentication**. It listens only on localhost and remains active until that FilmCraft window closes. Do not expose or tunnel port 9876. Pi itself has your full user permissions; the skill asks before edits but does not enforce a security boundary. To stop control, close FilmCraft. A normal FilmCraft launch has no control channel.

To check associations: `gio mime application/x-filmcraft`, `gio info -a standard::content-type project.fcproj`. `xdg-mime query filetype project.fcproj` may report `application/json` due to a separate detector; Thunar uses GIO. If Thunar still caches an older association, restart Thunar after saving open file operations.

The live connection requires a graphical session. From a trusted dedicated Pi session, `/mcp` should show `filmcraft_live` connected; outside this working directory it remains disabled. Inspection tools: `project_inspect`, `sequence_inspect`, `ui_inspect`, `ui_elements`, `ui_screenshot`. The integration does not open the project in a second headless editor.
