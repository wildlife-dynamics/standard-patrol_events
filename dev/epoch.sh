#!/bin/bash
# Usage: dev/epoch.sh <source dir>... -> a short fingerprint of those sources (commit,
# uncommitted changes and new files), used as WT_CACHE__EPOCH by `make run-dev`.
# The step cache pins steps to package versions, which editable installs can't move;
# this changes on any edit, so a cached result never outlives the code that made it.
set -e
for dir in "$@"; do
    git -C "$dir" rev-parse HEAD
    git -C "$dir" diff HEAD -- .
    git -C "$dir" ls-files --others --exclude-standard -z -- . | (cd "$dir" && xargs -0 cat 2>/dev/null || true)
done | shasum | cut -c1-16
