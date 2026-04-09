#!/usr/bin/env bash
# Convenience wrapper: start the Lumen.AI Streamlit app.
# Ollama is treated as an external dependency — start it separately with `ollama serve`.
exec "$(dirname "${BASH_SOURCE[0]}")/lumen.sh" start
