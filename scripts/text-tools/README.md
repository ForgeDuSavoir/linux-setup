# Text tools

## Dictation output

`dictation-stop.sh` removes leading whitespace from successful Whisper output,
including its usual initial space. Existing word spacing, paragraphs and subsequent
indentation remain unchanged; the existing ellipsis-line filter and shell trailing-
newline behavior are retained. Failure still retains recorded audio.

Targeted deployment (no recorder/model/typing/desktop action):

```sh
bash scripts/text-tools/install_text_tools.sh --dictation-stop-only
python3 scripts/text-tools/test_dictation_output.py
```

The installer replaces scripts atomically and refuses symlinked final targets.
Normal installation without arguments still deploys all five text tools. The
private test exercises the actual stop script on nine whitespace/format cases,
fake recorder signals, fake Whisper/notifications, error/audio retention and a
scoped install preserving an unrelated personal script. No microphone, real model,
actual text injection, private audio or personal notification bus is used.

Live stop-only update verified against the source; other installed text tools
were unchanged. Prior script backup:
`~/.local/state/linux-setup/text-tools-upgrades/20261120T230336Z-x3g2pr9n/dictation-stop`.
