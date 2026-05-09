#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-}"
DRY_RUN="${2:-}"

if [[ -z "${VERSION}" ]]; then
  echo "Usage: npm run release:sync-publish -- <version> [--dry-run]" >&2
  exit 1
fi

if ! [[ "${VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+([+-][0-9A-Za-z.-]+)?$ ]]; then
  echo "Invalid version: ${VERSION}. Expected semver-like format (example: 0.6.1)." >&2
  exit 1
fi

if [[ -n "${DRY_RUN}" && "${DRY_RUN}" != "--dry-run" ]]; then
  echo "Unknown option: ${DRY_RUN}. Supported option: --dry-run" >&2
  exit 1
fi

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_cmd npm
require_cmd python3

cd "${ROOT_DIR}"

echo "Checking npm authentication..."
if ! NPM_USER="$(npm whoami 2>/dev/null)"; then
  cat >&2 <<'EOF'
npm authentication is missing for the current user.
Run:
  npm login --registry=https://registry.npmjs.org/
Then verify:
  npm whoami
EOF
  exit 1
fi
echo "npm authenticated as: ${NPM_USER}"

PACKAGE_NAME="$(node -p "require('./package.json').name")"
if npm view "${PACKAGE_NAME}" version >/dev/null 2>&1; then
  if ! npm owner ls "${PACKAGE_NAME}" 2>/dev/null | awk '{print $1}' | grep -Fxq "${NPM_USER}"; then
    cat >&2 <<EOF
npm user '${NPM_USER}' is not an owner of package '${PACKAGE_NAME}'.
Ask a current owner to grant publish rights:
  npm owner add ${NPM_USER} ${PACKAGE_NAME}
EOF
    exit 1
  fi
fi

echo "Bumping npm package version to ${VERSION}..."
npm version "${VERSION}" --no-git-tag-version --allow-same-version

echo "Syncing Python/FastAPI/MCP versions to ${VERSION}..."
python3 scripts/set_release_version.py "${VERSION}"

echo "Refreshing egg-info metadata..."
python3 setup.py egg_info >/dev/null

echo "Preparing isolated release environment..."
python3 -m venv .venv-release
source .venv-release/bin/activate
python -m pip install --upgrade pip build twine >/dev/null

echo "Building Python artifacts..."
rm -rf build
python -m build
twine check "dist/notemd_mcp-${VERSION}"*

if [[ "${DRY_RUN}" == "--dry-run" ]]; then
  echo "Dry-run mode: validating npm package bundle only..."
  npm pack --dry-run >/dev/null
  echo "Dry-run mode: skipping twine upload."
else
  echo "Publishing npm package..."
  npm publish

  echo "Publishing PyPI package..."
  twine upload "dist/notemd_mcp-${VERSION}"*
fi

echo "Release completed for version ${VERSION}."
