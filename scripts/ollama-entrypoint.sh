#!/bin/sh
set -eu
ollama serve &
pid=$!
i=0
until ollama list >/dev/null 2>&1; do
  i=$((i+1))
  if [ "$i" -gt 60 ]; then
    echo "ollama failed to start"
    exit 1
  fi
  sleep 1
done
ollama pull "$OLLAMA_MODEL"
wait "$pid"
