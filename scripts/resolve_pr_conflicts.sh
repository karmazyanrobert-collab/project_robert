#!/usr/bin/env bash
set -euo pipefail

TARGET_BRANCH="${1:-main}"
PR_BRANCH="${2:-codex/create-new-university-data-platform-demo}"

CONFLICT_FILES=(
  "DEMO_SCENARIO.md"
  "README.md"
  "dashboard/app.py"
  "src/data_quality.py"
  "src/semantic_layer.py"
  "tests/test_pipeline.py"
)

echo "Switching to PR branch: ${PR_BRANCH}"
git checkout "${PR_BRANCH}"

echo "Fetching target branch: origin/${TARGET_BRANCH}"
git fetch origin "${TARGET_BRANCH}"

echo "Merging origin/${TARGET_BRANCH}. Conflicts are expected for known demo files."
set +e
git merge "origin/${TARGET_BRANCH}"
MERGE_STATUS=$?
set -e

if [[ ${MERGE_STATUS} -ne 0 ]]; then
  echo "Keeping PR version (--ours) for known conflicting files."
  for file in "${CONFLICT_FILES[@]}"; do
    git checkout --ours "${file}"
    git add "${file}"
  done
fi

echo "Checking that merge markers are absent."
if grep -R -n -E '^(<<<<<<<|=======|>>>>>>>)' "${CONFLICT_FILES[@]}"; then
  echo "Merge markers are still present. Resolve them manually before committing." >&2
  exit 1
fi

git commit -m "Resolve PR conflicts keeping Russian demo version" || true

echo "Done. Push with: git push origin ${PR_BRANCH}"
