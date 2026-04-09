#!/usr/bin/env bash
# Convenience wrapper: stop the Lumen.AI Streamlit app.
# Ollama is treated as an external dependency and is not touched.
exec "$(dirname "${BASH_SOURCE[0]}")/lumen.sh" stop
