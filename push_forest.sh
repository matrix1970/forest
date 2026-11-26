#!/usr/bin/env bash

# push_forest.sh
# Usage: ./push_forest.sh <site>
# Performs git add, commit, pull (rebase), and push (force-with-lease) for the forest repo.

set -euo pipefail

# Verify argument
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <site>"
  exit 1
fi

SITE="$1"
# Determine repository root (assumes script is within the repo)
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "${REPO_ROOT}"

# Stage all changes
git add .

# Create commit message with site and timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
COMMIT_MSG="Update ${SITE} report ${TIMESTAMP}"

git commit -m "${COMMIT_MSG}" || echo "No changes to commit."

# Pull latest changes with rebase to avoid conflicts
git pull --rebase origin main

# Push with force‑with‑lease to ensure safe overwrite
git push --force-with-lease origin main
