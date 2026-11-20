# Contextual Obsidian

`bash configs/obsidian/configure_obsidian.sh` installs native `session-obsidian`
and a same-ID local `obsidian.desktop` override. Menu launch without arguments
opens the registered vault at the confirmed session project root, or Agora.
Explicit URI/file requests bypass routing. No CLI activation or vault registration.

Requires standard Arch `/usr/bin/obsidian`, the existing downstream session tools,
explicit `agora_root` configuration and an already registered Agora vault.
Normal `configs/install_configs.sh` runs this after Session Manager configuration.

[Contract, safety, private tests, deployment and explicit return](../../runtime/session-obsidian.md).
No real Obsidian window is launched during installation or automated validation.
