#!/usr/bin/env bash
set -e

echo "=== Installing Hermes Antigravity Plugin ==="

PLUGIN_DIR="${HOME}/.hermes/plugins/model-providers/antigravity"
mkdir -p "${PLUGIN_DIR}"

BASE_URL="https://raw.githubusercontent.com/melihaltin/hermes-antigravity/main"
FILES=("plugin.yaml" "__init__.py" "adapter.py" "login.py")

for file in "${FILES[@]}"; do
    echo "Downloading ${file}..."
    curl -fsSL "${BASE_URL}/${file}" -o "${PLUGIN_DIR}/${file}"
done

echo -e "\033[0;32mPlugin downloaded to ${PLUGIN_DIR}\033[0m"

# Find python
PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
fi

if [ -n "${PYTHON_BIN}" ]; then
    echo "Starting Google login with ${PYTHON_BIN}..."
    "${PYTHON_BIN}" "${PLUGIN_DIR}/login.py"
else
    echo "Please run: python3 ${PLUGIN_DIR}/login.py"
fi

if command -v hermes >/dev/null 2>&1; then
    hermes plugins enable antigravity || true
fi

echo -e "\n\033[0;32mInstallation complete! Run:\033[0m"
echo "  hermes model antigravity/gemini-3.8-flash"
echo "  or"
echo "  hermes model antigravity/claude-sonnet-4-6"
