#!/bin/sh
set -eu

export OLLAMA_HOST=0.0.0.0:11434
ollama serve &
ollama_pid=$!

shutdown() {
    kill "$ollama_pid" 2>/dev/null || true
    wait "$ollama_pid" 2>/dev/null || true
}
trap shutdown EXIT INT TERM

export OLLAMA_HOST=127.0.0.1:11434
until ollama list >/dev/null 2>&1; do
    if ! kill -0 "$ollama_pid" 2>/dev/null; then
        wait "$ollama_pid"
        exit 1
    fi
    sleep 2
done

ollama pull "${OLLAMA_MODEL:-gemma2:2b}"
ollama pull "${OLLAMA_EMBED_MODEL:-nomic-embed-text}"

wait "$ollama_pid"
