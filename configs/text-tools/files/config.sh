# Shared configuration for text manipulation, dictation and LLM transformations.

OLLAMA_MODEL="qwen3.5:4b"

WHISPER_MODEL="${HOME}/.local/share/whisper.cpp/ggml-small.bin"
WHISPER_LANGUAGE="fr"

TEXT_TOOLS_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp}/text-tools"
